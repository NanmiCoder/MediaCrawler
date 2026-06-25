# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/tiktok/_store_impl.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习 and 研究目的使用。使用者应遵守以下原则：
# 1. 不得用于 any 商业用途。
# 2. 使用时应遵守目标平台的使用条款 and robots.txt规则。
# 3. 不得进行大规模爬取 or 对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于 any 非法 or 不当 the 用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则 and LICENSE中的所有条款。

import asyncio
import json
import os
import pathlib
from typing import Dict

from sqlalchemy import select

import config
from base.base_crawler import AbstractStore
from database.db_session import get_session
from database.models import TiktokAweme, TiktokAwemeComment, TiktokCreator
from tools import utils
from tools.async_file_writer import AsyncFileWriter
from var import crawler_type_var
from database.mongodb_store_base import MongoDBStoreBase


class TikTokCsvStoreImplement(AbstractStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="tiktok"
        )

    async def store_content(self, content_item: Dict):
        await self.file_writer.write_to_csv(
            item=content_item,
            item_type="contents"
        )

    async def store_comment(self, comment_item: Dict):
        await self.file_writer.write_to_csv(
            item=comment_item,
            item_type="comments"
        )

    async def store_creator(self, creator: Dict):
        await self.file_writer.write_to_csv(
            item=creator,
            item_type="creators"
        )


class TikTokDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        aweme_id = content_item.get("aweme_id")
        async with get_session() as session:
            result = await session.execute(select(TiktokAweme).where(TiktokAweme.aweme_id == aweme_id))
            aweme_detail = result.scalar_one_or_none()

            if not aweme_detail:
                content_item["add_ts"] = utils.get_current_timestamp()
                if content_item.get("title") or content_item.get("desc"):
                    new_content = TiktokAweme(**content_item)
                    session.add(new_content)
            else:
                for key, value in content_item.items():
                    setattr(aweme_detail, key, value)
            await session.commit()

    async def store_comment(self, comment_item: Dict):
        comment_id = comment_item.get("comment_id")
        async with get_session() as session:
            result = await session.execute(select(TiktokAwemeComment).where(TiktokAwemeComment.comment_id == comment_id))
            comment_detail = result.scalar_one_or_none()

            if not comment_detail:
                comment_item["add_ts"] = utils.get_current_timestamp()
                new_comment = TiktokAwemeComment(**comment_item)
                session.add(new_comment)
            else:
                for key, value in comment_item.items():
                    setattr(comment_detail, key, value)
            await session.commit()

    async def store_creator(self, creator: Dict):
        user_id = creator.get("user_id")
        async with get_session() as session:
            result = await session.execute(select(TiktokCreator).where(TiktokCreator.user_id == user_id))
            user_detail = result.scalar_one_or_none()

            if not user_detail:
                creator["add_ts"] = utils.get_current_timestamp()
                new_creator = TiktokCreator(**creator)
                session.add(new_creator)
            else:
                for key, value in creator.items():
                    setattr(user_detail, key, value)
            await session.commit()


class TikTokJsonStoreImplement(AbstractStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="tiktok"
        )

    async def store_content(self, content_item: Dict):
        await self.file_writer.write_single_item_to_json(
            item=content_item,
            item_type="contents"
        )

    async def store_comment(self, comment_item: Dict):
        await self.file_writer.write_single_item_to_json(
            item=comment_item,
            item_type="comments"
        )

    async def store_creator(self, creator: Dict):
        await self.file_writer.write_single_item_to_json(
            item=creator,
            item_type="creators"
        )


class TikTokJsonlStoreImplement(AbstractStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="tiktok"
        )

    async def store_content(self, content_item: Dict):
        await self.file_writer.write_to_jsonl(
            item=content_item,
            item_type="contents"
        )

    async def store_comment(self, comment_item: Dict):
        await self.file_writer.write_to_jsonl(
            item=comment_item,
            item_type="comments"
        )

    async def store_creator(self, creator: Dict):
        await self.file_writer.write_to_jsonl(
            item=creator,
            item_type="creators"
        )


class TikTokSqliteStoreImplement(TikTokDbStoreImplement):
    pass


class TikTokMongoStoreImplement(AbstractStore):
    def __init__(self):
        self.mongo_store = MongoDBStoreBase(collection_prefix="tiktok")

    async def store_content(self, content_item: Dict):
        aweme_id = content_item.get("aweme_id")
        if not aweme_id:
            return

        await self.mongo_store.save_or_update(
            collection_suffix="contents",
            query={"aweme_id": aweme_id},
            data=content_item
        )
        utils.logger.info(f"[TikTokMongoStoreImplement.store_content] Saved aweme {aweme_id} to MongoDB")

    async def store_comment(self, comment_item: Dict):
        comment_id = comment_item.get("comment_id")
        if not comment_id:
            return

        await self.mongo_store.save_or_update(
            collection_suffix="comments",
            query={"comment_id": comment_id},
            data=comment_item
        )
        utils.logger.info(f"[TikTokMongoStoreImplement.store_comment] Saved comment {comment_id} to MongoDB")

    async def store_creator(self, creator_item: Dict):
        user_id = creator_item.get("user_id")
        if not user_id:
            return

        await self.mongo_store.save_or_update(
            collection_suffix="creators",
            query={"user_id": user_id},
            data=creator_item
        )
        utils.logger.info(f"[TikTokMongoStoreImplement.store_creator] Saved creator {user_id} to MongoDB")


class TikTokExcelStoreImplement:
    def __new__(cls, *args, **kwargs):
        from store.excel_store_base import ExcelStoreBase
        return ExcelStoreBase.get_instance(
            platform="tiktok",
            crawler_type=crawler_type_var.get()
        )
