# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

"""
Image scheduler service for timeout detection and retry scheduling.
Runs as a background asyncio task, scanning periodically.
"""
import asyncio
from datetime import datetime
from typing import Optional

from .image_task_db import image_task_db
from .image_queue import image_queue_service


# Configuration constants (per user decisions D-01, D-02)
SCAN_INTERVAL = 300  # 5 minutes (D-01)
TIMEOUT_THRESHOLD = 120  # seconds (D-02)


class ImageSchedulerService:
    """
    Scheduler service that periodically scans for:
    - Timeout tasks (downloading too long)
    - Retry tasks (next_retry_at has passed)
    """

    def __init__(self, scan_interval: int = SCAN_INTERVAL, timeout_threshold: int = TIMEOUT_THRESHOLD):
        self._scan_interval = scan_interval
        self._timeout_threshold = timeout_threshold
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_scan_at: Optional[datetime] = None

    def start(self) -> None:
        """Start the scheduler loop."""
        if self._running:
            return
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        print(f"[ImageScheduler] Started, interval: {self._scan_interval}s, timeout: {self._timeout_threshold}s")

    def stop(self) -> None:
        """Stop the scheduler loop."""
        if not self._running:
            return
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                asyncio.get_event_loop().run_until_complete(self._scheduler_task)
            except asyncio.CancelledError:
                pass
        self._scheduler_task = None
        print("[ImageScheduler] Stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that runs every scan_interval seconds."""
        print("[ImageScheduler] Started scheduler loop")
        while self._running:
            try:
                await self._run_scan()
                self._last_scan_at = datetime.now()
                await asyncio.sleep(self._scan_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ImageScheduler] Error in scan: {e}")
                await asyncio.sleep(60)  # Backoff on error
        print("[ImageScheduler] Stopped scheduler loop")

    async def _run_scan(self) -> None:
        """
        Run a single scan cycle:
        1. Detect timeout tasks and mark as failed
        2. Clear next_retry_at for ready retry tasks
        3. Load pending tasks (including cleared retry tasks) into queue
        """
        timeout_count = await self._scan_timeout_tasks()
        retry_count = await self._scan_retry_tasks()
        loaded_count = await image_queue_service.enqueue_from_db()
        if timeout_count > 0 or retry_count > 0 or loaded_count > 0:
            print(f"[ImageScheduler] Scan result: timeout={timeout_count}, retry_cleared={retry_count}, loaded={loaded_count}")

    async def _scan_timeout_tasks(self) -> int:
        """
        Find tasks that have been downloading for too long and mark as failed.

        Returns:
            Number of timeout tasks found
        """
        timeout_tasks = await image_task_db.get_timeout_tasks(self._timeout_threshold)
        for task in timeout_tasks:
            await image_task_db.mark_failed(task.id, "Download timeout")
        return len(timeout_tasks)

    async def _scan_retry_tasks(self) -> int:
        """
        Find tasks ready for retry and clear their next_retry_at.
        The cleared tasks will be picked up by enqueue_from_db() in _run_scan().

        Returns:
            Number of retry tasks cleared
        """
        retry_tasks = await image_task_db.get_ready_retry_tasks()
        for task in retry_tasks:
            await image_task_db.clear_next_retry_at(task.id)
        return len(retry_tasks)

    def get_stats(self) -> dict:
        """
        Get scheduler status.

        Returns:
            Dict with running status, config, and last scan time
        """
        return {
            "running": self._running,
            "scan_interval": self._scan_interval,
            "timeout_threshold": self._timeout_threshold,
            "last_scan_at": self._last_scan_at.isoformat() if self._last_scan_at else None
        }


# Global singleton
image_scheduler = ImageSchedulerService()
