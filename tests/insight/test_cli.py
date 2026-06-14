# -*- coding: utf-8 -*-
import pytest

from insight.cli import build_parser, cmd_crawl_once, cmd_status


def test_parser_crawl_once():
    args = build_parser().parse_args(["crawl-once", "kw_daily"])
    assert args.name == "kw_daily"
    assert args.func is cmd_crawl_once


def test_parser_status_default_limit():
    args = build_parser().parse_args(["status"])
    assert args.limit == 20
    assert args.func is cmd_status


def test_parser_status_custom_limit():
    args = build_parser().parse_args(["status", "--limit", "5"])
    assert args.limit == 5


def test_parser_requires_subcommand():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
