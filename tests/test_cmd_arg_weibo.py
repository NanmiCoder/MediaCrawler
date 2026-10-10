# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_cmd_arg_weibo.py
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

import config
import pytest
from cmd_arg import parse_cmd
from cmd_arg.arg import _normalize_weibo_note_id


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("R3bk1ydAR", "R3bk1ydAR"),
        ("4982041758140155", "4982041758140155"),
        ("https://weibo.com/7798025479/R3bk1ydAR?refer_flag=1001030103_", "R3bk1ydAR"),
        ("https://m.weibo.cn/detail/4982041758140155", "4982041758140155"),
        ("https://m.weibo.cn/status/R3bk1ydAR", "R3bk1ydAR"),
        ("  https://weibo.com/7798025479/R3bk1ydAR  ", "R3bk1ydAR"),
    ],
)
def test_normalize_weibo_note_id(raw, expected):
    assert _normalize_weibo_note_id(raw) == expected


@pytest.mark.asyncio
async def test_weibo_detail_cli_sets_specified_ids():
    await parse_cmd(
        [
            "--platform",
            "wb",
            "--type",
            "detail",
            "--specified_id",
            "https://weibo.com/7798025479/R3bk1ydAR?refer_flag=1001030103_,4982041758140155",
        ]
    )

    assert config.WEIBO_SPECIFIED_ID_LIST == ["R3bk1ydAR", "4982041758140155"]
