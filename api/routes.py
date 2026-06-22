"""
douyin_scraper.api.routes — API 路由
======================================
v6 新增：FastAPI 路由层，对 DouyinScraper 模块的 HTTP 封装。

API 设计决策：
  1. 所有长时间操作返回 task_id，客户端轮询状态
  2. 每个任务独立 workspace，互不干扰
  3. 结果文件通过 /scrape/result/{task_id} 下载
  4. 错误响应包含 exit_code 分类（1=可重试, 2=不可重试, 3=致命）

我实际执行时踩过的坑：
  - HTTP handler 中直接运行采集 → 请求超时
  - 没有任务隔离 → 并发请求互相干扰
  - 错误只返回 500 → 客户端无法区分可重试和不可重试错误
  - 结果文件路径硬编码 → 部署后找不到文件
"""

import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Literal

from douyin_scraper import DouyinScraper, ScraperConfig
from douyin_scraper.exceptions import (
    ConfigError,
    FatalError,
    NonRetryableError,
    RetryableError,
    ScraperError,
)
from douyin_scraper.utils import (
    check_disk_space,
    check_port_in_use,
    check_command_exists,
    setup_ffmpeg,
)

from .tasks import TaskManager
from .utils import validate_path_in_workspace
from .ws import ws_manager

logger = logging.getLogger("douyin_scraper.api")

router = APIRouter(prefix="/scrape", tags=["scrape"])

# 全局任务管理器（由 main.py 注入）
_task_manager: Optional[TaskManager] = None


def set_task_manager(tm: TaskManager) -> None:
    global _task_manager
    _task_manager = tm


def get_task_manager() -> TaskManager:
    if _task_manager is None:
        raise RuntimeError("TaskManager 未初始化")
    return _task_manager


# ═══════════════════════════════════════════════════════════════
# 请求模型
# ═══════════════════════════════════════════════════════════════

class SearchRequest(BaseModel):
    """搜索采集请求"""
    keywords: List[str] = Field(..., description="搜索关键词列表")
    max_count: int = Field(20, description="每个关键词最大采集数", ge=1, le=200)
    project_dir: Optional[str] = Field(None, description="工作目录（默认自动创建）")

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("keywords 不能为空")
        if len(v) > 50:
            raise ValueError("keywords 最多 50 个")
        for kw in v:
            if len(kw) > 200:
                raise ValueError(f"关键词过长: {kw[:50]}...")
        return v


class CommentsRequest(BaseModel):
    """评论采集请求"""
    task_id: Optional[str] = Field(None, description="搜索任务 ID")
    video_ids: Optional[List[str]] = Field(None, description="直接指定视频 ID 列表")
    max_comments_per_video: int = Field(
        50, description="每个视频最多采集评论数", ge=1, le=5000
    )
    video_jsonl: Optional[str] = Field(None, description="视频 JSONL 路径")
    project_dir: Optional[str] = Field(None, description="工作目录")


class ScriptsRequest(BaseModel):
    """文案提取请求"""
    task_id: Optional[str] = Field(None, description="搜索任务 ID（读取其 script_sources 输出）")
    video_jsonl: Optional[str] = Field(None, description="视频 JSONL 路径")
    model: Literal["tiny", "base", "small", "medium", "large"] = Field(
        "small", description="Whisper 模型大小: tiny/base/small/medium/large"
    )
    project_dir: Optional[str] = Field(None, description="工作目录")


class MergeRequest(BaseModel):
    """合并数据请求"""
    search_task_id: Optional[str] = Field(None, description="搜索任务 ID（生成 content_asset）")
    comments_task_id: Optional[str] = Field(None, description="评论任务 ID（可选）")
    scripts_task_id: Optional[str] = Field(None, description="文案任务 ID（可选）")
    video_jsonl: Optional[str] = Field(None, description="视频 JSONL 路径")
    comments_jsonl: Optional[str] = Field(None, description="评论 JSONL 路径")
    scripts_jsonl: Optional[str] = Field(None, description="文案 JSONL 路径")
    output_csv: Optional[str] = Field(None, description="输出 CSV 路径")
    project_dir: Optional[str] = Field(None, description="工作目录")


