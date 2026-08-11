# -*- coding: utf-8 -*-

from unittest.mock import AsyncMock

import httpx
import pytest
from tenacity import RetryError

from media_platform.xhs.client import XiaoHongShuClient
from media_platform.xhs.exception import IPBlockError, PlatformAccessError


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
    client = XiaoHongShuClient(
        headers={"Cookie": "web_session=test"},
        playwright_page=object(),
        cookie_dict={},
    )
    client._refresh_proxy_if_expired = AsyncMock()
    return client


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403, 429])
async def test_raw_response_rejects_access_http_status(monkeypatch, status_code):
    calls = 0

    async def request_impl(method, url, **kwargs):
        nonlocal calls
        calls += 1
        return httpx.Response(
            status_code,
            text="blocked",
            request=httpx.Request(method, url),
        )

    monkeypatch.setattr(
        "media_platform.xhs.client.make_async_client",
        lambda **kwargs: FakeAsyncClient(request_impl),
    )

    with pytest.raises(PlatformAccessError):
        await make_client().request(
            "GET", "https://www.xiaohongshu.com/user/profile/test", return_response=True
        )

    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("code", "expected_exception"),
    [(300011, PlatformAccessError), ("300012", IPBlockError)],
)
async def test_raw_response_rejects_known_business_block(
    monkeypatch, code, expected_exception
):
    calls = 0

    async def request_impl(method, url, **kwargs):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={"success": False, "code": code, "msg": "blocked"},
            request=httpx.Request(method, url),
        )

    monkeypatch.setattr(
        "media_platform.xhs.client.make_async_client",
        lambda **kwargs: FakeAsyncClient(request_impl),
    )

    with pytest.raises(expected_exception):
        await make_client().request(
            "GET", "https://www.xiaohongshu.com/explore/test", return_response=True
        )

    assert calls == 1


@pytest.mark.asyncio
async def test_raw_response_keeps_successful_html(monkeypatch):
    async def request_impl(method, url, **kwargs):
        return httpx.Response(
            200,
            text="<html>ok</html>",
            request=httpx.Request(method, url),
        )

    monkeypatch.setattr(
        "media_platform.xhs.client.make_async_client",
        lambda **kwargs: FakeAsyncClient(request_impl),
    )

    result = await make_client().request(
        "GET", "https://www.xiaohongshu.com/explore/test", return_response=True
    )

    assert result == "<html>ok</html>"


@pytest.mark.asyncio
async def test_html_detail_does_not_multiply_transport_retries(monkeypatch):
    calls = 0

    async def request_impl(method, url, **kwargs):
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timed out", request=httpx.Request(method, url))

    monkeypatch.setattr(
        "media_platform.xhs.client.make_async_client",
        lambda **kwargs: FakeAsyncClient(request_impl),
    )

    with pytest.raises(RetryError):
        await make_client().get_note_by_id_from_html(
            "test", xsec_source="pc_search", xsec_token="token"
        )

    assert calls == 3
