# -*- coding: utf-8 -*-
"""Tests for Xiaohongshu author-reply comment filtering helpers."""

from store.xhs.comment_author import (
    clear_saved_comment_ids,
    is_author_comment,
    is_top_level_comment,
    mark_comment_saved,
    pop_pending_top_comment,
    remember_pending_top_comment,
    reset_note_comment_session,
    top_level_has_author_reply_inline,
)


def test_is_top_level_comment():
    assert is_top_level_comment({"target_comment": {}}) is True
    assert is_top_level_comment({"target_comment": {"id": "c1"}}) is False
    assert is_top_level_comment({"_root_comment_id": "c1"}) is False


def test_is_author_comment_by_show_tags():
    item = {"show_tags": ["is_author"], "user_info": {"user_id": "u2"}}
    assert is_author_comment(item, "u1") is True


def test_is_author_comment_by_chinese_tag_and_user_object():
    item = {"show_tags": [{"type": "作者"}], "user": {"userid": "author1"}}
    assert is_author_comment(item, "other") is True
    by_id = {"show_tags": [], "user": {"userid": "author1"}}
    assert is_author_comment(by_id, "author1") is True


def test_is_author_comment_by_user_id():
    item = {"show_tags": [], "user_info": {"user_id": "author1"}}
    assert is_author_comment(item, "author1") is True
    assert is_author_comment(item, "other") is False


def test_top_level_has_author_reply_inline():
    top = {
        "id": "top1",
        "sub_comments": [
            {"show_tags": [], "user_info": {"user_id": "u2"}},
            {"show_tags": ["is_author"], "user_info": {"user_id": "author"}},
        ],
    }
    assert top_level_has_author_reply_inline(top, "author") is True
    assert top_level_has_author_reply_inline(top, "missing") is True


def test_pending_top_comment_flow():
    note_id = "note1"
    reset_note_comment_session(note_id)
    remember_pending_top_comment(note_id, {"id": "top1", "content": "hello"})
    pending = pop_pending_top_comment(note_id, "top1")
    assert pending["id"] == "top1"
    assert pop_pending_top_comment(note_id, "top1") is None


def test_mark_comment_saved_dedup():
    clear_saved_comment_ids()
    assert mark_comment_saved("c1") is True
    assert mark_comment_saved("c1") is False


def test_author_reply_without_target_comment_is_still_saved(monkeypatch):
    """Sub-comment APIs often omit target_comment; they must still be kept."""
    import asyncio

    import store.xhs as xs
    from store.xhs.comment_author import register_note_author

    monkeypatch.setenv("XHS_SAVE_ONLY_AUTHOR_REPLY_THREADS", "true")
    captured = []

    class FakeStore:
        async def store_comment(self, comment_item):
            captured.append(comment_item)

    orig = xs.XhsStoreFactory.create_store
    xs.XhsStoreFactory.create_store = staticmethod(lambda: FakeStore())
    clear_saved_comment_ids()
    reset_note_comment_session("note1")
    register_note_author("note1", "author")
    try:
        asyncio.run(
            xs.batch_update_xhs_note_comments(
                "note1",
                [
                    {
                        "id": "top1",
                        "content": "问一下今天怎么看",
                        "user_info": {"user_id": "fan", "nickname": "粉丝"},
                        "target_comment": {},
                    }
                ],
            )
        )
        asyncio.run(
            xs.batch_update_xhs_note_comments(
                "note1",
                [
                    {
                        "id": "reply1",
                        "content": "分批买",
                        "user_info": {"user_id": "author", "nickname": "贴主"},
                        "show_tags": ["is_author"],
                        "_root_comment_id": "top1",
                    }
                ],
            )
        )
    finally:
        xs.XhsStoreFactory.create_store = orig

    by_id = {row["comment_id"]: row for row in captured}
    assert set(by_id) == {"top1", "reply1"}
    assert by_id["top1"]["comment_level"] == "top"
    assert by_id["top1"]["has_author_reply"] is True
    assert by_id["reply1"]["comment_level"] == "author_reply"
    assert by_id["reply1"]["is_author_reply"] is True


def test_author_first_level_comment_is_saved_without_replies(monkeypatch):
    import asyncio

    import store.xhs as xs
    from store.xhs.comment_author import register_note_author

    monkeypatch.setenv("XHS_SAVE_ONLY_AUTHOR_REPLY_THREADS", "true")
    captured = []

    class FakeStore:
        async def store_comment(self, comment_item):
            captured.append(comment_item)

    orig = xs.XhsStoreFactory.create_store
    xs.XhsStoreFactory.create_store = staticmethod(lambda: FakeStore())
    clear_saved_comment_ids()
    reset_note_comment_session("note1")
    register_note_author("note1", "author")
    try:
        asyncio.run(
            xs.batch_update_xhs_note_comments(
                "note1",
                [
                    {
                        "id": "solo",
                        "content": "贴主自己留的一级评论",
                        "user_info": {"user_id": "author", "nickname": "贴主"},
                        "show_tags": ["is_author"],
                        "target_comment": {},
                    }
                ],
            )
        )
        asyncio.run(xs.finalize_xhs_note_comments("note1"))
    finally:
        xs.XhsStoreFactory.create_store = orig

    assert len(captured) == 1
    row = captured[0]
    assert row["comment_id"] == "solo"
    assert row["comment_level"] == "top"
    assert row["is_author_reply"] is True
    assert row["has_author_reply"] is True


def test_get_comments_does_not_call_undefined_helper():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "media_platform" / "xhs" / "core.py").read_text(
        encoding="utf-8"
    )
    assert "clear_saved_comment_ids()" not in source.split("async def get_comments", 1)[1].split(
        "async def create_xhs_client", 1
    )[0]
