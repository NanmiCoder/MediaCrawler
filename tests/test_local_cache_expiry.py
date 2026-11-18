# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_local_cache_expiry.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio

import pytest

from cache.local_cache import ExpiringLocalCache


@pytest.mark.asyncio
async def test_local_cleanup_removes_all_expired_entries_and_keeps_running(monkeypatch):
    now = 100.0
    monkeypatch.setattr("cache.local_cache.time.time", lambda: now)
    cache = ExpiringLocalCache(cron_interval=0.001)
    try:
        cache.set("first", "one", 1)
        cache.set("second", "two", 1)
        cache.set("live", "three", 20)
        now = 102.0
        await asyncio.sleep(0.02)
        assert not cache._cron_task.done()
        assert cache.keys("*") == ["live"]
        assert cache.get("live") == "three"
    finally:
        cache._cron_task.cancel()
        await asyncio.gather(cache._cron_task, return_exceptions=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("reader", ["get", "keys"])
async def test_expiry_boundary_is_consistent_for_get_and_keys(monkeypatch, reader):
    now = 100.0
    monkeypatch.setattr("cache.local_cache.time.time", lambda: now)
    cache = ExpiringLocalCache()
    try:
        cache.set("item", "value", 1)
        now = 101.0
        if reader == "get":
            assert cache.get("item") is None
        else:
            assert cache.keys("*") == []
    finally:
        cache._cron_task.cancel()
        await asyncio.gather(cache._cron_task, return_exceptions=True)
