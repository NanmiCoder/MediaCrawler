# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 16:58
# @Desc    : 小红书存储实现类
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


class XhsCsvStoreImplement(AbstractStore):
    csv_store_path: str = "data/xhs"

    def make_save_file_name(self, store_type: str) -> str:
        """
        make save file name by store type
        Args:
            store_type: contents or comments

        Returns: eg: data/xhs/search_comments_20240114.csv ...

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
            f.fileno()
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


class XhsDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        """
        Xiaohongshu content DB storage implementation
        Args:
            content_item: content item dict

        Returns:

        """
        from .xhs_store_db_types import XHSNote
        note_id = content_item.get("note_id")
        if not await XHSNote.filter(note_id=note_id).first():
            content_item["add_ts"] = utils.get_current_timestamp()
            note_pydantic = pydantic_model_creator(XHSNote, name="XHSPydanticCreate", exclude=('id',))
            note_data = note_pydantic(**content_item)
            note_pydantic.model_validate(note_data)
            await XHSNote.create(**note_data.model_dump())
        else:
            note_pydantic = pydantic_model_creator(XHSNote, name="XHSPydanticUpdate", exclude=('id', 'add_ts'))
            note_data = note_pydantic(**content_item)
            note_pydantic.model_validate(note_data)
            await XHSNote.filter(note_id=note_id).update(**note_data.model_dump())

    async def store_comment(self, comment_item: Dict):
        """
        Xiaohongshu content DB storage implementation
        Args:
            comment_item: comment item dict

        Returns:

        """
        from .xhs_store_db_types import XHSNoteComment
        comment_id = comment_item.get("comment_id")
        if not await XHSNoteComment.filter(comment_id=comment_id).first():
            comment_item["add_ts"] = utils.get_current_timestamp()
            comment_pydantic = pydantic_model_creator(XHSNoteComment, name="CommentPydanticCreate", exclude=('id',))
            comment_data = comment_pydantic(**comment_item)
            comment_pydantic.model_validate(comment_data)
            await XHSNoteComment.create(**comment_data.model_dump())
        else:
            comment_pydantic = pydantic_model_creator(XHSNoteComment, name="CommentPydanticUpdate",
                                                      exclude=('id', 'add_ts',))
            comment_data = comment_pydantic(**comment_item)
            comment_pydantic.model_validate(comment_data)
            await XHSNoteComment.filter(comment_id=comment_id).update(**comment_data.model_dump())


class XhsJsonStoreImplement(AbstractStore):
    json_store_path: str = "data/xhs"
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
