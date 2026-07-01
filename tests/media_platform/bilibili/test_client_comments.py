# -*- coding: utf-8 -*-

import pytest

from media_platform.bilibili.client import BilibiliClient
from media_platform.bilibili.field import BilibiliCommentType, CommentOrderType


@pytest.fixture
def bili_client():
    return object.__new__(BilibiliClient)


@pytest.mark.asyncio
async def test_get_comments_uses_comment_type(monkeypatch, bili_client):
    captured = {}

    async def fake_get(uri, params=None, enable_params_sign=True):
        captured["uri"] = uri
        captured["params"] = params
        return {}

    monkeypatch.setattr(bili_client, "get", fake_get)

    await bili_client.get_comments(
        oid="123456",
        comment_type=BilibiliCommentType.ARTICLE,
        order_mode=CommentOrderType.DEFAULT,
        next=0,
    )

    assert captured["uri"] == "/x/v2/reply/wbi/main"
    assert captured["params"]["oid"] == "123456"
    assert captured["params"]["type"] == 12


@pytest.mark.asyncio
async def test_get_video_comments_keeps_type_1(monkeypatch, bili_client):
    captured = {}

    async def fake_get(uri, params=None, enable_params_sign=True):
        captured["params"] = params
        return {}

    monkeypatch.setattr(bili_client, "get", fake_get)

    await bili_client.get_video_comments("998877")

    assert captured["params"]["oid"] == "998877"
    assert captured["params"]["type"] == 1


@pytest.mark.asyncio
async def test_get_all_comments_limits_first_level_before_fetching_sub_comments(monkeypatch, bili_client):
    fetched_roots = []
    saved_batches = []

    async def fake_get_comments(oid, comment_type, order_mode, next):
        return {
            "cursor": {"is_end": True, "next": 0},
            "replies": [
                {"rpid": 1, "rcount": 1, "content": {"message": "a"}, "member": {"mid": 1, "uname": "u1"}},
                {"rpid": 2, "rcount": 1, "content": {"message": "b"}, "member": {"mid": 2, "uname": "u2"}},
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
        fetched_roots.append(level_one_comment_id)

    async def fake_callback(oid, comments):
        saved_batches.append(comments)

    async def fake_sleep(_):
        return None

    monkeypatch.setattr(bili_client, "get_comments", fake_get_comments)
    monkeypatch.setattr(bili_client, "get_all_level_two_comments", fake_get_all_level_two_comments)
    monkeypatch.setattr("media_platform.bilibili.client.asyncio.sleep", fake_sleep)

    result = await bili_client.get_all_comments(
        oid="123",
        comment_type=BilibiliCommentType.ARTICLE,
        crawl_interval=0,
        is_fetch_sub_comments=True,
        callback=fake_callback,
        max_count=1,
    )

    assert [comment["rpid"] for comment in saved_batches[0]] == [1]
    assert fetched_roots == [1]
    assert [comment["rpid"] for comment in result] == [1]


@pytest.mark.asyncio
async def test_get_video_all_comments_wrapper_preserves_trimmed_sub_comment_fetch(monkeypatch, bili_client):
    fetched_roots = []
    saved_batches = []

    async def fake_get_all_comments(
        oid,
        comment_type,
        crawl_interval,
        is_fetch_sub_comments,
        callback,
        max_count,
    ):
        assert oid == "123"
        assert comment_type is BilibiliCommentType.VIDEO
        assert is_fetch_sub_comments is True
        assert max_count == 1
        await callback(
            oid,
            [{"rpid": 1, "rcount": 1, "content": {"message": "a"}, "member": {"mid": 1, "uname": "u1"}}],
        )
        fetched_roots.append(1)
        return [{"rpid": 1, "rcount": 1, "content": {"message": "a"}, "member": {"mid": 1, "uname": "u1"}}]

    async def fake_callback(oid, comments):
        saved_batches.append(comments)

    monkeypatch.setattr(bili_client, "get_all_comments", fake_get_all_comments)

    result = await bili_client.get_video_all_comments(
        video_id="123",
        crawl_interval=0,
        is_fetch_sub_comments=True,
        callback=fake_callback,
        max_count=1,
    )

    assert [comment["rpid"] for comment in saved_batches[0]] == [1]
    assert fetched_roots == [1]
    assert [comment["rpid"] for comment in result] == [1]
