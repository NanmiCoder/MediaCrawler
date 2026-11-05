# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api\security.py
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

"""Access boundary shared by HTTP endpoints and WebSocket handshakes."""

import ipaddress
import os
import secrets
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


LOCAL_DEV_ORIGINS = {
    "http://localhost:5173", "http://localhost:3000",
    "http://127.0.0.1:5173", "http://127.0.0.1:3000",
}


def _is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class APIAccessMiddleware:
    """Local-only by default; setting a token requires it for every API client."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] not in {"http", "websocket"} or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        token = os.environ.get("MEDIACRAWLER_API_TOKEN", "")
        status_code = 403
        if token:
            scheme, _, credential = headers.get("authorization", "").partition(" ")
            allowed = scheme.lower() == "bearer" and secrets.compare_digest(
                credential.encode(), token.encode()
            )
            status_code = 401
        else:
            peer = (scope.get("client") or ("", 0))[0]
            try:
                host = urlsplit("//" + headers.get("host", "")).hostname or ""
            except ValueError:
                host = ""
            allowed = _is_loopback(peer) and (host == "localhost" or _is_loopback(host))
            origin = headers.get("origin")
            if origin:
                scheme = "https" if scope["scheme"] in {"https", "wss"} else "http"
                same_origin = f"{scheme}://{headers.get('host', '')}"
                allowed = allowed and origin in LOCAL_DEV_ORIGINS | {same_origin}

        if allowed:
            await self.app(scope, receive, send)
        elif scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
        else:
            response = JSONResponse(
                {"detail": "API access requires a trusted local client or configured Bearer token"},
                status_code=status_code,
                headers={"WWW-Authenticate": "Bearer"} if token else None,
            )
            await response(scope, receive, send)
