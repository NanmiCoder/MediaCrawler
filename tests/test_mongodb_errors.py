# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_mongodb_errors.py
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

from unittest.mock import AsyncMock, Mock

import pytest

from database.mongodb_store_base import MongoDBStoreBase


@pytest.mark.asyncio
async def test_mongodb_failed_write_reaches_the_caller(monkeypatch):
    store = MongoDBStoreBase("xhs")
    collection = Mock(update_one=AsyncMock(side_effect=OSError("database unavailable")))
    monkeypatch.setattr(store, "get_collection", AsyncMock(return_value=collection))
    with pytest.raises(OSError, match="database unavailable"):
        await store.save_or_update("contents", {"note_id": "1"}, {"title": "test"})


@pytest.mark.asyncio
async def test_mongodb_successful_upsert_retains_its_contract(monkeypatch):
    store = MongoDBStoreBase("xhs")
    collection = Mock(update_one=AsyncMock())
    monkeypatch.setattr(store, "get_collection", AsyncMock(return_value=collection))
    assert await store.save_or_update("contents", {"note_id": "1"}, {"title": "test"}) is True
    collection.update_one.assert_awaited_once_with({"note_id": "1"}, {"$set": {"title": "test"}}, upsert=True)


@pytest.mark.asyncio
async def test_mongodb_platform_store_does_not_log_false_success(monkeypatch):
    from store.xhs._store_impl import XhsMongoStoreImplement
    from tools import utils
    store = XhsMongoStoreImplement()
    monkeypatch.setattr(store.mongo_store, "get_collection", AsyncMock(side_effect=OSError("offline")))
    log = Mock()
    monkeypatch.setattr(utils.logger, "info", log)
    with pytest.raises(OSError, match="offline"):
        await store.store_content({"note_id": "1", "title": "example"})
    assert not any("Saved note" in str(call) for call in log.call_args_list)