class ResetRequest(BaseModel):
    """重置步骤请求"""
    step: str = Field(..., description="要重置的步骤名称")
    clear_dedupe: bool = Field(False, description="是否同时清除去重索引")
    project_dir: Optional[str] = Field(None, description="工作目录")

    @field_validator("step")
    @classmethod
    def validate_step(cls, v: str) -> str:
        valid_steps = {
            "clone_repo", "setup_env", "config_douyin",
            "run_search", "fetch_comments", "install_ffmpeg",
            "install_whisper", "run_extract", "merge_csv",
        }
        if v not in valid_steps:
            raise ValueError(
                f"无效步骤名: {v}，有效步骤: {', '.join(sorted(valid_steps))}"
            )
        return v


class RunAllRequest(BaseModel):
    """一键运行请求"""
    keywords: List[str] = Field(..., description="搜索关键词列表")
    max_count: int = Field(20, description="每个关键词最大采集数")
    steps: Optional[List[str]] = Field(None, description="指定步骤（默认全部）")
    project_dir: Optional[str] = Field(None, description="工作目录")


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def _make_scraper(project_dir: Optional[str], workspace: str) -> DouyinScraper:
    """
    创建 DouyinScraper 实例。

    ★ 我实际执行时：多个请求共享同一个 scraper 实例，
    状态互相覆盖 → 每个任务独立实例。★

    Docker 环境检测：如果 /app/main.py 存在（Docker 容器），
    使用 /app/ 作为 project_dir（MediaCrawler 项目根），
    workspace 作为数据输出目录。
    """
    if project_dir is None:
        # Docker 检测：/app/main.py 存在 → 容器环境
        if Path("/app/main.py").exists():
            project_dir = "/app/"
        else:
            project_dir = workspace

    # 每个任务使用独立的 state_dir，避免任务间状态污染
    # workspace 格式: /app/workspaces/<task_id> → state_dir = /app/workspaces/<task_id>/state
    ws_path = Path(workspace)
    task_id = ws_path.name  # 从 workspace 路径中提取 task_id
    state_dir_name = f"workspaces/{task_id}/state"

    config_dict: Dict[str, Any] = {
        "project_dir": project_dir,
        "state_dir_name": state_dir_name,
        "enable_cdp_mode": False,  # Docker 中不用 CDP，用 headless playwright
    }
    return DouyinScraper(config_dict)


def _error_response(e: Exception) -> HTTPException:
    """将异常转换为 HTTP 响应"""
    if isinstance(e, ScraperError):
        status_map = {1: 503, 2: 400, 3: 500}  # 可重试/不可重试/致命
        status_code = status_map.get(e.exit_code, 500)
        return HTTPException(
            status_code=status_code,
            detail={
                "error": str(e),
                "step": e.step,
                "exit_code": e.exit_code,
                "details": e.details,
            },
        )
    # 非 ScraperError：不暴露内部信息给 API 调用者
    logger.error("未预期异常: %s", e, exc_info=True)
    return HTTPException(
        status_code=500,
        detail={"error": "内部错误，请查看日志"},
    )


# ═══════════════════════════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════════════════════════

def _search_output_result(paths: Dict[str, Any], output: Path) -> Dict[str, Any]:
    return {
        "video_jsonl": paths.get("video_jsonl", str(output)),
        "video_csv": paths.get("video_csv", ""),
        "csv_stats": paths.get("csv_stats", {}),
    }



def _title_clean_result(paths: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title_clean_jsonl": paths.get("title_clean_jsonl", ""),
        "title_clean_csv": paths.get("title_clean_csv", ""),
        "title_clean_stats": paths.get("title_clean_stats", {}),
    }



def _script_source_result(paths: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "script_sources_jsonl": paths.get("script_sources_jsonl", ""),
        "script_sources_csv": paths.get("script_sources_csv", ""),
        "script_sources_stats": paths.get("script_sources_stats", {}),
    }



def _comments_output_result(
    paths: Dict[str, Any],
    output: Path,
) -> Dict[str, Any]:
    comments_raw_jsonl = paths.get("comments_raw_jsonl", str(output))
    return {
        "comments_jsonl": comments_raw_jsonl,
        "comments_raw_jsonl": comments_raw_jsonl,
        "comments_raw_csv": paths.get("comments_raw_csv", ""),
        "comments_clean_jsonl": paths.get("comments_clean_jsonl", ""),
        "comments_clean_csv": paths.get("comments_clean_csv", ""),
        "comments_stats": paths.get("comments_stats", {}),
        "clean_stats": paths.get("clean_stats", {}),
    }



