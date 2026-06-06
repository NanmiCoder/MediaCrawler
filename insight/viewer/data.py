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
    """将 Unix 时间戳（秒）格式化为 'YYYY-MM-DD HH:MM'。None/0 返回 '—'。"""
    raise NotImplementedError


def load_notes() -> list[dict[str, Any]]:
    """加载所有笔记，按发布时间 time 倒序。"""
    raise NotImplementedError


def load_comments(note_id: str) -> list[dict[str, Any]]:
    """加载指定笔记的评论，按 create_time 升序。"""
    raise NotImplementedError