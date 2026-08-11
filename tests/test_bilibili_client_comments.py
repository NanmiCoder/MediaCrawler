# -*- coding: utf-8 -*-
"""
教学版回归测试(B站 bilibili):确保视频评论首页的置顶评论及楼中楼不会遗漏。

覆盖:
1. top/top_replies 与 replies 重复时,置顶评论只回调一次并触发楼中楼抓取。
2. 兼容 top 直接返回评论对象的接口形态。
"""

import pytest

from media_platform.bilibili.client import BilibiliClient


@pytest.mark.asyncio
async def test_video_comments_include_pinned_comment_once_and_fetch_replies():
    client = object.__new__(BilibiliClient)
    pinned = {"rpid": 193769108192, "rcount": 6}
    regular = {"rpid": 193434771680, "rcount": 0}
    callbacks = []
    sub_comment_calls = []

    async def get_video_comments(video_id, order_mode, next_page):
        return {
            "cursor": {"is_end": True, "next": 0},
            "replies": [pinned.copy(), regular],
            "top": {"upper": pinned},
            "top_replies": [pinned],
        }

    async def get_video_all_level_two_comments(
        video_id, comment_id, order_mode, ps, crawl_interval, callback
    ):
        sub_comment_calls.append(comment_id)

    async def callback(video_id, comments):
        callbacks.append([comment["rpid"] for comment in comments])

    client.get_video_comments = get_video_comments
    client.get_video_all_level_two_comments = get_video_all_level_two_comments

    await client.get_video_all_comments(
        video_id="323173868",
        crawl_interval=0,
        is_fetch_sub_comments=True,
        callback=callback,
        max_count=10,
    )

    assert callbacks == [[pinned["rpid"], regular["rpid"]]]
    assert sub_comment_calls == [pinned["rpid"]]


@pytest.mark.asyncio
async def test_video_comments_accept_direct_top_comment():
    client = object.__new__(BilibiliClient)
    callbacks = []

    async def get_video_comments(video_id, order_mode, next_page):
        return {
            "cursor": {"is_end": True, "next": 0},
            "replies": [],
            "top": {"rpid": 1, "rcount": 0},
        }

    async def callback(video_id, comments):
        callbacks.extend(comments)

    client.get_video_comments = get_video_comments

    await client.get_video_all_comments(
        video_id="323173868", crawl_interval=0, callback=callback, max_count=10
    )

    assert [comment["rpid"] for comment in callbacks] == [1]
