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
# SQL接口集合

from typing import Dict, List, Union

from async_db import AsyncMysqlDB
from async_sqlite_db import AsyncSqliteDB
from var import media_crawler_db_var


async def query_content_by_content_id(content_id: str) -> Dict:
    """
    查询一条文章记录
    Args:
        content_id: 文章ID

    Returns:
        Dict: 文章记录字典，如果不存在则返回空字典

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from juejin_article where article_id = '{content_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    if len(rows) > 0:
        return rows[0]
    return dict()


async def add_new_content(content_item: Dict) -> int:
    """
    新增一条文章记录
    Args:
        content_item: 文章内容字典

    Returns:
        int: 插入记录的ID

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    last_row_id: int = await async_db_conn.item_to_table("juejin_article", content_item)
    return last_row_id


async def update_content_by_content_id(content_id: str, content_item: Dict) -> int:
    """
    更新一条文章记录
    Args:
        content_id: 文章ID
        content_item: 文章内容字典

    Returns:
        int: 影响的行数

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    effect_row: int = await async_db_conn.update_table("juejin_article", content_item, "article_id", content_id)
    return effect_row


async def query_comment_by_comment_id(comment_id: str) -> Dict:
    """
    查询一条评论记录
    Args:
        comment_id: 评论ID

    Returns:
        Dict: 评论记录字典，如果不存在则返回空字典

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from juejin_comment where comment_id = '{comment_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    if len(rows) > 0:
        return rows[0]
    return dict()


async def add_new_comment(comment_item: Dict) -> int:
    """
    新增一条评论记录
    Args:
        comment_item: 评论内容字典

    Returns:
        int: 插入记录的ID

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    last_row_id: int = await async_db_conn.item_to_table("juejin_comment", comment_item)
    return last_row_id


async def update_comment_by_comment_id(comment_id: str, comment_item: Dict) -> int:
    """
    更新一条评论记录
    Args:
        comment_id: 评论ID
        comment_item: 评论内容字典

    Returns:
        int: 影响的行数

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    effect_row: int = await async_db_conn.update_table("juejin_comment", comment_item, "comment_id", comment_id)
    return effect_row


async def query_creator_by_user_id(user_id: str) -> Dict:
    """
    查询一条创作者记录
    Args:
        user_id: 用户ID

    Returns:
        Dict: 创作者记录字典，如果不存在则返回空字典

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from juejin_creator where user_id = '{user_id}'"
    rows: List[Dict] = await async_db_conn.query(sql)
    if len(rows) > 0:
        return rows[0]
    return dict()


async def add_new_creator(creator_item: Dict) -> int:
    """
    新增一条创作者记录
    Args:
        creator_item: 创作者信息字典

    Returns:
        int: 插入记录的ID

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    last_row_id: int = await async_db_conn.item_to_table("juejin_creator", creator_item)
    return last_row_id


async def update_creator_by_user_id(user_id: str, creator_item: Dict) -> int:
    """
    更新一条创作者记录
    Args:
        user_id: 用户ID
        creator_item: 创作者信息字典

    Returns:
        int: 影响的行数

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    effect_row: int = await async_db_conn.update_table("juejin_creator", creator_item, "user_id", user_id)
    return effect_row


async def query_articles_by_keyword(keyword: str, limit: int = 20) -> List[Dict]:
    """
    根据关键词查询文章
    Args:
        keyword: 搜索关键词
        limit: 限制返回数量

    Returns:
        List[Dict]: 文章列表

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from juejin_article where title like '%{keyword}%' or brief_content like '%{keyword}%' limit {limit}"
    rows: List[Dict] = await async_db_conn.query(sql)
    return rows


async def query_comments_by_article_id(article_id: str) -> List[Dict]:
    """
    根据文章ID查询评论
    Args:
        article_id: 文章ID

    Returns:
        List[Dict]: 评论列表

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from juejin_comment where article_id = '{article_id}' order by created_time desc"
    rows: List[Dict] = await async_db_conn.query(sql)
    return rows


async def query_articles_by_creator(user_id: str, limit: int = 20) -> List[Dict]:
    """
    根据创作者ID查询文章
    Args:
        user_id: 创作者ID
        limit: 限制返回数量

    Returns:
        List[Dict]: 文章列表

    """
    async_db_conn: Union[AsyncMysqlDB, AsyncSqliteDB] = media_crawler_db_var.get()
    sql: str = f"select * from juejin_article where author_id = '{user_id}' order by created_time desc limit {limit}"
    rows: List[Dict] = await async_db_conn.query(sql)
    return rows 