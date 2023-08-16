import asyncio
import os
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from base.proxy_account_pool import AccountPool
from models import douyin
from tools import utils
from var import request_keyword_var

from .client import DOUYINClient
from .exception import DataFetchError
from .login import DouYinLogin


class DouYinCrawler(AbstractCrawler):
    platform: str
    login_type: str
    context_page: Page
    dy_client: DOUYINClient
    account_pool: AccountPool
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"  # fixed
        self.index_url = "https://www.douyin.com"

    def init_config(self, platform: str, login_type: str, account_pool: AccountPool) -> None:
        self.platform = platform
        self.login_type = login_type
        self.account_pool = account_pool

    async def start(self) -> None:
        account_phone, playwright_proxy, httpx_proxy = self.create_proxy_info()
        async with async_playwright() as playwright:
            # Launch a browser context.
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium,
                playwright_proxy,
                self.user_agent,
                headless=config.HEADLESS
            )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            self.dy_client = await self.create_douyin_client(httpx_proxy)
            if not await self.dy_client.ping(browser_context=self.browser_context):
                login_obj = DouYinLogin(
                    login_type=self.login_type,
                    login_phone=account_phone,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()
                await self.dy_client.update_cookies(browser_context=self.browser_context)

            # search_posts
            await self.search()

            utils.logger.info("Douyin Crawler finished ...")

    async def search(self) -> None:
        utils.logger.info("Begin search douyin keywords")
        for keyword in config.KEYWORDS.split(","):
            request_keyword_var.set(keyword)
            utils.logger.info(f"Current keyword: {keyword}")
            aweme_list: List[str] = []
            dy_limit_count = 10  # douyin fixed limit page 10
            page = 0
            while (page + 1) * dy_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                try:
                    posts_res = await self.dy_client.search_info_by_keyword(keyword=keyword,
                                                                            offset=page * dy_limit_count)
                except DataFetchError:
                    utils.logger.error(f"search douyin keyword: {keyword} failed")
                    break
                page += 1
                for post_item in posts_res.get("data"):
                    try:
                        aweme_info: Dict = post_item.get("aweme_info") or \
                                           post_item.get("aweme_mix_info", {}).get("mix_items")[0]
                    except TypeError:
                        continue
                    aweme_list.append(aweme_info.get("aweme_id", ""))
                    await douyin.update_douyin_aweme(aweme_item=aweme_info)
            utils.logger.info(f"keyword:{keyword}, aweme_list:{aweme_list}")
            await self.batch_get_note_comments(aweme_list)

    async def batch_get_note_comments(self, aweme_list: List[str]) -> None:
        task_list: List[Task] = []
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        for aweme_id in aweme_list:
            task = asyncio.create_task(self.get_comments(aweme_id, semaphore), name=aweme_id)
            task_list.append(task)
        await asyncio.wait(task_list)

    async def get_comments(self, aweme_id: str, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            try:
                await self.dy_client.get_aweme_all_comments(
                    aweme_id=aweme_id,
                    callback=douyin.batch_update_dy_aweme_comments,
                )
                utils.logger.info(f"aweme_id: {aweme_id} comments have all been obtained completed ...")
            except DataFetchError as e:
                utils.logger.error(f"aweme_id: {aweme_id} get comments failed, error: {e}")

    def create_proxy_info(self) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        """Create proxy info for playwright and httpx"""
        if not config.ENABLE_IP_PROXY:
            return None, None, None

        # phone: 13012345671  ip_proxy: 111.122.xx.xx1:8888
        phone, ip_proxy = self.account_pool.get_account()  # type: ignore
        playwright_proxy = {
            "server": f"{config.IP_PROXY_PROTOCOL}{ip_proxy}",
            "username": config.IP_PROXY_USER,
            "password": config.IP_PROXY_PASSWORD,
        }
        httpx_proxy = f"{config.IP_PROXY_PROTOCOL}{config.IP_PROXY_USER}:{config.IP_PROXY_PASSWORD}@{ip_proxy}"
        return phone, playwright_proxy, httpx_proxy

    async def create_douyin_client(self, httpx_proxy: Optional[str]) -> DOUYINClient:
        """Create douyin client"""
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())  # type: ignore
        douyin_client = DOUYINClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Host": "www.douyin.com",
                "Origin": "https://www.douyin.com/",
                "Referer": "https://www.douyin.com/",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return douyin_client

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data",
                                         config.USER_DATA_DIR % self.platform)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )  # type: ignore
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context

    async def close(self) -> None:
        """Close browser context"""
        await self.browser_context.close()
        utils.logger.info("Browser context closed ...")
