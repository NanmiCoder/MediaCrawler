# -*- coding: utf-8 -*-
"""Creator timelines stop at the first note already stored."""

import config
import pytest

from media_platform.xhs.client import XiaoHongShuClient
from tools.incremental import collect_newest, xhs_note_id, xhs_note_is_pinned


def _note(note_id, sticky=False):
    note = {"note_id": note_id}
    if sticky:
        note["sticky"] = True
    return note


@pytest.mark.asyncio
async def test_stops_before_known_note_and_skips_the_next_page(tmp_path, monkeypatch):
    known = tmp_path / "known.txt"
    known.write_text("n3\n", encoding="utf-8")
    monkeypatch.setenv("CRAWL_KNOWN_CONTENT_IDS_FILE", str(known))
    orig = config.CRAWLER_MAX_NOTES_COUNT
    config.CRAWLER_MAX_NOTES_COUNT = 5
    calls = {"n": 0}
    pages = [
        {"has_more": True, "cursor": "next", "notes": [_note(f"n{i}") for i in range(1, 6)]},
        {"has_more": False, "cursor": "", "notes": [_note("n6")]},
    ]

    async def get_notes(*_args, **_kwargs):
        page = pages[calls["n"]]
        calls["n"] += 1
        return page

    try:
        client = XiaoHongShuClient.__new__(XiaoHongShuClient)
        client.get_notes_by_creator = get_notes
        fetched = []

        async def callback(notes):
            fetched.append([note["note_id"] for note in notes])

        result = await client.get_all_notes_by_creator("user", crawl_interval=0, callback=callback)
    finally:
        config.CRAWLER_MAX_NOTES_COUNT = orig

    assert [note["note_id"] for note in result] == ["n1", "n2"]
    assert fetched == [["n1", "n2"]]
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_known_pin_does_not_stop_before_newer_notes(tmp_path, monkeypatch):
    known = tmp_path / "known.txt"
    known.write_text("pin\nn3\n", encoding="utf-8")
    monkeypatch.setenv("CRAWL_KNOWN_CONTENT_IDS_FILE", str(known))
    orig = config.CRAWLER_MAX_NOTES_COUNT
    config.CRAWLER_MAX_NOTES_COUNT = 5

    calls = {"n": 0}

    async def get_notes(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] > 1:
            raise AssertionError("遇到已入库笔记后不应再翻页")
        return {
            "has_more": True,
            "cursor": "next",
            "notes": [_note("pin", sticky=True), _note("n1"), _note("n2"), _note("n3"), _note("n4")],
        }

    try:
        client = XiaoHongShuClient.__new__(XiaoHongShuClient)
        client.get_notes_by_creator = get_notes
        result = await client.get_all_notes_by_creator("user", crawl_interval=0)
    finally:
        config.CRAWLER_MAX_NOTES_COUNT = orig

    assert [note["note_id"] for note in result] == ["n1", "n2"]


@pytest.mark.asyncio
async def test_fills_the_limit_from_later_pages_when_nothing_is_known(tmp_path, monkeypatch):
    monkeypatch.delenv("CRAWL_KNOWN_CONTENT_IDS_FILE", raising=False)
    orig = config.CRAWLER_MAX_NOTES_COUNT
    config.CRAWLER_MAX_NOTES_COUNT = 3
    pages = [
        {"has_more": True, "cursor": "next", "notes": [_note("n1"), _note("n2")]},
        {"has_more": False, "cursor": "", "notes": [_note("n3"), _note("n4")]},
    ]
    calls = {"n": 0}

    async def get_notes(*_args, **_kwargs):
        page = pages[calls["n"]]
        calls["n"] += 1
        return page

    try:
        client = XiaoHongShuClient.__new__(XiaoHongShuClient)
        client.get_notes_by_creator = get_notes
        result = await client.get_all_notes_by_creator("user", crawl_interval=0)
    finally:
        config.CRAWLER_MAX_NOTES_COUNT = orig

    assert [note["note_id"] for note in result] == ["n1", "n2", "n3"]
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_collect_newest_is_the_only_stop_rule():
    notes = [_note("a"), _note("b", sticky=True), _note("c"), _note("d")]

    async def pages():
        yield notes

    cut = await collect_newest(
        pages(),
        known_ids={"b", "c"},
        limit=5,
        item_id=xhs_note_id,
        is_pinned=xhs_note_is_pinned,
    )
    assert [note["note_id"] for note in cut.collect] == ["a"]
    assert cut.stopped_id == "c"
    assert xhs_note_is_pinned({"corner_tag_info": {"text": "置顶"}}) is True
