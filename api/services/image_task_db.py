# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/services/image_task_db.py
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
Image task database service using SQLite.
Manages download task state, retries, and priority queue.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

import aiosqlite


# Default database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "image_tasks.db"


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(str, Enum):
    """Task priority enumeration."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ImageTask:
    """Image download task data class."""
    id: int
    url: str
    status: TaskStatus
    priority: TaskPriority
    retry_count: int
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    local_path: Optional[str] = None
    next_retry_at: Optional[datetime] = None


class ImageTaskDB:
    """
    SQLite-based task database for image downloads.

    Features:
    - Task CRUD operations
    - Priority-based task ordering
    - Exponential backoff retry
    - Deduplication by URL
    """

    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._lock = asyncio.Lock()

    async def init_db(self) -> None:
        """Create tables and indexes."""
        # Ensure data directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS image_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error_message TEXT,
                    local_path TEXT,
                    next_retry_at TEXT
                )
            ''')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_status ON image_tasks(status)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_priority ON image_tasks(priority)')
            await db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_url ON image_tasks(url)')
            await db.commit()
        print(f"[ImageTaskDB] Database initialized at {self._db_path}")

    async def add_task(self, url: str, priority: TaskPriority = TaskPriority.MEDIUM) -> int:
        """
        Add new task.

        Args:
            url: Image URL to download
            priority: Task priority (high/medium/low)

        Returns:
            Task ID

        Raises:
            IntegrityError: If URL already exists
        """
        now = datetime.now().isoformat()
        async with self._lock:
            async with aiosqlite.connect(self._db_path) as db:
                cursor = await db.execute('''
                    INSERT INTO image_tasks (url, status, priority, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (url, TaskStatus.PENDING.value, priority.value, now, now))
                await db.commit()
                return cursor.lastrowid

    async def get_task_by_url(self, url: str) -> Optional[ImageTask]:
        """Get task by URL for deduplication check."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM image_tasks WHERE url = ?', (url,))
            row = await cursor.fetchone()
            return self._row_to_task(row) if row else None

    async def get_pending_task(self) -> Optional[ImageTask]:
        """Get next pending task ordered by priority (high > medium > low)."""
        async with self._lock:
            async with aiosqlite.connect(self._db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute('''
                    SELECT * FROM image_tasks
                    WHERE status = ?
                    ORDER BY
                        CASE priority
                            WHEN 'high' THEN 0
                            WHEN 'medium' THEN 1
                            WHEN 'low' THEN 2
                        END,
                        created_at ASC
                    LIMIT 1
                ''', (TaskStatus.PENDING.value,))
                row = await cursor.fetchone()
                return self._row_to_task(row) if row else None

    async def update_status(self, task_id: int, status: TaskStatus, error_message: Optional[str] = None) -> None:
        """Update task status."""
        now = datetime.now().isoformat()
        async with self._lock:
            async with aiosqlite.connect(self._db_path) as db:
                if error_message:
                    await db.execute('''
                        UPDATE image_tasks SET status = ?, updated_at = ?, error_message = ?
                        WHERE id = ?
                    ''', (status.value, now, error_message, task_id))
                else:
                    await db.execute('''
                        UPDATE image_tasks SET status = ?, updated_at = ?
                        WHERE id = ?
                    ''', (status.value, now, task_id))
                await db.commit()

    async def mark_completed(self, task_id: int, local_path: str) -> None:
        """Mark task as completed with local path."""
        now = datetime.now().isoformat()
        async with self._lock:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute('''
                    UPDATE image_tasks
                    SET status = ?, updated_at = ?, local_path = ?
                    WHERE id = ?
                ''', (TaskStatus.COMPLETED.value, now, local_path, task_id))
                await db.commit()

    async def mark_failed(self, task_id: int, error: str, max_retries: int = 5) -> None:
        """Mark task as failed, schedule retry with exponential backoff if under max retries."""
        now = datetime.now()
        async with self._lock:
            async with aiosqlite.connect(self._db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute('SELECT retry_count FROM image_tasks WHERE id = ?', (task_id,))
                row = await cursor.fetchone()
                retry_count = row['retry_count'] if row else 0

                if retry_count < max_retries:
                    # Schedule for retry with exponential backoff
                    next_delay = 2 ** retry_count  # 1s, 2s, 4s, 8s...
                    next_retry_at = now + timedelta(seconds=next_delay)
                    await db.execute('''
                        UPDATE image_tasks
                        SET status = ?, updated_at = ?, error_message = ?,
                            retry_count = retry_count + 1, next_retry_at = ?
                        WHERE id = ?
                    ''', (TaskStatus.PENDING.value, now.isoformat(), error, next_retry_at.isoformat(), task_id))
                else:
                    # Max retries exceeded
                    await db.execute('''
                        UPDATE image_tasks
                        SET status = ?, updated_at = ?, error_message = ?
                        WHERE id = ?
                    ''', (TaskStatus.FAILED.value, now.isoformat(), error, task_id))
                await db.commit()

    async def get_stats(self) -> dict:
        """Get queue statistics."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute('''
                SELECT status, COUNT(*) as count FROM image_tasks GROUP BY status
            ''')
            rows = await cursor.fetchall()
            stats = {TaskStatus.PENDING.value: 0, TaskStatus.DOWNLOADING.value: 0,
                     TaskStatus.COMPLETED.value: 0, TaskStatus.FAILED.value: 0}
            for row in rows:
                stats[row[0]] = row[1]
            return stats

    def _row_to_task(self, row: aiosqlite.Row) -> ImageTask:
        """Convert database row to ImageTask."""
        return ImageTask(
            id=row['id'],
            url=row['url'],
            status=TaskStatus(row['status']),
            priority=TaskPriority(row['priority']),
            retry_count=row['retry_count'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            error_message=row['error_message'],
            local_path=row['local_path'],
            next_retry_at=datetime.fromisoformat(row['next_retry_at']) if row['next_retry_at'] else None
        )


# Global singleton
image_task_db = ImageTaskDB()
