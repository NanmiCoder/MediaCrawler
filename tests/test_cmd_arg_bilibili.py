# -*- coding: utf-8 -*-

import config
import pytest
from cmd_arg import parse_cmd


@pytest.mark.asyncio
async def test_bilibili_detail_cli_splits_video_and_article_ids():
    await parse_cmd(
        [
            "--platform",
            "bili",
            "--type",
            "detail",
            "--specified_id",
            "BV1Sz4y1U77N,https://www.bilibili.com/read/cv123456,cv654321",
        ]
    )

    assert config.BILI_SPECIFIED_ID_LIST == ["BV1Sz4y1U77N"]
    assert config.BILI_SPECIFIED_ARTICLE_ID_LIST == [
        "https://www.bilibili.com/read/cv123456",
        "cv654321",
    ]
