from typing import List

from tortoise import Tortoise, run_async

from config.db_config import *
from tools import utils


def get_platform_models() -> List[str]:
    models = ["store.xhs", "store.douyin", "store.bilibili", "store.kuaishou", "store.weibo"]
    return models


async def init_db(create_db: bool = False) -> None:
    await Tortoise.init(
        db_url=RELATION_DB_URL,
        modules={'models': get_platform_models()},
        _create_db=create_db
    )

async def close() -> None:
    await Tortoise.close_connections()

async def init():
    await init_db(create_db=True)
    await Tortoise.generate_schemas()
    utils.logger.info("[db.init] Init DB Success!")


if __name__ == '__main__':
    run_async(init())
