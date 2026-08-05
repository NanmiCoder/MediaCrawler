# -*- coding: utf-8 -*-

import pytest

from media_platform.bilibili.client import BilibiliClient


@pytest.fixture
def bili_client():
    return object.__new__(BilibiliClient)


@pytest.mark.asyncio
async def test_get_article_info_calls_article_view_endpoint(monkeypatch, bili_client):
    captured = {}

    async def fake_get(uri, params=None, enable_params_sign=True):
        captured["uri"] = uri
        captured["params"] = params
        captured["enable_params_sign"] = enable_params_sign
        return {"id": 123456, "title": "article title"}

    monkeypatch.setattr(bili_client, "get", fake_get)

    result = await bili_client.get_article_info("123456")

    assert captured["uri"] == "/x/article/view"
    assert captured["params"] == {"id": "123456"}
    assert captured["enable_params_sign"] is False
    assert result["title"] == "article title"
