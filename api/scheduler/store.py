# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


class SchedulerStore:
    """Small SQLite store for scheduler state."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else PROJECT_ROOT / "data" / "scheduler" / "scheduler.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS instances (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    login_type TEXT NOT NULL,
                    headless INTEGER NOT NULL DEFAULT 0,
                    save_option TEXT NOT NULL,
                    browser_profile_dir TEXT NOT NULL,
                    cdp_debug_port INTEGER NOT NULL,
                    default_params_json TEXT NOT NULL,
                    crawler_type TEXT NOT NULL DEFAULT 'search',
                    target_text TEXT NOT NULL DEFAULT '',
                    params_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL,
                    current_task_id TEXT,
                    last_task_id TEXT,
                    pid INTEGER,
                    last_error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL,
                    crawler_type TEXT NOT NULL,
                    target_text TEXT NOT NULL DEFAULT '',
                    params_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    pid INTEGER,
                    exit_code INTEGER,
                    artifact_dir TEXT NOT NULL DEFAULT '',
                    error_message TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    FOREIGN KEY(instance_id) REFERENCES instances(id)
                );

                CREATE TABLE IF NOT EXISTS task_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    modified_at REAL NOT NULL,
                    record_count INTEGER,
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                );
                """
            )
            self._ensure_instance_columns(conn)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_instance_status ON tasks(instance_id, status, created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_logs_task ON task_logs(task_id, id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id)")

    def _ensure_instance_columns(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(instances)").fetchall()}
        additions = {
            "crawler_type": "ALTER TABLE instances ADD COLUMN crawler_type TEXT NOT NULL DEFAULT 'search'",
            "target_text": "ALTER TABLE instances ADD COLUMN target_text TEXT NOT NULL DEFAULT ''",
            "params_json": "ALTER TABLE instances ADD COLUMN params_json TEXT NOT NULL DEFAULT '{}'",
            "last_task_id": "ALTER TABLE instances ADD COLUMN last_task_id TEXT",
        }
        for column, statement in additions.items():
            if column not in columns:
                conn.execute(statement)

    def create_instance(
        self,
        payload: dict[str, Any],
        profile_dir: str,
        cdp_debug_port: int,
        instance_id: str | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        instance_id = instance_id or uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO instances (
                    id, name, platform, login_type, headless, save_option,
                    browser_profile_dir, cdp_debug_port, default_params_json,
                    crawler_type, target_text, params_json,
                    status, current_task_id, last_task_id, pid, last_error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'idle', NULL, NULL, NULL, '', ?, ?)
                """,
                (
                    instance_id,
                    payload["name"],
                    payload["platform"],
                    payload["login_type"],
                    1 if payload.get("headless") else 0,
                    payload["save_option"],
                    profile_dir,
                    cdp_debug_port,
                    _json_dumps(payload.get("default_params")),
                    payload.get("crawler_type", "search"),
                    payload.get("target_text", ""),
                    _json_dumps(payload.get("params")),
                    now,
                    now,
                ),
            )
        return self.get_instance(instance_id)

    def list_instances(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM instances ORDER BY created_at DESC").fetchall()
        return [self._instance_from_row(row) for row in rows]

    def get_instance(self, instance_id: str) -> Optional[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM instances WHERE id = ?", (instance_id,)).fetchone()
        return self._instance_from_row(row) if row else None

    def update_instance(self, instance_id: str, **fields: Any) -> Optional[dict[str, Any]]:
        if not fields:
            return self.get_instance(instance_id)
        allowed = {
            "name",
            "platform",
            "login_type",
            "headless",
            "save_option",
            "browser_profile_dir",
            "cdp_debug_port",
            "default_params_json",
            "crawler_type",
            "target_text",
            "params_json",
            "status",
            "current_task_id",
            "last_task_id",
            "pid",
            "last_error",
        }
        assignments: list[str] = []
        values: list[Any] = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            if key == "headless" and value is not None:
                value = 1 if value else 0
            assignments.append(f"{key} = ?")
            values.append(value)
        if not assignments:
            return self.get_instance(instance_id)
        assignments.append("updated_at = ?")
        values.append(utc_now())
        values.append(instance_id)
        with self._lock, self._connect() as conn:
            conn.execute(f"UPDATE instances SET {', '.join(assignments)} WHERE id = ?", values)
        return self.get_instance(instance_id)

    def delete_instance(self, instance_id: str) -> bool:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT status FROM instances WHERE id = ?", (instance_id,)).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM instances WHERE id = ?", (instance_id,))
        return True

    def list_cdp_ports(self) -> list[int]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT cdp_debug_port FROM instances").fetchall()
        return [int(row["cdp_debug_port"]) for row in rows if row["cdp_debug_port"]]

    def create_task(self, payload: dict[str, Any], artifact_dir: str) -> dict[str, Any]:
        now = utc_now()
        task_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                    id, instance_id, crawler_type, target_text, params_json,
                    status, pid, exit_code, artifact_dir, error_message,
                    created_at, updated_at, started_at, finished_at
                )
                VALUES (?, ?, ?, ?, ?, 'queued', NULL, NULL, ?, '', ?, ?, NULL, NULL)
                """,
                (
                    task_id,
                    payload["instance_id"],
                    payload["crawler_type"],
                    payload.get("target_text", ""),
                    _json_dumps(payload.get("params")),
                    artifact_dir,
                    now,
                    now,
                ),
            )
        return self.get_task(task_id)

    def list_tasks(self, instance_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        with self._lock, self._connect() as conn:
            if instance_id:
                rows = conn.execute(
                    "SELECT * FROM tasks WHERE instance_id = ? ORDER BY created_at DESC LIMIT ?",
                    (instance_id, limit),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._task_from_row(row) for row in rows]

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._task_from_row(row) if row else None

    def get_next_queued_task(self, instance_id: str) -> Optional[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM tasks
                WHERE instance_id = ? AND status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (instance_id,),
            ).fetchone()
        return self._task_from_row(row) if row else None

    def get_latest_task(self, instance_id: str) -> Optional[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM tasks
                WHERE instance_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (instance_id,),
            ).fetchone()
        return self._task_from_row(row) if row else None

    def update_task(self, task_id: str, **fields: Any) -> Optional[dict[str, Any]]:
        if not fields:
            return self.get_task(task_id)
        allowed = {
            "status",
            "pid",
            "exit_code",
            "artifact_dir",
            "error_message",
            "started_at",
            "finished_at",
        }
        assignments: list[str] = []
        values: list[Any] = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            assignments.append(f"{key} = ?")
            values.append(value)
        if not assignments:
            return self.get_task(task_id)
        assignments.append("updated_at = ?")
        values.append(utc_now())
        values.append(task_id)
        with self._lock, self._connect() as conn:
            conn.execute(f"UPDATE tasks SET {', '.join(assignments)} WHERE id = ?", values)
        return self.get_task(task_id)

    def append_log(self, task_id: str, message: str, level: str = "info") -> dict[str, Any]:
        timestamp = utc_now()
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO task_logs (task_id, timestamp, level, message) VALUES (?, ?, ?, ?)",
                (task_id, timestamp, level, message),
            )
            log_id = int(cursor.lastrowid)
        return {
            "id": log_id,
            "task_id": task_id,
            "timestamp": timestamp,
            "level": level,
            "message": message,
        }

    def list_logs(self, task_id: str, limit: int = 300) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM (
                    SELECT * FROM task_logs
                    WHERE task_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                ) ORDER BY id ASC
                """,
                (task_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def replace_artifacts(self, task_id: str, artifacts: Iterable[dict[str, Any]]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM artifacts WHERE task_id = ?", (task_id,))
            conn.executemany(
                """
                INSERT INTO artifacts (id, task_id, path, type, size, modified_at, record_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        artifact.get("id") or uuid.uuid4().hex,
                        task_id,
                        artifact["path"],
                        artifact["type"],
                        artifact["size"],
                        artifact["modified_at"],
                        artifact.get("record_count"),
                    )
                    for artifact in artifacts
                ],
            )

    def list_artifacts(self, task_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM artifacts WHERE task_id = ? ORDER BY modified_at DESC",
                (task_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def scheduler_counts(self) -> dict[str, int]:
        with self._lock, self._connect() as conn:
            instances_total = conn.execute("SELECT COUNT(*) FROM instances").fetchone()[0]
            running_instances = conn.execute("SELECT COUNT(*) FROM instances WHERE status = 'running'").fetchone()[0]
            queued_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'queued'").fetchone()[0]
            running_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'running'").fetchone()[0]
        return {
            "instances_total": int(instances_total),
            "running_instances": int(running_instances),
            "queued_tasks": int(queued_tasks),
            "running_tasks": int(running_tasks),
        }

    def _instance_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["headless"] = bool(data["headless"])
        data["default_params"] = _json_loads(data.pop("default_params_json", None))
        data["params"] = _json_loads(data.pop("params_json", None))
        return data

    def _task_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["params"] = _json_loads(data.pop("params_json", None))
        return data
