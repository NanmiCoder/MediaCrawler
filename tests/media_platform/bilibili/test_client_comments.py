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
