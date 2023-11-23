import argparse
import asyncio
import sys

import config
import db
from base import proxy_account_pool
from media_platform.douyin import DouYinCrawler
from media_platform.kuaishou import KuaishouCrawler
from media_platform.xhs import XiaoHongShuCrawler


class CrawlerFactory:
    @staticmethod
    def create_crawler(platform: str):
        if platform == "xhs":
            return XiaoHongShuCrawler()
        elif platform == "dy":
            return DouYinCrawler()
        elif platform == "ks":
            return KuaishouCrawler()
        else:
            raise ValueError("Invalid Media Platform Currently only supported xhs or dy ...")


async def main():
    # define command line params ...
    parser = argparse.ArgumentParser(description='Media crawler program.')
    parser.add_argument('--platform', type=str, help='Media platform select (xhs | dy | ks)',
                        choices=["xhs", "dy", "ks"], default=config.PLATFORM)
    parser.add_argument('--lt', type=str, help='Login type (qrcode | phone | cookie)',
                        choices=["qrcode", "phone", "cookie"], default=config.LOGIN_TYPE)
    parser.add_argument('--type', type=str, help='crawler type (search | detail)',
                        choices=["search", "detail"], default=config.CRAWLER_TYPE)

    # init account pool
    account_pool = proxy_account_pool.create_account_pool()

    # init db
    if config.IS_SAVED_DATABASED:
        await db.init_db()

    args = parser.parse_args()
    crawler = CrawlerFactory.create_crawler(platform=args.platform)
    crawler.init_config(
        platform=args.platform,
        login_type=args.lt,
        account_pool=account_pool,
        crawler_type=args.type
    )
    await crawler.start()


if __name__ == '__main__':
    try:
        # asyncio.run(main())
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        sys.exit()
