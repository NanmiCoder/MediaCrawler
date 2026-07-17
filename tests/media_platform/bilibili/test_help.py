# -*- coding: utf-8 -*-

import pytest

from media_platform.bilibili.help import parse_article_info_from_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("cv123456", "123456"),
        ("123456", "123456"),
        ("https://www.bilibili.com/read/cv123456", "123456"),
        ("https://www.bilibili.com/read/cv123456?spm_id_from=333.999.0.0", "123456"),
    ],
)
def test_parse_article_info_from_url(raw, expected):
    article_info = parse_article_info_from_url(raw)
    assert article_info.article_id == expected
    assert article_info.article_type == "article"


def test_parse_article_info_from_url_invalid():
    with pytest.raises(ValueError):
        parse_article_info_from_url("https://www.bilibili.com/video/BV1d54y1g7db")
