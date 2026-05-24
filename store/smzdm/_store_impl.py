# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/smzdm/_store_impl.py
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

from typing import Dict
from sqlalchemy import select
import config
from base.base_crawler import AbstractStore
from database.db_session import get_session
from database.models import SmzdmPost, SmzdmComment
from tools import utils
from tools.async_file_writer import AsyncFileWriter
from database.mongodb_store_base import MongoDBStoreBase
from var import crawler_type_var


class SmzdmCsvStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="smzdm", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        """
        保存商品/文章信息至 CSV
        """
        await self.writer.write_to_csv(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        """
        保存评论信息至 CSV
        """
        await self.writer.write_to_csv(item_type="comments", item=comment_item)

    async def store_creator(self, creator: Dict):
        pass


class SmzdmDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        """
        保存商品/文章信息至 DB
        """
        postId = content_item.get("post_id")
        async with get_session() as session:
            stmt = select(SmzdmPost).where(SmzdmPost.post_id == postId)
            result = await session.execute(stmt)
            existingContent = result.scalars().first()
            if existingContent:
                for key, value in content_item.items():
                    if hasattr(existingContent, key):
                        setattr(existingContent, key, value)
            else:
                if "add_ts" not in content_item:
                    content_item["add_ts"] = utils.get_current_timestamp()
                newPost = SmzdmPost(**content_item)
                session.add(newPost)
            await session.commit()

    async def store_comment(self, comment_item: Dict):
        """
        保存评论信息至 DB
        """
        commentId = comment_item.get("comment_id")
        async with get_session() as session:
            stmt = select(SmzdmComment).where(SmzdmComment.comment_id == commentId)
            result = await session.execute(stmt)
            existingComment = result.scalars().first()
            if existingComment:
                for key, value in comment_item.items():
                    if hasattr(existingComment, key):
                        setattr(existingComment, key, value)
            else:
                if "add_ts" not in comment_item:
                    comment_item["add_ts"] = utils.get_current_timestamp()
                newComment = SmzdmComment(**comment_item)
                session.add(newComment)
            await session.commit()

    async def store_creator(self, creator: Dict):
        pass


class SmzdmJsonStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="smzdm", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        """
        保存商品/文章信息至 JSON
        """
        await self.writer.write_single_item_to_json(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        """
        保存评论信息至 JSON
        """
        await self.writer.write_single_item_to_json(item_type="comments", item=comment_item)

    async def store_creator(self, creator: Dict):
        pass


class SmzdmJsonlStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="smzdm", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        """
        保存商品/文章信息至 JSONL
        """
        await self.writer.write_to_jsonl(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        """
        保存评论信息至 JSONL
        """
        await self.writer.write_to_jsonl(item_type="comments", item=comment_item)

    async def store_creator(self, creator: Dict):
        pass


class SmzdmSqliteStoreImplement(SmzdmDbStoreImplement):
    pass


class SmzdmMongoStoreImplement(AbstractStore):
    def __init__(self):
        self.mongoStore = MongoDBStoreBase(collection_prefix="smzdm")

    async def store_content(self, content_item: Dict):
        """
        保存商品/文章信息至 MongoDB
        """
        postId = content_item.get("post_id")
        if postId:
            await self.mongoStore.save_or_update(
                collection_suffix="contents", query={"post_id": postId}, data=content_item
            )

    async def store_comment(self, comment_item: Dict):
        """
        保存评论信息至 MongoDB
        """
        commentId = comment_item.get("comment_id")
        if commentId:
            await self.mongoStore.save_or_update(
                collection_suffix="comments", query={"comment_id": commentId}, data=comment_item
            )

    async def store_creator(self, creator: Dict):
        pass


class SmzdmExcelStoreImplement:
    def __new__(cls, *args, **kwargs):
        from store.excel_store_base import ExcelStoreBase
        return ExcelStoreBase.get_instance(platform="smzdm", crawler_type=crawler_type_var.get())
