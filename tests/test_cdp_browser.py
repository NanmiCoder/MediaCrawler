# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock, MagicMock

import pytest

import config
from tools.cdp_browser import CDPBrowserManager


@pytest.mark.asyncio
async def test_existing_browser_prefers_discovered_websocket_url(monkeypatch, caplog):
    monkeypatch.setattr(config, "CDP_CONNECT_EXISTING", True)
    monkeypatch.setattr(config, "BROWSER_LAUNCH_TIMEOUT", 60)

    manager = CDPBrowserManager()
    manager.debug_port = 9222
    manager._get_browser_websocket_url = AsyncMock(  # type: ignore[method-assign]
        return_value="ws://localhost:9222/devtools/browser/generated-id"
    )

    browser = MagicMock()
    browser.is_connected.return_value = True
    browser.contexts = []

    playwright = MagicMock()
    playwright.chromium.connect_over_cdp = AsyncMock(return_value=browser)

    await manager._connect_via_cdp(playwright)

    manager._get_browser_websocket_url.assert_awaited_once_with(9222)
    playwright.chromium.connect_over_cdp.assert_awaited_once_with(
        "ws://localhost:9222/devtools/browser/generated-id",
        timeout=60000,
    )
    assert "Please check your browser for a confirmation dialog" not in caplog.text


@pytest.mark.asyncio
async def test_existing_browser_falls_back_to_direct_when_discovery_fails(monkeypatch):
    monkeypatch.setattr(config, "CDP_CONNECT_EXISTING", True)
    monkeypatch.setattr(config, "BROWSER_LAUNCH_TIMEOUT", 60)

    manager = CDPBrowserManager()
    manager.debug_port = 9222
    manager._get_browser_websocket_url = AsyncMock(  # type: ignore[method-assign]
        side_effect=RuntimeError("no endpoint")
    )

    browser = MagicMock()
    browser.is_connected.return_value = True
    browser.contexts = []

    playwright = MagicMock()
    playwright.chromium.connect_over_cdp = AsyncMock(return_value=browser)

    await manager._connect_via_cdp(playwright)

    playwright.chromium.connect_over_cdp.assert_awaited_once_with(
        "ws://localhost:9222/devtools/browser",
        timeout=60000,
    )


@pytest.mark.asyncio
async def test_get_browser_websocket_url_uses_ipv4_loopback(monkeypatch):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/generated-id"
    }
    client = MagicMock()
    client.get = AsyncMock(return_value=response)
    async_client = MagicMock()
    async_client.__aenter__ = AsyncMock(return_value=client)
    async_client.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr("tools.cdp_browser.httpx.AsyncClient", lambda: async_client)

    ws_url = await CDPBrowserManager()._get_browser_websocket_url(9222)

    assert ws_url == "ws://127.0.0.1:9222/devtools/browser/generated-id"
    client.get.assert_awaited_once_with(
        "http://127.0.0.1:9222/json/version", timeout=10
    )


@pytest.mark.asyncio
async def test_existing_browser_falls_back_to_direct_for_invalid_discovered_url(monkeypatch):
    monkeypatch.setattr(config, "CDP_CONNECT_EXISTING", True)
    monkeypatch.setattr(config, "BROWSER_LAUNCH_TIMEOUT", 60)

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"webSocketDebuggerUrl": "http://127.0.0.1:9222/not-cdp"}
    client = MagicMock()
    client.get = AsyncMock(return_value=response)
    async_client = MagicMock()
    async_client.__aenter__ = AsyncMock(return_value=client)
    async_client.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr("tools.cdp_browser.httpx.AsyncClient", lambda: async_client)

    manager = CDPBrowserManager()
    manager.debug_port = 9222
    browser = MagicMock()
    browser.is_connected.return_value = True
    browser.contexts = []
    playwright = MagicMock()
    playwright.chromium.connect_over_cdp = AsyncMock(return_value=browser)

    await manager._connect_via_cdp(playwright)

    playwright.chromium.connect_over_cdp.assert_awaited_once_with(
        "ws://localhost:9222/devtools/browser", timeout=60000
    )


@pytest.mark.asyncio
async def test_launched_browser_uses_discovered_websocket_url(monkeypatch):
    monkeypatch.setattr(config, "CDP_CONNECT_EXISTING", False)

    manager = CDPBrowserManager()
    manager.debug_port = 9223
    manager._get_browser_websocket_url = AsyncMock(  # type: ignore[method-assign]
        return_value="ws://localhost:9223/devtools/browser/generated-id"
    )

    browser = MagicMock()
    browser.is_connected.return_value = True
    browser.contexts = []

    playwright = MagicMock()
    playwright.chromium.connect_over_cdp = AsyncMock(return_value=browser)

    await manager._connect_via_cdp(playwright)

    manager._get_browser_websocket_url.assert_awaited_once_with(9223)
    playwright.chromium.connect_over_cdp.assert_awaited_once_with(
        "ws://localhost:9223/devtools/browser/generated-id"
    )
