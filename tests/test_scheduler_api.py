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


def test_scheduler_api_creates_and_runs_job(monkeypatch, tmp_path):
    manager = SchedulerManager(store=SchedulerStore(tmp_path / "scheduler.db"), project_root=tmp_path)

    async def noop_start(task):
        return None

    monkeypatch.setattr(manager, "_start_task_locked", noop_start)
    monkeypatch.setattr(scheduler_router, "scheduler_manager", manager)

    client = TestClient(app)
    job_response = client.post(
        "/api/scheduler/jobs",
        json={
            "name": "小红书作业 A",
            "platform": "xhs",
            "login_type": "qrcode",
            "save_option": "jsonl",
            "crawler_type": "search",
            "target_text": "AI 工具",
            "params": {"max_notes_count": 5},
        },
    )
    assert job_response.status_code == 200
    job = job_response.json()
    assert job["crawler_type"] == "search"
    assert job["target_text"] == "AI 工具"
    assert job["params"] == {"max_notes_count": 5}

    run_response = client.post(f"/api/scheduler/jobs/{job['id']}/run")
    assert run_response.status_code == 200
    task = run_response.json()
    assert task["instance_id"] == job["id"]
    assert task["target_text"] == "AI 工具"

    refreshed_job = client.get(f"/api/scheduler/jobs/{job['id']}").json()
    assert refreshed_job["last_task_id"] == task["id"]
    assert client.get(f"/api/scheduler/jobs/{job['id']}/logs").status_code == 200
    assert client.get(f"/api/scheduler/jobs/{job['id']}/artifacts").status_code == 200


def test_scheduler_api_deletes_job_artifact(monkeypatch, tmp_path):
    manager = SchedulerManager(store=SchedulerStore(tmp_path / "scheduler.db"), project_root=tmp_path)
    monkeypatch.setattr(scheduler_router, "scheduler_manager", manager)

    client = TestClient(app)
    job = client.post(
        "/api/scheduler/jobs",
        json={"name": "小红书作业 A", "platform": "xhs", "save_option": "jsonl"},
    ).json()
    artifact_dir = tmp_path / "artifacts" / "task-a"
    artifact_dir.mkdir(parents=True)
    artifact_file = artifact_dir / "data.jsonl"
    artifact_file.write_text('{"id": 1}\n', encoding="utf-8")
    task = manager.store.create_task(
        {"instance_id": job["id"], "crawler_type": "search", "target_text": "", "params": {}},
        str(artifact_dir),
    )
    manager.store.update_instance(job["id"], last_task_id=task["id"])
    manager.store.replace_artifacts(task["id"], manager._scan_artifacts(artifact_dir))
    artifact = manager.store.list_artifacts(task["id"])[0]

    response = client.delete(f"/api/scheduler/jobs/{job['id']}/artifacts/{artifact['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert not artifact_file.exists()
