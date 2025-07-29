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
    """计算数据保存文件的前部分排序数字，支持每次运行代码不写到同一个文件中
    Args:
        file_store_path: 文件存储路径
    Returns:
        file nums: 文件编号
    """
    if not os.path.exists(file_store_path):
        return 1
    try:
        return max([int(file_name.split("_")[0]) for file_name in os.listdir(file_store_path)]) + 1
    except ValueError:
        return 1


class JuejinCsvStoreImplement(AbstractStore):
    csv_store_path: str = "data/juejin"
    file_count: int = calculate_number_of_files(csv_store_path)

    def make_save_file_name(self, store_type: str) -> str:
        """
        根据存储类型生成保存文件名
        Args:
            store_type: 存储类型 contents | comments | creators

        Returns: 例如: data/juejin/1_search_contents_20240114.csv

        """
        return f"{self.csv_store_path}/{self.file_count}_{crawler_type_var.get()}_{store_type}_{utils.get_current_date()}.csv"

    async def save_data_to_csv(self, save_item: Dict, store_type: str):
        """
        将数据保存为CSV格式
        Args:
            save_item: 保存的内容字典信息
            store_type: 保存类型 contents | comments | creators

        Returns: 无返回值

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
        掘金文章CSV存储实现
        Args:
            content_item: 文章内容字典

        Returns:

        """
        await self.save_data_to_csv(save_item=content_item, store_type="contents")

    async def store_comment(self, comment_item: Dict):
        """
        掘金评论CSV存储实现
        Args:
            comment_item: 评论内容字典

        Returns:

        """
        await self.save_data_to_csv(save_item=comment_item, store_type="comments")

    async def store_creator(self, creator: Dict):
        """
        掘金创作者CSV存储实现
        Args:
            creator: 创作者信息字典

        Returns:

        """
        await self.save_data_to_csv(save_item=creator, store_type="creators")


class JuejinDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        """
        掘金文章数据库存储实现
        Args:
            content_item: 文章内容字典
        """
        from . import juejin_store_sql
        article_id = content_item.get("article_id")
        if not article_id:
            return
        
        # 查询是否已存在
        existing_article = await juejin_store_sql.query_content_by_content_id(article_id)
        if existing_article:
            # 更新现有记录
            await juejin_store_sql.update_content_by_content_id(article_id, content_item)
        else:
            # 插入新记录
            await juejin_store_sql.add_new_content(content_item)

    async def store_comment(self, comment_item: Dict):
        """
        掘金评论数据库存储实现
        Args:
            comment_item: 评论内容字典
        """
        from . import juejin_store_sql
        comment_id = comment_item.get("comment_id")
        if not comment_id:
            return
            
        # 查询是否已存在
        existing_comment = await juejin_store_sql.query_comment_by_comment_id(comment_id)
        if existing_comment:
            # 更新现有记录
            await juejin_store_sql.update_comment_by_comment_id(comment_id, comment_item)
        else:
            # 插入新记录
            await juejin_store_sql.add_new_comment(comment_item)

    async def store_creator(self, creator: Dict):
        """
        掘金创作者数据库存储实现
        Args:
            creator: 创作者信息字典
        """
        from . import juejin_store_sql
        user_id = creator.get("user_id")
        if not user_id:
            return
            
        # 查询是否已存在
        existing_creator = await juejin_store_sql.query_creator_by_user_id(user_id)
        if existing_creator:
            # 更新现有记录
            await juejin_store_sql.update_creator_by_user_id(user_id, creator)
        else:
            # 插入新记录
            await juejin_store_sql.add_new_creator(creator)


class JuejinJsonStoreImplement(AbstractStore):
    json_store_path: str = "data/juejin"
    file_count: int = calculate_number_of_files(json_store_path)

    def make_save_file_name(self, store_type: str) -> str:
        """
        根据存储类型生成保存文件名
        Args:
            store_type: 存储类型 contents | comments | creators

        Returns: 例如: data/juejin/1_search_contents_20240114.json

        """
        return f"{self.json_store_path}/{self.file_count}_{crawler_type_var.get()}_{store_type}_{utils.get_current_date()}.json"

    async def save_data_to_json(self, save_item: Dict, store_type: str):
        """
        将数据保存为JSON格式
        Args:
            save_item: 保存的内容字典信息
            store_type: 保存类型 contents | comments | creators

        Returns: 无返回值

        """
        pathlib.Path(self.json_store_path).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(store_type=store_type)
        
        # 读取现有数据
        save_data = []
        if os.path.exists(save_file_name):
            async with aiofiles.open(save_file_name, 'r', encoding='utf-8') as file:
                try:
                    content = await file.read()
                    save_data = json.loads(content) if content else []
                except json.JSONDecodeError:
                    save_data = []
        
        # 添加新数据
        save_data.append(save_item)
        
        # 写入文件
        async with aiofiles.open(save_file_name, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(save_data, ensure_ascii=False, indent=2))

    async def store_content(self, content_item: Dict):
        """
        掘金文章JSON存储实现
        Args:
            content_item: 文章内容字典

        Returns:

        """
        await self.save_data_to_json(save_item=content_item, store_type="contents")

    async def store_comment(self, comment_item: Dict):
        """
        掘金评论JSON存储实现
        Args:
            comment_item: 评论内容字典

        Returns:

        """
        await self.save_data_to_json(save_item=comment_item, store_type="comments")

    async def store_creator(self, creator: Dict):
        """
        掘金创作者JSON存储实现
        Args:
            creator: 创作者信息字典

        Returns:

        """
        await self.save_data_to_json(save_item=creator, store_type="creators")


class JuejinStoreFactory:
    STORES = {
        "csv": JuejinCsvStoreImplement,
        "db": JuejinDbStoreImplement,
        "json": JuejinJsonStoreImplement,
        "sqlite": JuejinDbStoreImplement,  # SQLite使用相同的数据库实现
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = JuejinStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[JuejinStoreFactory.create_store] Invalid save data option")
        return store_class() 