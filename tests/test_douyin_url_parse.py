# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_douyin_url_parse.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""抖音作品输入解析的回归测试。

图文作品的链接是 ``/note/<aweme_id>``，短链跳转后落到 iesdouyin.com 的
``/share/note/<aweme_id>/``。它们和视频一样都带作品 ID，应直接解析出来，
而不是被当成短链再去请求一次。

这里只测纯函数，不发网络请求。
"""

from __future__ import annotations

import pytest

from media_platform.douyin.help import parse_video_info_from_url


def test_pure_aweme_id_is_normal():
    info = parse_video_info_from_url("7525082444551310602")

    assert info.aweme_id == "7525082444551310602"
    assert info.url_type == "normal"


def test_video_url_is_normal():
    info = parse_video_info_from_url("https://www.douyin.com/video/7525082444551310602")

    assert info.aweme_id == "7525082444551310602"
    assert info.url_type == "normal"


def test_modal_id_url():
    info = parse_video_info_from_url(
        "https://www.douyin.com/root/search/python?modal_id=7471165520058862848"
    )

    assert info.aweme_id == "7471165520058862848"
    assert info.url_type == "modal"


def test_note_url_is_normal():
    """图文作品页 /note/<id> 不能被当成短链"""
    info = parse_video_info_from_url("https://www.douyin.com/note/7525082444551310602")

    assert info.aweme_id == "7525082444551310602"
    assert info.url_type == "normal"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.iesdouyin.com/share/note/7525082444551310602/?region=CN&mid=7525082500000000000",
        "https://www.iesdouyin.com/share/video/7525082444551310602/?region=CN&mid=7525082500000000000",
    ],
)
def test_resolved_share_url_is_normal(url):
    """短链跳转后的 share 页（视频或图文）都要能取到作品 ID"""
    info = parse_video_info_from_url(url)

    assert info.aweme_id == "7525082444551310602"
    assert info.url_type == "normal"


def test_share_short_link_is_marked_short():
    info = parse_video_info_from_url("https://v.douyin.com/iF12345ABC/")

    assert info.aweme_id == ""
    assert info.url_type == "short"


def test_unknown_long_url_raises():
    with pytest.raises(ValueError):
        parse_video_info_from_url(
            "https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE"
        )
