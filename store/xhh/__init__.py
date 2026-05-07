# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
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

from typing import Dict

import config
from tools import utils

from ._store_impl import (
    XhhCsvStoreImplement,
    XhhJsonStoreImplement,
    XhhJsonlStoreImplement,
)


class XhhStoreFactory:
    STORES = {
        "csv": XhhCsvStoreImplement,
        "json": XhhJsonStoreImplement,
        "jsonl": XhhJsonlStoreImplement,
    }

    @staticmethod
    def create_store():
        store_class = XhhStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            # 默认 jsonl
            store_class = XhhJsonlStoreImplement
        return store_class()


async def update_xhh_post(post_item: Dict):
    """
    Store xiaoheihe post data
    Args:
        post_item: normalized post dict from core._normalize_post()
    """
    utils.logger.info(
        f"[store.xhh.update_xhh_post] Storing post link_id={post_item.get('link_id')}"
    )
    await XhhStoreFactory.create_store().store_content(post_item)
