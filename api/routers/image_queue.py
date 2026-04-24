# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

"""
Image queue management API routes.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from ..services import image_queue_service, image_task_db, image_scheduler
from ..services.image_task_db import TaskPriority


router = APIRouter(prefix="/image-queue", tags=["image-queue"])


class EnqueueRequest(BaseModel):
    """Request to enqueue an image download task."""
    url: str
    priority: Optional[str] = Field(default="medium", description="high, medium, or low")


class EnqueueResponse(BaseModel):
    """Response for enqueue request."""
    success: bool
    message: str


class StatsResponse(BaseModel):
    """Response for queue stats."""
    queue_size: int
    max_size: int
    consumer_count: int
    running: bool
    pending: int
    downloading: int
    completed: int
    failed: int
    # Scheduler status
    scheduler_running: bool
    scheduler_interval: int
    scheduler_last_scan: Optional[str] = None


@router.post("/enqueue", response_model=EnqueueResponse)
async def enqueue_download(request: EnqueueRequest):
    """
    Add an image URL to the download queue.

    Args:
        request: The enqueue request with URL and optional priority

    Returns:
        EnqueueResponse indicating success or failure
    """
    # Validate priority
    try:
        priority = TaskPriority(request.priority.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid priority: {request.priority}. Must be one of: high, medium, low"
        )

    success = await image_queue_service.enqueue(request.url, priority)

    if success:
        return EnqueueResponse(success=True, message=f"Enqueued: {request.url}")
    else:
        return EnqueueResponse(success=False, message=f"URL already exists or queue full: {request.url}")


@router.get("/stats", response_model=StatsResponse)
async def get_queue_stats():
    """
    Get queue statistics.

    Returns:
        StatsResponse with queue and task counts
    """
    queue_stats = image_queue_service.get_stats()
    db_stats = await image_task_db.get_stats()
    scheduler_stats = image_scheduler.get_stats()

    return StatsResponse(
        queue_size=queue_stats["queue_size"],
        max_size=queue_stats["max_size"],
        consumer_count=queue_stats["consumer_count"],
        running=queue_stats["running"],
        pending=db_stats.get("pending", 0),
        downloading=db_stats.get("downloading", 0),
        completed=db_stats.get("completed", 0),
        failed=db_stats.get("failed", 0),
        scheduler_running=scheduler_stats["running"],
        scheduler_interval=scheduler_stats["scan_interval"],
        scheduler_last_scan=scheduler_stats.get("last_scan_at")
    )


@router.post("/load-from-db")
async def load_from_database():
    """
    Load pending tasks from database into queue.

    Returns:
        Number of tasks loaded
    """
    count = await image_queue_service.enqueue_from_db()
    return {"loaded": count}