def _script_output_result(
    paths: Dict[str, Any],
    output: Path,
) -> Dict[str, Any]:
    script_raw_jsonl = paths.get("script_raw_jsonl", str(output))
    return {
        "scripts_jsonl": script_raw_jsonl,
        "script_raw_jsonl": script_raw_jsonl,
        "script_raw_csv": paths.get("script_raw_csv", ""),
        "script_raw_stats": paths.get("script_raw_stats", {}),
        "script_clean_jsonl": paths.get("script_clean_jsonl", ""),
        "script_clean_csv": paths.get("script_clean_csv", ""),
        "script_clean_stats": paths.get("script_clean_stats", {}),
    }


# Search endpoint

@router.post("/search", summary="触发搜索采集")
async def search(req: SearchRequest) -> Dict[str, Any]:
    """
    触发搜索采集任务（异步执行）。

    返回 task_id，使用 GET /scrape/status/{task_id} 查询进度。
    """
    tm = get_task_manager()
    task = tm.create_task("search", params=req.model_dump())

    def _do_search() -> Dict[str, Any]:
        logger.info("API search request task_id=%s keywords=%r", task.task_id, req.keywords)
        scraper = _make_scraper(req.project_dir, task.workspace)
        output = scraper.search(keywords=req.keywords, max_count=req.max_count)
        paths = scraper.get_paths()
        result = _search_output_result(paths, output)
        result.update(_title_clean_result(paths))
        result.update(_script_source_result(paths))
        result["status"] = scraper.get_status()
        return result

    tm.submit(task, _do_search)
    return {"task_id": task.task_id, "status": "submitted", "type": "search"}


@router.post("/comments", summary="触发评论采集")
async def fetch_comments(req: CommentsRequest) -> Dict[str, Any]:
    """
    触发评论采集任务（异步执行）。
    需要先完成搜索采集，或提供 video_jsonl 路径。
    """
    tm = get_task_manager()
    task = tm.create_task("comments", params=req.model_dump())

    def _do_comments() -> Dict[str, Any]:
        scraper = _make_scraper(req.project_dir, task.workspace)
        source_task_id = req.task_id
        video_path: Optional[Path] = None
        if req.task_id:
            source_task = tm.get_task(req.task_id)
            if not source_task:
                raise NonRetryableError(
                    f"搜索任务不存在: {req.task_id}",
                    step="fetch_comments",
                )
            source_outputs = (Path(source_task.workspace) / "outputs").resolve()
            csv_path = source_outputs / "search_result.csv"
            jsonl_path = source_outputs / "search_result.jsonl"
            if csv_path.exists():
                video_path = validate_path_in_workspace(str(csv_path.resolve()), source_outputs)
            elif jsonl_path.exists():
                video_path = validate_path_in_workspace(str(jsonl_path.resolve()), source_outputs)
            else:
                raise NonRetryableError(
                    f"搜索任务无可用输出: {req.task_id}",
                    step="fetch_comments",
                )
        elif req.video_jsonl:
            video_path = validate_path_in_workspace(
                req.video_jsonl, Path(task.workspace)
            )
        output = scraper.fetch_comments(
            video_jsonl=video_path,
            video_ids=req.video_ids,
            source_task_id=source_task_id,
            max_comments_per_video=req.max_comments_per_video,
        )
        paths = scraper.get_paths()
        result = _comments_output_result(paths, output)
        result["status"] = scraper.get_status()
        return result

    tm.submit(task, _do_comments)
    return {"task_id": task.task_id, "status": "submitted", "type": "comments"}


