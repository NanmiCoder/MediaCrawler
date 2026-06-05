# -*- coding: utf-8 -*-
"""insight 的 SQLite 访问层：运行记录与上游表计数。"""

import os
import sqlite3
import time
from typing import List, Dict, Optional

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

# 仅允许对这些上游表做计数，避免 SQL 注入
_COUNTABLE_TABLES = {"xhs_note", "xhs_note_comment"}


class InsightDB:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            ddl = f.read()
        with self._connect() as conn:
            conn.executescript(ddl)

    def start_run(self, job_name: str, crawler_type: str) -> int:
        now = int(time.time())
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO insight_runs (job_name, crawler_type, started_ts, status) "
                "VALUES (?, ?, ?, 'running')",
                (job_name, crawler_type, now),
            )
            return int(cur.lastrowid)

    def finish_run(
        self,
        run_id: int,
        *,
        exit_code: Optional[int],
        status: str,
        notes_crawled: int = 0,
        comments_crawled: int = 0,
        error_msg: Optional[str] = None,
    ) -> None:
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                "UPDATE insight_runs SET finished_ts=?, exit_code=?, status=?, "
                "notes_crawled=?, comments_crawled=?, error_msg=? WHERE id=?",
                (now, exit_code, status, notes_crawled, comments_crawled, error_msg, run_id),
            )

    def count_rows(self, table: str) -> int:
        if table not in _COUNTABLE_TABLES:
            raise ValueError(f"count_rows: table {table!r} not allowed")
        with self._connect() as conn:
            try:
                row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
            except sqlite3.OperationalError:
                return 0  # 表尚未由上游 --init_db 创建
            return int(row["c"])

    def recent_runs(self, limit: int = 20) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM insight_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
