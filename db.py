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
from async_sqlite_db import AsyncSqliteDB
from tools import utils
from var import db_conn_pool_var, media_crawler_db_var


async def init_mediacrawler_db():
    """
    初始化数据库链接池对象，并将该对象塞给media_crawler_db_var上下文变量
    Returns:

    """
    pool = await aiomysql.create_pool(
        host=config.MYSQL_DB_HOST,
        port=config.MYSQL_DB_PORT,
        user=config.MYSQL_DB_USER,
        password=config.MYSQL_DB_PWD,
        db=config.MYSQL_DB_NAME,
        autocommit=True,
    )
    async_db_obj = AsyncMysqlDB(pool)

    # 将连接池对象和封装的CRUD sql接口对象放到上下文变量中
    db_conn_pool_var.set(pool)
    media_crawler_db_var.set(async_db_obj)


async def init_sqlite_db():
    """
    初始化SQLite数据库对象，并将该对象塞给media_crawler_db_var上下文变量
    Returns:

    """
    async_db_obj = AsyncSqliteDB(config.SQLITE_DB_PATH)
    
    # 将SQLite数据库对象放到上下文变量中
    media_crawler_db_var.set(async_db_obj)


async def init_db():
    """
    初始化db连接池
    Returns:

    """
    utils.logger.info("[init_db] start init mediacrawler db connect object")
    if config.SAVE_DATA_OPTION == "sqlite":
        await init_sqlite_db()
        utils.logger.info("[init_db] end init sqlite db connect object")
    else:
        await init_mediacrawler_db()
        utils.logger.info("[init_db] end init mysql db connect object")


async def close():
    """
    关闭数据库连接
    Returns:

    """
    utils.logger.info("[close] close mediacrawler db connection")
    if config.SAVE_DATA_OPTION == "sqlite":
        # SQLite数据库连接会在AsyncSqliteDB对象销毁时自动关闭
        utils.logger.info("[close] sqlite db connection will be closed automatically")
    else:
        # MySQL连接池关闭
        db_pool: aiomysql.Pool = db_conn_pool_var.get()
        if db_pool is not None:
            db_pool.close()
            utils.logger.info("[close] mysql db pool closed")


async def init_table_schema(db_type: str = None):
    """
    用来初始化数据库表结构，请在第一次需要创建表结构的时候使用，多次执行该函数会将已有的表以及数据全部删除
    Args:
        db_type: 数据库类型，可选值为 'sqlite' 或 'mysql'，如果不指定则使用配置文件中的设置
    Returns:

    """
    # 如果没有指定数据库类型，则使用配置文件中的设置
    if db_type is None:
        db_type = config.SAVE_DATA_OPTION
    
    if db_type == "sqlite":
        utils.logger.info("[init_table_schema] begin init sqlite table schema ...")
        
        # 检查并删除可能存在的损坏数据库文件
        import os
        if os.path.exists(config.SQLITE_DB_PATH):
            try:
                # 尝试删除现有的数据库文件
                os.remove(config.SQLITE_DB_PATH)
                utils.logger.info(f"[init_table_schema] removed existing sqlite db file: {config.SQLITE_DB_PATH}")
            except Exception as e:
                utils.logger.warning(f"[init_table_schema] failed to remove existing sqlite db file: {e}")
                # 如果删除失败，尝试重命名文件
                try:
                    backup_path = f"{config.SQLITE_DB_PATH}.backup_{utils.get_current_timestamp()}"
                    os.rename(config.SQLITE_DB_PATH, backup_path)
                    utils.logger.info(f"[init_table_schema] renamed existing sqlite db file to: {backup_path}")
                except Exception as rename_e:
                    utils.logger.error(f"[init_table_schema] failed to rename existing sqlite db file: {rename_e}")
                    raise rename_e
        
        await init_sqlite_db()
        async_db_obj: AsyncSqliteDB = media_crawler_db_var.get()
        async with aiofiles.open("schema/sqlite_tables.sql", mode="r", encoding="utf-8") as f:
            schema_sql = await f.read()
            await async_db_obj.executescript(schema_sql)
            utils.logger.info("[init_table_schema] sqlite table schema init successful")
    elif db_type == "mysql":
        utils.logger.info("[init_table_schema] begin init mysql table schema ...")
        await init_mediacrawler_db()
        async_db_obj: AsyncMysqlDB = media_crawler_db_var.get()
        async with aiofiles.open("schema/tables.sql", mode="r", encoding="utf-8") as f:
            schema_sql = await f.read()
            await async_db_obj.execute(schema_sql)
            utils.logger.info("[init_table_schema] mysql table schema init successful")
            await close()
    else:
        utils.logger.error(f"[init_table_schema] 不支持的数据库类型: {db_type}")
        raise ValueError(f"不支持的数据库类型: {db_type}，支持的类型: sqlite, mysql")


def show_database_options():
    """
    显示支持的数据库选项
    """
    print("\n=== MediaCrawler 数据库初始化工具 ===")
    print("支持的数据库类型:")
    print("1. sqlite  - SQLite 数据库 (轻量级，无需额外配置)")
    print("2. mysql   - MySQL 数据库 (需要配置数据库连接信息)")
    print("3. config  - 使用配置文件中的设置")
    print("4. exit    - 退出程序")
    print("="*50)


def get_user_choice():
    """
    获取用户选择的数据库类型
    Returns:
        str: 用户选择的数据库类型
    """
    while True:
        choice = input("请输入数据库类型 (sqlite/mysql/config/exit): ").strip().lower()
        
        if choice in ['sqlite', 'mysql', 'config', 'exit']:
            return choice
        else:
            print("❌ 无效的选择，请输入: sqlite, mysql, config 或 exit")


async def main():
    """
    主函数，处理用户交互和数据库初始化
    """
    try:
        show_database_options()
        
        while True:
            choice = get_user_choice()
            
            if choice == 'exit':
                print("👋 程序已退出")
                break
            elif choice == 'config':
                print(f"📋 使用配置文件中的设置: {config.SAVE_DATA_OPTION}")
                await init_table_schema()
                print("✅ 数据库表结构初始化完成！")
                break
            else:
                print(f"🚀 开始初始化 {choice.upper()} 数据库...")
                await init_table_schema(choice)
                print("✅ 数据库表结构初始化完成！")
                break
                
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    except Exception as e:
        print(f"\n❌ 初始化失败: {str(e)}")
        utils.logger.error(f"[main] 数据库初始化失败: {str(e)}")


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