@router.post("/scripts", summary="触发言案提取")
async def extract_scripts(req: ScriptsRequest) -> Dict[str, Any]:
    """
    触发视频文案提取任务（异步执行）。
    需要先完成搜索采集，或提供 video_jsonl 路径。
    """
    tm = get_task_manager()
    task = tm.create_task("scripts", params=req.model_dump())

    def _do_scripts() -> Dict[str, Any]:
        scraper = _make_scraper(req.project_dir, task.workspace)
        script_sources_jsonl: Optional[Path] = None
        script_sources_csv: Optional[Path] = None
        title_clean_csv: Optional[Path] = None
        if req.task_id:
            source_task = tm.get_task(req.task_id)
            if not source_task:
                raise NonRetryableError(
                    f"搜索任务不存在: {req.task_id}",
                    step="extract_scripts",
                )
            source_outputs = Path(source_task.workspace) / "outputs"
            jsonl_path = source_outputs / "script_sources.jsonl"
            csv_path = source_outputs / "script_sources.csv"
            title_clean_path = source_outputs / "search_title_clean.csv"
            if jsonl_path.exists():
                script_sources_jsonl = jsonl_path
            if csv_path.exists():
                script_sources_csv = csv_path
            if title_clean_path.exists():
                title_clean_csv = title_clean_path
            if not script_sources_jsonl and not script_sources_csv:
                raise NonRetryableError(
                    f"搜索任务无可用 script_sources 输出: {req.task_id}",
                    step="extract_scripts",
                )
        else:
            current_outputs = Path(task.workspace) / "outputs"
            jsonl_path = current_outputs / "script_sources.jsonl"
            csv_path = current_outputs / "script_sources.csv"
            title_clean_path = current_outputs / "search_title_clean.csv"
            if jsonl_path.exists():
                script_sources_jsonl = jsonl_path
            if csv_path.exists():
                script_sources_csv = csv_path
            if title_clean_path.exists():
                title_clean_csv = title_clean_path

        if script_sources_jsonl or script_sources_csv:
            output = scraper.extract_script_raw(
                script_sources_jsonl=script_sources_jsonl,
                script_sources_csv=script_sources_csv,
                model=req.model,
                title_clean_csv=title_clean_csv,
            )
            paths = scraper.get_paths()
            result = _script_output_result(paths, output)
            result["status"] = scraper.get_status()
            return result

        video_path = Path(req.video_jsonl) if req.video_jsonl else None
        if video_path:
            video_path = validate_path_in_workspace(
                req.video_jsonl, Path(task.workspace)
            )
        output = scraper.extract_scripts(
            video_jsonl=video_path, model=req.model
        )
        paths = scraper.get_paths()
        result = _script_output_result(paths, output)
        result["scripts_jsonl"] = str(output)
        result["status"] = scraper.get_status()
        return result

    tm.submit(task, _do_scripts)
    return {"task_id": task.task_id, "status": "submitted", "type": "scripts"}


@router.post("/merge", summary="触发数据合并")
async def merge(req: MergeRequest) -> Dict[str, Any]:
    """
    触发数据合并任务（异步执行）。
    合并视频、评论、文案数据生成标准 CSV。
    """
    tm = get_task_manager()
    task = tm.create_task("merge", params=req.model_dump())

    def _do_merge() -> Dict[str, Any]:
        scraper = _make_scraper(req.project_dir, task.workspace)
        if req.search_task_id:
            search_task = tm.get_task(req.search_task_id)
            if not search_task or search_task.status != "completed":
                raise NonRetryableError(
                    f"搜索任务不可用: {req.search_task_id}",
                    step="merge_csv",
                )
            search_outputs = Path(search_task.workspace) / "outputs"
            search_csv = search_outputs / "search_result.csv"
            if not search_csv.exists():
                raise NonRetryableError(
                    f"搜索任务无 search_result.csv: {req.search_task_id}",
                    step="merge_csv",
                )

            comments_outputs: Optional[Path] = None
            if req.comments_task_id:
                comments_task = tm.get_task(req.comments_task_id)
                if not comments_task or comments_task.status != "completed":
                    raise NonRetryableError(
                        f"评论任务不可用: {req.comments_task_id}",
                        step="merge_csv",
                    )
                comments_outputs = Path(comments_task.workspace) / "outputs"

            scripts_outputs: Optional[Path] = None
            if req.scripts_task_id:
                scripts_task = tm.get_task(req.scripts_task_id)
                if not scripts_task or scripts_task.status != "completed":
                    raise NonRetryableError(
                        f"文案任务不可用: {req.scripts_task_id}",
                        step="merge_csv",
                    )
                scripts_outputs = Path(scripts_task.workspace) / "outputs"

            jsonl_path, csv_path, stats = scraper.build_content_asset(
                search_outputs_dir=search_outputs,
                comments_outputs_dir=comments_outputs,
                scripts_outputs_dir=scripts_outputs,
            )
            return {
                "content_asset_jsonl": str(jsonl_path),
                "content_asset_csv": str(csv_path),
                "content_asset_stats": stats,
                "status": scraper.get_status(),
            }

        workspace = Path(task.workspace)
        v_path = Path(req.video_jsonl) if req.video_jsonl else None
        c_path = Path(req.comments_jsonl) if req.comments_jsonl else None
        s_path = Path(req.scripts_jsonl) if req.scripts_jsonl else None
        o_path = Path(req.output_csv) if req.output_csv else None
        # 路径遍历防护：验证所有用户提供的路径都在 workspace 内
        if v_path:
            v_path = validate_path_in_workspace(req.video_jsonl, workspace)
        if c_path:
            c_path = validate_path_in_workspace(req.comments_jsonl, workspace)
        if s_path:
            s_path = validate_path_in_workspace(req.scripts_jsonl, workspace)
        if o_path:
            o_path = validate_path_in_workspace(req.output_csv, workspace)
        output = scraper.merge(
            video_jsonl=v_path,
            comments_jsonl=c_path,
            scripts_jsonl=s_path,
            output_csv=o_path,
        )
        return {"csv_path": str(output), "status": scraper.get_status()}

    tm.submit(task, _do_merge)
    return {"task_id": task.task_id, "status": "submitted", "type": "merge"}


