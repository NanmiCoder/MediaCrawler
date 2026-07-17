# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/services/run_history.py
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

"""
爬取运行历史清单（run history manifest）。

以 JSON 文件持久化每次爬取运行的元数据（run_id / 平台 / 类型 / 起止时间 /
状态 / 记录数等）。爬虫以子进程方式启动，与 API 进程不共享内存，只有 API 的
CrawlerManager 能安全写本清单（start 时 append，_read_output 检测退出时 finalize）。
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 清单文件路径：<repo>/data/.run_history.json
RUN_HISTORY_PATH = Path(__file__).parent.parent.parent / "data" / ".run_history.json"


def _ensure_dir() -> None:
    """确保 data 目录存在。"""
    RUN_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_runs() -> List[dict]:
    """读取并解析运行清单。文件缺失或损坏时返回空列表。"""
    if not RUN_HISTORY_PATH.exists():
        return []
    try:
        with open(RUN_HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def save_runs(runs: List[dict]) -> None:
    """原子写入运行清单：先写临时文件再 os.replace，避免写一半被读到。"""
    _ensure_dir()
    tmp_path = RUN_HISTORY_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(runs, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, RUN_HISTORY_PATH)


def append_run(run: dict) -> None:
    """追加一条运行记录（load → append → save）。仅 API 进程调用，无需加锁。"""
    runs = load_runs()
    runs.append(run)
    save_runs(runs)


def update_run(run_id: str, patch: dict) -> None:
    """按 run_id 找到记录并合并 patch 字段（load → merge → save）。找不到则忽略。"""
    runs = load_runs()
    updated = False
    for run in runs:
        if run.get("run_id") == run_id:
            run.update(patch)
            updated = True
            break
    if updated:
        save_runs(runs)


def clear_runs() -> None:
    """清空运行清单（覆盖为空列表）。"""
    save_runs([])


def generate_run_id() -> str:
    """生成运行 id：run_<时间戳>_<短uuid>。"""
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    short = uuid.uuid4().hex[:6]
    return f"run_{ts}_{short}"


def recover_orphan_runs() -> int:
    """
    孤儿恢复：把仍处于 running 状态的记录标记为 failed。

    API 进程崩溃/重启后，之前 running 的记录永远不会被 finalize。启动时调用本函数
    将它们标记为 failed，避免历史里残留永远 running 的记录。返回恢复的条数。
    """
    runs = load_runs()
    recovered = 0
    for run in runs:
        if run.get("status") == "running":
            run["status"] = "failed"
            run["error_message"] = "orphaned run (API restarted before completion)"
            run["ended_at"] = run.get("ended_at") or datetime.now().isoformat()
            recovered += 1
    if recovered:
        save_runs(runs)
    return recovered


def get_recent_runs(limit: Optional[int] = 50) -> List[dict]:
    """返回最近的运行记录，最新在前，上限 limit。"""
    runs = load_runs()
    runs.sort(key=lambda r: r.get("started_at", ""), reverse=True)
    if limit is not None:
        runs = runs[:limit]
    return runs
