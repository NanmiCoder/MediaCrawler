# -*- coding: utf-8 -*-

from fastapi.testclient import TestClient

from api.main import app
from api.routers import scheduler as scheduler_router
from api.scheduler.manager import SchedulerManager
from api.scheduler.store import SchedulerStore


def test_scheduler_api_creates_instance_and_task(monkeypatch, tmp_path):
    manager = SchedulerManager(store=SchedulerStore(tmp_path / "scheduler.db"), project_root=tmp_path)

    async def noop_start(task):
        return None

    monkeypatch.setattr(manager, "_start_task_locked", noop_start)
    monkeypatch.setattr(scheduler_router, "scheduler_manager", manager)

    client = TestClient(app)
    instance_response = client.post(
        "/api/scheduler/instances",
        json={
            "name": "小红书账号 A",
            "platform": "xhs",
            "login_type": "qrcode",
            "save_option": "jsonl",
        },
    )
    assert instance_response.status_code == 200
    instance = instance_response.json()
    assert instance["status"] == "idle"

    task_response = client.post(
        "/api/scheduler/tasks",
        json={
            "instance_id": instance["id"],
            "crawler_type": "search",
            "target_text": "编程副业",
            "params": {"max_notes_count": 5},
        },
    )
    assert task_response.status_code == 200
    task = task_response.json()
    assert task["instance_id"] == instance["id"]
    assert task["status"] == "queued"

    logs_response = client.get(f"/api/scheduler/tasks/{task['id']}/logs")
    assert logs_response.status_code == 200
