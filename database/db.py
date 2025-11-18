# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/database/db.py
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

# persist-1<persist1@126.com>
# 原因：将 db.py 改造为模块，移除直接执行入口，修复相对导入问题。
# 副作用：无
# 回滚策略：还原此文件。
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from tools import utils
from database.db_session import create_tables

async def init_table_schema(db_type: str):
    """
    Initializes the database table schema.
    This will create tables based on the ORM models.
    Args:
        db_type: The type of database, 'sqlite' or 'mysql'.
    """
    utils.logger.info(f"[init_table_schema] begin init {db_type} table schema ...")
    await create_tables(db_type)
    utils.logger.info(f"[init_table_schema] {db_type} table schema init successful")

async def init_db(db_type: str = None):
    await init_table_schema(db_type)

async def close():
    """
    Placeholder for closing database connections if needed in the future.
    """
    pass