@router.post("/run-all", summary="一键执行全部步骤")
async def run_all(req: RunAllRequest) -> Dict[str, Any]:
    """
    一键执行全部采集步骤（搜索→评论→文案→合并）。
    """
    tm = get_task_manager()
    task = tm.create_task("run_all", params=req.model_dump())

    def _do_run_all() -> Dict[str, Any]:
        config_dict: Dict[str, Any] = {
            "project_dir": req.project_dir or task.workspace,
            "keywords": req.keywords,
            "max_videos_per_keyword": req.max_count,
        }
        scraper = DouyinScraper(config_dict)
        return scraper.run_all(steps=req.steps)

    tm.submit(task, _do_run_all)
    return {"task_id": task.task_id, "status": "submitted", "type": "run_all"}


@router.get("/status/{task_id}", summary="查询任务状态")
async def get_status(task_id: str) -> Dict[str, Any]:
    """查询异步任务的状态"""
    tm = get_task_manager()
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return task.to_dict()


@router.get("/result/{task_id}", summary="下载结果文件")
async def get_result(task_id: str):
    """
    下载任务的结果文件（CSV 或 JSONL）。

    ★ 我实际执行时：结果文件散落在各处，用户找不到。
    v6：通过 task_id 自动定位结果文件。★
    """
    tm = get_task_manager()
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"任务未完成，当前状态: {task.status}",
        )

    result_path = tm.get_result_path(task_id)
    if not result_path:
        raise HTTPException(status_code=404, detail="结果文件不存在")

    if result_path.is_file():
        # 确定媒体类型
        media_type = "application/octet-stream"
        if result_path.suffix == ".csv":
            media_type = "text/csv"
        elif result_path.suffix == ".jsonl":
            media_type = "application/jsonl"

        filename = result_path.name
        return FileResponse(
            path=str(result_path),
            media_type=media_type,
            filename=filename,
        )
    elif result_path.is_dir():
        # 返回目录下所有文件列表
        files = [f.name for f in result_path.rglob("*") if f.is_file()]
        return JSONResponse(content={"task_id": task_id, "files": files})

    raise HTTPException(status_code=404, detail="结果路径无效")


@router.post("/reset", summary="重置步骤状态")
async def reset_step(req: ResetRequest) -> Dict[str, Any]:
    """
    重置某步骤的状态为 pending。

    ★ 我实际执行时：步骤失败后无法重新执行，只能手动删除状态文件。
    v6：通过 API 重置，可选清除去重索引。★
    """
    try:
        scraper = _make_scraper(req.project_dir, "./workspace_default")
        scraper.reset_step(req.step, clear_dedupe=req.clear_dedupe)
        return {"status": "reset", "step": req.step, "clear_dedupe": req.clear_dedupe}
    except ScraperError as e:
        raise _error_response(e)
    except Exception as e:
        raise _error_response(e)


