# -*- coding: utf-8 -*-

import pytest

from media_platform.bilibili.client import BilibiliClient
from media_platform.bilibili.field import BilibiliCommentType


@pytest.mark.asyncio
async def test_video_comments_trim_first_level_before_fetching_sub_comments(monkeypatch):
    client = object.__new__(BilibiliClient)
    fetched_roots = []
    saved_batches = []

    async def fake_get_comments(oid, comment_type, order_mode, next):
        assert comment_type is BilibiliCommentType.VIDEO
        return {
            "cursor": {"is_end": True, "next": 0},
            "replies": [
                {"rpid": 1, "rcount": 1, "content": {"message": "a"}},
                {"rpid": 2, "rcount": 1, "content": {"message": "b"}},
            ],
        }

    async def fake_get_all_level_two_comments(
        oid,
        comment_type,
        level_one_comment_id,
        order_mode,
        ps,
        crawl_interval,
        callback,
    ):
        assert comment_type is BilibiliCommentType.VIDEO
        fetched_roots.append(level_one_comment_id)

    async def fake_callback(video_id, comments):
        saved_batches.append(comments)

    async def fake_sleep(_):
        return None

    monkeypatch.setattr(client, "get_comments", fake_get_comments)
    monkeypatch.setattr(client, "get_all_level_two_comments", fake_get_all_level_two_comments)
    monkeypatch.setattr("media_platform.bilibili.client.asyncio.sleep", fake_sleep)

    result = await client.get_video_all_comments(
        video_id="123",
        crawl_interval=0,
        is_fetch_sub_comments=True,
        callback=fake_callback,
        max_count=1,
    )

    assert [comment["rpid"] for comment in saved_batches[0]] == [1]
    assert fetched_roots == [1]
    assert [comment["rpid"] for comment in result] == [1]
