# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_weibo_search_pagination_end.py
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

from unittest.mock import AsyncMock

import httpx
import pytest
from tenacity import RetryError, wait_fixed

from media_platform.weibo.client import WeiboClient
from media_platform.weibo.exception import DataFetchError, NoMoreResultsError


class FakeAsyncClient:
    def __init__(self, request_impl):
        self.request_impl = request_impl

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def request(self, *args, **kwargs):
        return await self.request_impl(*args, **kwargs)


def make_client():
    client = WeiboClient(
        headers={"Cookie": "SUB=test"},
        playwright_page=object(),
        cookie_dict={},
    )
    client._refresh_proxy_if_expired = AsyncMock()
    return client


def patch_transport(monkeypatch, payload):
    calls = {"count": 0}

    async def request_impl(method, url, **kwargs):
        calls["count"] += 1
        return httpx.Response(200, json=payload, request=httpx.Request(method, url))

    monkeypatch.setattr(
        "media_platform.weibo.client.make_async_client",
        lambda **kwargs: FakeAsyncClient(request_impl),
    )
    return calls


@pytest.mark.asyncio
async def test_end_of_results_raises_no_more_results_without_retry(monkeypatch):
    """翻到最后一页时微博返回 ok=0/"这里还没有内容",应识别为分页结束而非可重试的错误。"""
    calls = patch_transport(
        monkeypatch, {"ok": 0, "msg": "这里还没有内容", "data": {"cards": []}}
    )

    with pytest.raises(NoMoreResultsError):
        await make_client().get("/api/container/getIndex", {"page": 18})

    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_genuine_error_still_raises_data_fetch_error(monkeypatch):
    """非"无更多内容"的 ok=0 仍应按原有逻辑视为错误并重试。"""
    calls = patch_transport(monkeypatch, {"ok": 0, "msg": "请求过于频繁"})
    # Drop the 3s backoff so the retry path does not stall the suite.
    monkeypatch.setattr(WeiboClient.request.retry, "wait", wait_fixed(0))

    with pytest.raises(RetryError) as exc_info:
        await make_client().get("/api/container/getIndex", {"page": 2})

    assert isinstance(exc_info.value.last_attempt.exception(), DataFetchError)
    assert calls["count"] == 5


@pytest.mark.asyncio
async def test_creator_notes_pagination_stops_gracefully(monkeypatch):
    """创作者主页翻到头时应返回已采集的结果,而不是让异常冒泡。"""
    pages = [
        {
            "ok": 1,
            "data": {
                "cardlistInfo": {"since_id": "s1"},
                "cards": [{"card_type": 9, "mblog": {"id": "1"}}],
            },
        },
        {"ok": 0, "msg": "这里还没有内容", "data": {"cards": []}},
    ]
    call_index = {"i": 0}

    async def request_impl(method, url, **kwargs):
        payload = pages[min(call_index["i"], len(pages) - 1)]
        call_index["i"] += 1
        return httpx.Response(200, json=payload, request=httpx.Request(method, url))

    monkeypatch.setattr(
        "media_platform.weibo.client.make_async_client",
        lambda **kwargs: FakeAsyncClient(request_impl),
    )

    notes = await make_client().get_all_notes_by_creator_id(
        creator_id="123", container_id="107603123", crawl_interval=0
    )

    assert [note["mblog"]["id"] for note in notes] == ["1"]