@router.get("/tasks", summary="列出所有任务")
async def list_tasks(
    task_type: Optional[str] = Query(None, description="按类型过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回数量上限"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """列出任务（支持分页）"""
    tm = get_task_manager()
    all_tasks = tm.list_tasks(task_type=task_type, status=status, limit=10000)
    total = len(all_tasks)
    # 应用 offset 和 limit
    paginated = all_tasks[offset : offset + limit]
    return {
        "tasks": [t.to_dict() for t in paginated],
        "total": total,
        "offset": offset,
        "limit": limit,
        "stats": tm.get_stats(),
    }


@router.delete("/tasks/{task_id}", summary="删除任务记录")
async def delete_task(task_id: str) -> Dict[str, str]:
    """删除任务记录"""
    tm = get_task_manager()
    if tm.delete_task(task_id):
        return {"status": "deleted", "task_id": task_id}
    raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")


@router.post("/cleanup", summary="清理过期任务")
async def cleanup_tasks(
    max_age_hours: int = Query(72, ge=1, description="保留最近 N 小时的任务"),
) -> Dict[str, Any]:
    """清理超过指定时间的已完成/失败任务"""
    tm = get_task_manager()
    removed = tm.cleanup_old_tasks(max_age_hours=max_age_hours)
    return {"removed": removed, "remaining": len(tm.list_tasks())}


# ═══════════════════════════════════════════════════════════════
# 数据管理 API
# ═══════════════════════════════════════════════════════════════

import csv
import io
import json as _json

MAX_EXPORT_ROWS = 200
MAX_EXPORT_BYTES = 2 * 1024 * 1024  # 2MB


def _find_result_files(workspace: Path) -> List[Path]:
    """在 workspace 中查找 CSV/JSONL 结果文件（最多 2 层深度）"""
    results: List[Path] = []
    for pattern in ("*.csv", "*.jsonl"):
        for p in workspace.rglob(pattern):
            if len(p.relative_to(workspace).parts) <= 2 and p.is_file():
                results.append(p)
    return results


def _count_file_rows(path: Path) -> int:
    """统计文件行数（不含空行），出错返回 0"""
    try:
        count = 0
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
    except OSError:
        return 0


def _read_jsonl_rows(path: Path, limit: int = MAX_EXPORT_ROWS) -> List[Dict[str, Any]]:
    """读取 JSONL 文件，返回字典列表"""
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(_json.loads(line))
                except _json.JSONDecodeError:
                    continue
                if len(rows) >= limit:
                    break
    except OSError:
        pass
    return rows


def _read_csv_rows(path: Path, limit: int = MAX_EXPORT_ROWS) -> List[Dict[str, Any]]:
    """读取 CSV 文件，返回字典列表"""
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
                if len(rows) >= limit:
                    break
    except OSError:
        pass
    return rows


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """规范化一行数据，确保关键字段存在"""
    return {
        "video_id": str(row.get("video_id", row.get("id", ""))),
        "platform": str(row.get("platform", "douyin")),
        "script_text": str(row.get("script_text", row.get("script", row.get("text", "")))),
        "likes": str(row.get("likes", row.get("like_count", ""))),
        "favorites": str(row.get("favorites", row.get("collect_count", ""))),
        "shares": str(row.get("shares", row.get("share_count", ""))),
        "comments": str(row.get("comments", row.get("comment_count", ""))),
    }


@router.get("/data/list", summary="列出可导出的数据文件")
async def list_data_files() -> Dict[str, Any]:
    """
    扫描所有已完成任务的 workspace，返回可导出的数据文件列表。
    每条记录包含：task_id, task_type, file_name, file_size, row_count, created_at
    """
    tm = get_task_manager()
    all_tasks = tm.list_tasks(status="completed", limit=10000)

    items: List[Dict[str, Any]] = []
    for task in all_tasks:
        workspace = Path(task.workspace)
        if not workspace.exists():
            continue
        files = _find_result_files(workspace)
        for fpath in files:
            try:
                stat = fpath.stat()
                items.append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "file_name": fpath.name,
                    "file_path": str(fpath.relative_to(workspace)),
                    "file_size": stat.st_size,
                    "row_count": _count_file_rows(fpath),
                    "created_at": task.completed_at or task.created_at,
                    "keywords": task.params.get("keywords", []),
                })
            except OSError:
                continue

    # 按完成时间降序
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return {"items": items, "total": len(items)}


