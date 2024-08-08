# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/4/6 15:30
# @Desc    : sql接口集合

from typing import Dict, List

from db import AsyncMysqlDB
from var import media_crawler_db_var


async def query_content_by_content_id(content_id: str) -> Dict:
    """
    查询一条内容记录（xhs的帖子 ｜ 抖音的视频 ｜ 微博 ｜ 快手视频 ...）
    Args:
        content_id:

    Returns:

    """
    async_db_conn: AsyncMysqlDB = media_crawler_db_var.get()
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
    async_db_conn: AsyncMysqlDB = media_crawler_db_var.get()
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
    async_db_conn: AsyncMysqlDB = media_crawler_db_var.get()
    effect_row: int = await async_db_conn.update_table("bilibili_video", content_item, "video_id", content_id)
    return effect_row



async def query_comment_by_comment_id(comment_id: str) -> Dict:
    """
    查询一条评论内容
    Args:
        comment_id:

    Returns:

    """
    async_db_conn: AsyncMysqlDB = media_crawler_db_var.get()
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
    async_db_conn: AsyncMysqlDB = media_crawler_db_var.get()
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
    async_db_conn: AsyncMysqlDB = media_crawler_db_var.get()
    effect_row: int = await async_db_conn.update_table("bilibili_video_comment", comment_item, "comment_id", comment_id)
    return effect_row


async def query_creator_by_creator_id(creator_id: str) -> Dict:
    """
    查询up主信息
    Args:
        creator_id:

    Returns:

    """
    async_db_conn: AsyncMysqlDB = media_crawler_db_var.get()
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
    async_db_conn: AsyncMysqlDB = media_crawler_db_var.get()
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
    async_db_conn: AsyncMysqlDB = media_crawler_db_var.get()
    effect_row: int = await async_db_conn.update_table("bilibili_up_info", creator_item, "user_id", creator_id)
    return effect_row

