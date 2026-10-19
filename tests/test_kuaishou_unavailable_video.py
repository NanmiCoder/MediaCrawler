# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_kuaishou_unavailable_video.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""快手详情接口遇到「不可用视频」时的回归测试。

回归背景：快手对已删除/私密/不存在的视频返回的是
``visionVideoDetail: {photo: null, author: null}`` —— key 存在、值是 null。
而 ``detail.get("photo", {})`` 只在 key **缺失** 时给默认值，key 存在且为 null
时拿到的仍是 ``None``，紧接着的 ``photo.get(...)`` 抛 AttributeError；
该异常不在 ``get_video_info_task`` 的 except 列表里，又会穿过
``asyncio.gather``，把整轮爬取直接带崩。

这里不发起网络请求，只用 stub client 驱动真实的任务函数。
"""

from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from media_platform.kuaishou.core import KuaishouCrawler  # noqa: E402

PHOTO_ID = "3x3zxz4mjrsc8ke"
UNAVAILABLE_PHOTO_ID = "3xf8enb8dbj6uig"

# 真实响应里 photo/author 为 null 的那个视频
UNAVAILABLE_DETAIL = {
    "visionVideoDetail": {
        "status": 1,
        "type": "video",
        "author": None,
        "photo": None,
        "tags": [],
    }
}

NORMAL_DETAIL = {
    "visionVideoDetail": {
        "status": 1,
        "type": "video",
        "author": {"name": "余胜军说Java"},
        "photo": {"id": PHOTO_ID, "caption": "我教你学Python", "likeCount": 167000},
        "tags": [],
    }
}


class _StubClient:
    def __init__(self, payload):
        self._payload = payload

    async def get_video_info(self, photo_id):  # noqa: ANN001
        return self._payload


def _make_crawler(payload) -> SimpleNamespace:
    """只借 get_video_info_task 用到的 self.ks_client，不需要完整 crawler"""
    return SimpleNamespace(ks_client=_StubClient(payload))


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """去掉任务里的固定延时与随机抖动，测试不应真的等待"""
    monkeypatch.setattr(config, "CRAWLER_MAX_SLEEP_SEC", 0)
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)


@pytest.mark.asyncio
async def test_unavailable_video_is_skipped_instead_of_crashing():
    """photo 为 null 时返回 None（跳过），而不是抛 AttributeError"""
    crawler = _make_crawler(UNAVAILABLE_DETAIL)

    result = await KuaishouCrawler.get_video_info_task(
        crawler, UNAVAILABLE_PHOTO_ID, asyncio.Semaphore(1)
    )

    assert result is None


@pytest.mark.asyncio
async def test_missing_photo_key_is_also_skipped():
    """photo 字段整个缺失时同样跳过（.get 的默认值路径）"""
    crawler = _make_crawler({"visionVideoDetail": {"status": 1, "author": None}})

    result = await KuaishouCrawler.get_video_info_task(
        crawler, UNAVAILABLE_PHOTO_ID, asyncio.Semaphore(1)
    )

    assert result is None


@pytest.mark.asyncio
async def test_normal_video_still_returns_detail():
    """正常视频不受影响"""
    crawler = _make_crawler(NORMAL_DETAIL)

    result = await KuaishouCrawler.get_video_info_task(
        crawler, PHOTO_ID, asyncio.Semaphore(1)
    )

    assert result is not None
    assert result["photo"]["id"] == PHOTO_ID


@pytest.mark.asyncio
async def test_empty_vision_video_detail_returns_none():
    """visionVideoDetail 整体缺失时返回 None"""
    crawler = _make_crawler({})

    result = await KuaishouCrawler.get_video_info_task(
        crawler, PHOTO_ID, asyncio.Semaphore(1)
    )

    assert result is None
