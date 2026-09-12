# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_douyin_search_start_page.py
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

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import config
from media_platform.douyin import core as douyin_core
from media_platform.douyin.core import DouYinCrawler


def _page(logid: str, *aweme_ids: str) -> dict:
    return {
        "data": [{"aweme_info": {"aweme_id": aweme_id}} for aweme_id in aweme_ids],
        "extra": {"logid": logid},
    }


def _make_crawler(monkeypatch, responses, start_page: int, max_notes: int):
    monkeypatch.setattr(config, "KEYWORDS", "test")
    monkeypatch.setattr(config, "START_PAGE", start_page)
    monkeypatch.setattr(config, "CRAWLER_MAX_NOTES_COUNT", max_notes)
    monkeypatch.setattr(config, "CRAWLER_MAX_SLEEP_SEC", 0)
    monkeypatch.setattr(config, "PUBLISH_TIME_TYPE", 0)

    stored = []

    async def fake_store(aweme_item):
        stored.append(aweme_item["aweme_id"])

    monkeypatch.setattr(douyin_core.douyin_store, "update_douyin_aweme", fake_store)

    crawler = DouYinCrawler()
    crawler.dy_client = SimpleNamespace(search_info_by_keyword=AsyncMock(side_effect=responses))
    crawler.get_aweme_media = AsyncMock()
    crawler.batch_get_note_comments = AsyncMock()
    return crawler, stored


@pytest.mark.asyncio
async def test_start_page_greater_than_one_chains_search_id(monkeypatch):
    crawler, stored = _make_crawler(
        monkeypatch,
        responses=[_page("logid-1", "a1"), _page("logid-2", "b1")],
        start_page=2,
        max_notes=10,
    )

    await crawler.search()

    calls = crawler.dy_client.search_info_by_keyword.call_args_list
    assert [(c.kwargs["offset"], c.kwargs["search_id"]) for c in calls] == [
        (0, ""),
        (10, "logid-1"),
    ]
    assert stored == ["b1"]


@pytest.mark.asyncio
async def test_default_start_page_requests_first_page_only_once(monkeypatch):
    crawler, stored = _make_crawler(
        monkeypatch,
        responses=[_page("logid-1", "a1")],
        start_page=1,
        max_notes=10,
    )

    await crawler.search()

    calls = crawler.dy_client.search_info_by_keyword.call_args_list
    assert [(c.kwargs["offset"], c.kwargs["search_id"]) for c in calls] == [(0, "")]
    assert stored == ["a1"]
