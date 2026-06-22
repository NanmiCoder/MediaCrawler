"""
douyin_scraper.api.tasks — 异步任务管理
=========================================
v6 新增：轻量级异步任务调度器。

我实际执行时踩过的坑：
  - 采集任务动辄运行数小时，HTTP 请求会超时
    → 必须后台执行，返回 task_id 供查询
  - 多个任务同时操作同一个工作目录
    → 每个任务独立工作目录，互不干扰
  - 任务进程崩溃后无状态记录
    → 任务状态持久化到 JSON，重启后可恢复
  - 内存中存储所有任务导致重启丢失
    → 可选 SQLite 持久化（默认 JSON 文件）

设计决策：
  - 使用 threading 而非 asyncio，因为 DouyinScraper 内部全是同步 I/O
  - 任务状态三态：pending → running → completed/failed
  - 每个任务创建独立的 DouyinScraper 实例
  - 任务结果文件通过 task_id 关联
"""

import atexit
import json
import logging
import os
import shutil
import signal
import tempfile
import threading
import time as _time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException

from .utils import validate_no_symlink
from .ws import ws_manager

logger = logging.getLogger("douyin_scraper.api")

_CST = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(_CST).isoformat()


def _atomic_write_json(filepath: Path, data: dict) -> None:
    """
    原子写入 JSON 文件：先写临时文件，再 os.replace 替换原文件。
    防止写入过程中崩溃导致文件损坏。

    Args:
        filepath: 目标 JSON 文件路径
        data: 要写入的字典数据
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(filepath.parent),
        prefix=filepath.stem + ".tmp",
        suffix=".json",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(filepath))
    except Exception:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


class TaskInfo:
    """单个任务的信息"""

    def __init__(
        self,
        task_id: str,
        task_type: str,
        workspace: str,
        params: Optional[dict] = None,
    ) -> None:
        self.task_id = task_id
        self.task_type = task_type
        self.workspace = workspace
        self.params = params or {}
        self.status: str = "pending"  # pending / running / completed / failed
        self.created_at: str = _now_iso()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.error: Optional[str] = None
        self.exit_code: int = 0
        self.result: Optional[Dict[str, Any]] = None
        self.progress: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "workspace": self.workspace,
            "params": self.params,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "exit_code": self.exit_code,
            "result": self.result,
            "progress": self.progress,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskInfo":
        task = cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            workspace=data["workspace"],
            params=data.get("params"),
        )
        task.status = data.get("status", "pending")
        task.created_at = data.get("created_at", _now_iso())
        task.started_at = data.get("started_at")
        task.completed_at = data.get("completed_at")
        task.error = data.get("error")
        task.exit_code = data.get("exit_code", 0)
        task.result = data.get("result")
        task.progress = data.get("progress", "")
        return task


class TaskManager:
    """
    异步任务管理器。

    ★ 我实际执行时：直接在 HTTP handler 中运行采集，导致：
      1. 请求超时（采集耗时远超 HTTP 超时）
      2. 无法并发（同一进程只能做一个采集任务）
      3. 进程崩溃全部丢失
    v6：后台线程 + 任务注册表 + 状态持久化。
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self._base_dir = Path(base_dir or os.environ.get(
            "DY_WORKSPACE_DIR", "./workspaces"
        ))
        self._base_dir.mkdir(parents=True, exist_ok=True)

        # 内存任务注册表
        self._tasks: Dict[str, TaskInfo] = {}
        self._lock = threading.Lock()

        # 优雅关闭：收到 SIGTERM 后等待任务完成的超时时间（秒）
        self.GRACEFUL_SHUTDOWN_TIMEOUT: int = 60
        # 关闭信号标志（信号处理器设置，工作线程/轮询循环检查）
        self._shutdown_flag = threading.Event()

        # 持久化文件
        self._state_file = self._base_dir / "tasks_registry.json"

        # 从持久化文件恢复
        self._load_registry()

        # atexit 注册标记（避免重复注册）
        self._atexit_registered: bool = False

        # 启动时清理残留的 running 任务（上次进程异常退出遗留）
        self.cleanup_stale_tasks()

    def _register_shutdown_handlers(self) -> None:
        """
        注册优雅关闭处理器（替代纯 atexit 方案）。

        工作流：
        1. Docker/Podman 发送 SIGTERM → 我们的 handler 收到
        2. 设置 _shutdown_flag，通知所有轮询循环停止
        3. 等待运行中任务完成（最多 GRACEFUL_SHUTDOWN_TIMEOUT 秒）
        4. 超时后仍未结束的标记为 failed (exit_code=4, "被中断")
        5. atexit 兜底：进程崩溃/非正常退出时仍然会标记残留任务
        """
        if self._atexit_registered:
            return
        self._atexit_registered = True

        def _do_graceful_shutdown(source: str) -> None:
            """核心优雅关闭逻辑，信号处理器和 atexit 兜底共用"""
            # 防止重复执行（SIGTERM + atexit 可能同时触发）
            if self._shutdown_flag.is_set():
                return
            self._shutdown_flag.set()

            running_count = sum(
                1 for t in self._tasks.values() if t.status == "running"
            )
            if running_count == 0:
                logger.info("[%s] 没有运行中任务，直接退出", source)
                return

            logger.warning(
                "[%s] 优雅关闭开始：等待 %d 个运行中任务完成（最多 %ds）...",
                source, running_count, self.GRACEFUL_SHUTDOWN_TIMEOUT,
            )

            deadline = _time.monotonic() + self.GRACEFUL_SHUTDOWN_TIMEOUT
            while _time.monotonic() < deadline:
                with self._lock:
                    still_running = [
                        t for t in self._tasks.values()
                        if t.status == "running"
                    ]
                if not still_running:
                    break
                _time.sleep(0.5)

            # 检查结果
            with self._lock:
                killed = 0
                finished = 0
                for task in self._tasks.values():
                    if task.status == "running":
                        task.status = "failed"
                        task.completed_at = _now_iso()
                        task.error = "任务被中断：服务正在关闭（容器重启/进程退出）"
                        task.exit_code = 4  # 被外部中断（区别于 3=致命错误）
                        killed += 1
                    elif task.status == "completed":
                        finished += 1
                if killed > 0:
                    self._save_registry()
                logger.info(
                    "[%s] 优雅关闭完成 — %d 完成, %d 被中断",
                    source, finished, killed,
                )

        # ── SIGTERM 处理器（Docker stop / docker-compose restart）──
        def _sigterm_handler(signum: int, frame: Any) -> None:
            _do_graceful_shutdown("SIGTERM")
            # 恢复默认行为让进程自然退出
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            os.kill(os.getpid(), signal.SIGTERM)

        # ── SIGINT 处理器（Ctrl+C）──
        def _sigint_handler(signum: int, frame: Any) -> None:
            _do_graceful_shutdown("SIGINT")
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            os.kill(os.getpid(), signal.SIGINT)

        signal.signal(signal.SIGTERM, _sigterm_handler)
        signal.signal(signal.SIGINT, _sigint_handler)
        logger.debug("已注册 SIGTERM/SIGINT 优雅关闭处理器")

        # ── atexit 兜底：进程崩溃/非正常退出时仍然会触发 ──
        def _atexit_safety_net() -> None:
            if not self._shutdown_flag.is_set():
                _do_graceful_shutdown("atexit（异常退出）")

        atexit.register(_atexit_safety_net)

    def cleanup_stale_tasks(self) -> int:
        """
        清理残留的 running 任务（进程异常退出后重启时调用）。
        将超过 1 小时仍在 running 的任务标记为 failed。
        """
        cutoff = datetime.now(_CST) - timedelta(hours=1)
        stale_count = 0
        with self._lock:
            for task in self._tasks.values():
                if task.status != "running":
                    continue
                started = task.started_at or task.created_at
                try:
                    started_dt = datetime.fromisoformat(started)
                    if started_dt < cutoff:
                        task.status = "failed"
                        task.completed_at = _now_iso()
                        task.error = "任务超时，可能因进程异常退出"
                        task.exit_code = 3
                        stale_count += 1
                except (ValueError, TypeError):
                    # 无法解析时间，也标记为 failed
                    task.status = "failed"
                    task.completed_at = _now_iso()
                    task.error = "任务状态异常，时间无法解析"
                    task.exit_code = 3
                    stale_count += 1
            if stale_count > 0:
                self._save_registry()
        if stale_count:
            logger.warning("清理 %d 个残留 running 任务", stale_count)
        return stale_count

    def _load_registry(self) -> None:
        """从 JSON 文件恢复任务注册表"""
        if not self._state_file.exists():
            return
        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for task_data in data.get("tasks", []):
                task = TaskInfo.from_dict(task_data)
                self._tasks[task.task_id] = task
            logger.info("恢复 %d 个任务记录", len(self._tasks))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("任务注册表损坏，跳过恢复: %s", e)

    def _save_registry(self) -> None:
        """持久化任务注册表到 JSON（原子写入）"""
        self._base_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "tasks": [t.to_dict() for t in self._tasks.values()],
            "updated_at": _now_iso(),
        }
        try:
            _atomic_write_json(self._state_file, data)
        except (OSError, PermissionError):
            logger.warning("任务注册表写入失败")

    def create_task(
        self,
        task_type: str,
        params: Optional[dict] = None,
    ) -> TaskInfo:
        """
        创建新任务，返回 TaskInfo。

        Args:
            task_type: search / comments / scripts / merge / run_all
            params: 任务参数（keywords, model, 等）
        """
        task_id = uuid.uuid4().hex[:12]
        # 防止 UUID4 碰撞：最多重试 3 次
        for _ in range(3):
            with self._lock:
                if task_id not in self._tasks:
                    break
            task_id = uuid.uuid4().hex[:12]
        else:
            raise RuntimeError("task_id 碰撞 3 次，无法生成唯一 ID")
        workspace = str(self._base_dir / task_id)

        task = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            workspace=workspace,
            params=params,
        )

        with self._lock:
            self._tasks[task_id] = task
            self._save_registry()

        logger.info("创建任务: %s (%s)", task_id, task_type)
        return task

    def submit(
        self,
        task: TaskInfo,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        提交任务到后台线程执行。

        ★ 设计决策：使用 threading 而非 asyncio ★
        因为 DouyinScraper 内部全是同步 I/O（subprocess、文件写入、
        faster-whisper），在 async 中调用需要 run_in_executor，
        不如直接用线程简单。

        线程安全：所有对 TaskInfo 属性的修改都在 self._lock 下进行。
        """
        def _worker() -> None:
            with self._lock:
                task.status = "running"
                task.started_at = _now_iso()
                self._save_registry()

            self._broadcast("task_started", task)

            try:
                result = func(*args, **kwargs)
                with self._lock:
                    task.status = "completed"
                    task.completed_at = _now_iso()
                    task.result = result if isinstance(result, dict) else {"output": str(result)}
                    self._save_registry()
                logger.info("任务完成: %s", task.task_id)
                self._broadcast("task_completed", task)
            except Exception as e:
                with self._lock:
                    task.status = "failed"
                    task.completed_at = _now_iso()
                    task.error = str(e)[:500]

                    # 分类退出码
                    from douyin_scraper.utils import classify_error
                    task.exit_code = classify_error(e)
                    self._save_registry()
                logger.error(
                    "任务失败: %s (exit_code=%d): %s",
                    task.task_id, task.exit_code, task.error,
                )
                self._broadcast("task_failed", task)

        thread = threading.Thread(
            target=_worker,
            name=f"task-{task.task_id}",
            daemon=False,
        )
        thread.start()
        # 注册优雅关闭处理器：收到 SIGTERM 后等待任务完成
        self._register_shutdown_handlers()

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """查询任务状态"""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[TaskInfo]:
        """列出任务"""
        tasks = list(self._tasks.values())

        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        if status:
            tasks = [t for t in tasks if t.status == status]

        # 按创建时间降序
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    def delete_task(self, task_id: str) -> bool:
        """删除任务记录及对应 workspace 目录"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                # 先清理磁盘 workspace
                workspace_path = Path(task.workspace)
                if workspace_path.exists():
                    try:
                        shutil.rmtree(str(workspace_path), ignore_errors=True)
                        logger.info("已清理 workspace: %s", workspace_path)
                    except Exception as e:
                        logger.warning("清理 workspace 失败: %s: %s", workspace_path, e)
                del self._tasks[task_id]
                self._save_registry()
                return True
        return False

    def cleanup_old_tasks(self, max_age_hours: int = 72) -> int:
        """
        清理超过 max_age_hours 的已完成/失败任务。
        ★ 我实际执行时：任务注册表无限增长，占用磁盘。
        """
        cutoff = datetime.now(_CST) - timedelta(hours=max_age_hours)
        removed = 0
        with self._lock:
            to_remove = []
            for tid, task in self._tasks.items():
                if task.status in ("completed", "failed"):
                    completed = task.completed_at or task.created_at
                    try:
                        completed_dt = datetime.fromisoformat(completed)
                        if completed_dt < cutoff:
                            to_remove.append(tid)
                    except (ValueError, TypeError):
                        pass
            for tid in to_remove:
                del self._tasks[tid]
                removed += 1
            if removed:
                self._save_registry()
        logger.info("清理 %d 个过期任务", removed)
        return removed

    @staticmethod
    def _search_result_names() -> tuple[str, ...]:
        return ("search_result.csv", "search_result.jsonl")


    @staticmethod
    def _run_all_result_names() -> tuple[str, ...]:
        return ("search_result.csv", "search_result.jsonl")


    @classmethod
    def _preferred_result_names(cls, task_type: str) -> tuple[str, ...]:
        selector = getattr(cls, f"_{task_type}_result_names", None)
        if selector is None:
            return ()
        return selector()


    def get_result_path(self, task_id: str) -> Optional[Path]:
        """Return the primary result file without changing task-specific semantics."""
        task = self.get_task(task_id)
        if not task or task.status != "completed":
            return None

        workspace = Path(task.workspace)
        outputs_dir = workspace / "outputs"
        for name in self._preferred_result_names(task.task_type):
            preferred = outputs_dir / name
            if not preferred.exists():
                continue
            try:
                validate_no_symlink(preferred)
                return preferred
            except HTTPException:
                logger.warning("结果路径含符号链接，拒绝访问: %s", preferred)

        # Compatibility fallback for legacy/custom outputs.
        if outputs_dir.exists():
            for pattern in ("*.csv", "*.jsonl"):
                candidates = sorted(
                    outputs_dir.rglob(pattern),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                for candidate in candidates:
                    try:
                        validate_no_symlink(candidate)
                        return candidate
                    except HTTPException:
                        continue

        if workspace.exists():
            try:
                validate_no_symlink(workspace)
                return workspace
            except HTTPException:
                logger.warning("结果路径含符号链接，拒绝访问: %s", workspace)
                return None

        return None

    def get_stats(self) -> Dict[str, Any]:
        """获取任务统计（修复：枚举成员转字符串）"""
        stats: Dict[str, int] = {
            "total": len(self._tasks),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
        }
        for task in self._tasks.values():
            # task.status 是 TaskStatus 枚举成员，需要取 .value 得到字符串
            status_str = task.status.value if hasattr(task.status, 'value') else str(task.status)
            if status_str in stats:
                stats[status_str] += 1
        return stats

    def update_progress(self, task_id: str, progress: str) -> None:
        """
        更新任务进度字符串。

        Args:
            task_id: 任务 ID
            progress: 进度描述文本
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.progress = progress
                self._save_registry()
        if task:
            self._broadcast("task_progress", task)

    def _broadcast(self, event_type: str, task: TaskInfo) -> None:
        """
        通过 WebSocket 广播任务状态变更。

        Args:
            event_type: 事件类型 (task_started/task_progress/task_completed/task_failed)
            task: 任务信息对象
        """
        message = {
            "type": event_type,
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress,
            "timestamp": _now_iso(),
        }
        if event_type == "task_completed" and task.result:
            message["result"] = task.result
        if event_type == "task_failed" and task.error:
            message["error"] = task.error
        ws_manager.broadcast_sync(message)
