from tortoise import Tortoise, run_async

from config.db_config import *
from tools import utils


async def init_db(create_db: bool = False) -> None:
    await Tortoise.init(
        db_url=RELATION_DB_URL,
        modules={'models': ['models']},
        # modules={'models': ['models.kuaishou']}, # generate special table
        _create_db=create_db
    )


async def init():
    await init_db(create_db=True)
    await Tortoise.generate_schemas()
    utils.logger.info("Init DB Success!")


if __name__ == '__main__':
    run_async(init())
