# -*- coding: utf-8 -*-
import httpx
import config


def make_async_client(**kwargs) -> httpx.AsyncClient:
    """Create an httpx.AsyncClient with project-wide defaults.

    Reads DISABLE_SSL_VERIFY from config (default False).
    Set DISABLE_SSL_VERIFY = True in config/base_config.py only when running
    behind an intercepting proxy (corporate gateway, Burp, mitmproxy, etc.).
    """
    kwargs.setdefault("verify", not getattr(config, "DISABLE_SSL_VERIFY", False))
    return httpx.AsyncClient(**kwargs)
