import argparse
import asyncio
import sys

import config
import db
from base.base_crawler import AbstractCrawler
from media_platform.bilibili import BilibiliCrawler
from media_platform.douyin import DouYinCrawler
from media_platform.kuaishou import KuaishouCrawler
from media_platform.weibo import WeiboCrawler
from media_platform.xhs import XiaoHongShuCrawler


class CrawlerFactory:
    CRAWLERS = {
        "xhs": XiaoHongShuCrawler,
        "dy": DouYinCrawler,
        "ks": KuaishouCrawler,
        "bili": BilibiliCrawler,
        "wb": WeiboCrawler
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(platform)
        if not crawler_class:
            raise ValueError("Invalid Media Platform Currently only supported xhs or dy or ks or bili ...")
        return crawler_class()


async def craw(platform, login_type, crawler_type):
    """爬虫入口

    Args:
        platform (str): 将要爬取的平台
        login_type (str): 登录方式
        crawler_type (str): 爬虫模式
        
    可选的平台：`xhs`, `dy`, `ks`, `bili`, `wb`
    
    可选的登录方式：`qrcode`, `phone`, `cookie`
    
    可选的爬虫模式：`search`, `detail`, `creator`
    """

    # init db
    if config.SAVE_DATA_OPTION == "db":
        await db.init_db()
    
    crawler = CrawlerFactory.create_crawler(platform=platform)
    crawler.init_config(
        platform=platform,
        login_type=login_type,
        crawler_type=crawler_type
    )
    await crawler.start()
    
    if config.SAVE_DATA_OPTION == "db":
        await db.close()


if __name__ == '__main__':
    # define command line params ...
    parser = argparse.ArgumentParser(description='Media crawler program.')
    parser.add_argument('--platform', type=str, help='Media platform select (xhs | dy | ks | bili | wb)',
                        choices=["xhs", "dy", "ks", "bili", "wb"], default=config.PLATFORM)
    parser.add_argument('--lt', type=str, help='Login type (qrcode | phone | cookie)',
                        choices=["qrcode", "phone", "cookie"], default=config.LOGIN_TYPE)
    parser.add_argument('--type', type=str, help='crawler type (search | detail | creator)',
                        choices=["search", "detail", "creator"], default=config.CRAWLER_TYPE)
    args = parser.parse_args()
    
    try:
        # asyncio.run(main())
        asyncio.get_event_loop().run_until_complete(craw(platform=args.platform, login_type=args.lt, crawler_type=args.type))
    except KeyboardInterrupt:
        sys.exit()
