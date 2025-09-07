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
