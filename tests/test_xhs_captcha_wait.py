from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from tenacity import RetryError, wait_none

from media_platform.xhs.client import XiaoHongShuClient, raise_for_captcha, wait_for_captcha
from media_platform.xhs.exception import CaptchaRequiredError, DataFetchError, NoteNotFoundError


async def record_sleep(values, seconds):
    values.append(seconds)


@pytest.mark.parametrize("status", [461, 471])
def test_captcha_status_raises_specific_error(status):
    response = httpx.Response(
        status,
        headers={"Verifytype": "slider", "Verifyuuid": "uuid-1"},
        request=httpx.Request("GET", "https://example.test"),
    )

    with pytest.raises(CaptchaRequiredError, match="slider"):
        raise_for_captcha(response)


@pytest.mark.asyncio
async def test_wait_for_captcha_continues_after_manual_verification():
    operation = AsyncMock(
        side_effect=[CaptchaRequiredError("verify"), {"notes": []}]
    )
    sleeps = []
    times = iter([0.0, 1.0])

    result = await wait_for_captcha(
        operation,
        sleep=lambda seconds: record_sleep(sleeps, seconds),
        monotonic=lambda: next(times),
    )

    assert result == {"notes": []}
    assert sleeps == [10]
    assert operation.await_count == 2


@pytest.mark.asyncio
async def test_wait_for_captcha_calls_presenter_once_for_repeated_captcha():
    operation = AsyncMock(
        side_effect=[
            CaptchaRequiredError("verify"),
            CaptchaRequiredError("verify"),
            {"notes": []},
        ]
    )
    presenter = AsyncMock()
    sleeps = []
    times = iter([0.0, 1.0])

    result = await wait_for_captcha(
        operation,
        on_captcha=presenter,
        sleep=lambda seconds: record_sleep(sleeps, seconds),
        monotonic=lambda: next(times),
    )

    assert result == {"notes": []}
    presenter.assert_awaited_once_with()
    assert sleeps == [10, 10]
    assert operation.await_count == 3


@pytest.mark.asyncio
async def test_wait_for_captcha_stops_after_five_minutes():
    operation = AsyncMock(side_effect=CaptchaRequiredError("verify"))
    times = iter([0.0, 300.0])
    sleep = AsyncMock()

    with pytest.raises(CaptchaRequiredError):
        await wait_for_captcha(
            operation, sleep=sleep, monotonic=lambda: next(times)
        )

    assert operation.await_count == 2
    sleep.assert_awaited_once_with(10)


@pytest.mark.asyncio
async def test_captcha_deadline_starts_when_captcha_is_first_seen():
    clock = {"now": 0.0}
    attempts = 0
    sleeps = []

    async def operation():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            clock["now"] = 301.0
            raise CaptchaRequiredError("verify")
        return {"notes": []}

    result = await wait_for_captcha(
        operation,
        sleep=lambda seconds: record_sleep(sleeps, seconds),
        monotonic=lambda: clock["now"],
    )

    assert result == {"notes": []}
    assert attempts == 2
    assert sleeps == [10]


@pytest.mark.asyncio
async def test_wait_for_captcha_does_not_retry_other_errors():
    operation = AsyncMock(side_effect=RuntimeError("network"))
    sleep = AsyncMock()
    presenter = AsyncMock()

    with pytest.raises(RuntimeError, match="network"):
        await wait_for_captcha(operation, sleep=sleep, on_captcha=presenter)

    sleep.assert_not_awaited()
    presenter.assert_not_awaited()
    assert operation.await_count == 1


class _ResponseClient:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, *args, **kwargs):
        self.calls += 1
        return self.response


class _SequenceResponseClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, *args, **kwargs):
        self.requests.append((args, deepcopy(kwargs)))
        return self.responses.pop(0)


class _CookieContext:
    def __init__(self, values):
        self.values = list(values)
        self.calls = 0

    async def cookies(self, urls=None):
        self.calls += 1
        value = self.values.pop(0)
        return [{"name": "a1", "value": value}]


def _client_for_request_tests():
    client = XiaoHongShuClient.__new__(XiaoHongShuClient)
    client.proxy = None
    client.timeout = 1
    client.IP_ERROR_CODE = 300012
    client.NOTE_NOT_FOUND_CODE = -510000
    client.NOTE_ABNORMAL_CODE = -510001
    client.IP_ERROR_STR = "Network connection error"
    client._refresh_proxy_if_expired = AsyncMock()
    client.playwright_page = SimpleNamespace(
        bring_to_front=AsyncMock(),
        goto=AsyncMock(),
    )
    return client


