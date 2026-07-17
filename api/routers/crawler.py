# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/routers/crawler.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..schemas import CrawlerStartRequest, CrawlerStatusResponse, ClearHistoryRequest
from ..services import crawler_manager
from ..services import run_history

router = APIRouter(prefix="/crawler", tags=["crawler"])

# 项目根目录 / data 目录（清除数据文件用）
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# 平台短名 → 存储目录名 / ORM 表名前缀 映射
PLATFORM_MAP = {
    "dy": ("douyin", "douyin"),
    "xhs": ("xhs", "xhs"),
    "ks": ("kuaishou", "kuaishou"),
    "bili": ("bilibili", "bilibili"),
    "wb": ("weibo", "weibo"),
    "tieba": ("tieba", "tieba"),
    "zhihu": ("zhihu", "zhihu"),
}


@router.post("/start")
async def start_crawler(request: CrawlerStartRequest):
    """Start crawler task"""
    success = await crawler_manager.start(request)
    if not success:
        # Handle concurrent/duplicate requests: if process is already running, return 400 instead of 500
        if crawler_manager.process and crawler_manager.process.poll() is None:
            raise HTTPException(status_code=400, detail="Crawler is already running")
        raise HTTPException(status_code=500, detail="Failed to start crawler")

    return {"status": "ok", "message": "Crawler started successfully"}


@router.post("/stop")
async def stop_crawler():
    """Stop crawler task"""
    success = await crawler_manager.stop()
    if not success:
        # Handle concurrent/duplicate requests: if process already exited/doesn't exist, return 400 instead of 500
        if not crawler_manager.process or crawler_manager.process.poll() is not None:
            raise HTTPException(status_code=400, detail="No crawler is running")
        raise HTTPException(status_code=500, detail="Failed to stop crawler")

    return {"status": "ok", "message": "Crawler stopped successfully"}


@router.get("/status", response_model=CrawlerStatusResponse)
async def get_crawler_status():
    """Get crawler status"""
    return crawler_manager.get_status()


@router.get("/logs")
async def get_logs(limit: int = 100):
    """Get recent logs"""
    logs = crawler_manager.logs[-limit:] if limit > 0 else crawler_manager.logs
    return {"logs": [log.model_dump() for log in logs]}


@router.get("/history")
async def get_run_history(limit: int = 50):
    """获取爬取运行历史，最新在前，上限 limit"""
    runs = run_history.get_recent_runs(limit=limit)
    return {"runs": runs}


@router.delete("/history")
async def clear_history(request: ClearHistoryRequest):
    """
    清除历史数据。可分别清：数据文件 / DB 表 / 运行清单。

    爬取进行中拒绝清除（409），避免破坏追加模式文件。
    """
    # 爬取中拒绝
    if crawler_manager.status == "running":
        raise HTTPException(status_code=409, detail="Cannot clear history while crawler is running")

    result = {"deleted_files": 0, "truncated_tables": [], "cleared_runs": False}

    # 1. 清数据文件
    if request.clear_files:
        result["deleted_files"] = _delete_data_files(request.platform)

    # 2. 清 DB 表
    if request.clear_db:
        result["truncated_tables"] = _truncate_db_tables(request.platform)

    # 3. 清运行清单
    if request.clear_runs:
        run_history.clear_runs()
        result["cleared_runs"] = True

    return result


def _delete_data_files(platform: str | None) -> int:
    """删除 data/ 下的数据文件，可选按平台过滤。跳过 .run_history.json 清单本身。"""
    if not DATA_DIR.exists():
        return 0
    supported_extensions = {".json", ".jsonl", ".csv", ".xlsx", ".xls"}
    # 平台短名 → 存储目录名
    platform_dir = PLATFORM_MAP.get(platform, ("", ""))[0] if platform else ""
    deleted = 0
    for root, _dirs, filenames in os.walk(DATA_DIR):
        root_path = Path(root)
        try:
            rel = str(root_path.relative_to(DATA_DIR))
        except ValueError:
            continue
        # 平台过滤：目录路径需包含平台存储名
        if platform_dir and platform_dir not in rel.lower():
            continue
        for filename in filenames:
            if filename == ".run_history.json":
                continue  # 跳过运行清单本身
            if filename == ".bgm_tags.json":
                continue  # 跳过 BGM 场景标签标注文件
            file_path = root_path / filename
            if file_path.suffix.lower() not in supported_extensions:
                continue
            try:
                file_path.unlink()
                deleted += 1
            except Exception:
                continue
    return deleted


def _truncate_db_tables(platform: str | None) -> list[str]:
    """truncate ORM 表，可选按平台过滤。文件存储模式（无 engine）返回空列表。"""
    try:
        from database.db_session import get_async_engine
        from database import models
        import asyncio
        from sqlalchemy import text
    except Exception:
        return []

    engine = get_async_engine()
    if engine is None:
        # 文件存储模式（jsonl/json/csv/excel），无 DB，跳过
        return []

    # 收集所有 ORM 表名
    all_tables = [t.name for t in models.Base.metadata.tables.values()]
    # 平台过滤：表名前缀匹配
    if platform:
        prefix = PLATFORM_MAP.get(platform, ("", ""))[1]
        if not prefix:
            return []
        target_tables = [t for t in all_tables if t.startswith(prefix)]
    else:
        target_tables = all_tables

    truncated = []

    async def _do_truncate():
        async with engine.begin() as conn:
            for table_name in target_tables:
                # 表名来自代码常量，无注入风险，但仍用 text 绑定
                await conn.execute(text(f'DELETE FROM "{table_name}"'))
                truncated.append(table_name)

    try:
        asyncio.get_event_loop().run_until_complete(_do_truncate())
    except RuntimeError:
        # 已有事件循环时（FastAPI 上下文），用新线程跑
        import threading
        result_holder = {"err": None}

        def _run():
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(_do_truncate())
                new_loop.close()
            except Exception as e:
                result_holder["err"] = e

        t = threading.Thread(target=_run)
        t.start()
        t.join()
        if result_holder["err"]:
            raise result_holder["err"]

    return truncated
