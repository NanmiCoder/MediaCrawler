# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_zhihu_fetch_errors.py
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

"""知乎请求失败时的异常处理回归测试。

1. ``ZhiHuClient.request`` 的 ``@retry`` 没有 ``reraise=True``，重试用尽后抛出的是
   ``tenacity.RetryError``，``search()`` 里的 ``except DataFetchError`` 永远匹配不到，
   一次搜索失败（含 403）就让整个爬虫退出。
2. ``get_comments`` 没有异常处理，某一条内容的评论接口报错会经 ``gather`` 传出，
   同批其他内容的评论也拿不到，并终止整个爬虫。

不发真实网络请求：签名函数和 httpx 客户端都被替换。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import httpx
import pytest

import config
from media_platform.zhihu.client import ZhiHuClient
from media_platform.zhihu.core import ZhihuCrawler
from media_platform.zhihu.exception import DataFetchError, ForbiddenError
from model.m_zhihu import ZhihuContent


class FakeAsyncClient:
    def __init__(self, status_code: int, calls: list):
        self.status_code = status_code
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def request(self, method, url, **kwargs):
        self.calls.append(url)
        return httpx.Response(
            self.status_code, text="error", request=httpx.Request(method, url)
        )


def make_client(monkeypatch, status_code: int, calls: list) -> ZhiHuClient:
    monkeypatch.setattr(
        "media_platform.zhihu.client.make_async_client",
        lambda **kwargs: FakeAsyncClient(status_code, calls),
    )
    monkeypatch.setattr(
        "media_platform.zhihu.client.sign",
        lambda url, cookies: {"x-zst-81": "x", "x-zse-96": "x"},
    )
    client = ZhiHuClient(
        headers={"cookie": "d_c0=test"},
        playwright_page=object(),
        cookie_dict={"d_c0": "test"},
    )
    client._refresh_proxy_if_expired = AsyncMock()
    return client


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code, expected", [(500, DataFetchError), (403, ForbiddenError)]
)
async def test_request_reraises_original_error_after_retries(
    monkeypatch, status_code, expected
):
    calls: list = []
    client = make_client(monkeypatch, status_code, calls)

    with pytest.raises(expected):
        await client.request("GET", "https://www.zhihu.com/api/v4/test")

    assert len(calls) == 3  # retries still happen


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [500, 403])
async def test_search_stops_gracefully_on_fetch_error(monkeypatch, status_code):
    calls: list = []
    monkeypatch.setattr(config, "KEYWORDS", "python")
    monkeypatch.setattr(config, "START_PAGE", 1)
    monkeypatch.setattr(config, "CRAWLER_MAX_NOTES_COUNT", 20)

    crawler = ZhihuCrawler()
    crawler.zhihu_client = make_client(monkeypatch, status_code, calls)

    await crawler.search()  # must not raise

    assert len(calls) == 3


def make_content(content_id: str) -> ZhihuContent:
    return ZhihuContent(content_id=content_id, content_type="answer")


@pytest.mark.asyncio
async def test_one_failing_comment_fetch_does_not_abort_the_batch(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_GET_COMMENTS", True)
    monkeypatch.setattr(config, "MAX_CONCURRENCY_NUM", 1)
    monkeypatch.setattr(config, "CRAWLER_MAX_SLEEP_SEC", 0)

    fetched = []

    async def get_note_all_comments(content, crawl_interval, callback):
        if content.content_id == "bad":
            raise ForbiddenError("forbidden")
        fetched.append(content.content_id)

    crawler = ZhihuCrawler()
    crawler.zhihu_client = Mock()
    crawler.zhihu_client.get_note_all_comments = get_note_all_comments

    await crawler.batch_get_content_comments(
        [make_content("a"), make_content("bad"), make_content("b")]
    )

    assert sorted(fetched) == ["a", "b"]
