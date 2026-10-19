# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_douyin_argus_header.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""抖音 ArgusSecurityPlugin 请求头的回归测试。

回归背景：抖音在边缘网关挂了 ArgusSecurityPlugin，对一批接口做业务前置校验。
缺少 ``x-tt-argus`` 请求头时直接 403，响应体为
``Blocked by ArgusSecurityPlugin Uifid Not Found``；补上 uifid 参数但仍没有这个头
则是 ``... Signature Not Found``（容易误导成 a_bogus / verifyFp 的问题）。
网关当前不校验该头的取值，传固定字符串即可。

这里不发起任何网络请求，只断言客户端默认请求头带上了这两个头。
"""

from __future__ import annotations

import pytest

from media_platform.douyin.client import DOUYIN_ARGUS_HEADER_VALUE, DouYinClient

COOKIE_DICT = {
    "sessionid": "fake-session",
    "UIFID": "uifid-from-cookie",
    "UIFID_TEMP": "uifid-temp-from-cookie",
}


class _StubPage:
    async def evaluate(self, expression):  # noqa: ANN001
        return {}


def _make_client(cookie_dict: dict) -> DouYinClient:
    return DouYinClient(
        headers={"User-Agent": "test-user-agent", "Cookie": "a=1"},
        playwright_page=_StubPage(),
        cookie_dict=cookie_dict,
    )


def test_argus_header_is_present_by_default():
    """x-tt-argus 必须在默认请求头里"""
    client = _make_client(COOKIE_DICT)

    assert client.headers.get("x-tt-argus") == DOUYIN_ARGUS_HEADER_VALUE


def test_uifid_header_comes_from_cookie():
    """uifid 头取自 cookie 里的 UIFID"""
    client = _make_client(COOKIE_DICT)

    assert client.headers.get("uifid") == "uifid-from-cookie"


def test_uifid_header_falls_back_to_uifid_temp():
    """没有 UIFID 时退到 UIFID_TEMP"""
    client = _make_client({"sessionid": "s", "UIFID_TEMP": "temp-only"})

    assert client.headers.get("uifid") == "temp-only"


def test_missing_uifid_omits_header():
    """cookie 里两种都没有时不发这个头（发空值可能被当成「有但为空」）"""
    client = _make_client({"sessionid": "s"})

    assert client.headers.get("uifid") is None
    assert client.headers.get("x-tt-argus") == DOUYIN_ARGUS_HEADER_VALUE


def test_caller_supplied_values_win():
    """调用方显式传了同名头时不覆盖"""
    client = DouYinClient(
        headers={"User-Agent": "ua", "Cookie": "a=1", "x-tt-argus": "custom"},
        playwright_page=_StubPage(),
        cookie_dict=COOKIE_DICT,
    )

    assert client.headers.get("x-tt-argus") == "custom"