@router.get("/data/preview/{task_id}", summary="预览任务结果数据（前 20 行）")
async def preview_data(task_id: str) -> Dict[str, Any]:
    """返回任务结果文件的前 20 行数据"""
    tm = get_task_manager()
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"任务未完成，当前状态: {task.status}")

    workspace = Path(task.workspace)
    files = _find_result_files(workspace)
    if not files:
        raise HTTPException(status_code=404, detail="未找到结果文件")

    # 优先 CSV，其次 JSONL
    target = next((f for f in files if f.suffix == ".csv"), files[0])

    if target.suffix == ".csv":
        rows = _read_csv_rows(target, limit=20)
    else:
        raw_rows = _read_jsonl_rows(target, limit=20)
        rows = [_normalize_row(r) for r in raw_rows]

    return {
        "task_id": task_id,
        "file_name": target.name,
        "rows": rows,
        "total_rows": _count_file_rows(target),
    }


class ExportRequest(BaseModel):
    """数据导出请求"""
    task_ids: List[str] = Field(..., description="任务 ID 列表（支持多选）")
    format: Literal["csv", "txt"] = Field("csv", description="导出格式")
    limit: int = Field(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS, description="最大行数上限")

    @field_validator("task_ids")
    @classmethod
    def validate_task_ids(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("task_ids 不能为空")
        if len(v) > 50:
            raise ValueError("一次最多导出 50 个任务")
        return v


@router.post("/data/export", summary="导出数据（CSV 或 TXT）")
async def export_data(req: ExportRequest):
    """
    批量导出多个任务的结果数据。

    CSV 格式：列 video_id, platform, script_text, likes, favorites, shares, comments（| 分隔多值）
    TXT 格式：每行一条，字段用 || 分隔：video_id||script_text||likes||favorites||shares||comments
              上限 200 行、2MB、UTF-8
    """
    tm = get_task_manager()

    # 收集所有行
    all_rows: List[Dict[str, Any]] = []
    for task_id in req.task_ids:
        task = tm.get_task(task_id)
        if not task or task.status != "completed":
            continue
        workspace = Path(task.workspace)
        files = _find_result_files(workspace)
        if not files:
            continue
        target = next((f for f in files if f.suffix == ".csv"), files[0])
        if target.suffix == ".csv":
            rows = _read_csv_rows(target, limit=req.limit)
        else:
            raw_rows = _read_jsonl_rows(target, limit=req.limit)
            rows = [_normalize_row(r) for r in raw_rows]
        all_rows.extend(rows)
        if len(all_rows) >= req.limit:
            all_rows = all_rows[:req.limit]
            break

    if not all_rows:
        raise HTTPException(status_code=404, detail="未找到可导出的数据（任务未完成或无结果文件）")

    if req.format == "csv":
        # CSV 格式：标准 CSV，comments 字段多值用 | 分隔
        output = io.StringIO()
        fieldnames = ["video_id", "platform", "script_text", "likes", "favorites", "shares", "comments"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        size = 0
        written = 0
        for row in all_rows:
            norm = _normalize_row(row)
            writer.writerow(norm)
            written += 1
            size = output.tell()
            if size >= MAX_EXPORT_BYTES:
                break
        content = output.getvalue().encode("utf-8")
        media_type = "text/csv; charset=utf-8"
        filename = f"export_{len(req.task_ids)}tasks_{written}rows.csv"

    else:  # txt
        # TXT 格式：每行 video_id||script_text||likes||favorites||shares||comments
        lines: List[str] = []
        size = 0
        for row in all_rows:
            norm = _normalize_row(row)
            parts = [
                norm["video_id"],
                norm["script_text"],
                norm["likes"],
                norm["favorites"],
                norm["shares"],
                norm["comments"],
            ]
            line = "||".join(parts) + "\n"
            line_bytes = line.encode("utf-8")
            if size + len(line_bytes) > MAX_EXPORT_BYTES:
                break
            lines.append(line)
            size += len(line_bytes)
        content = "".join(lines).encode("utf-8")
        media_type = "text/plain; charset=utf-8"
        filename = f"export_{len(req.task_ids)}tasks_{len(lines)}rows.txt"

    from fastapi.responses import Response
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# WebSocket 路由已移至 main.py（路径：/ws/tasks），
# 避免 /scrape 前缀导致路径不匹配。
