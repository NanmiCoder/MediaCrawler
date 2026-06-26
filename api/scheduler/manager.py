# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from api.schemas.crawler import CrawlerTypeEnum
from .schemas import InstanceCreateRequest, InstanceUpdateRequest, TaskCreateRequest
from .store import PROJECT_ROOT, SchedulerStore, _json_dumps, utc_now


@dataclass
class InstanceRuntime:
    instance_id: str
    task_id: str
    process: subprocess.Popen
    read_task: Optional[asyncio.Task] = None
    wait_task: Optional[asyncio.Task] = None
    canceled: bool = False


class SchedulerManager:
    """Manage multiple crawler subprocess instances."""

    def __init__(
        self,
        store: SchedulerStore | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.store = store or SchedulerStore()
        self.project_root = project_root or PROJECT_ROOT
        self.base_dir = self.project_root / "data" / "scheduler"
        self.profile_dir = self.base_dir / "profiles"
        self.artifact_dir = self.base_dir / "artifacts"
        self._lock = asyncio.Lock()
        self._runtimes: dict[str, InstanceRuntime] = {}

    def list_instances(self) -> list[dict[str, Any]]:
        return self.store.list_instances()

    def get_instance(self, instance_id: str) -> Optional[dict[str, Any]]:
        return self.store.get_instance(instance_id)

    def create_instance(self, request: InstanceCreateRequest) -> dict[str, Any]:
        payload = request.model_dump(mode="json")
        instance_id = uuid.uuid4().hex
        cdp_debug_port = request.cdp_debug_port or self._allocate_cdp_port()
        profile_dir = request.browser_profile_dir.strip()
        if not profile_dir:
            profile_dir = str(self.profile_dir / instance_id)
        else:
            profile_path = Path(profile_dir)
            if not profile_path.is_absolute():
                profile_dir = str(self.project_root / profile_path)
        return self.store.create_instance(payload, profile_dir, cdp_debug_port, instance_id=instance_id)

    async def update_instance(self, instance_id: str, request: InstanceUpdateRequest) -> Optional[dict[str, Any]]:
        async with self._lock:
            instance = self.store.get_instance(instance_id)
            if not instance:
                return None
            if instance["status"] in {"running", "stopping"}:
                mutable_running_fields = {"status"}
                changed_fields = {
                    key
                    for key, value in request.model_dump(exclude_unset=True).items()
                    if value is not None
                }
                if changed_fields - mutable_running_fields:
                    raise RuntimeError("running instance cannot be edited")
            fields = request.model_dump(mode="json", exclude_unset=True)
            if "default_params" in fields:
                fields["default_params_json"] = _json_dumps(fields.pop("default_params"))
            return self.store.update_instance(instance_id, **fields)

    async def delete_instance(self, instance_id: str) -> bool:
        async with self._lock:
            instance = self.store.get_instance(instance_id)
            if not instance:
                return False
            if instance["status"] in {"running", "stopping"}:
                raise RuntimeError("running instance cannot be deleted")
            return self.store.delete_instance(instance_id)

    def list_tasks(self, instance_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return self.store.list_tasks(instance_id=instance_id, limit=limit)

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        return self.store.get_task(task_id)

    async def create_task(self, request: TaskCreateRequest) -> dict[str, Any]:
        async with self._lock:
            instance = self.store.get_instance(request.instance_id)
            if not instance:
                raise KeyError("instance not found")
            if instance["status"] == "disabled":
                raise RuntimeError("instance is disabled")
            artifact_dir = self.artifact_dir / request.instance_id
            payload = request.model_dump(mode="json")
            task = self.store.create_task(payload, str(artifact_dir / "pending"))
            real_artifact_dir = artifact_dir / task["id"]
            task = self.store.update_task(task["id"], artifact_dir=str(real_artifact_dir))
            if instance["status"] in {"idle", "error"} and request.instance_id not in self._runtimes:
                await self._start_task_locked(task)
                task = self.store.get_task(task["id"])
            return task

    async def create_login_task(self, instance_id: str) -> dict[str, Any]:
        request = TaskCreateRequest(instance_id=instance_id, crawler_type=CrawlerTypeEnum.LOGIN, target_text="")
        return await self.create_task(request)

    async def start_task(self, task_id: str) -> Optional[dict[str, Any]]:
        async with self._lock:
            task = self.store.get_task(task_id)
            if not task:
                return None
            if task["status"] != "queued":
                raise RuntimeError("only queued tasks can be started")
            await self._start_task_locked(task)
            return self.store.get_task(task_id)

    async def cancel_task(self, task_id: str) -> Optional[dict[str, Any]]:
        async with self._lock:
            task = self.store.get_task(task_id)
            if not task:
                return None
            if task["status"] == "queued":
                self.store.append_log(task_id, "Task canceled before start", "warning")
                return self.store.update_task(task_id, status="canceled", finished_at=utc_now())
            if task["status"] != "running":
                return task
            runtime = self._runtimes.get(task["instance_id"])
            if runtime and runtime.task_id == task_id:
                runtime.canceled = True
                self.store.append_log(task_id, "Stopping crawler subprocess ...", "warning")
                self.store.update_instance(task["instance_id"], status="stopping")
                try:
                    runtime.process.terminate()
                except ProcessLookupError:
                    pass
            return self.store.update_task(task_id, status="canceled", finished_at=utc_now())

    def list_logs(self, task_id: str, limit: int = 300) -> list[dict[str, Any]]:
        return self.store.list_logs(task_id, limit)

    def list_artifacts(self, task_id: str) -> list[dict[str, Any]]:
        return self.store.list_artifacts(task_id)

    def status(self) -> dict[str, int]:
        return self.store.scheduler_counts()

    async def _start_task_locked(self, task: dict[str, Any]) -> None:
        instance = self.store.get_instance(task["instance_id"])
        if not instance:
            raise KeyError("instance not found")
        if instance["id"] in self._runtimes:
            return

        artifact_dir = Path(task["artifact_dir"])
        artifact_dir.mkdir(parents=True, exist_ok=True)
        Path(instance["browser_profile_dir"]).mkdir(parents=True, exist_ok=True)

        cmd = self._build_command(instance, task)
        self.store.append_log(task["id"], f"Starting crawler: {' '.join(cmd)}", "info")
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                bufsize=1,
                cwd=str(self.project_root),
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
        except Exception as exc:
            message = f"Failed to start crawler: {type(exc).__name__}: {exc}"
            self.store.append_log(task["id"], message, "error")
            self.store.update_task(task["id"], status="failed", error_message=message, finished_at=utc_now())
            self.store.update_instance(instance["id"], status="error", current_task_id=None, pid=None, last_error=message)
            return

        runtime = InstanceRuntime(instance_id=instance["id"], task_id=task["id"], process=process)
        runtime.read_task = asyncio.create_task(self._read_output(runtime))
        runtime.wait_task = asyncio.create_task(self._watch_process(runtime))
        self._runtimes[instance["id"]] = runtime
        now = utc_now()
        self.store.update_task(task["id"], status="running", pid=process.pid, started_at=now)
        self.store.update_instance(
            instance["id"],
            status="running",
            current_task_id=task["id"],
            pid=process.pid,
            last_error="",
        )
        self.store.append_log(task["id"], f"Crawler subprocess started, pid={process.pid}", "success")

    def _build_command(self, instance: dict[str, Any], task: dict[str, Any]) -> list[str]:
        params = {**instance.get("default_params", {}), **task.get("params", {})}
        crawler_type = task["crawler_type"]
        save_option = str(params.get("save_option", instance["save_option"]))
        headless = self._as_bool(params.get("headless", instance["headless"]))
        target_text = task.get("target_text", "")

        cmd = ["uv", "run", "python", "main.py"]
        cmd.extend(["--platform", instance["platform"]])
        cmd.extend(["--lt", str(params.get("login_type", instance["login_type"]))])
        cmd.extend(["--type", crawler_type])
        cmd.extend(["--save_data_option", save_option])
        cmd.extend(["--save_data_path", task["artifact_dir"]])
        cmd.extend(["--instance_id", instance["id"]])
        cmd.extend(["--browser_profile_dir", instance["browser_profile_dir"]])
        cmd.extend(["--cdp_debug_port", str(instance["cdp_debug_port"])])
        cmd.extend(["--cdp_connect_existing", self._bool_arg(params.get("cdp_connect_existing", False))])
        cmd.extend(["--headless", self._bool_arg(headless)])

        if crawler_type == "search":
            keywords = target_text or str(params.get("keywords", ""))
            if keywords:
                cmd.extend(["--keywords", keywords])
        elif crawler_type == "detail":
            specified_id = target_text or str(params.get("specified_id", ""))
            if specified_id:
                cmd.extend(["--specified_id", specified_id])
        elif crawler_type == "creator":
            creator_id = target_text or str(params.get("creator_id", ""))
            if creator_id:
                cmd.extend(["--creator_id", creator_id])

        option_map = {
            "start": "--start",
            "start_page": "--start",
            "enable_comments": "--get_comment",
            "enable_sub_comments": "--get_sub_comment",
            "max_notes_count": "--crawler_max_notes_count",
            "max_comments_count": "--max_comments_count_singlenotes",
            "content_filters": "--content_filters",
            "max_concurrency_num": "--max_concurrency_num",
            "cookies": "--cookies",
            "enable_ip_proxy": "--enable_ip_proxy",
            "ip_proxy_pool_count": "--ip_proxy_pool_count",
            "ip_proxy_provider_name": "--ip_proxy_provider_name",
            "static_proxy_url": "--static_proxy_url",
        }
        for key, flag in option_map.items():
            if key not in params or params[key] in (None, ""):
                continue
            value = params[key]
            if isinstance(value, bool):
                value = self._bool_arg(value)
            elif isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            cmd.extend([flag, str(value)])
        return cmd

    async def _read_output(self, runtime: InstanceRuntime) -> None:
        loop = asyncio.get_running_loop()
        process = runtime.process
        try:
            while process.poll() is None and process.stdout:
                line = await loop.run_in_executor(None, process.stdout.readline)
                if not line:
                    break
                self._append_process_log(runtime.task_id, line)
            if process.stdout:
                remaining = await loop.run_in_executor(None, process.stdout.read)
                for line in remaining.splitlines():
                    self._append_process_log(runtime.task_id, line)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.store.append_log(runtime.task_id, f"Log reader error: {type(exc).__name__}: {exc}", "error")

    async def _watch_process(self, runtime: InstanceRuntime) -> None:
        loop = asyncio.get_running_loop()
        return_code = await loop.run_in_executor(None, runtime.process.wait)
        if runtime.read_task:
            try:
                await asyncio.wait_for(runtime.read_task, timeout=3)
            except asyncio.TimeoutError:
                runtime.read_task.cancel()

        async with self._lock:
            task = self.store.get_task(runtime.task_id)
            if not task:
                self._runtimes.pop(runtime.instance_id, None)
                return
            if runtime.canceled or task["status"] == "canceled":
                task_status = "canceled"
                error_message = ""
                instance_status = "idle"
                level = "warning"
                message = f"Crawler subprocess canceled, exit_code={return_code}"
            elif return_code == 0:
                task_status = "succeeded"
                error_message = ""
                instance_status = "idle"
                level = "success"
                message = "Crawler subprocess finished successfully"
            else:
                task_status = "failed"
                error_message = f"Crawler subprocess exited with code {return_code}"
                instance_status = "error"
                level = "error"
                message = error_message

            artifacts = self._scan_artifacts(Path(task["artifact_dir"]))
            self.store.replace_artifacts(task["id"], artifacts)
            self.store.update_task(
                task["id"],
                status=task_status,
                exit_code=return_code,
                error_message=error_message,
                finished_at=utc_now(),
            )
            self.store.update_instance(
                runtime.instance_id,
                status=instance_status,
                current_task_id=None,
                pid=None,
                last_error=error_message,
            )
            self.store.append_log(task["id"], message, level)
            self._runtimes.pop(runtime.instance_id, None)

            if task_status in {"succeeded", "canceled"}:
                next_task = self.store.get_next_queued_task(runtime.instance_id)
                if next_task:
                    await self._start_task_locked(next_task)

    def _scan_artifacts(self, root: Path) -> list[dict[str, Any]]:
        if not root.exists():
            return []
        artifacts: list[dict[str, Any]] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            stat = path.stat()
            artifacts.append(
                {
                    "path": str(path),
                    "type": path.suffix.lstrip(".") or "file",
                    "size": stat.st_size,
                    "modified_at": stat.st_mtime,
                    "record_count": self._count_records(path),
                }
            )
        return artifacts

    def _count_records(self, path: Path) -> Optional[int]:
        try:
            if path.suffix == ".jsonl":
                with path.open("r", encoding="utf-8") as f:
                    return sum(1 for line in f if line.strip())
            if path.suffix == ".json":
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                return len(data) if isinstance(data, list) else None
            if path.suffix == ".csv":
                with path.open("r", encoding="utf-8") as f:
                    lines = sum(1 for line in f if line.strip())
                return max(lines - 1, 0)
        except Exception:
            return None
        return None

    def _append_process_log(self, task_id: str, line: str) -> None:
        line = line.strip()
        if not line:
            return
        self.store.append_log(task_id, line, self._parse_log_level(line))

    def _parse_log_level(self, line: str) -> str:
        line_upper = line.upper()
        if "ERROR" in line_upper or "FAILED" in line_upper or "异常" in line:
            return "error"
        if "WARNING" in line_upper or "WARN" in line_upper:
            return "warning"
        if "SUCCESS" in line_upper or "完成" in line or "成功" in line:
            return "success"
        if "DEBUG" in line_upper:
            return "debug"
        return "info"

    def _allocate_cdp_port(self) -> int:
        used_ports = set(self.store.list_cdp_ports())
        port = 9222
        while port in used_ports:
            port += 1
        return port

    def _bool_arg(self, value: Any) -> str:
        return "true" if self._as_bool(value) else "false"

    def _as_bool(self, value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "t", "on"}
        return bool(value)


scheduler_manager = SchedulerManager()
