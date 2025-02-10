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
# @Author  : relakkes@gmail.com
# @Time    : 2024/4/6 14:54
# @Desc    : mediacrawler db 管理
import asyncio
from typing import Dict
from urllib.parse import urlparse

import aiofiles
import aiomysql

import config
from async_db import AsyncMysqlDB
from tools import utils
from var import db_conn_pool_var, media_crawler_db_var


async def init_mediacrawler_db():
    """
    初始化数据库链接池对象，并将该对象塞给media_crawler_db_var上下文变量
    Returns:

    """
    pool = await aiomysql.create_pool(
        host=config.RELATION_DB_HOST,
        port=config.RELATION_DB_PORT,
        user=config.RELATION_DB_USER,
        password=config.RELATION_DB_PWD,
        db=config.RELATION_DB_NAME,
        autocommit=True,
    )
    async_db_obj = AsyncMysqlDB(pool)

    # 将连接池对象和封装的CRUD sql接口对象放到上下文变量中
    db_conn_pool_var.set(pool)
    media_crawler_db_var.set(async_db_obj)


async def init_db():
    """
    初始化db连接池
    Returns:

    """
    utils.logger.info("[init_db] start init mediacrawler db connect object")
    await init_mediacrawler_db()
    utils.logger.info("[init_db] end init mediacrawler db connect object")


async def close():
    """
    关闭连接池
    Returns:

    """
    utils.logger.info("[close] close mediacrawler db pool")
    db_pool: aiomysql.Pool = db_conn_pool_var.get()
    if db_pool is not None:
        db_pool.close()


async def init_table_schema():
    """
    用来初始化数据库表结构，请在第一次需要创建表结构的时候使用，多次执行该函数会将已有的表以及数据全部删除
    Returns:

    """
    utils.logger.info("[init_table_schema] begin init mysql table schema ...")
    await init_mediacrawler_db()
    async_db_obj: AsyncMysqlDB = media_crawler_db_var.get()
    async with aiofiles.open("schema/tables.sql", mode="r", encoding="utf-8") as f:
        schema_sql = await f.read()
        await async_db_obj.execute(schema_sql)
        utils.logger.info("[init_table_schema] mediacrawler table schema init successful")
        await close()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(init_table_schema())
