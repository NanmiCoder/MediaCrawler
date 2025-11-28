# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/weibo/_store_impl.py
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


# -*- coding: utf-8 -*-
# @Author  : persist1@126.com
# @Time    : 2025/9/5 19:34
# @Desc    : 微博存储实现类
import asyncio
import csv
import json
import os
import pathlib
from typing import Dict

import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from base.base_crawler import AbstractStore
from database.models import WeiboCreator, WeiboNote, WeiboNoteComment
from tools import utils, words
from tools.async_file_writer import AsyncFileWriter
from database.db_session import get_session
from var import crawler_type_var
from database.mongodb_store_base import MongoDBStoreBase


def calculate_number_of_files(file_store_path: str) -> int:
    """计算数据保存文件的前部分排序数字，支持每次运行代码不写到同一个文件中
    Args:
        file_store_path;
    Returns:
        file nums
    """
    if not os.path.exists(file_store_path):
        return 1
    try:
        return max([int(file_name.split("_")[0]) for file_name in os.listdir(file_store_path)]) + 1
    except ValueError:
        return 1


class WeiboCsvStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="weibo", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        """
        Weibo content CSV storage implementation
        Args:
            content_item: note item dict

        Returns:

        """
        await self.writer.write_to_csv(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        """
        Weibo comment CSV storage implementation
        Args:
            comment_item: comment item dict

        Returns:

        """
        await self.writer.write_to_csv(item_type="comments", item=comment_item)

    async def store_creator(self, creator: Dict):
        """
        Weibo creator CSV storage implementation
        Args:
            creator:

        Returns:

        """
        await self.writer.write_to_csv(item_type="creators", item=creator)


class WeiboDbStoreImplement(AbstractStore):

    async def store_content(self, content_item: Dict):
        """
        Weibo content DB storage implementation
        Args:
            content_item: content item dict

        Returns:

        """
        note_id = content_item.get("note_id")
        async with get_session() as session:
            stmt = select(WeiboNote).where(WeiboNote.note_id == note_id)
            res = await session.execute(stmt)
            db_note = res.scalar_one_or_none()
            if db_note:
                db_note.last_modify_ts = utils.get_current_timestamp()
                for key, value in content_item.items():
                    if hasattr(db_note, key):
                        setattr(db_note, key, value)
            else:
                content_item["add_ts"] = utils.get_current_timestamp()
                content_item["last_modify_ts"] = utils.get_current_timestamp()
                db_note = WeiboNote(**content_item)
                session.add(db_note)
            await session.commit()

    async def store_comment(self, comment_item: Dict):
        """
        Weibo content DB storage implementation
        Args:
            comment_item: comment item dict

        Returns:

        """
        comment_id = comment_item.get("comment_id")
        async with get_session() as session:
            stmt = select(WeiboNoteComment).where(WeiboNoteComment.comment_id == comment_id)
            res = await session.execute(stmt)
            db_comment = res.scalar_one_or_none()
            if db_comment:
                db_comment.last_modify_ts = utils.get_current_timestamp()
                for key, value in comment_item.items():
                    if hasattr(db_comment, key):
                        setattr(db_comment, key, value)
            else:
                comment_item["add_ts"] = utils.get_current_timestamp()
                comment_item["last_modify_ts"] = utils.get_current_timestamp()
                db_comment = WeiboNoteComment(**comment_item)
                session.add(db_comment)
            await session.commit()

    async def store_creator(self, creator: Dict):
        """
        Weibo creator DB storage implementation
        Args:
            creator:

        Returns:

        """
        user_id = creator.get("user_id")
        async with get_session() as session:
            stmt = select(WeiboCreator).where(WeiboCreator.user_id == user_id)
            res = await session.execute(stmt)
            db_creator = res.scalar_one_or_none()
            if db_creator:
                db_creator.last_modify_ts = utils.get_current_timestamp()
                for key, value in creator.items():
                    if hasattr(db_creator, key):
                        setattr(db_creator, key, value)
            else:
                creator["add_ts"] = utils.get_current_timestamp()
                creator["last_modify_ts"] = utils.get_current_timestamp()
                db_creator = WeiboCreator(**creator)
                session.add(db_creator)
            await session.commit()


class WeiboJsonStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="weibo", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        """
        content JSON storage implementation
        Args:
            content_item:

        Returns:

        """
        await self.writer.write_single_item_to_json(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        """
        comment JSON storage implementation
        Args:
            comment_item:

        Returns:

        """
        await self.writer.write_single_item_to_json(item_type="comments", item=comment_item)

    async def store_creator(self, creator: Dict):
        """
        creator JSON storage implementation
        Args:
            creator:

        Returns:

        """
        await self.writer.write_single_item_to_json(item_type="creators", item=creator)


class WeiboSqliteStoreImplement(WeiboDbStoreImplement):
    """
    Weibo content SQLite storage implementation
    """
    pass


class WeiboMongoStoreImplement(AbstractStore):
    """微博MongoDB存储实现"""

    def __init__(self):
        self.mongo_store = MongoDBStoreBase(collection_prefix="weibo")

    async def store_content(self, content_item: Dict):
        """
        存储微博内容到MongoDB
        Args:
            content_item: 微博内容数据
        """
        note_id = content_item.get("note_id")
        if not note_id:
            return

        await self.mongo_store.save_or_update(
            collection_suffix="contents",
            query={"note_id": note_id},
            data=content_item
        )
        utils.logger.info(f"[WeiboMongoStoreImplement.store_content] Saved note {note_id} to MongoDB")

    async def store_comment(self, comment_item: Dict):
        """
        存储评论到MongoDB
        Args:
            comment_item: 评论数据
        """
        comment_id = comment_item.get("comment_id")
        if not comment_id:
            return

        await self.mongo_store.save_or_update(
            collection_suffix="comments",
            query={"comment_id": comment_id},
            data=comment_item
        )
        utils.logger.info(f"[WeiboMongoStoreImplement.store_comment] Saved comment {comment_id} to MongoDB")

    async def store_creator(self, creator_item: Dict):
        """
        存储创作者信息到MongoDB
        Args:
            creator_item: 创作者数据
        """
        user_id = creator_item.get("user_id")
        if not user_id:
            return

        await self.mongo_store.save_or_update(
            collection_suffix="creators",
            query={"user_id": user_id},
            data=creator_item
        )
        utils.logger.info(f"[WeiboMongoStoreImplement.store_creator] Saved creator {user_id} to MongoDB")


class WeiboExcelStoreImplement:
    """微博Excel存储实现 - 全局单例"""

    def __new__(cls, *args, **kwargs):
        from store.excel_store_base import ExcelStoreBase
        return ExcelStoreBase.get_instance(
            platform="weibo",
            crawler_type=crawler_type_var.get()
        )
