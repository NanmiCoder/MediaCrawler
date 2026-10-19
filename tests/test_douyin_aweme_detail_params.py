# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_douyin_aweme_detail_params.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""抖音 aweme detail 接口的风控参数回归测试。

回归背景：上游 detail 接口的 Argus 风控要求 ``uifid`` / ``verifyFp`` / ``fp``
三个参数，缺一时直接 403，响应体为
``Blocked by ArgusSecurityPlugin Uifid Not Found``（补上 uifid 但 verifyFp 不对时
换成 ``... Signature Not Found``）。原先只传 aweme_id，于是详情全线失败，
连带媒体也拿不到。

这里不发起任何网络请求，只锁定这三个参数确实被带上、且取值来自浏览器 cookie。
"""

from __future__ import annotations

import pytest

from media_platform.douyin.client import DouYinClient

AWEME_ID = "7525538910311632128"


class _StubPage:
    """占位 page，仅用于构造 client；本测试不会走到 playwright 调用"""

    async def evaluate(self, expression):  # noqa: ANN001
        return {}


def _make_client(cookie_dict: dict) -> DouYinClient:
    return DouYinClient(
        headers={
            "User-Agent": "test-user-agent",
            "Cookie": "a=1",
            "Origin": "https://www.douyin.com/",
        },
        playwright_page=_StubPage(),
        cookie_dict=cookie_dict,
    )


@pytest.mark.asyncio
async def test_aweme_detail_sends_uifid_and_verify_fp(monkeypatch):
    """uifid 与 verifyFp/fp 必须成套出现，且都取自 cookie"""
    captured: dict = {}

    async def fake_get(uri, params=None, headers=None):  # noqa: ANN001
        captured["uri"] = uri
        captured["params"] = dict(params or {})
        return {"aweme_detail": {"aweme_id": AWEME_ID}}

    client = _make_client(
        {"s_v_web_id": "verify_test_fp", "UIFID": "uifid-from-cookie"}
    )
    monkeypatch.setattr(client, "get", fake_get)

    await client.get_video_by_id(AWEME_ID)

    assert captured["uri"] == "/aweme/v1/web/aweme/detail/"
    assert captured["params"]["aweme_id"] == AWEME_ID
    assert captured["params"]["uifid"] == "uifid-from-cookie"
    # verifyFp 与 fp 必须同源，且用 cookie 里的 s_v_web_id（自生成的会被判 Signature Not Found）
    assert captured["params"]["verifyFp"] == "verify_test_fp"
    assert captured["params"]["fp"] == "verify_test_fp"


@pytest.mark.asyncio
async def test_aweme_detail_falls_back_to_uifid_temp(monkeypatch):
    """没有 UIFID 时退到 UIFID_TEMP"""
    captured: dict = {}

    async def fake_get(uri, params=None, headers=None):  # noqa: ANN001
        captured["params"] = dict(params or {})
        return {"aweme_detail": {}}

    client = _make_client({"s_v_web_id": "fp", "UIFID_TEMP": "temp-only"})
    monkeypatch.setattr(client, "get", fake_get)

    await client.get_video_by_id(AWEME_ID)

    assert captured["params"]["uifid"] == "temp-only"


@pytest.mark.asyncio
async def test_aweme_detail_without_cookies_still_requests(monkeypatch):
    """cookie 缺失时不能抛异常，参数退化为空串（由服务端决定是否放行）"""
    captured: dict = {}

    async def fake_get(uri, params=None, headers=None):  # noqa: ANN001
        captured["params"] = dict(params or {})
        return {"aweme_detail": {}}

    client = _make_client({})
    monkeypatch.setattr(client, "get", fake_get)

    await client.get_video_by_id(AWEME_ID)

    assert captured["params"]["uifid"] == ""
    assert captured["params"]["verifyFp"] == ""
    assert captured["params"]["fp"] == ""
