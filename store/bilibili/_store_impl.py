# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/bilibili/_store_impl.py
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
# @Desc    : B站存储实现类
import asyncio
import csv
import json
import os
import pathlib
from typing import Dict

import aiofiles
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

import config
from base.base_crawler import AbstractStore
from database.db_session import get_session
from database.models import BilibiliVideoComment, BilibiliVideo, BilibiliUpInfo, BilibiliUpDynamic, BilibiliContactInfo
from tools.async_file_writer import AsyncFileWriter
from tools import utils, words
from var import crawler_type_var
from database.mongodb_store_base import MongoDBStoreBase


class BiliCsvStoreImplement(AbstractStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="bili"
        )

    async def store_content(self, content_item: Dict):
        """
        content CSV storage implementation
        Args:
            content_item:

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=content_item,
            item_type="videos"
        )

    async def store_comment(self, comment_item: Dict):
        """
        comment CSV storage implementation
        Args:
            comment_item:

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=comment_item,
            item_type="comments"
        )

    async def store_creator(self, creator: Dict):
        """
        creator CSV storage implementation
        Args:
            creator:

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=creator,
            item_type="creators"
        )

    async def store_contact(self, contact_item: Dict):
        """
        creator contact CSV storage implementation
        Args:
            contact_item: creator's contact item dict

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=contact_item,
            item_type="contacts"
        )

    async def store_dynamic(self, dynamic_item: Dict):
        """
        creator dynamic CSV storage implementation
        Args:
            dynamic_item: creator's contact item dict

        Returns:

        """
        await self.file_writer.write_to_csv(
            item=dynamic_item,
            item_type="dynamics"
        )


class BiliDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        """
        Bilibili content DB storage implementation
        Args:
            content_item: content item dict
        """
        video_id = content_item.get("video_id")
        async with get_session() as session:
            result = await session.execute(select(BilibiliVideo).where(BilibiliVideo.video_id == video_id))
            video_detail = result.scalar_one_or_none()

            if not video_detail:
                content_item["add_ts"] = utils.get_current_timestamp()
                new_content = BilibiliVideo(**content_item)
                session.add(new_content)
            else:
                for key, value in content_item.items():
                    setattr(video_detail, key, value)
            await session.commit()

    async def store_comment(self, comment_item: Dict):
        """
        Bilibili comment DB storage implementation
        Args:
            comment_item: comment item dict
        """
        comment_id = comment_item.get("comment_id")
        async with get_session() as session:
            result = await session.execute(select(BilibiliVideoComment).where(BilibiliVideoComment.comment_id == comment_id))
            comment_detail = result.scalar_one_or_none()

            if not comment_detail:
                comment_item["add_ts"] = utils.get_current_timestamp()
                new_comment = BilibiliVideoComment(**comment_item)
                session.add(new_comment)
            else:
                for key, value in comment_item.items():
                    setattr(comment_detail, key, value)
            await session.commit()

    async def store_creator(self, creator: Dict):
        """
        Bilibili creator DB storage implementation
        Args:
            creator: creator item dict
        """
        creator_id = creator.get("user_id")
        async with get_session() as session:
            result = await session.execute(select(BilibiliUpInfo).where(BilibiliUpInfo.user_id == creator_id))
            creator_detail = result.scalar_one_or_none()

            if not creator_detail:
                creator["add_ts"] = utils.get_current_timestamp()
                new_creator = BilibiliUpInfo(**creator)
                session.add(new_creator)
            else:
                for key, value in creator.items():
                    setattr(creator_detail, key, value)
            await session.commit()

    async def store_contact(self, contact_item: Dict):
        """
        Bilibili contact DB storage implementation
        Args:
            contact_item: contact item dict
        """
        up_id = contact_item.get("up_id")
        fan_id = contact_item.get("fan_id")
        async with get_session() as session:
            result = await session.execute(
                select(BilibiliContactInfo).where(BilibiliContactInfo.up_id == up_id, BilibiliContactInfo.fan_id == fan_id)
            )
            contact_detail = result.scalar_one_or_none()

            if not contact_detail:
                contact_item["add_ts"] = utils.get_current_timestamp()
                new_contact = BilibiliContactInfo(**contact_item)
                session.add(new_contact)
            else:
                for key, value in contact_item.items():
                    setattr(contact_detail, key, value)
            await session.commit()

    async def store_dynamic(self, dynamic_item):
        """
        Bilibili dynamic DB storage implementation
        Args:
            dynamic_item: dynamic item dict
        """
        dynamic_id = dynamic_item.get("dynamic_id")
        async with get_session() as session:
            result = await session.execute(select(BilibiliUpDynamic).where(BilibiliUpDynamic.dynamic_id == dynamic_id))
            dynamic_detail = result.scalar_one_or_none()

            if not dynamic_detail:
                dynamic_item["add_ts"] = utils.get_current_timestamp()
                new_dynamic = BilibiliUpDynamic(**dynamic_item)
                session.add(new_dynamic)
            else:
                for key, value in dynamic_item.items():
                    setattr(dynamic_detail, key, value)
            await session.commit()


class BiliJsonStoreImplement(AbstractStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="bili"
        )

    async def store_content(self, content_item: Dict):
        """
        content JSON storage implementation
        Args:
            content_item:

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=content_item,
            item_type="contents"
        )

    async def store_comment(self, comment_item: Dict):
        """
        comment JSON storage implementation
        Args:
            comment_item:

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=comment_item,
            item_type="comments"
        )

    async def store_creator(self, creator: Dict):
        """
        creator JSON storage implementation
        Args:
            creator:

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=creator,
            item_type="creators"
        )

    async def store_contact(self, contact_item: Dict):
        """
        creator contact JSON storage implementation
        Args:
            contact_item: creator's contact item dict

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=contact_item,
            item_type="contacts"
        )

    async def store_dynamic(self, dynamic_item: Dict):
        """
        creator dynamic JSON storage implementation
        Args:
            dynamic_item: creator's contact item dict

        Returns:

        """
        await self.file_writer.write_single_item_to_json(
            item=dynamic_item,
            item_type="dynamics"
        )



class BiliSqliteStoreImplement(BiliDbStoreImplement):
    pass


class BiliMongoStoreImplement(AbstractStore):
    """B站MongoDB存储实现"""

    def __init__(self):
        self.mongo_store = MongoDBStoreBase(collection_prefix="bilibili")

    async def store_content(self, content_item: Dict):
        """
        存储视频内容到MongoDB
        Args:
            content_item: 视频内容数据
        """
        video_id = content_item.get("video_id")
        if not video_id:
            return

        await self.mongo_store.save_or_update(
            collection_suffix="contents",
            query={"video_id": video_id},
            data=content_item
        )
        utils.logger.info(f"[BiliMongoStoreImplement.store_content] Saved video {video_id} to MongoDB")

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
        utils.logger.info(f"[BiliMongoStoreImplement.store_comment] Saved comment {comment_id} to MongoDB")

    async def store_creator(self, creator_item: Dict):
        """
        存储UP主信息到MongoDB
        Args:
            creator_item: UP主数据
        """
        user_id = creator_item.get("user_id")
        if not user_id:
            return

        await self.mongo_store.save_or_update(
            collection_suffix="creators",
            query={"user_id": user_id},
            data=creator_item
        )
        utils.logger.info(f"[BiliMongoStoreImplement.store_creator] Saved creator {user_id} to MongoDB")
