import sys
import asyncio
from typing import Optional, List, Dict

from playwright.async_api import async_playwright
from playwright.async_api import Page
from playwright.async_api import Cookie
from playwright.async_api import BrowserContext

import utils
from .client import DOUYINClient
from base_crawler import Crawler


class DouYinCrawler(Crawler):
    def __init__(self):
        self.keywords: Optional[str] = None
        self.scan_qrcode_time: Optional[int] = None
        self.cookies: Optional[List[Cookie]] = None
        self.browser_context: Optional[BrowserContext] = None
        self.context_page: Optional[Page] = None
        self.proxy: Optional[Dict] = None
        self.user_agent = utils.get_user_agent()
        self.dy_client: Optional[DOUYINClient] = None

    def init_config(self, **kwargs):
        self.keywords = kwargs.get("keywords")
        self.scan_qrcode_time = kwargs.get("scan_qrcode_time")

    async def start(self):
        async with async_playwright() as playwright:
            chromium = playwright.chromium
            browser = await chromium.launch(headless=False)
            self.browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=self.user_agent,
                proxy=self.proxy
            )
            # execute JS to bypass anti automation/crawler detection
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto("https://www.douyin.com")

            # scan qrcode login
            await self.login()
            await self.update_cookies()

            # block main crawler coroutine
            await asyncio.Event().wait()

    async def update_cookies(self):
        self.cookies = await self.browser_context.cookies()

    async def login(self):
        pass

    def search_posts(self):
        pass

    def get_comments(self, item_id: str):
        pass
