# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock, MagicMock

import pytest

import config
from tools.cdp_browser import CDPBrowserManager


@pytest.mark.asyncio
async def test_existing_browser_attach_failure_explains_what_to_do(monkeypatch):
    monkeypatch.setattr(config, "CDP_CONNECT_EXISTING", True)
    monkeypatch.setattr(config, "BROWSER_LAUNCH_TIMEOUT", 60)

    manager = CDPBrowserManager()
    manager.debug_port = 9222
    manager._get_browser_websocket_url = AsyncMock(  # type: ignore[method-assign]
        side_effect=RuntimeError("HTTP 404: ")
    )

    direct_error = TimeoutError("connect_over_cdp: Timeout 60000ms exceeded.")
    playwright = MagicMock()
    playwright.chromium.connect_over_cdp = AsyncMock(side_effect=direct_error)

    with pytest.raises(RuntimeError) as exc_info:
        await manager._connect_via_cdp(playwright)

    message = str(exc_info.value)
    assert "port 9222 within 60s" in message
    assert "remote debugging dialog was not accepted" in message
    assert "tab or window is not responding" in message
    assert "Timeout 60000ms exceeded" in message
    assert "HTTP 404" in message
    assert exc_info.value.__cause__ is direct_error
    playwright.chromium.connect_over_cdp.assert_awaited_once()
