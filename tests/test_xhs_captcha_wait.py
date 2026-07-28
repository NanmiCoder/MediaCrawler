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
async def test_wait_for_captcha_stops_after_five_minutes():
    operation = AsyncMock(side_effect=CaptchaRequiredError("verify"))
    times = iter([0.0, 300.0])

    with pytest.raises(CaptchaRequiredError):
        await wait_for_captcha(
            operation, sleep=AsyncMock(), monotonic=lambda: next(times)
        )

    assert operation.await_count == 1


@pytest.mark.asyncio
async def test_wait_for_captcha_does_not_retry_other_errors():
    operation = AsyncMock(side_effect=RuntimeError("network"))
    sleep = AsyncMock()

    with pytest.raises(RuntimeError, match="network"):
        await wait_for_captcha(operation, sleep=sleep)

    sleep.assert_not_awaited()
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


def _client_for_request_tests():
    client = XiaoHongShuClient.__new__(XiaoHongShuClient)
    client.proxy = None
    client.timeout = 1
    client.IP_ERROR_CODE = 300012
    client.NOTE_NOT_FOUND_CODE = -510000
    client.NOTE_ABNORMAL_CODE = -510001
    client.IP_ERROR_STR = "Network connection error"
    client._refresh_proxy_if_expired = AsyncMock()
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
        lambda operation: wait_for_captcha(
            operation,
            sleep=lambda seconds: record_sleep(sleeps, seconds),
            monotonic=lambda: next(times),
        ),
    )

    result = await _client_for_request_tests().request("GET", "https://example.test")

    assert result == {"notes": []}
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
