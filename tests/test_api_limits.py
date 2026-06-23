# -*- coding: utf-8 -*-
import pytest
import config
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from cmd_arg import parse_cmd
from api.schemas import CrawlerStartRequest, PlatformEnum, LoginTypeEnum, CrawlerTypeEnum
from api.services.crawler_manager import CrawlerManager
from api.main import app


@pytest.fixture
def scrape_client(monkeypatch, tmp_path):
    monkeypatch.delenv("DY_API_KEY", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("DY_API_AUTH_REQUIRED", "0")

    task_manager = MagicMock()
    task_manager.create_task.return_value = SimpleNamespace(
        task_id="limits-task",
        workspace=str(tmp_path / "limits-task"),
    )
    client = TestClient(app)
    with patch("api.routes.get_task_manager", return_value=task_manager):
        yield client, task_manager
    client.close()


@pytest.mark.asyncio
async def test_cmd_arg_crawler_max_notes_count():
    # Store original values
    orig_notes = config.CRAWLER_MAX_NOTES_COUNT
    orig_comments = config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES

    try:
        await parse_cmd([
            "--platform", "xhs",
            "--crawler_max_notes_count", "42",
            "--max_comments_count_singlenotes", "24"
        ])
        assert config.CRAWLER_MAX_NOTES_COUNT == 42
        assert config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES == 24
    finally:
        config.CRAWLER_MAX_NOTES_COUNT = orig_notes
        config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = orig_comments

def test_crawler_manager_build_command():
    cm = CrawlerManager()

    # 1. No max limits passed in API request
    req1 = CrawlerStartRequest(
        platform=PlatformEnum.XHS,
        login_type=LoginTypeEnum.QRCODE,
        crawler_type=CrawlerTypeEnum.SEARCH,
        keywords="test",
        max_notes_count=None,
        max_comments_count=None
    )
    cmd1 = cm._build_command(req1)
    # Check that the custom arguments are NOT present
    assert "--crawler_max_notes_count" not in cmd1
    assert "--max_comments_count_singlenotes" not in cmd1

    # 2. Both limits passed in API request
    req2 = CrawlerStartRequest(
        platform=PlatformEnum.XHS,
        login_type=LoginTypeEnum.QRCODE,
        crawler_type=CrawlerTypeEnum.SEARCH,
        keywords="test",
        max_notes_count=50,
        max_comments_count=5
    )
    cmd2 = cm._build_command(req2)
    # Check that they are correctly added
    assert "--crawler_max_notes_count" in cmd2
    idx_notes = cmd2.index("--crawler_max_notes_count")
    assert cmd2[idx_notes + 1] == "50"

    assert "--max_comments_count_singlenotes" in cmd2
    idx_comments = cmd2.index("--max_comments_count_singlenotes")
    assert cmd2[idx_comments + 1] == "5"

def test_scrape_search_with_limits(scrape_client):
    client, task_manager = scrape_client

    legacy_response = client.post("/api/crawler/start", json={})
    assert legacy_response.status_code == 404

    response = client.post("/scrape/search", json={
        "keywords": ["test"],
        "max_count": 50,
    })

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "limits-task",
        "status": "submitted",
        "type": "search",
    }
    task_manager.create_task.assert_called_once_with(
        "search",
        params={
            "keywords": ["test"],
            "max_count": 50,
            "project_dir": None,
        },
    )
    task_manager.submit.assert_called_once()


def test_scrape_search_without_limits(scrape_client):
    client, task_manager = scrape_client

    response = client.post("/scrape/search", json={
        "keywords": ["test"],
    })

    assert response.status_code == 200
    task_manager.create_task.assert_called_once_with(
        "search",
        params={
            "keywords": ["test"],
            "max_count": 20,
            "project_dir": None,
        },
    )
    task_manager.submit.assert_called_once()


@pytest.mark.parametrize(
    ("path", "payload", "field_name", "value"),
    [
        ("/scrape/search", {"keywords": ["test"]}, "max_count", 0),
        ("/scrape/search", {"keywords": ["test"]}, "max_count", -1),
        ("/scrape/search", {"keywords": ["test"]}, "max_count", 201),
        ("/scrape/comments", {}, "max_comments_per_video", 0),
        ("/scrape/comments", {}, "max_comments_per_video", -1),
        ("/scrape/comments", {}, "max_comments_per_video", 5001),
    ],
)
def test_scrape_rejects_invalid_limits(
    scrape_client,
    path,
    payload,
    field_name,
    value,
):
    client, task_manager = scrape_client
    request_payload = {**payload, field_name: value}
    response = client.post(path, json=request_payload)

    assert response.status_code == 422
    task_manager.create_task.assert_not_called()
    task_manager.submit.assert_not_called()
