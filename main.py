import argparse
import asyncio
import sys

import config
from base.base_crawler import AbstractCrawler
from media_platform.xhs import XiaoHongShuCrawler


class CrawlerFactory:
    CRAWLERS = {
        "xhs": XiaoHongShuCrawler
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(platform)
        if not crawler_class:
            raise ValueError("Invalid Media Platform Currently only supported xhs or dy or ks or bili ...")
        return crawler_class()


async def main():
    # define command line params ...
    parser = argparse.ArgumentParser(description='Media crawler program.')
    parser.add_argument('--platform', type=str, help='Media platform select (xhs)',
                        choices=["xhs"], default=config.PLATFORM)
    parser.add_argument('--lt', type=str, help='Login type (qrcode | phone | cookie)',
                        choices=["qrcode", "phone", "cookie"], default=config.LOGIN_TYPE)
    parser.add_argument('--type', type=str, help='crawler type (search | detail | creator)',
                        choices=["search", "detail", "creator"], default=config.CRAWLER_TYPE)
    parser.add_argument('--start', type=int, help='crawler type (number of start page)',
                         default=config.START_PAGE)
    parser.add_argument('--keywords', type=str, help='crawler type (please input keywords)',
                         default=config.KEYWORDS)

    args = parser.parse_args()
    crawler = CrawlerFactory.create_crawler(platform=args.platform)
    crawler.init_config(
        platform=args.platform,
        login_type=args.lt,
        crawler_type=args.type,
        start_page=args.start,
        keyword=args.keywords
    )
    await crawler.start()

if __name__ == '__main__':
    try:
        # asyncio.run(main())
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        sys.exit()
