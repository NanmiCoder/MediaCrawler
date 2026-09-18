# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_bilibili_login_state.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""B 站登录态判定的回归测试。

回归背景：``check_login_state`` 曾经只判断 SESSDATA **是否存在**。当浏览器里
残留一份过期 SESSDATA 时（B 站不会主动清掉它），流程会被判成"登录成功"：
既跳过扫码，又把这份死 cookie 灌给 API client。后果是详情和评论照常爬到
（这两个接口不要求登录），但 playurl 依据 Cookie 定清晰度，视频被静默限制在 480P。

这里只测判定逻辑本身，不启浏览器、不发网络请求。
"""

from __future__ import annotations

from media_platform.bilibili.login import is_login_cookie_refreshed

STALE = "sessdata-remaining-from-expired-session"
FRESH = "sessdata-reissued-by-qrcode-scan"


def test_stale_sessdata_is_not_treated_as_logged_in() -> None:
    """残留的过期 SESSDATA 不能算登录成功（本次回归的核心）"""
    assert is_login_cookie_refreshed({"SESSDATA": STALE}, STALE) is False


def test_absent_sessdata_is_not_logged_in() -> None:
    """完全没有 SESSDATA 时未登录；只有 DedeUserID 不足以证明会话有效"""
    assert is_login_cookie_refreshed({}, "") is False
    assert is_login_cookie_refreshed({"DedeUserID": "434377496"}, "") is False


def test_refreshed_sessdata_is_logged_in() -> None:
    """扫码换发成新值之后才放行"""
    assert is_login_cookie_refreshed({"SESSDATA": FRESH}, STALE) is True


def test_sessdata_appearing_from_nothing_is_logged_in() -> None:
    """本来就没有 SESSDATA（真未登录）时，扫码写进来的任意值都算成功"""
    assert is_login_cookie_refreshed({"SESSDATA": FRESH}, "") is True
