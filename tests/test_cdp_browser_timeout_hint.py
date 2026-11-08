# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

import config
from tools.cdp_browser import CDPBrowserManager


async def _attach_with_failed_discovery(monkeypatch, direct_error, discovery_error):
    monkeypatch.setattr(config, "CDP_CONNECT_EXISTING", True)
    monkeypatch.setattr(config, "BROWSER_LAUNCH_TIMEOUT", 60)

    manager = CDPBrowserManager()
    manager.debug_port = 9222
    manager._get_browser_websocket_url = AsyncMock(  # type: ignore[method-assign]
        side_effect=discovery_error
    )

    playwright = MagicMock()
    playwright.chromium.connect_over_cdp = AsyncMock(side_effect=direct_error)

    with pytest.raises(RuntimeError) as exc_info:
        await manager._connect_via_cdp(playwright)

    playwright.chromium.connect_over_cdp.assert_awaited_once()
    return exc_info.value


@pytest.mark.asyncio
async def test_existing_browser_attach_failure_explains_what_to_do(monkeypatch):
    direct_error = PlaywrightTimeoutError("BrowserType.connect_over_cdp: Timeout 60000ms exceeded.")

    error = await _attach_with_failed_discovery(
        monkeypatch, direct_error, RuntimeError("HTTP 404: ")
    )

    message = str(error)
    assert "port 9222 within 60s" in message
    assert "remote debugging dialog was not accepted" in message
    assert "tab or window is not responding" in message
    assert "Timeout 60000ms exceeded" in message
    assert "HTTP 404" in message
    assert error.__cause__ is direct_error


@pytest.mark.asyncio
async def test_existing_browser_refused_attach_does_not_blame_tabs(monkeypatch):
    direct_error = PlaywrightError(
        "BrowserType.connect_over_cdp: WebSocket error: "
        "ws://localhost:9222/devtools/browser 404 Not Found"
    )

    error = await _attach_with_failed_discovery(
        monkeypatch, direct_error, RuntimeError("HTTP 404: <html>not found</html>")
    )

    message = str(error)
    assert "Port 9222 is reachable but refused the browser CDP connection" in message
    assert "CDP_DEBUG_PORT" in message
    assert "within 60s" not in message
    assert "tab or window is not responding" not in message
    assert "WebSocket error" in message
    assert "HTTP 404" in message
    assert error.__cause__ is direct_error
