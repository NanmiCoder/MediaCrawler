# -*- coding: utf-8 -*-
import pytest

from insight.runner import build_crawl_args


def test_search_job_args():
    job = {"name": "kw", "type": "search", "keywords": "a,b", "hour": 2}
    args = build_crawl_args(job)
    assert args[:6] == ["--platform", "xhs", "--type", "search", "--save_data_option", "sqlite"]
    assert "--keywords" in args and args[args.index("--keywords") + 1] == "a,b"
    assert args[args.index("--get_comment") + 1] == "true"


def test_detail_job_joins_note_ids():
    job = {"name": "w", "type": "detail", "note_ids": ["n1", "n2"], "hour": 3}
    args = build_crawl_args(job)
    assert "--type" in args and args[args.index("--type") + 1] == "detail"
    assert args[args.index("--specified_id") + 1] == "n1,n2"


def test_creator_job_joins_creator_ids():
    job = {"name": "c", "type": "creator", "creator_ids": ["c1"], "hour": 4}
    args = build_crawl_args(job)
    assert args[args.index("--creator_id") + 1] == "c1"


def test_optional_max_comments_and_sub_comment():
    job = {"name": "k", "type": "search", "keywords": "x", "hour": 2,
           "max_comments": 50, "get_sub_comment": True}
    args = build_crawl_args(job)
    assert args[args.index("--max_comments_count_singlenotes") + 1] == "50"
    assert args[args.index("--get_sub_comment") + 1] == "true"


def test_invalid_type_raises():
    with pytest.raises(ValueError):
        build_crawl_args({"name": "bad", "type": "homefeed", "hour": 1})


def test_search_missing_keywords_raises():
    with pytest.raises(ValueError):
        build_crawl_args({"name": "bad", "type": "search", "hour": 1})


def test_detail_missing_note_ids_raises():
    with pytest.raises(ValueError):
        build_crawl_args({"name": "bad", "type": "detail", "hour": 1})


def test_creator_missing_ids_raises():
    with pytest.raises(ValueError):
        build_crawl_args({"name": "bad", "type": "creator", "hour": 1})
