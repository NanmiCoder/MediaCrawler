# -*- coding: utf-8 -*-
"""纯数据层：从 database/sqlite_tables.db 读取小红书笔记与评论。

不导入 Streamlit，方便单测。
"""
from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import Any

# 与上游约定一致：数据库固定路径（不读 .env）
DB_PATH = Path(__file__).resolve().parents[2] / "database" / "sqlite_tables.db"


def format_ts(ts: int | None) -> str:
    """将 Unix 时间戳格式化为 'YYYY-MM-DD HH:MM'。None/0 返回 '—'。

    DB 实际存储毫秒级时间戳（13 位），同时兼容秒级（10 位）以方便测试。
    判定阈值 1e12（≈ 33658 年的秒数，远大于任何合理秒级时间戳）。
    """
    if not ts:
        return "—"
    # 兼容毫秒与秒：> 1e12 视为毫秒
    seconds = ts / 1000 if ts > 1e12 else ts
    return datetime.datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M")


def load_notes(db_path: Path | None = None) -> list[dict[str, Any]]:
    """加载所有笔记，按发布时间 time 倒序。db_path=None 时使用 DB_PATH。"""
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT note_id, title, liked_count, comment_count, time, "
            "source_keyword, nickname, desc "
            "FROM xhs_note ORDER BY time DESC"
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def load_comments(note_id: str, db_path: Path | None = None) -> list[dict[str, Any]]:
    """加载指定笔记的评论，按 create_time 升序。db_path=None 时使用 DB_PATH。"""
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT comment_id, note_id, nickname, content, like_count, create_time "
            "FROM xhs_note_comment WHERE note_id = ? ORDER BY create_time ASC",
            (note_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()