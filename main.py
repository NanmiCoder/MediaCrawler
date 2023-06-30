import sys
import asyncio
import argparse

import config
from tools import utils
from base import proxy_account_pool
from media_platform.douyin import DouYinCrawler
from media_platform.xhs import XiaoHongShuCrawler
from aiohttp import web


class CrawlerFactory:
    @staticmethod
    def create_crawler(platform: str):
        if platform == "xhs":
            return XiaoHongShuCrawler()
        elif platform == "dy":
            return DouYinCrawler()
        else:
            raise ValueError("Invalid Media Platform Currently only supported xhs or douyin ...")

crawler = CrawlerFactory().create_crawler(platform=config.PLATFORM)
async def handle(request):
    name = request.match_info.get('name', "Anonymous")
    # await crawler.start()
    s=await crawler.start2(name)
    print(s)
    text = "Hello, " + name
    return web.Response(text=text)

app = web.Application()
app.add_routes([web.get('/{name}', handle)])





async def main():
    utils.init_loging_config()
    # define command line params ...
    parser = argparse.ArgumentParser(description='Media crawler program.')
    parser.add_argument('--platform', type=str, help='Media platform select (xhs|dy)...', default=config.PLATFORM)
    parser.add_argument('--lt', type=str, help='Login type (qrcode | phone | cookie)', default=config.LOGIN_TYPE_COOKIE)

    # init account pool
    account_pool = proxy_account_pool.create_account_pool()

    args = parser.parse_args()
    crawler.init_config(
        command_args=args,
        account_pool=account_pool
    )
    await crawler.start()

    """
    # retry when exception ...
    while True:
        try:
            await crawler.start()
        except Exception as e:
            logging.info(f"crawler start error: {e} ...")
            await crawler.close()
            # If you encounter an exception
            # sleep for a period of time before retrying
            # to avoid frequent requests that may result in the account being blocked.
            await asyncio.sleep(config.RETRY_INTERVAL)
    """


if __name__ == '__main__':
    try:
        asyncio.run(main())
        web.run_app(app,port=8081)
    except KeyboardInterrupt:
        sys.exit()
