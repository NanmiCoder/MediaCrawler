# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_cmd_arg_media.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""--get_media 命令行开关测试。

注意：parse_cmd 会就地覆盖全局 config，因此每个用例都用 monkeypatch 还原，
避免污染其他测试。
"""

from __future__ import annotations

import config
import pytest
from cmd_arg import parse_cmd


@pytest.fixture(autouse=True)
def _isolate_config(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_GET_MEDIA", False)
    monkeypatch.setattr(config, "PLATFORM", "xhs")
    monkeypatch.setattr(config, "CRAWLER_TYPE", "search")
    yield


BASE_ARGS = ["--platform", "xhs", "--type", "detail", "--specified_id", "note-1"]


@pytest.mark.asyncio
async def test_get_media_true_enables_switch():
    await parse_cmd([*BASE_ARGS, "--get_media", "true"])

    assert config.ENABLE_GET_MEDIA is True


@pytest.mark.asyncio
async def test_get_media_false_keeps_switch_off():
    await parse_cmd([*BASE_ARGS, "--get_media", "false"])

    assert config.ENABLE_GET_MEDIA is False


@pytest.mark.asyncio
async def test_get_media_defaults_to_config_value(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_GET_MEDIA", True)

    args = await parse_cmd(BASE_ARGS)

    assert config.ENABLE_GET_MEDIA is True
    assert args.get_media is True


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("yes", True), ("y", True), ("1", True), ("no", False), ("n", False), ("0", False)],
)
@pytest.mark.asyncio
async def test_get_media_accepts_boolean_aliases(raw, expected):
    await parse_cmd([*BASE_ARGS, "--get_media", raw])

    assert config.ENABLE_GET_MEDIA is expected


@pytest.mark.asyncio
async def test_get_media_returns_value_in_namespace():
    args = await parse_cmd([*BASE_ARGS, "--get_media", "true"])

    assert args.get_media is True
