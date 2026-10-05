# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_file_transactions.py
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

import asyncio
import csv
import json
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest

import config
from tools.async_file_writer import AsyncFileWriter


@pytest.fixture
def writer(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))
    monkeypatch.setattr(config, "ENABLE_GET_WORDCLOUD", False)
    return AsyncFileWriter("xhs", "search")


@pytest.mark.asyncio
async def test_json_serialization_failure_preserves_previous_data(writer):
    await writer.write_single_item_to_json({"note_id": "saved"}, "contents")
    path = writer._get_file_path("json", "contents")
    with open(path, "rb") as source:
        original = source.read()
    with pytest.raises(TypeError):
        await writer.write_single_item_to_json({"unsupported": object()}, "contents")
    with open(path, "rb") as source:
        assert source.read() == original


@pytest.mark.asyncio
async def test_corrupt_json_is_not_silently_replaced(writer):
    path = writer._get_file_path("json", "contents")
    with open(path, "w", encoding="utf-8") as target:
        target.write('[{"valuable": "partial')
    with pytest.raises(json.JSONDecodeError):
        await writer.write_single_item_to_json({"new": "value"}, "contents")
    with open(path, encoding="utf-8") as source:
        assert source.read() == '[{"valuable": "partial'


@pytest.mark.asyncio
async def test_json_replace_failure_preserves_previous_data(writer, monkeypatch):
    await writer.write_single_item_to_json({"old": "value"}, "contents")
    monkeypatch.setattr("os.replace", Mock(side_effect=OSError("disk failure")))
    with pytest.raises(OSError, match="disk failure"):
        await writer.write_single_item_to_json({"new": "value"}, "contents")
    with open(writer._get_file_path("json", "contents"), encoding="utf-8") as source:
        assert json.load(source) == [{"old": "value"}]
    assert not list(Path(writer._get_file_path("json", "contents")).parent.glob("*.tmp"))


@pytest.mark.asyncio
async def test_json_concurrent_appends_keep_every_record(writer):
    await asyncio.gather(*(
        writer.write_single_item_to_json({"id": number}, "contents")
        for number in range(20)
    ))
    with open(writer._get_file_path("json", "contents"), encoding="utf-8") as source:
        rows = json.load(source)
    assert sorted(row["id"] for row in rows) == list(range(20))


@pytest.mark.asyncio
@pytest.mark.parametrize("file_type,method", [
    ("json", "write_single_item_to_json"), ("jsonl", "write_to_jsonl"), ("csv", "write_to_csv"),
])
async def test_separate_writers_share_a_file_without_losing_records(writer, file_type, method):
    await asyncio.gather(*(
        getattr(AsyncFileWriter("xhs", "search"), method)({"id": number}, "contents")
        for number in range(30)
    ))
    with open(writer._get_file_path(file_type, "contents"), newline="", encoding="utf-8-sig") as source:
        if file_type == "json":
            rows = json.load(source)
        elif file_type == "jsonl":
            rows = [json.loads(line) for line in source]
        else:
            rows = list(csv.DictReader(source))
    assert sorted(int(row["id"]) for row in rows) == list(range(30))


@pytest.mark.asyncio
async def test_cancelled_json_writer_finishes_io_before_next_append(writer, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    append = writer._append_json

    def delayed_append(path, item):
        started.set()
        if not release.wait(5):
            raise TimeoutError("test failed to release writer")
        append(path, item)

    monkeypatch.setattr(writer, "_append_json", delayed_append)
    first = asyncio.create_task(writer.write_single_item_to_json({"id": 1}, "contents"))
    try:
        assert await asyncio.to_thread(started.wait, 5)
        first.cancel()
        second = asyncio.create_task(writer.write_single_item_to_json({"id": 2}, "contents"))
        await asyncio.sleep(0)
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await first
    await second
    with open(writer._get_file_path("json", "contents"), encoding="utf-8") as source:
        assert json.load(source) == [{"id": 1}, {"id": 2}]
