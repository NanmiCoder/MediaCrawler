# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_xhs_note_url_parse.py
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

"""小红书笔记链接解析的回归测试。

``parse_note_info_from_note_url`` 过去用 ``url.split("/")[-1].split("?")[0]``
取笔记 ID：链接在 ID 后面多一个斜杠（``/explore/<id>/?xsec_token=...``）时
取到的是空字符串，带 ``#`` 锚点时 ID 会带上锚点内容。

这里只测纯函数，不发网络请求。
"""

from __future__ import annotations

import pytest

from media_platform.xhs.help import parse_note_info_from_note_url

NOTE_ID = "66fad51c000000001b0224b8"
TOKEN = "AB3rO-QopW5sgrJ41GwN01WCXh6yWPxjSoFI9D5JIMgKw="


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.xiaohongshu.com/explore/{NOTE_ID}?xsec_token={TOKEN}&xsec_source=pc_search",
        f"https://www.xiaohongshu.com/explore/{NOTE_ID}/?xsec_token={TOKEN}&xsec_source=pc_search",
        f"https://www.xiaohongshu.com/explore/{NOTE_ID}/",
        f"https://www.xiaohongshu.com/explore/{NOTE_ID}",
        f"https://www.xiaohongshu.com/discovery/item/{NOTE_ID}?xsec_token={TOKEN}&xsec_source=pc_search#comments",
        f"https://www.xiaohongshu.com/discovery/item/{NOTE_ID}#comments",
    ],
)
def test_note_id_is_parsed(url):
    assert parse_note_info_from_note_url(url).note_id == NOTE_ID


def test_query_params_still_parsed_with_trailing_slash():
    info = parse_note_info_from_note_url(
        f"https://www.xiaohongshu.com/explore/{NOTE_ID}/?xsec_token={TOKEN}&xsec_source=pc_search"
    )

    assert info.xsec_token == TOKEN
    assert info.xsec_source == "pc_search"
