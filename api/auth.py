# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

"""API key authentication helpers for HTTP and WebSocket endpoints."""

import base64
import os
import secrets
from typing import Optional, Tuple

from fastapi import HTTPException, Security, WebSocket, status
from fastapi.security import APIKeyHeader

API_KEY_ENV = "DY_API_KEY"
API_KEY_FALLBACK_ENV = "API_KEY"
API_KEY_REQUIRED_ENV = "DY_API_AUTH_REQUIRED"
API_KEY_HEADER = "X-API-Key"
WS_API_KEY_PROTOCOL_PREFIX = "mc-api-key."

api_key_header = APIKeyHeader(
    name=API_KEY_HEADER,
    scheme_name="MediaCrawlerApiKey",
    description=f"Set this value to the configured {API_KEY_ENV}.",
    auto_error=False,
)


def get_configured_api_key() -> str:
    """Return the current configured API key, or an empty string when disabled."""
    return (
        os.environ.get(API_KEY_ENV, "").strip()
        or os.environ.get(API_KEY_FALLBACK_ENV, "").strip()
    )


def is_api_key_enabled() -> bool:
    """Whether API key authentication is enabled."""
    return bool(get_configured_api_key())


def is_api_key_required() -> bool:
    """Whether startup must fail when no API key is configured."""
    return os.environ.get(API_KEY_REQUIRED_ENV, "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def validate_auth_configuration() -> None:
    """Fail closed when authentication is required but no key is configured."""
    if is_api_key_required() and not is_api_key_enabled():
        raise RuntimeError(
            f"{API_KEY_ENV} or {API_KEY_FALLBACK_ENV} must be set when "
            f"{API_KEY_REQUIRED_ENV}=1"
        )


def is_valid_api_key(candidate: Optional[str]) -> bool:
    """Validate a candidate using a constant-time comparison."""
    configured = get_configured_api_key()
    if not configured:
        return True
    if not candidate:
        return False
    return secrets.compare_digest(candidate, configured)


async def require_api_key(
    candidate: Optional[str] = Security(api_key_header),
) -> None:
    """FastAPI dependency protecting HTTP API routers."""
    if not is_valid_api_key(candidate):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def encode_websocket_api_key(api_key: str) -> str:
    """Encode an API key as a WebSocket subprotocol-safe token."""
    encoded = base64.urlsafe_b64encode(api_key.encode("utf-8")).decode("ascii")
    return f"{WS_API_KEY_PROTOCOL_PREFIX}{encoded.rstrip('=')}"


def _decode_websocket_protocol(protocol: str) -> Optional[str]:
    if not protocol.startswith(WS_API_KEY_PROTOCOL_PREFIX):
        return None
    encoded = protocol[len(WS_API_KEY_PROTOCOL_PREFIX):]
    if not encoded:
        return None
    try:
        padding = "=" * (-len(encoded) % 4)
        return base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def get_websocket_api_key(ws: WebSocket) -> Tuple[Optional[str], Optional[str]]:
    """
    Return the candidate key and the subprotocol to echo during accept.

    Browser clients use a WebSocket subprotocol so credentials do not appear in
    request URLs. Header and query-string forms remain available for non-browser
    and backwards-compatible clients.
    """
    header_candidate = ws.headers.get(API_KEY_HEADER)
    if header_candidate:
        return header_candidate, None

    protocols = ws.headers.get("sec-websocket-protocol", "")
    for raw_protocol in protocols.split(","):
        protocol = raw_protocol.strip()
        candidate = _decode_websocket_protocol(protocol)
        if candidate is not None:
            return candidate, protocol

    return ws.query_params.get("api_key"), None
