import asyncio
from contextlib import suppress
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


@pytest.mark.asyncio
async def test_stop_failure_keeps_active_process_and_reader():
    manager = CrawlerManager()
    manager.status = "running"
    active_config = request()
    manager.current_config = active_config
    manager.task_id = "old-task"
    process = MagicMock()
    process.poll.return_value = None
    process.send_signal.side_effect = OSError("terminate failed")
    process.kill.side_effect = OSError("kill failed")
    manager.process = process
    reader = MagicMock()
    reader.done.return_value = False
    manager._read_task = reader

    assert await manager.stop() is False

    process.kill.assert_called_once_with()
    assert manager.status == "error"
    assert manager.error_message is not None
    assert "terminate failed" in manager.error_message
    assert "kill failed" in manager.error_message
    assert manager.process is process
    assert manager._read_task is reader
    assert manager.current_config is active_config
    assert manager.last_exit_code is None
    assert manager.finished_at is None
    reader.cancel.assert_not_called()


@pytest.mark.asyncio
async def test_stop_waits_for_killed_process_and_reader_before_restart():
    manager = CrawlerManager()
    manager.status = "running"
    manager.current_config = request()
    manager.task_id = "old-task"
    process = MagicMock()
    process.returncode = None
    process.poll.side_effect = lambda: process.returncode

    def delayed_exit(timeout):
        process.returncode = -9
        return process.returncode

    process.wait.side_effect = delayed_exit
    manager.process = process

    async def monitor_output():
        await asyncio.Event().wait()

    reader = asyncio.create_task(monitor_output())
    manager._read_task = reader

    with patch(
        "api.services.crawler_manager.asyncio.sleep", new_callable=AsyncMock
    ):
        stopped = await manager.stop()

    try:
        assert stopped is True
        process.kill.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=5)
        assert manager.status == "idle"
        assert manager.current_config is None
        assert manager.last_exit_code == -9
        assert manager.finished_at is not None
        assert manager.error_message is None
        assert reader.done()
        assert reader.cancelled()
        assert manager._read_task is None

        new_process = MagicMock()
        new_process.poll.return_value = None
        with patch(
            "api.services.crawler_manager.subprocess.Popen", return_value=new_process
        ):
            with patch(
                "api.services.crawler_manager.asyncio.create_task",
                side_effect=lambda coroutine: coroutine.close(),
            ):
                task_id = await manager.start(request())

        assert task_id is not None
        assert manager.task_id == task_id
    finally:
        if not reader.done():
            reader.cancel()
        with suppress(asyncio.CancelledError):
            await reader


@pytest.mark.asyncio
async def test_old_reader_uses_its_process_and_cannot_overwrite_new_task():
    manager = CrawlerManager()
    manager.status = "running"
    manager.current_config = request()
    manager.task_id = "old-task"
    old_process = MagicMock()
    old_process.poll.side_effect = [None, 0]
    old_process.returncode = 7
    old_process.stdout.readline.return_value = "old output\n"
    old_process.stdout.read.return_value = ""
    manager.process = old_process

    new_process = MagicMock()
    new_process.poll.return_value = 0
    new_process.returncode = 0
    new_config = request()

    async def switch_to_new_task(_entry):
        manager.process = new_process
        manager.task_id = "new-task"
        manager.status = "running"
        manager.current_config = new_config
        manager.last_exit_code = None
        manager.finished_at = None

    manager._push_log = AsyncMock(side_effect=switch_to_new_task)

    await manager._read_output()

    old_process.stdout.read.assert_called_once_with()
    new_process.stdout.read.assert_not_called()
    assert manager.process is new_process
    assert manager.task_id == "new-task"
    assert manager.status == "running"
    assert manager.current_config is new_config
    assert manager.last_exit_code is None
    assert manager.finished_at is None


@pytest.mark.asyncio
async def test_read_output_error_records_terminal_metadata():
    manager = CrawlerManager()
    manager.status = "running"
    manager.current_config = request()
    manager.task_id = "task-123"
    process = MagicMock()
    process.poll.return_value = None
    process.returncode = 17
    process.stdout.readline.side_effect = RuntimeError("read failed")
    manager.process = process

    await manager._read_output()

    status = manager.get_status()
    assert status["status"] == "error"
    assert status["task_id"] == "task-123"
    assert status["last_exit_code"] == 17
    assert status["finished_at"] is not None
    assert status["error_message"] == "Error reading output: read failed"


@pytest.mark.asyncio
async def test_old_reader_error_cannot_overwrite_new_task():
    manager = CrawlerManager()
    manager.status = "running"
    manager.current_config = request()
    manager.task_id = "old-task"
    old_process = MagicMock()
    old_process.poll.return_value = None
    manager.process = old_process

    new_process = MagicMock()
    new_config = request()

    def fail_after_switch():
        manager.process = new_process
        manager.task_id = "new-task"
        manager.status = "running"
        manager.current_config = new_config
        manager.last_exit_code = None
        manager.finished_at = None
        manager._logs = []
        raise RuntimeError("old reader failed")

    old_process.stdout.readline.side_effect = fail_after_switch

    await manager._read_output()

    assert manager.logs == []
    assert manager.process is new_process
    assert manager.task_id == "new-task"
    assert manager.status == "running"
    assert manager.current_config is new_config
    assert manager.last_exit_code is None
    assert manager.finished_at is None


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
