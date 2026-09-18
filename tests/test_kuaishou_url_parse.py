# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_kuaishou_url_parse.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""快手视频输入解析的回归测试。

覆盖三种输入形态：
1. 纯视频 ID
2. 标准视频页 ``/short-video/<id>``
3. 分享短链 ``/f/<share_token>`` —— 注意路径里是 **share_token 而不是视频 ID**，
   必须跟随 302 重定向才能拿到真实 ID，所以只标记 ``url_type="short"`` 交给调用方。

这里只测纯函数，不发网络请求。
"""

from __future__ import annotations

import pytest

from media_platform.kuaishou.help import parse_video_info_from_url


def test_pure_video_id_is_normal():
    info = parse_video_info_from_url("3xf8enb8dbj6uig")

    assert info.video_id == "3xf8enb8dbj6uig"
    assert info.url_type == "normal"


def test_short_video_url_is_normal():
    info = parse_video_info_from_url(
        "https://www.kuaishou.com/short-video/3x3zxz4mjrsc8ke"
        "?authorId=3x84qugg4ch9zhs&streamSource=search&area=searchxxnull&searchKey=python"
    )

    assert info.video_id == "3x3zxz4mjrsc8ke"
    assert info.url_type == "normal"


def test_share_short_link_is_marked_short():
    """分享短链必须标记为 short —— 路径里的 token 不是视频 ID"""
    info = parse_video_info_from_url("https://www.kuaishou.com/f/X9Idt15MQb9L2cv")

    assert info.video_id == "X9Idt15MQb9L2cv"
    assert info.url_type == "short"


def test_share_short_link_with_dash_in_token():
    info = parse_video_info_from_url("https://www.kuaishou.com/f/X-a8vLyTxvEvN2jg")

    assert info.video_id == "X-a8vLyTxvEvN2jg"
    assert info.url_type == "short"


def test_short_video_url_is_not_confused_with_share_link():
    """带 query 的标准视频页不能被误判成短链"""
    info = parse_video_info_from_url(
        "https://www.kuaishou.com/short-video/3xyziwesje8e9jg"
        "?shareToken=X9Idt15MQb9L2cv&shareObjectId=3xyziwesje8e9jg"
    )

    assert info.video_id == "3xyziwesje8e9jg"
    assert info.url_type == "normal"


def test_unparsable_url_raises():
    with pytest.raises(ValueError):
        parse_video_info_from_url("https://www.kuaishou.com/profile/3x84qugg4ch9zhs")
