# -*- coding: utf-8 -*-
import asyncio
import os
import random
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from model.m_zhihu import ZhihuContent
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import zhihu as zhihu_store
from tools import utils
from var import crawler_type_var, source_keyword_var

from .client import ZhiHuClient
from .exception import DataFetchError
from .help import ZhiHuJsonExtractor
from .login import ZhiHuLogin


class ZhihuCrawler(AbstractCrawler):
    context_page: Page
    zhihu_client: ZhiHuClient
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.index_url = "https://www.zhihu.com"
        # self.user_agent = utils.get_user_agent()
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        self._extractor = ZhiHuJsonExtractor()

    async def start(self) -> None:
        """
        Start the crawler
        Returns:

        """
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # Launch a browser context.
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium,
                None,
                self.user_agent,
                headless=config.HEADLESS
            )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url, wait_until="domcontentloaded")

            # Create a client to interact with the zhihu website.
            self.zhihu_client = await self.create_zhihu_client(httpx_proxy_format)
            if not await self.zhihu_client.pong():
                login_obj = ZhiHuLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # input your phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()
                await self.zhihu_client.update_cookies(browser_context=self.browser_context)

            # 知乎的搜索接口需要打开搜索页面之后cookies才能访问API，单独的首页不行
            utils.logger.info("[ZhihuCrawler.start] Zhihu跳转到搜索页面获取搜索页面的Cookies，改过程需要5秒左右")
            await self.context_page.goto(f"{self.index_url}/search?q=python&search_source=Guess&utm_content=search_hot&type=content")
            await asyncio.sleep(5)
            await self.zhihu_client.update_cookies(browser_context=self.browser_context)

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for notes and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                raise NotImplementedError
            elif config.CRAWLER_TYPE == "creator":
                # Get creator's information and their notes and comments
                raise NotImplementedError
            else:
                pass

            utils.logger.info("[ZhihuCrawler.start] Zhihu Crawler finished ...")

    async def search(self) -> None:
        """Search for notes and retrieve their comment information."""
        utils.logger.info("[ZhihuCrawler.search] Begin search zhihu keywords")
        zhihu_limit_count = 20  # zhihu limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < zhihu_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = zhihu_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[ZhihuCrawler.search] Current search keyword: {keyword}")
            page = 1
            while (page - start_page + 1) * zhihu_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[ZhihuCrawler.search] Skip page {page}")
                    page += 1
                    continue

                try:
                    utils.logger.info(f"[ZhihuCrawler.search] search zhihu keyword: {keyword}, page: {page}")
                    content_list: List[ZhihuContent]  = await self.zhihu_client.get_note_by_keyword(
                        keyword=keyword,
                        page=page,
                    )
                    utils.logger.info(f"[ZhihuCrawler.search] Search contents :{content_list}")
                    if not content_list:
                        utils.logger.info("No more content!")
                        break

                    page += 1
                    for content in content_list:
                        await zhihu_store.update_zhihu_content(content)

                    await self.batch_get_content_comments(content_list)
                except DataFetchError:
                    utils.logger.error("[ZhihuCrawler.search] Search content error")
                    return

    async def batch_get_content_comments(self, content_list: List[ZhihuContent]):
        """
        Batch get content comments
        Args:
            content_list:

        Returns:

        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[ZhihuCrawler.batch_get_content_comments] Crawling comment mode is not enabled")
            return

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for content_item in content_list:
            task = asyncio.create_task(self.get_comments(content_item, semaphore), name=content_item.content_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments(self, content_item: ZhihuContent, semaphore: asyncio.Semaphore):
        """
        Get note comments with keyword filtering and quantity limitation
        Args:
            content_item:
            semaphore:

        Returns:

        """
        async with semaphore:
            utils.logger.info(f"[ZhihuCrawler.get_comments] Begin get note id comments {content_item.content_id}")
            await self.zhihu_client.get_note_all_comments(
                content=content_item,
                crawl_interval=random.random(),
                callback=zhihu_store.batch_update_zhihu_note_comments
            )

    @staticmethod
    def format_proxy_info(ip_proxy_info: IpInfoModel) -> Tuple[Optional[Dict], Optional[Dict]]:
        """format proxy info for playwright and httpx"""
        playwright_proxy = {
            "server": f"{ip_proxy_info.protocol}{ip_proxy_info.ip}:{ip_proxy_info.port}",
            "username": ip_proxy_info.user,
            "password": ip_proxy_info.password,
        }
        httpx_proxy = {
            f"{ip_proxy_info.protocol}": f"http://{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"
        }
        return playwright_proxy, httpx_proxy

    async def create_zhihu_client(self, httpx_proxy: Optional[str]) -> ZhiHuClient:
        """Create zhihu client"""
        utils.logger.info("[ZhihuCrawler.create_zhihu_client] Begin create zhihu API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        zhihu_client_obj = ZhiHuClient(
            proxies=httpx_proxy,
            headers={
                'accept': '*/*',
                'accept-language': 'zh-CN,zh;q=0.9',
                'cookie': cookie_str,
                'priority': 'u=1, i',
                'referer': 'https://www.zhihu.com/search?q=python&time_interval=a_year&type=content',
                'user-agent': self.user_agent,
                'x-api-version': '3.0.91',
                'x-app-za': 'OS=Web',
                'x-requested-with': 'fetch',
                'x-zse-93': '101_3_3.0',
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return zhihu_client_obj

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("[ZhihuCrawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
            # feat issue #14
            # we will save login state to avoid login every time
            user_data_dir = os.path.join(os.getcwd(), "browser_data",
                                         config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context

    async def close(self):
        """Close browser context"""
        await self.browser_context.close()
        utils.logger.info("[ZhihuCrawler.close] Browser context closed ...")
