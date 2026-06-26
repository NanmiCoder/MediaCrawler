# -*- coding: utf-8 -*-

from fastapi import APIRouter, HTTPException, Query

from api.scheduler.manager import scheduler_manager
from api.scheduler.schemas import (
    ArtifactResponse,
    InstanceCreateRequest,
    InstanceResponse,
    InstanceUpdateRequest,
    SchedulerStatusResponse,
    TaskCreateRequest,
    TaskLogResponse,
    TaskResponse,
)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/status", response_model=SchedulerStatusResponse)
async def scheduler_status():
    return scheduler_manager.status()


@router.get("/instances", response_model=list[InstanceResponse])
async def list_instances():
    return scheduler_manager.list_instances()


@router.post("/instances", response_model=InstanceResponse)
async def create_instance(request: InstanceCreateRequest):
    return scheduler_manager.create_instance(request)


@router.get("/instances/{instance_id}", response_model=InstanceResponse)
async def get_instance(instance_id: str):
    instance = scheduler_manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    return instance


@router.patch("/instances/{instance_id}", response_model=InstanceResponse)
async def update_instance(instance_id: str, request: InstanceUpdateRequest):
    try:
        instance = await scheduler_manager.update_instance(instance_id, request)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    return instance


@router.delete("/instances/{instance_id}")
async def delete_instance(instance_id: str):
    try:
        deleted = await scheduler_manager.delete_instance(instance_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Instance not found")
    return {"status": "ok", "message": "Instance deleted"}


@router.post("/instances/{instance_id}/login", response_model=TaskResponse)
async def login_instance(instance_id: str):
    try:
        return await scheduler_manager.create_login_task(instance_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Instance not found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    instance_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    return scheduler_manager.list_tasks(instance_id=instance_id, limit=limit)


@router.post("/tasks", response_model=TaskResponse)
async def create_task(request: TaskCreateRequest):
    try:
        return await scheduler_manager.create_task(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Instance not found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    task = scheduler_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/start", response_model=TaskResponse)
async def start_task(task_id: str):
    try:
        task = await scheduler_manager.start_task(task_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: str):
    task = await scheduler_manager.cancel_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks/{task_id}/logs", response_model=list[TaskLogResponse])
async def list_task_logs(task_id: str, limit: int = Query(default=300, ge=1, le=1000)):
    if not scheduler_manager.get_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return scheduler_manager.list_logs(task_id, limit=limit)


@router.get("/tasks/{task_id}/artifacts", response_model=list[ArtifactResponse])
async def list_task_artifacts(task_id: str):
    if not scheduler_manager.get_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return scheduler_manager.list_artifacts(task_id)
