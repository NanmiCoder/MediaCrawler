# -*- coding: utf-8 -*-

import config
import pytest
from cmd_arg import parse_cmd
from media_platform.xhs import XiaoHongShuCrawler


@pytest.mark.asyncio
async def test_collect_cli_type_is_not_downgraded():
    """`--type collect` must be accepted, not silently fall back to search."""
    await parse_cmd(["--platform", "xhs", "--type", "collect"])
    assert config.CRAWLER_TYPE == "collect"


@pytest.mark.asyncio
async def test_get_collected_notes_uses_logged_in_user_when_list_empty(monkeypatch):
    """Empty XHS_COLLECT_USER_ID_LIST -> crawl the logged-in account's own
    collection: resolve its user_id and forward the collected notes to the
    detail/comment pipeline."""
    monkeypatch.setattr(config, "XHS_COLLECT_USER_ID_LIST", [])

    crawler = XiaoHongShuCrawler()
    calls = {}

    class FakeClient:
        async def get_self_user_id(self):
            return "5f0000000000000000000abc"

        async def get_all_notes_by_collect(
            self, user_id, crawl_interval, callback, xsec_token, xsec_source
        ):
            calls["collect_user_id"] = user_id
            return [
                {"note_id": "n1", "xsec_token": "t1"},
                {"note_id": "n2", "xsec_token": "t2"},
            ]

    crawler.xhs_client = FakeClient()

    async def fake_batch(note_ids, xsec_tokens):
        calls["note_ids"] = note_ids
        calls["xsec_tokens"] = xsec_tokens

    monkeypatch.setattr(crawler, "batch_get_note_comments", fake_batch)

    await crawler.get_collected_notes()

    assert calls["collect_user_id"] == "5f0000000000000000000abc"
    assert calls["note_ids"] == ["n1", "n2"]
    assert calls["xsec_tokens"] == ["t1", "t2"]


@pytest.mark.asyncio
async def test_get_collected_notes_parses_configured_profile_url(monkeypatch):
    """A configured profile URL is parsed into user_id + xsec_token, and the
    logged-in user's own id is NOT used."""
    url = (
        "https://www.xiaohongshu.com/user/profile/5f58bd990000000001003753"
        "?xsec_token=ABtoken123=&xsec_source=pc_search"
    )
    monkeypatch.setattr(config, "XHS_COLLECT_USER_ID_LIST", [url])

    crawler = XiaoHongShuCrawler()
    seen = {}

    class FakeClient:
        async def get_self_user_id(self):
            seen["self_called"] = True
            return "SHOULD_NOT_BE_USED"

        async def get_all_notes_by_collect(
            self, user_id, crawl_interval, callback, xsec_token, xsec_source
        ):
            seen["user_id"] = user_id
            seen["xsec_token"] = xsec_token
            return []

    crawler.xhs_client = FakeClient()

    async def fake_batch(note_ids, xsec_tokens):
        seen["batch_called"] = True

    monkeypatch.setattr(crawler, "batch_get_note_comments", fake_batch)

    await crawler.get_collected_notes()

    assert seen["user_id"] == "5f58bd990000000001003753"
    assert seen["xsec_token"] == "ABtoken123="
    assert "self_called" not in seen
