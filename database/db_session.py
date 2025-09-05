from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from .models import Base
from config import SAVE_DATA_OPTION
from config.db_config import mysql_db_config, sqlite_db_config

# Keep a cache of engines
_engines = {}

def get_async_engine(db_type: str = None):
    if db_type is None:
        db_type = SAVE_DATA_OPTION

    if db_type in _engines:
        return _engines[db_type]

    if db_type in ["json", "csv"]:
        return None

    if db_type == "sqlite":
        db_url = f"sqlite+aiosqlite:///{sqlite_db_config['db_path']}"
    elif db_type == "mysql" or db_type == "db":
        db_url = f"mysql+asyncmy://{mysql_db_config['user']}:{mysql_db_config['password']}@{mysql_db_config['host']}:{mysql_db_config['port']}/{mysql_db_config['db_name']}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    engine = create_async_engine(db_url, echo=False)
    _engines[db_type] = engine
    return engine


async def create_tables(db_type: str = None):
    engine = get_async_engine(db_type)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncSession:
    engine = get_async_engine(SAVE_DATA_OPTION)
    AsyncSessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = AsyncSessionFactory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()