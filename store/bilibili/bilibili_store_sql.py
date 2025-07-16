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
# @Time    : 2024/4/6 15:30
# @Desc    : sql接口集合

from typing import Dict, List, Union

from async_db import AsyncMysqlDB
from async_sqlite_db import AsyncSqliteDB
from var import media_crawler_db_var


async def query_content_by_content_id(content_id: str) -> Dict:
    """
    查询一条内容记录（xhs的帖子 ｜ 抖音的视频 ｜ 微博 ｜ 快手视频 ...）
    Args:
        content_id:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from bilibili_video where video_id = '{content_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    if len(rows) > 0:
        return rows[0]
    return dict()


async def add_new_content(content_item: Dict) -> int:
    """
    新增一条内容记录（xhs的帖子 ｜ 抖音的视频 ｜ 微博 ｜ 快手视频 ...）
    Args:
        content_item:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    last_row_id: int = await async_db_conn.item_to_table("bilibili_video", content_item)
    return last_row_id


async def update_content_by_content_id(content_id: str, content_item: Dict) -> int:
    """
    更新一条记录（xhs的帖子 ｜ 抖音的视频 ｜ 微博 ｜ 快手视频 ...）
    Args:
        content_id:
        content_item:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    effect_row: int = await async_db_conn.update_table("bilibili_video", content_item, "video_id", content_id)
    return effect_row



async def query_comment_by_comment_id(comment_id: str) -> Dict:
    """
    查询一条评论内容
    Args:
        comment_id:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from bilibili_video_comment where comment_id = '{comment_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    if len(rows) > 0:
        return rows[0]
    return dict()


async def add_new_comment(comment_item: Dict) -> int:
    """
    新增一条评论记录
    Args:
        comment_item:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    last_row_id: int = await async_db_conn.item_to_table("bilibili_video_comment", comment_item)
    return last_row_id


async def update_comment_by_comment_id(comment_id: str, comment_item: Dict) -> int:
    """
    更新增一条评论记录
    Args:
        comment_id:
        comment_item:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    effect_row: int = await async_db_conn.update_table("bilibili_video_comment", comment_item, "comment_id", comment_id)
    return effect_row


async def query_creator_by_creator_id(creator_id: str) -> Dict:
    """
    查询up主信息
    Args:
        creator_id:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from bilibili_up_info where user_id = '{creator_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    if len(rows) > 0:
        return rows[0]
    return dict()


async def add_new_creator(creator_item: Dict) -> int:
    """
    新增up主信息
    Args:
        creator_item:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    last_row_id: int = await async_db_conn.item_to_table("bilibili_up_info", creator_item)
    return last_row_id


async def update_creator_by_creator_id(creator_id: str, creator_item: Dict) -> int:
    """
    更新up主信息
    Args:
        creator_id:
        creator_item:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    effect_row: int = await async_db_conn.update_table("bilibili_up_info", creator_item, "user_id", creator_id)
    return effect_row


async def query_contact_by_up_and_fan(up_id: str, fan_id: str) -> Dict:
    """
    查询一条关联关系
    Args:
        up_id:
        fan_id:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from bilibili_contact_info where up_id = '{up_id}' and fan_id = '{fan_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    if len(rows) > 0:
        return rows[0]
    return dict()


async def add_new_contact(contact_item: Dict) -> int:
    """
    新增关联关系
    Args:
        contact_item:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    last_row_id: int = await async_db_conn.item_to_table("bilibili_contact_info", contact_item)
    return last_row_id


async def update_contact_by_id(id: str, contact_item: Dict) -> int:
    """
    更新关联关系
    Args:
        id:
        contact_item:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    effect_row: int = await async_db_conn.update_table("bilibili_contact_info", contact_item, "id", id)
    return effect_row


async def query_dynamic_by_dynamic_id(dynamic_id: str) -> Dict:
    """
    查询一条动态信息
    Args:
        dynamic_id:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from bilibili_up_dynamic where dynamic_id = '{dynamic_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    if len(rows) > 0:
        return rows[0]
    return dict()


async def add_new_dynamic(dynamic_item: Dict) -> int:
    """
    新增动态信息
    Args:
        dynamic_item:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    last_row_id: int = await async_db_conn.item_to_table("bilibili_up_dynamic", dynamic_item)
    return last_row_id


async def update_dynamic_by_dynamic_id(dynamic_id: str, dynamic_item: Dict) -> int:
    """
    更新动态信息
    Args:
        dynamic_id:
        dynamic_item:

    Returns:

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    effect_row: int = await async_db_conn.update_table("bilibili_up_dynamic", dynamic_item, "dynamic_id", dynamic_id)
    return effect_row
