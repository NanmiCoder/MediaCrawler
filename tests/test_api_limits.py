# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests\test_api_limits.py
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

import pytest
import config
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from cmd_arg import parse_cmd
from api.schemas import CrawlerStartRequest, PlatformEnum, LoginTypeEnum, CrawlerTypeEnum
from api.services.crawler_manager import CrawlerManager
from api.main import app


@pytest.fixture(autouse=True)
def api_authentication(monkeypatch):
    monkeypatch.setenv("MEDIACRAWLER_API_TOKEN", "test-api-limits")

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


def test_crawler_manager_passes_media_switch():
    cm = CrawlerManager()

    req_off = CrawlerStartRequest(
        platform=PlatformEnum.XHS,
        login_type=LoginTypeEnum.QRCODE,
        crawler_type=CrawlerTypeEnum.DETAIL,
        specified_ids="note-1",
    )
    cmd_off = cm._build_command(req_off)
    idx_off = cmd_off.index("--get_media")
    assert cmd_off[idx_off + 1] == "false"

    req_on = CrawlerStartRequest(
        platform=PlatformEnum.XHS,
        login_type=LoginTypeEnum.QRCODE,
        crawler_type=CrawlerTypeEnum.DETAIL,
        specified_ids="note-1",
        enable_media=True,
    )
    cmd_on = cm._build_command(req_on)
    idx_on = cmd_on.index("--get_media")
    assert cmd_on[idx_on + 1] == "true"


def test_api_schema_exposes_media_switch_default_off():
    assert CrawlerStartRequest(platform=PlatformEnum.XHS).enable_media is False

def test_api_start_crawler_with_limits():
    client = TestClient(app, headers={"Authorization": "Bearer test-api-limits"})

    with patch("api.routers.crawler.crawler_manager.start", new_callable=AsyncMock) as mock_start:
        mock_start.return_value = True

        # Test case 1: with limits
        response = client.post("/api/crawler/start", json={
            "platform": "xhs",
            "login_type": "qrcode",
            "crawler_type": "search",
            "keywords": "test",
            "max_notes_count": 50,
            "max_comments_count": 5
        })

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "message": "Crawler started successfully"}

        mock_start.assert_called_once()
        called_request = mock_start.call_args[0][0]
        assert called_request.platform == PlatformEnum.XHS
        assert called_request.max_notes_count == 50
        assert called_request.max_comments_count == 5

def test_api_start_crawler_without_limits():
    client = TestClient(app, headers={"Authorization": "Bearer test-api-limits"})

    with patch("api.routers.crawler.crawler_manager.start", new_callable=AsyncMock) as mock_start:
        mock_start.return_value = True

        # Test case 2: without limits
        response = client.post("/api/crawler/start", json={
            "platform": "xhs",
            "login_type": "qrcode",
            "crawler_type": "search",
            "keywords": "test"
        })

        assert response.status_code == 200
        mock_start.assert_called_once()
        called_request = mock_start.call_args[0][0]
        assert called_request.platform == PlatformEnum.XHS
        assert called_request.max_notes_count is None
        assert called_request.max_comments_count is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("max_notes_count", 0),
        ("max_notes_count", -1),
        ("max_notes_count", 10001),
        ("max_comments_count", 0),
        ("max_comments_count", -1),
        ("max_comments_count", 10001),
    ],
)
def test_api_rejects_invalid_limits(field_name, value):
    client = TestClient(app, headers={"Authorization": "Bearer test-api-limits"})
    payload = {
        "platform": "xhs",
        "login_type": "qrcode",
        "crawler_type": "search",
        "keywords": "test",
        field_name: value,
    }

    with patch("api.routers.crawler.crawler_manager.start", new_callable=AsyncMock) as mock_start:
        response = client.post("/api/crawler/start", json=payload)

    assert response.status_code == 422
    mock_start.assert_not_called()
