from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.schemas import CrawlerStartRequest, PlatformEnum
from api.services.crawler_manager import CrawlerManager


def request() -> CrawlerStartRequest:
    return CrawlerStartRequest(platform=PlatformEnum.XHS, keywords="重庆企业主资产配置")


@pytest.mark.asyncio
async def test_start_returns_task_id_and_clears_completion_state():
    manager = CrawlerManager()
    manager.last_exit_code = 1
    manager.finished_at = datetime.now()
    process = MagicMock()
    process.poll.return_value = None

    with patch("api.services.crawler_manager.subprocess.Popen", return_value=process):
        with patch(
            "api.services.crawler_manager.asyncio.create_task",
            side_effect=lambda coroutine: coroutine.close(),
        ):
            task_id = await manager.start(request())

    assert isinstance(task_id, str)
    assert task_id == manager.task_id
    assert manager.last_exit_code is None
    assert manager.finished_at is None
    assert manager.status == "running"


@pytest.mark.asyncio
async def test_read_output_records_exit_metadata():
    manager = CrawlerManager()
    manager.status = "running"
    manager.current_config = request()
    manager.task_id = "task-123"
    process = MagicMock()
    process.poll.side_effect = [0, 0]
    process.returncode = 0
    process.stdout.readline.return_value = ""
    process.stdout.read.return_value = ""
    manager.process = process

    await manager._read_output()

    status = manager.get_status()
    assert status["status"] == "idle"
    assert status["task_id"] == "task-123"
    assert status["last_exit_code"] == 0
    assert status["finished_at"] is not None
    assert status["platform"] is None


def test_start_endpoint_returns_task_id():
    client = TestClient(app)
    with patch(
        "api.routers.crawler.crawler_manager.start",
        new_callable=AsyncMock,
        return_value="task-123",
    ):
        response = client.post(
            "/api/crawler/start",
            json={"platform": "xhs", "keywords": "重庆企业主资产配置"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "message": "Crawler started successfully",
        "task_id": "task-123",
    }


def test_status_endpoint_serializes_completion_fields():
    client = TestClient(app)
    status = {
        "status": "idle",
        "platform": None,
        "crawler_type": None,
        "started_at": "2026-07-27T10:00:00+08:00",
        "error_message": None,
        "task_id": "task-123",
        "last_exit_code": 0,
        "finished_at": "2026-07-27T10:02:00+08:00",
    }
    with patch("api.routers.crawler.crawler_manager.get_status", return_value=status):
        response = client.get("/api/crawler/status")

    assert response.status_code == 200
    assert response.json() == status
