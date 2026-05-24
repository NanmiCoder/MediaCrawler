# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/smzdm/__init__.py
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

from typing import List
import config
from base.base_crawler import AbstractStore
from ._store_impl import (SmzdmCsvStoreImplement,
                          SmzdmDbStoreImplement,
                          SmzdmJsonStoreImplement,
                          SmzdmJsonlStoreImplement,
                          SmzdmSqliteStoreImplement,
                          SmzdmMongoStoreImplement,
                          SmzdmExcelStoreImplement)
from tools import utils


class SmzdmStoreFactory:
    STORES = {
        "csv": SmzdmCsvStoreImplement,
        "db": SmzdmDbStoreImplement,
        "postgres": SmzdmDbStoreImplement,
        "json": SmzdmJsonStoreImplement,
        "jsonl": SmzdmJsonlStoreImplement,
        "sqlite": SmzdmSqliteStoreImplement,
        "mongodb": SmzdmMongoStoreImplement,
        "excel": SmzdmExcelStoreImplement,
    }

    @staticmethod
    def createStore() -> AbstractStore:
        """
        创建具体的存储类实例
        """
        storeClass = SmzdmStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not storeClass:
            raise ValueError("[SmzdmStoreFactory.createStore] Invalid save option...")
        return storeClass()


async def updateSmzdmPost(postItem: dict):
    """
    更新什么值得买商品/文章数据
    """
    postItem.update({"last_modify_ts": utils.get_current_timestamp()})
    await SmzdmStoreFactory.createStore().store_content(postItem)


async def batchUpdateSmzdmComments(comments: List[dict]):
    """
    批量更新什么值得买评论数据
    """
    if not comments:
        return
    for commentItem in comments:
        commentItem.update({"last_modify_ts": utils.get_current_timestamp()})
        await SmzdmStoreFactory.createStore().store_comment(commentItem)
