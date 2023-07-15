import random
import asyncio
import logging
from asyncio import Task
from typing import Optional, List, Dict, Tuple
from argparse import Namespace

from playwright.async_api import Page
from playwright.async_api import BrowserContext
from playwright.async_api import async_playwright

import config
from tools import utils
from .exception import *
from .login import XHSLogin
from .client import XHSClient
from models import xhs as xhs_model
from base.base_crawler import AbstractCrawler
from base.proxy_account_pool import AccountPool


class XiaoHongShuCrawler(AbstractCrawler):

    def __init__(self):
        self.browser_context: Optional[BrowserContext] = None
        self.context_page: Optional[Page] = None
        self.user_agent = utils.get_user_agent()
        self.xhs_client: Optional[XHSClient] = None
        self.index_url = "https://www.xiaohongshu.com"
        self.command_args: Optional[Namespace] = None
        self.account_pool: Optional[AccountPool] = None

    def init_config(self, **kwargs):
        for key in kwargs.keys():
            setattr(self, key, kwargs[key])

    async def start(self):
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

            # Create a client to interact with the xiaohongshu website.
            self.xhs_client = await self.create_xhs_client(httpx_proxy)
            if not await self.xhs_client.ping():
                login_obj = XHSLogin(
                    login_type=self.command_args.lt,
                    login_phone=account_phone,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()
                await self.xhs_client.update_cookies(browser_context=self.browser_context)

            # Search for notes and retrieve their comment information.
            await self.search_posts()

            logging.info("Xhs Crawler finished ...")

    async def search_posts(self):
        """Search for notes and retrieve their comment information."""
        logging.info("Begin search xiaohongshu keywords")
        for keyword in config.KEYWORDS.split(","):
            logging.info(f"Current keyword: {keyword}")
            note_list: List[str] = []
            max_note_len = config.MAX_PAGE_NUM
            page = 1
            while max_note_len > 0:
                posts_res = await self.xhs_client.get_note_by_keyword(
                    keyword=keyword,
                    page=page,
                )
                page += 1
                for post_item in posts_res.get("items"):
                    max_note_len -= 1
                    note_id = post_item.get("id")
                    try:
                        note_detail = await self.xhs_client.get_note_by_id(note_id)
                    except DataFetchError as ex:
                        logging.error(f"Get note detail error: {ex}")
                        continue
                    await xhs_model.update_xhs_note(note_detail)
                    await asyncio.sleep(0.05)
                    note_list.append(note_id)
            logging.info(f"keyword:{keyword}, note_list:{note_list}")
            # await self.batch_get_note_comments(note_list)

    async def batch_get_note_comments(self, note_list: List[str]):
        """Batch get note comments"""
        task_list: List[Task] = []
        for note_id in note_list:
            task = asyncio.create_task(self.get_comments(note_id), name=note_id)
            task_list.append(task)
        await asyncio.wait(task_list)

    async def get_comments(self, note_id: str):
        """Get note comments"""
        logging.info(f"Begin get note id comments {note_id}")
        all_comments = await self.xhs_client.get_note_all_comments(note_id=note_id, crawl_interval=random.random())
        for comment in all_comments:
            await xhs_model.update_xhs_note_comment(note_id=note_id, comment_item=comment)

    def create_proxy_info(self) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        """Create proxy info for playwright and httpx"""
        if not config.ENABLE_IP_PROXY:
            return None, None, None

        # phone: 13012345671  ip_proxy: 111.122.xx.xx1:8888
        phone, ip_proxy = self.account_pool.get_account()
        playwright_proxy = {
            "server": f"{config.IP_PROXY_PROTOCOL}{ip_proxy}",
            "username": config.IP_PROXY_USER,
            "password": config.IP_PROXY_PASSWORD,
        }
        httpx_proxy = f"{config.IP_PROXY_PROTOCOL}{config.IP_PROXY_USER}:{config.IP_PROXY_PASSWORD}@{ip_proxy}"
        return phone, playwright_proxy, httpx_proxy

    async def create_xhs_client(self, httpx_proxy: str) -> XHSClient:
        """Create xhs client"""
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        xhs_client_obj = XHSClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://www.xiaohongshu.com",
                "Referer": "https://www.xiaohongshu.com",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return xhs_client_obj

    async def launch_browser(self, chromium, playwright_proxy, user_agent, headless=True) -> BrowserContext:
        """Launch browser and create browser context"""
        if config.SAVE_LOGIN_STATE:
            # feat issue #14
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=config.USER_DATA_DIR % self.command_args.platform,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context

    async def close(self):
        """Close browser context"""
        await self.browser_context.close()
        logging.info("Browser context closed ...")
