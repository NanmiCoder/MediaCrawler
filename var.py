from asyncio.tasks import Task
from contextvars import ContextVar
from typing import List

import aiomysql

from async_db import AsyncMysqlDB

request_keyword_var: ContextVar[str] = ContextVar("request_keyword", default="")
crawler_type_var: ContextVar[str] = ContextVar("crawler_type", default="")
comment_tasks_var: ContextVar[List[Task]] = ContextVar("comment_tasks", default=[])
media_crawler_db_var: ContextVar[AsyncMysqlDB] = ContextVar("media_crawler_db_var")
db_conn_pool_var: ContextVar[aiomysql.Pool] = ContextVar("db_conn_pool_var")