@pytest.mark.asyncio
async def test_request_waits_for_captcha_instead_of_short_retry(monkeypatch):
    captcha = httpx.Response(
        461,
        headers={"Verifytype": "slider", "Verifyuuid": "uuid-1"},
        request=httpx.Request("GET", "https://example.test"),
    )
    success = httpx.Response(
        200,
        json={"success": True, "data": {"notes": []}},
        request=httpx.Request("GET", "https://example.test"),
    )
    responses = iter([captcha, success])

    def make_client(**kwargs):
        return _ResponseClient(next(responses))

    sleeps = []
    times = iter([0.0, 1.0])
    monkeypatch.setattr("media_platform.xhs.client.make_async_client", make_client)
    monkeypatch.setattr(
        "media_platform.xhs.client.wait_for_captcha",
        lambda operation, **kwargs: wait_for_captcha(
            operation,
            on_captcha=kwargs.get("on_captcha"),
            sleep=lambda seconds: record_sleep(sleeps, seconds),
            monotonic=lambda: next(times),
        ),
    )

    client = _client_for_request_tests()
    result = await client.request("GET", "https://example.test")

    assert result == {"notes": []}
    assert sleeps == [10]
    client.playwright_page.bring_to_front.assert_awaited_once_with()
    client.playwright_page.goto.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["get", "post"])
async def test_signed_requests_refresh_cookies_and_signature_after_captcha(
    monkeypatch, method
):
    captcha = httpx.Response(
        461,
        headers={"Verifytype": "slider", "Verifyuuid": "uuid-1"},
        request=httpx.Request(method.upper(), "https://example.test"),
    )
    success = httpx.Response(
        200,
        json={"success": True, "data": {"notes": []}},
        request=httpx.Request(method.upper(), "https://example.test"),
    )
    response_client = _SequenceResponseClient([captcha, success])
    context = _CookieContext(["old", "new"])
    client = _client_for_request_tests()
    client._host = "https://example.test"
    client._domain = "https://www.xiaohongshu.com"
    client.cookie_urls = [client._domain]
    client.headers = {"Cookie": "a1=initial"}
    client.cookie_dict = {"a1": "initial"}
    client.playwright_page = SimpleNamespace(
        context=context,
        bring_to_front=AsyncMock(),
        goto=AsyncMock(),
    )

    def sign_with_cookie(*, uri, data, cookie_str, method):
        return {
            "x-s": f"xs-{cookie_str}",
            "x-t": f"xt-{cookie_str}",
            "x-s-common": f"common-{cookie_str}",
            "x-b3-traceid": f"trace-{cookie_str}",
        }

    sleeps = []
    monkeypatch.setattr(
        "media_platform.xhs.client.make_async_client", lambda **kwargs: response_client
    )
    monkeypatch.setattr("media_platform.xhs.client.sign_with_xhshow", sign_with_cookie)
    monkeypatch.setattr(
        "media_platform.xhs.client.wait_for_captcha",
        lambda operation, **kwargs: wait_for_captcha(
            operation,
            on_captcha=kwargs.get("on_captcha"),
            sleep=lambda seconds: record_sleep(sleeps, seconds),
            monotonic=lambda: 0.0,
        ),
    )

    if method == "get":
        result = await client.get(
            "/api/sns/web/v1/search/notes", {"keyword": "重庆 火锅"}
        )
    else:
        result = await client.post(
            "/api/sns/web/v1/search/notes", {"keyword": "重庆 火锅"}
        )

    request_headers = [call[1]["headers"] for call in response_client.requests]
    assert result == {"notes": []}
    assert context.calls == 2
    assert client.cookie_dict == {"a1": "new"}
    assert [headers["Cookie"] for headers in request_headers] == ["a1=old", "a1=new"]
    assert [headers["X-T"] for headers in request_headers] == ["xt-a1=old", "xt-a1=new"]
    client.playwright_page.bring_to_front.assert_awaited_once_with()
    client.playwright_page.goto.assert_awaited_once_with(
        "https://www.xiaohongshu.com/search_result?keyword=%E9%87%8D%E5%BA%86%20%E7%81%AB%E9%94%85"
    )
    assert sleeps == [10]


@pytest.mark.asyncio
async def test_short_retry_keeps_retry_error_for_data_fetch_errors(monkeypatch):
    response = httpx.Response(
        200,
        json={"success": False, "code": 500, "msg": "network"},
        request=httpx.Request("GET", "https://example.test"),
    )
    response_client = _ResponseClient(response)
    client = _client_for_request_tests()
    previous_wait = XiaoHongShuClient._request_with_short_retry.retry.wait
    XiaoHongShuClient._request_with_short_retry.retry.wait = wait_none()
    monkeypatch.setattr(
        "media_platform.xhs.client.make_async_client", lambda **kwargs: response_client
    )
    try:
        with pytest.raises(RetryError) as exc_info:
            await client._request_with_short_retry("GET", "https://example.test")
    finally:
        XiaoHongShuClient._request_with_short_retry.retry.wait = previous_wait

    assert isinstance(exc_info.value.last_attempt.exception(), DataFetchError)
    assert response_client.calls == 3


@pytest.mark.asyncio
async def test_short_retry_does_not_retry_note_not_found(monkeypatch):
    response = httpx.Response(
        200,
        json={"success": False, "code": -510000, "msg": "missing"},
        request=httpx.Request("GET", "https://example.test"),
    )
    response_client = _ResponseClient(response)
    client = _client_for_request_tests()
    monkeypatch.setattr(
        "media_platform.xhs.client.make_async_client", lambda **kwargs: response_client
    )

    with pytest.raises(NoteNotFoundError):
        await client._request_with_short_retry("GET", "https://example.test")

    assert response_client.calls == 1
