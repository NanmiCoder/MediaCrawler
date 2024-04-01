# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 18:46
# @Desc    : 抖音存储实现类
import asyncio
import csv
import json
import os
import pathlib
from typing import Dict

import aiofiles
from tortoise.contrib.pydantic import pydantic_model_creator

from base.base_crawler import AbstractStore
from tools import utils
from var import crawler_type_var


class DouyinCsvStoreImplement(AbstractStore):
    csv_store_path: str = "data/douyin"

    def make_save_file_name(self, store_type: str) -> str:
        """
        make save file name by store type
        Args:
            store_type: contents or comments

        Returns: eg: data/douyin/search_comments_20240114.csv ...

        """
        return f"{self.csv_store_path}/{crawler_type_var.get()}_{store_type}_{utils.get_current_date()}.csv"

    async def save_data_to_csv(self, save_item: Dict, store_type: str):
        """
        Below is a simple way to save it in CSV format.
        Args:
            save_item:  save content dict info
            store_type: Save type contains content and comments（contents | comments）

        Returns: no returns

        """
        pathlib.Path(self.csv_store_path).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(store_type=store_type)
        async with aiofiles.open(save_file_name, mode='a+', encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if await f.tell() == 0:
                await writer.writerow(save_item.keys())
            await writer.writerow(save_item.values())

    async def store_content(self, content_item: Dict):
        """
        Xiaohongshu content CSV storage implementation
        Args:
            content_item: note item dict

        Returns:

        """
        await self.save_data_to_csv(save_item=content_item, store_type="contents")

    async def store_comment(self, comment_item: Dict):
        """
        Xiaohongshu comment CSV storage implementation
        Args:
            comment_item: comment item dict

        Returns:

        """
        await self.save_data_to_csv(save_item=comment_item, store_type="comments")


class DouyinDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        """
        Douyin content DB storage implementation
        Args:
            content_item: content item dict

        Returns:

        """
        from .douyin_store_db_types import DouyinAweme
        aweme_id = content_item.get("aweme_id")
        if not await DouyinAweme.filter(aweme_id=aweme_id).exists():
            content_item["add_ts"] = utils.get_current_timestamp()
            douyin_aweme_pydantic = pydantic_model_creator(DouyinAweme, name='DouyinAwemeCreate', exclude=('id',))
            douyin_data = douyin_aweme_pydantic(**content_item)
            douyin_aweme_pydantic.model_validate(douyin_data)
            await DouyinAweme.create(**douyin_data.dict())
        else:
            douyin_aweme_pydantic = pydantic_model_creator(DouyinAweme, name='DouyinAwemeUpdate',
                                                           exclude=('id', 'add_ts'))
            douyin_data = douyin_aweme_pydantic(**content_item)
            douyin_aweme_pydantic.model_validate(douyin_data)
            await DouyinAweme.filter(aweme_id=aweme_id).update(**douyin_data.model_dump())

    async def store_comment(self, comment_item: Dict):
        """
        Douyin content DB storage implementation
        Args:
            comment_item: comment item dict

        Returns:

        """
        from .douyin_store_db_types import DouyinAwemeComment
        comment_id = comment_item.get("comment_id")
        if not await DouyinAwemeComment.filter(comment_id=comment_id).exists():
            comment_item["add_ts"] = utils.get_current_timestamp()
            comment_pydantic = pydantic_model_creator(DouyinAwemeComment, name='DouyinAwemeCommentCreate',
                                                      exclude=('id',))
            comment_data = comment_pydantic(**comment_item)
            comment_pydantic.model_validate(comment_data)
            await DouyinAwemeComment.create(**comment_data.model_dump())
        else:
            comment_pydantic = pydantic_model_creator(DouyinAwemeComment, name='DouyinAwemeCommentUpdate',
                                                      exclude=('id', 'add_ts'))
            comment_data = comment_pydantic(**comment_item)
            comment_pydantic.model_validate(comment_data)
            await DouyinAwemeComment.filter(comment_id=comment_id).update(**comment_data.model_dump())


class DouyinJsonStoreImplement(AbstractStore):
    json_store_path: str = "data/douyin"
    lock = asyncio.Lock()

    def make_save_file_name(self, store_type: str) -> str:
        """
        make save file name by store type
        Args:
            store_type: Save type contains content and comments（contents | comments）

        Returns:

        """
        return f"{self.json_store_path}/{crawler_type_var.get()}_{store_type}_{utils.get_current_date()}.json"

    async def save_data_to_json(self, save_item: Dict, store_type: str):
        """
        Below is a simple way to save it in json format.
        Args:
            save_item: save content dict info
            store_type: Save type contains content and comments（contents | comments）

        Returns:

        """
        pathlib.Path(self.json_store_path).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(store_type=store_type)
        save_data = []

        async with self.lock:
            if os.path.exists(save_file_name):
                async with aiofiles.open(save_file_name, 'r', encoding='utf-8') as file:
                    save_data = json.loads(await file.read())

            save_data.append(save_item)
            async with aiofiles.open(save_file_name, 'w', encoding='utf-8') as file:
                await file.write(json.dumps(save_data, ensure_ascii=False))

    async def store_content(self, content_item: Dict):
        """
        content JSON storage implementation
        Args:
            content_item:

        Returns:

        """
        await self.save_data_to_json(content_item, "contents")

    async def store_comment(self, comment_item: Dict):
        """
        comment JSON storage implementatio
        Args:
            comment_item:

        Returns:

        """
        await self.save_data_to_json(comment_item, "comments")
