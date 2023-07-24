import os
import asyncio
from asyncio import Task
from argparse import Namespace
from typing import Optional, List, Dict, Tuple

from playwright.async_api import async_playwright
from playwright.async_api import BrowserType
from playwright.async_api import BrowserContext
from playwright.async_api import Page

import config
from tools import utils
from .client import DOUYINClient
from .exception import DataFetchError
from .login import DouYinLogin
from base.base_crawler import AbstractCrawler
from base.proxy_account_pool import AccountPool
from models import douyin


class DouYinCrawler(AbstractCrawler):
    dy_client: DOUYINClient

    def __init__(self) -> None:
        self.browser_context: Optional[BrowserContext] = None  # type: ignore
        self.context_page: Optional[Page] = None  # type: ignore
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"  # fixed
        self.index_url = "https://www.douyin.com"
        self.command_args: Optional[Namespace] = None  # type: ignore
        self.account_pool: Optional[AccountPool] = None  # type: ignore

    def init_config(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

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
                    login_type=self.command_args.lt,  # type: ignore
                    login_phone=account_phone,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()
                await self.dy_client.update_cookies(browser_context=self.browser_context)

            # search_posts
            await self.search_posts()

            utils.logger.info("Douyin Crawler finished ...")

    async def search_posts(self) -> None:
        utils.logger.info("Begin search douyin keywords")
        for keyword in config.KEYWORDS.split(","):
            utils.logger.info(f"Current keyword: {keyword}")
            aweme_list: List[str] = []
            max_note_len = config.MAX_PAGE_NUM
            page = 0
            while max_note_len > 0:
                try:
                    posts_res = await self.dy_client.search_info_by_keyword(keyword=keyword, offset=page * 10)
                except DataFetchError:
                    utils.logger.error(f"search douyin keyword: {keyword} failed")
                    break
                page += 1
                max_note_len -= 10
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

    async def batch_get_note_comments(self, aweme_list: List[str]):
        task_list: List[Task] = []
        _semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        for aweme_id in aweme_list:
            task = asyncio.create_task(self.get_comments(aweme_id, _semaphore), name=aweme_id)
            task_list.append(task)
        await asyncio.wait(task_list)

    async def get_comments(self, aweme_id: str, semaphore: "asyncio.Semaphore"):
        async with semaphore:
            try:
                await self.dy_client.get_aweme_all_comments(
                    aweme_id=aweme_id,
                    callback=douyin.batch_update_dy_aweme_comments
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
                                         config.USER_DATA_DIR % self.command_args.platform)  # type: ignore
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

    async def close(self):
        """Close browser context"""
        await self.browser_context.close()
        utils.logger.info("Browser context closed ...")
