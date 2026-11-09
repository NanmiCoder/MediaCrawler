# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_api_access.py
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
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api.main import app


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/api/crawler/status", "/api/crawler/logs", "/api/data/files", "/api/env/check"])
async def test_remote_api_requests_require_authentication(monkeypatch, path):
    monkeypatch.delenv("MEDIACRAWLER_API_TOKEN", raising=False)
    transport = httpx.ASGITransport(app=app, client=("198.51.100.8", 1234))
    async with httpx.AsyncClient(transport=transport, base_url="http://crawler.example") as client:
        response = await client.get(path)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_remote_token_and_local_same_origin_access(monkeypatch):
    monkeypatch.setenv("MEDIACRAWLER_API_TOKEN", "test-only-token")
    transport = httpx.ASGITransport(app=app, client=("198.51.100.8", 1234))
    async with httpx.AsyncClient(transport=transport, base_url="http://crawler.example") as client:
        assert (await client.get("/api/crawler/status")).status_code == 401
        response = await client.get("/api/crawler/status", headers={"Authorization": "Bearer test-only-token"})
        assert response.status_code == 200
    monkeypatch.delenv("MEDIACRAWLER_API_TOKEN")
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 1234))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8080") as client:
        assert (await client.get("/api/crawler/status", headers={"Origin": "http://localhost:8080"})).status_code == 200
        assert (await client.get("/api/crawler/status", headers={"Origin": "https://untrusted.example"})).status_code == 403
        assert (await client.get("/api/crawler/status", headers={"Host": "rebound.example"})).status_code == 403


@pytest.mark.parametrize("path", ["/api/ws/logs", "/api/ws/status"])
def test_cross_origin_websocket_is_rejected(monkeypatch, path):
    monkeypatch.delenv("MEDIACRAWLER_API_TOKEN", raising=False)
    async def local_client(scope, receive, send):
        scope["client"] = ("127.0.0.1", 1234)
        await app(scope, receive, send)

    with TestClient(local_client, base_url="http://localhost") as client:
        with client.websocket_connect("ws://localhost" + path, headers={"Origin": "http://localhost"}):
            pass
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("ws://localhost" + path, headers={"Origin": "https://untrusted.example"}):
                pytest.fail("Untrusted WebSocket was accepted")


@pytest.mark.parametrize("path", ["/api/ws/logs", "/api/ws/status"])
def test_websocket_token_policy_matches_http(monkeypatch, path):
    monkeypatch.setenv("MEDIACRAWLER_API_TOKEN", "test-only-token")
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("ws://localhost" + path, headers={"Authorization": "Bearer wrong-token"}):
                pytest.fail("Invalid token was accepted")
        with client.websocket_connect("ws://localhost" + path, headers={"Authorization": "Bearer test-only-token"}):
            pass


@pytest.mark.asyncio
@pytest.mark.parametrize("host", ["[", "[not-ip]"])
async def test_malformed_host_is_denied(monkeypatch, host):
    monkeypatch.delenv("MEDIACRAWLER_API_TOKEN", raising=False)
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 1234))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.get("/api/crawler/status", headers={"Host": host})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_untrusted_request_cannot_start_or_stop_a_process(monkeypatch):
    from api.services import crawler_manager
    monkeypatch.delenv("MEDIACRAWLER_API_TOKEN", raising=False)
    start = AsyncMock()
    stop = AsyncMock()
    monkeypatch.setattr(crawler_manager, "start", start)
    monkeypatch.setattr(crawler_manager, "stop", stop)
    transport = httpx.ASGITransport(app=app, client=("198.51.100.8", 1234))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8080") as client:
        assert (await client.post("/api/crawler/start", json={"platform": "xhs"})).status_code == 403
        assert (await client.post("/api/crawler/stop")).status_code == 403
    start.assert_not_awaited()
    stop.assert_not_awaited()
