# -*- coding: utf-8 -*-

from datetime import datetime

import pytest

from model.m_baidu_tieba import TiebaNote
from model.m_zhihu import ZhihuContent
from tools.content_filter import (
    ContentFilterError,
    filter_content_items,
    normalize_content_filters,
)


def test_content_filters_parse_units_and_aliases():
    filters = normalize_content_filters(
        "xhs",
        {"liked_count": {"min": "1万"}, "collect_count": {"max": "2万"}},
    )

    assert filters == {
        "liked_count": {"min": 10000.0},
        "collected_count": {"max": 20000.0},
    }


def test_content_filters_filter_dict_platform_items():
    items = [
        {"interact_info": {"liked_count": "9999", "collected_count": 10}},
        {"interact_info": {"liked_count": "1.2万", "collected_count": 5}},
    ]

    kept = filter_content_items("xhs", items, {"liked_count": {"min": 10000}})

    assert kept == [items[1]]


def test_content_filters_filter_bilibili_nested_metrics():
    items = [
        {"View": {"stat": {"like": 100, "favorite": 20}}},
        {"View": {"stat": {"like": 500, "favorite": 100}}},
    ]

    kept = filter_content_items(
        "bili",
        items,
        {"liked_count": {"min": 300}, "favorite_count": {"min": 50}},
    )

    assert kept == [items[1]]


def test_content_filters_parse_publish_time_filter():
    filters = normalize_content_filters("dy", {"publish_time": {"min": "2024-07-01"}})

    assert filters == {"publish_time": {"min": datetime(2024, 7, 1).timestamp()}}


def test_content_filters_filter_publish_time_dict_items():
    start_time = datetime(2024, 7, 1).timestamp()
    items = [
        {"time": start_time - 1},
        {"time": start_time},
        {"time": int((start_time + 1) * 1000)},
    ]

    kept = filter_content_items("xhs", items, {"publish_time": {"min": "2024-07-01"}})

    assert kept == items[1:]


def test_content_filters_filter_model_platform_items():
    tieba_items = [
        TiebaNote(note_id="1", title="a", note_url="u", tieba_name="t", tieba_link="l", total_replay_num=9, publish_time="2024-06-30 23:59:59"),
        TiebaNote(note_id="2", title="b", note_url="u", tieba_name="t", tieba_link="l", total_replay_num=10, publish_time="2024-07-01 00:00:00"),
    ]
    zhihu_items = [
        ZhihuContent(content_id="a", voteup_count=99, comment_count=10),
        ZhihuContent(content_id="b", voteup_count=100, comment_count=20),
    ]

    assert filter_content_items("tieba", tieba_items, {"reply_count": {"min": 10}}) == [tieba_items[1]]
    assert filter_content_items("tieba", tieba_items, {"publish_time": {"min": "2024-07-01"}}) == [tieba_items[1]]
    assert filter_content_items("zhihu", zhihu_items, {"voteup_count": {"min": 100}}) == [zhihu_items[1]]


def test_content_filters_reject_unsupported_field():
    with pytest.raises(ContentFilterError):
        normalize_content_filters("dy", {"view_count": {"min": 1}})
