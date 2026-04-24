# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

"""
Image download queue service with multiple consumers.
Uses asyncio.Queue for producer-consumer pattern.
"""
import asyncio
from datetime import datetime
from typing import List, Optional

from .image_task_db import ImageTask, TaskStatus, TaskPriority, image_task_db
from .image_downloader import image_downloader


# Configuration
QUEUE_MAX_SIZE = 300
CONSUMER_COUNT = 3


class ImageQueueService:
    """Service that manages an asyncio.Queue for image download tasks."""

    def __init__(self, queue_size: int = QUEUE_MAX_SIZE, consumer_count: int = CONSUMER_COUNT):
        self._queue_size = queue_size
        self._consumer_count = consumer_count
        self._queue: Optional[asyncio.Queue] = None
        self._consumers: List[asyncio.Task] = []
        self._running = False

    @property
    def queue_size(self) -> int:
        if self._queue is None:
            return 0
        return self._queue.qsize()

    def start(self) -> None:
        if self._running:
            return
        self._queue = asyncio.Queue(maxsize=self._queue_size)
        self._running = True
        for i in range(self._consumer_count):
            consumer = asyncio.create_task(self._consumer_loop(i))
            self._consumers.append(consumer)
        print(f"[ImageQueue] Started with {self._consumer_count} consumers, queue size: {self._queue_size}")

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        for consumer in self._consumers:
            consumer.cancel()
        for consumer in self._consumers:
            try:
                asyncio.get_event_loop().run_until_complete(consumer)
            except asyncio.CancelledError:
                pass
        self._consumers.clear()
        self._queue = None
        print("[ImageQueue] Stopped")

    async def enqueue(self, url: str, priority: TaskPriority = TaskPriority.MEDIUM) -> bool:
        existing = await image_task_db.get_task_by_url(url)
        if existing:
            print(f"[ImageQueue] URL already exists: {url}")
            return False
        try:
            task_id = await image_task_db.add_task(url, priority)
            task = ImageTask(
                id=task_id, url=url, status=TaskStatus.PENDING, priority=priority,
                retry_count=0, created_at=datetime.now(), updated_at=datetime.now()
            )
            self._queue.put_nowait(task)
            print(f"[ImageQueue] Enqueued: {url} (priority: {priority.value})")
            return True
        except Exception as e:
            print(f"[ImageQueue] Failed to enqueue {url}: {e}")
            return False

    async def enqueue_from_db(self) -> int:
        if self._queue is None:
            return 0
        count = 0
        while self._queue.qsize() < self._queue_size:
            task = await image_task_db.get_pending_task()
            if task is None:
                break
            await image_task_db.update_status(task.id, TaskStatus.DOWNLOADING)
            try:
                self._queue.put_nowait(task)
                count += 1
            except asyncio.QueueFull:
                await image_task_db.update_status(task.id, TaskStatus.PENDING)
                break
        if count > 0:
            print(f"[ImageQueue] Loaded {count} tasks from database")
        return count

    def get_stats(self) -> dict:
        return {
            "queue_size": self.queue_size, "max_size": self._queue_size,
            "consumer_count": self._consumer_count, "running": self._running
        }

    async def _consumer_loop(self, consumer_id: int) -> None:
        print(f"[ImageQueue] Consumer {consumer_id} started")
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process_task(task, consumer_id)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ImageQueue] Consumer {consumer_id} error: {e}")
                await asyncio.sleep(1.0)
        print(f"[ImageQueue] Consumer {consumer_id} stopped")

    async def _process_task(self, task: ImageTask, consumer_id: int) -> None:
        print(f"[ImageQueue] Consumer {consumer_id} processing task {task.id}: {task.url}")
        await image_task_db.update_status(task.id, TaskStatus.DOWNLOADING)
        interval = image_downloader.get_jitter_interval()
        await asyncio.sleep(interval)
        result = await image_downloader.download(task.url)
        if result.success:
            await image_task_db.mark_completed(task.id, result.local_path)
            print(f"[ImageQueue] Consumer {consumer_id} completed task {task.id}")
        else:
            await image_task_db.mark_failed(task.id, result.error)
            print(f"[ImageQueue] Consumer {consumer_id} failed task {task.id}: {result.error}")

image_queue_service = ImageQueueService()
