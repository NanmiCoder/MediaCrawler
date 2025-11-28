# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/main.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


import asyncio
import sys
import signal
from typing import Optional

import cmd_arg
import config
from database import db
from base.base_crawler import AbstractCrawler
from media_platform.bilibili import BilibiliCrawler
from media_platform.douyin import DouYinCrawler
from media_platform.kuaishou import KuaishouCrawler
from media_platform.tieba import TieBaCrawler
from media_platform.weibo import WeiboCrawler
from media_platform.xhs import XiaoHongShuCrawler
from media_platform.zhihu import ZhihuCrawler
from tools.async_file_writer import AsyncFileWriter
from var import crawler_type_var


class CrawlerFactory:
    CRAWLERS = {
        "xhs": XiaoHongShuCrawler,
        "dy": DouYinCrawler,
        "ks": KuaishouCrawler,
        "bili": BilibiliCrawler,
        "wb": WeiboCrawler,
        "tieba": TieBaCrawler,
        "zhihu": ZhihuCrawler,
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(platform)
        if not crawler_class:
            raise ValueError(
                "Invalid Media Platform Currently only supported xhs or dy or ks or bili ..."
            )
        return crawler_class()


crawler: Optional[AbstractCrawler] = None


# persist-1<persist1@126.com>
# 原因：增加 --init_db 功能，用于数据库初始化。
# 副作用：无
# 回滚策略：还原此文件。
async def main():
    # Init crawler
    global crawler

    # parse cmd
    args = await cmd_arg.parse_cmd()

    # init db
    if args.init_db:
        await db.init_db(args.init_db)
        print(f"Database {args.init_db} initialized successfully.")
        return  # Exit the main function cleanly



    crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
    await crawler.start()

    # Flush Excel data if using Excel export
    if config.SAVE_DATA_OPTION == "excel":
        try:
            from store.excel_store_base import ExcelStoreBase
            ExcelStoreBase.flush_all()
            print("[Main] Excel files saved successfully")
        except Exception as e:
            print(f"[Main] Error flushing Excel data: {e}")

    # Generate wordcloud after crawling is complete
    # Only for JSON save mode
    if config.SAVE_DATA_OPTION == "json" and config.ENABLE_GET_WORDCLOUD:
        try:
            file_writer = AsyncFileWriter(
                platform=config.PLATFORM,
                crawler_type=crawler_type_var.get()
            )
            await file_writer.generate_wordcloud_from_comments()
        except Exception as e:
            print(f"Error generating wordcloud: {e}")


async def async_cleanup():
    """异步清理函数，用于处理CDP浏览器等异步资源"""
    global crawler
    if crawler:
        # 检查并清理CDP浏览器
        if hasattr(crawler, 'cdp_manager') and crawler.cdp_manager:
            try:
                await crawler.cdp_manager.cleanup(force=True)  # 强制清理浏览器进程
            except Exception as e:
                # 只在非预期错误时打印
                error_msg = str(e).lower()
                if "closed" not in error_msg and "disconnected" not in error_msg:
                    print(f"[Main] 清理CDP浏览器时出错: {e}")

        # 检查并清理标准浏览器上下文（仅在非CDP模式下）
        elif hasattr(crawler, 'browser_context') and crawler.browser_context:
            try:
                # 检查上下文是否仍然打开
                if hasattr(crawler.browser_context, 'pages'):
                    await crawler.browser_context.close()
            except Exception as e:
                # 只在非预期错误时打印
                error_msg = str(e).lower()
                if "closed" not in error_msg and "disconnected" not in error_msg:
                    print(f"[Main] 关闭浏览器上下文时出错: {e}")

    # 关闭数据库连接
    if config.SAVE_DATA_OPTION in ["db", "sqlite"]:
        await db.close()

def cleanup():
    """同步清理函数"""
    try:
        # 创建新的事件循环来执行异步清理
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_cleanup())
        loop.close()
    except Exception as e:
        print(f"[Main] 清理时出错: {e}")


def signal_handler(signum, _frame):
    """信号处理器，处理Ctrl+C等中断信号"""
    print(f"\n[Main] 收到中断信号 {signum}，正在清理资源...")
    cleanup()
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号

    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        print("\n[Main] 收到键盘中断，正在清理资源...")
    finally:
        cleanup()
