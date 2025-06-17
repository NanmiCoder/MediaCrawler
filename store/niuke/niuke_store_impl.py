# -*- coding: utf-8 -*-
import asyncio
import csv
import json
import os
import pathlib
from typing import Dict

import aiofiles

import config
from base.base_crawler import AbstractStore
from tools import utils, words
from var import crawler_type_var


def calculate_number_of_files(file_store_path: str) -> int:
    if not os.path.exists(file_store_path):
        return 1
    try:
        return max([
            int(file_name.split("_")[0])
            for file_name in os.listdir(file_store_path)
        ]) + 1
    except ValueError:
        return 1


class NiukeCsvStoreImplement(AbstractStore):
    csv_store_path: str = "data/niuke"
    file_count: int = calculate_number_of_files(csv_store_path)

    def make_save_file_name(self, store_type: str) -> str:
        return f"{self.csv_store_path}/{self.file_count}_{crawler_type_var.get()}_{store_type}_{utils.get_current_date()}.csv"

    async def save_data_to_csv(self, save_item: Dict, store_type: str):
        pathlib.Path(self.csv_store_path).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(store_type)
        async with aiofiles.open(save_file_name, mode='a+', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            if await f.tell() == 0:
                await writer.writerow(save_item.keys())
            await writer.writerow(save_item.values())

    async def store_content(self, content_item: Dict):
        await self.save_data_to_csv(content_item, "contents")

    async def store_comment(self, comment_item: Dict):
        await self.save_data_to_csv(comment_item, "comments")

    async def store_creator(self, creator: Dict):
        await self.save_data_to_csv(creator, "creator")


class NiukeDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        from .niuke_store_sql import (
            add_new_content,
            query_content_by_content_id,
            update_content_by_content_id,
        )
        note_id = str(content_item.get("id"))
        note_detail: Dict = await query_content_by_content_id(content_id=note_id)
        if not note_detail:
            content_item["add_ts"] = utils.get_current_timestamp()
            await add_new_content(content_item)
        else:
            await update_content_by_content_id(note_id, content_item=content_item)

    async def store_comment(self, comment_item: Dict):
        pass

    async def store_creator(self, creator: Dict):
        pass


class NiukeJsonStoreImplement(AbstractStore):
    json_store_path: str = "data/niuke/json"
    words_store_path: str = "data/niuke/words"
    lock = asyncio.Lock()
    file_count: int = calculate_number_of_files(json_store_path)
    WordCloud = words.AsyncWordCloudGenerator()

    def make_save_file_name(self, store_type: str) -> (str, str):
        return (
            f"{self.json_store_path}/{crawler_type_var.get()}_{store_type}_{utils.get_current_date()}.json",
            f"{self.words_store_path}/{crawler_type_var.get()}_{store_type}_{utils.get_current_date()}",
        )

    async def save_data_to_json(self, save_item: Dict, store_type: str):
        pathlib.Path(self.json_store_path).mkdir(parents=True, exist_ok=True)
        pathlib.Path(self.words_store_path).mkdir(parents=True, exist_ok=True)
        save_file_name, words_file_name_prefix = self.make_save_file_name(store_type)
        save_data = []
        async with self.lock:
            if os.path.exists(save_file_name):
                async with aiofiles.open(save_file_name, 'r', encoding='utf-8') as file:
                    save_data = json.loads(await file.read())

            save_data.append(save_item)
            async with aiofiles.open(save_file_name, 'w', encoding='utf-8') as file:
                await file.write(json.dumps(save_data, ensure_ascii=False, indent=4))

            if config.ENABLE_GET_COMMENTS and config.ENABLE_GET_WORDCLOUD:
                try:
                    await self.WordCloud.generate_word_frequency_and_cloud(save_data, words_file_name_prefix)
                except Exception:
                    pass

    async def store_content(self, content_item: Dict):
        await self.save_data_to_json(content_item, "contents")

    async def store_comment(self, comment_item: Dict):
        await self.save_data_to_json(comment_item, "comments")

    async def store_creator(self, creator: Dict):
        await self.save_data_to_json(creator, "creator")
