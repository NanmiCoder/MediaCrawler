# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import csv
import json
import os
import re
import subprocess
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from api.schemas.crawler import CrawlerTypeEnum
from .schemas import JobCreateRequest, JobUpdateRequest, InstanceCreateRequest, InstanceUpdateRequest, TaskCreateRequest
from .store import PROJECT_ROOT, SchedulerStore, _json_dumps, utc_now

try:
    import jieba
except ImportError:  # pragma: no cover - dependency exists in normal project env
    jieba = None


COMMENT_STOP_WORDS = {
    "一个",
    "不是",
    "什么",
    "这个",
    "就是",
    "还是",
    "可以",
    "没有",
    "真的",
    "怎么",
    "哈哈",
    "哈哈哈",
    "感觉",
    "我们",
    "你们",
    "他们",
    "自己",
}


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

    def list_jobs(self) -> list[dict[str, Any]]:
        return self.store.list_instances()

    def get_instance(self, instance_id: str) -> Optional[dict[str, Any]]:
        return self.store.get_instance(instance_id)

    def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        return self.store.get_instance(job_id)

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

    def create_job(self, request: JobCreateRequest) -> dict[str, Any]:
        return self.create_instance(request)

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
            if "params" in fields:
                fields["params_json"] = _json_dumps(fields.pop("params"))
            return self.store.update_instance(instance_id, **fields)

    async def update_job(self, job_id: str, request: JobUpdateRequest) -> Optional[dict[str, Any]]:
        return await self.update_instance(job_id, request)

    async def delete_instance(self, instance_id: str) -> bool:
        async with self._lock:
            instance = self.store.get_instance(instance_id)
            if not instance:
                return False
            if instance["status"] in {"running", "stopping"}:
                raise RuntimeError("running instance cannot be deleted")
            return self.store.delete_instance(instance_id)

    async def delete_job(self, job_id: str) -> bool:
        return await self.delete_instance(job_id)

    def list_tasks(self, instance_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return self.store.list_tasks(instance_id=instance_id, limit=limit)

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        return self.store.get_task(task_id)

    async def create_task(self, request: TaskCreateRequest) -> dict[str, Any]:
        async with self._lock:
            instance = self.store.get_instance(request.instance_id)
            if not instance:
                raise KeyError("instance not found")
            self._ensure_can_run(instance)
            task = self._create_task_record(
                request.instance_id,
                request.crawler_type,
                request.target_text,
                request.params,
            )
            self.store.update_instance(instance["id"], last_task_id=task["id"])
            await self._start_task_locked(task)
            task = self.store.get_task(task["id"])
            return task

    async def create_login_task(self, instance_id: str) -> dict[str, Any]:
        request = TaskCreateRequest(instance_id=instance_id, crawler_type=CrawlerTypeEnum.LOGIN, target_text="")
        return await self.create_task(request)

    async def run_job(self, job_id: str, crawler_type: CrawlerTypeEnum | None = None) -> dict[str, Any]:
        async with self._lock:
            job = self.store.get_instance(job_id)
            if not job:
                raise KeyError("job not found")
            self._ensure_can_run(job)
            run_type = crawler_type or CrawlerTypeEnum(job["crawler_type"])
            target_text = "" if run_type == CrawlerTypeEnum.LOGIN else job.get("target_text", "")
            task = self._create_task_record(job_id, run_type, target_text, job.get("params", {}))
            self.store.update_instance(job_id, last_task_id=task["id"])
            await self._start_task_locked(task)
            return self.store.get_task(task["id"])

    async def login_job(self, job_id: str) -> dict[str, Any]:
        return await self.run_job(job_id, CrawlerTypeEnum.LOGIN)

    async def start_task(self, task_id: str) -> Optional[dict[str, Any]]:
        async with self._lock:
            task = self.store.get_task(task_id)
            if not task:
                return None
            if task["status"] != "queued":
                raise RuntimeError("only queued tasks can be started")
            instance = self.store.get_instance(task["instance_id"])
            if not instance:
                raise KeyError("instance not found")
            self._ensure_can_run(instance)
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

    async def stop_job(self, job_id: str) -> Optional[dict[str, Any]]:
        async with self._lock:
            job = self.store.get_instance(job_id)
            if not job:
                return None
            task_id = job.get("current_task_id")
            if not task_id:
                return job
            task = self.store.get_task(task_id)
            if not task or task["status"] != "running":
                return job
            runtime = self._runtimes.get(job_id)
            if runtime and runtime.task_id == task_id:
                runtime.canceled = True
                self.store.append_log(task_id, "Stopping crawler subprocess ...", "warning")
                self.store.update_instance(job_id, status="stopping")
                try:
                    runtime.process.terminate()
                except ProcessLookupError:
                    pass
            self.store.update_task(task_id, status="canceled", finished_at=utc_now())
            return self.store.get_instance(job_id)

    def list_logs(self, task_id: str, limit: int = 300) -> list[dict[str, Any]]:
        return self.store.list_logs(task_id, limit)

    def list_job_logs(self, job_id: str, limit: int = 300) -> list[dict[str, Any]]:
        job = self.store.get_instance(job_id)
        if not job:
            raise KeyError("job not found")
        task_id = self._job_task_id(job)
        return self.store.list_logs(task_id, limit) if task_id else []

    def list_artifacts(self, task_id: str) -> list[dict[str, Any]]:
        return self.store.list_artifacts(task_id)

    def list_job_artifacts(self, job_id: str) -> list[dict[str, Any]]:
        job = self.store.get_instance(job_id)
        if not job:
            raise KeyError("job not found")
        task_id = self._job_task_id(job)
        return self.store.list_artifacts(task_id) if task_id else []

    def list_job_artifact_summary(self, job_id: str, work_limit: int = 200, word_limit: int = 80) -> dict[str, Any]:
        job = self.store.get_instance(job_id)
        if not job:
            raise KeyError("job not found")
        task_id = self._job_task_id(job)
        if not task_id:
            return {"works": [], "word_cloud": []}

        works: list[dict[str, Any]] = []
        seen_works: set[str] = set()
        words: Counter[str] = Counter()
        for artifact in self.store.list_artifacts(task_id):
            path = self._safe_artifact_path(task_id, artifact["path"])
            if not path.is_file():
                continue
            name = path.name.lower()
            if "content" in name:
                for record in self._iter_artifact_records(path):
                    item = self._work_item(job["platform"], record)
                    key = item.get("url") or item.get("id")
                    if not key or key in seen_works:
                        continue
                    seen_works.add(key)
                    works.append(item)
            elif "comment" in name:
                for record in self._iter_artifact_records(path):
                    words.update(self._comment_words(record))

        works.sort(key=lambda item: self._metric_number(item.get("metrics", {}).get("点赞")), reverse=True)
        word_cloud = [{"text": word, "weight": count} for word, count in words.most_common(word_limit)]
        return {"works": works[:work_limit], "word_cloud": word_cloud}

    def open_job_artifact(self, job_id: str, artifact_id: str) -> dict[str, str]:
        _, artifact, path = self._job_artifact(job_id, artifact_id)
        if not path.is_file():
            raise RuntimeError("artifact file not found")
        try:
            if sys.platform == "darwin":
                cmd = (
                    ["open", "-t", str(path)]
                    if path.suffix.lower() in {".jsonl", ".json", ".csv", ".txt", ".log"}
                    else ["open", str(path)]
                )
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            elif sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", str(path)], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(exc.stderr.strip() or exc.stdout.strip() or "failed to open artifact") from exc
        return {"status": "ok", "message": "Artifact opened", "path": artifact["path"]}

    def delete_job_artifact(self, job_id: str, artifact_id: str) -> dict[str, str]:
        _, _, path = self._job_artifact(job_id, artifact_id)
        if path.exists():
            if not path.is_file():
                raise RuntimeError("artifact path is not a file")
            path.unlink()
        self.store.delete_artifact(artifact_id)
        return {"status": "ok", "message": "Artifact deleted"}

    def status(self) -> dict[str, int]:
        return self.store.scheduler_counts()

    def _create_task_record(
        self,
        instance_id: str,
        crawler_type: CrawlerTypeEnum | str,
        target_text: str,
        params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        artifact_dir = self.artifact_dir / instance_id
        payload = {
            "instance_id": instance_id,
            "crawler_type": str(crawler_type.value if isinstance(crawler_type, CrawlerTypeEnum) else crawler_type),
            "target_text": target_text or "",
            "params": params or {},
        }
        task = self.store.create_task(payload, str(artifact_dir / "pending"))
        real_artifact_dir = artifact_dir / task["id"]
        return self.store.update_task(task["id"], artifact_dir=str(real_artifact_dir))

    def _ensure_can_run(self, instance: dict[str, Any]) -> None:
        if instance["status"] == "disabled":
            raise RuntimeError("job is disabled")
        if instance["status"] in {"running", "stopping"} or instance["id"] in self._runtimes:
            raise RuntimeError("job is already running")

    def _job_task_id(self, job: dict[str, Any]) -> str:
        task_id = job.get("current_task_id") or job.get("last_task_id")
        if task_id:
            return task_id
        latest_task = self.store.get_latest_task(job["id"])
        return latest_task["id"] if latest_task else ""

    def _job_artifact(self, job_id: str, artifact_id: str) -> tuple[str, dict[str, Any], Path]:
        job = self.store.get_instance(job_id)
        if not job:
            raise KeyError("job not found")
        task_id = self._job_task_id(job)
        if not task_id:
            raise KeyError("artifact not found")
        artifact = next((item for item in self.store.list_artifacts(task_id) if item["id"] == artifact_id), None)
        if not artifact:
            raise KeyError("artifact not found")
        path = self._safe_artifact_path(task_id, artifact["path"])
        return task_id, artifact, path

    def _safe_artifact_path(self, task_id: str, artifact_path: str) -> Path:
        task = self.store.get_task(task_id)
        if not task:
            raise KeyError("task not found")
        root = Path(task["artifact_dir"]).resolve()
        path = Path(artifact_path).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise RuntimeError("artifact path is outside task directory") from exc
        return path

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
            self.store.update_instance(
                instance["id"],
                status="error",
                current_task_id=None,
                last_task_id=task["id"],
                pid=None,
                last_error=message,
            )
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
            last_task_id=task["id"],
            pid=process.pid,
            last_error="",
        )
        self.store.append_log(task["id"], f"Crawler subprocess started, pid={process.pid}", "success")

    def _build_command(self, instance: dict[str, Any], task: dict[str, Any]) -> list[str]:
        params = {**instance.get("default_params", {}), **instance.get("params", {}), **task.get("params", {})}
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
                last_task_id=task["id"],
                pid=None,
                last_error=error_message,
            )
            self.store.append_log(task["id"], message, level)
            self._runtimes.pop(runtime.instance_id, None)

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

    def _iter_artifact_records(self, path: Path, limit: int = 5000):
        try:
            if path.suffix == ".jsonl":
                with path.open("r", encoding="utf-8") as f:
                    for index, line in enumerate(f):
                        if index >= limit:
                            break
                        if line.strip():
                            yield json.loads(line)
            elif path.suffix == ".json":
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                rows = data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
                for record in rows[:limit]:
                    if isinstance(record, dict):
                        yield record
            elif path.suffix == ".csv":
                with path.open("r", encoding="utf-8") as f:
                    for index, record in enumerate(csv.DictReader(f)):
                        if index >= limit:
                            break
                        yield record
        except Exception:
            return

    def _work_item(self, platform: str, record: dict[str, Any]) -> dict[str, Any]:
        work_id = self._first_record_value(record, "aweme_id", "note_id", "video_id", "bvid", "content_id", "id")
        url = self._first_record_value(
            record,
            "aweme_url",
            "note_url",
            "video_url",
            "content_url",
            "source_url",
            "url",
            "web_url",
            "link",
        )
        if not url:
            url = self._default_work_url(platform, work_id, record)
        return {
            "id": str(work_id or ""),
            "title": self._first_record_value(record, "title", "desc", "note_title", "content", "content_text", "text") or "未命名作品",
            "url": url,
            "author": self._first_record_value(record, "nickname", "user_nickname", "author_name", "author", "screen_name") or "",
            "publish_time": self._format_record_time(self._first_record_value(record, "create_time", "publish_time", "time", "created_time")),
            "source_keyword": self._first_record_value(record, "source_keyword", "keyword") or "",
            "metrics": {
                "点赞": self._first_record_value(record, "liked_count", "like_count", "voteup_count"),
                "收藏": self._first_record_value(record, "collected_count", "favorite_count", "video_favorite_count"),
                "评论": self._first_record_value(record, "comment_count", "comments_count", "video_comment"),
                "转发": self._first_record_value(record, "share_count", "shared_count", "video_share_count"),
            },
        }

    def _comment_words(self, record: dict[str, Any]) -> list[str]:
        text = self._first_record_value(record, "content", "comment_content", "text", "desc")
        if not text:
            return []
        tokens = jieba.lcut(str(text)) if jieba else re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9]{2,}", str(text))
        words: list[str] = []
        for token in tokens:
            word = token.strip().lower()
            if len(word) < 2 or word in COMMENT_STOP_WORDS or re.fullmatch(r"\d+", word):
                continue
            if not re.search(r"[\u4e00-\u9fffA-Za-z]", word):
                continue
            words.append(word)
        return words

    def _first_record_value(self, record: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = record.get(key)
            if value not in (None, ""):
                return value
        return ""

    def _metric_number(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value or "").replace(",", "").strip()
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            return 0.0
        number = float(match.group())
        if "亿" in text:
            return number * 100000000
        if "万" in text or "w" in text.lower():
            return number * 10000
        return number

    def _default_work_url(self, platform: str, work_id: Any, record: dict[str, Any] | None = None) -> str:
        if not work_id:
            return ""
        record = record or {}
        work_id = str(work_id)
        if platform == "xhs":
            token = self._first_record_value(record, "xsec_token")
            suffix = f"?xsec_token={token}&xsec_source=pc_search" if token else ""
            return f"https://www.xiaohongshu.com/explore/{work_id}{suffix}"
        if platform == "dy":
            return f"https://www.douyin.com/video/{work_id}"
        if platform == "bili":
            return f"https://www.bilibili.com/video/{work_id if work_id.upper().startswith('BV') else f'av{work_id}'}"
        if platform == "ks":
            return f"https://www.kuaishou.com/short-video/{work_id}"
        if platform == "wb":
            return f"https://m.weibo.cn/detail/{work_id}"
        if platform == "tieba":
            return f"https://tieba.baidu.com/p/{work_id}"
        if platform == "zhihu":
            question_id = self._first_record_value(record, "question_id")
            content_type = str(self._first_record_value(record, "content_type")).lower()
            if question_id:
                return f"https://www.zhihu.com/question/{question_id}/answer/{work_id}"
            if content_type == "zvideo":
                return f"https://www.zhihu.com/zvideo/{work_id}"
            return f"https://zhuanlan.zhihu.com/p/{work_id}"
        return ""

    def _format_record_time(self, value: Any) -> str:
        if value in (None, ""):
            return ""
        try:
            timestamp = float(value)
        except (TypeError, ValueError):
            return str(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

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
