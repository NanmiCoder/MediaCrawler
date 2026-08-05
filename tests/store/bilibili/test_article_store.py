# -*- coding: utf-8 -*-

import pytest

from store import bilibili as bilibili_store


@pytest.mark.asyncio
async def test_update_bilibili_article_maps_article_fields(monkeypatch):
    saved = {}

    class FakeStore:
        async def store_content(self, content_item):
            saved.update(content_item)

    monkeypatch.setattr(bilibili_store.BiliStoreFactory, "create_store", lambda: FakeStore())
    monkeypatch.setattr(bilibili_store, "anonymize_user_id", lambda value: f"hash-{value}")
    monkeypatch.setattr(bilibili_store, "mask_nickname", lambda value: f"masked-{value}")

    await bilibili_store.update_bilibili_article({
        "id": 123456,
        "title": "title",
        "summary": "summary",
        "content": "content",
        "publish_time": 1710000000,
        "author": {"mid": 100, "name": "author"},
        "stats": {"like": 1, "favorite": 2, "share": 3, "reply": 4},
    })

    assert saved["article_id"] == "123456"
    assert saved["article_url"] == "https://www.bilibili.com/read/cv123456"
    assert saved["title"] == "title"
    assert saved["desc"] == "summary"
    assert saved["creator_hash"] == "hash-100"
    assert saved["nickname"] == "masked-author"
    assert saved["liked_count"] == "1"
    assert saved["favorite_count"] == "2"
    assert saved["share_count"] == "3"
    assert saved["comment_count"] == "4"


@pytest.mark.asyncio
async def test_update_bilibili_article_comment_maps_common_reply_fields(monkeypatch):
    saved = {}

    class FakeStore:
        async def store_article_comment(self, comment_item):
            saved.update(comment_item)

    monkeypatch.setattr(bilibili_store.BiliStoreFactory, "create_store", lambda: FakeStore())
    monkeypatch.setattr(bilibili_store, "anonymize_user_id", lambda value: f"hash-{value}")
    monkeypatch.setattr(bilibili_store, "mask_nickname", lambda value: f"masked-{value}")

    await bilibili_store.update_bilibili_article_comment("123456", {
        "rpid": 9,
        "parent": 0,
        "ctime": 1710000000,
        "content": {"message": "hello"},
        "member": {"mid": 10, "uname": "user"},
        "like": 5,
        "rcount": 1,
    })

    assert saved["article_id"] == "123456"
    assert saved["comment_id"] == "9"
    assert saved["parent_comment_id"] == "0"
    assert saved["content"] == "hello"
    assert saved["creator_hash"] == "hash-10"
    assert saved["nickname"] == "masked-user"
    assert saved["like_count"] == 5
