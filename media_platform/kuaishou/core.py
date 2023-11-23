import asyncio
import os
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from base.proxy_account_pool import AccountPool
from tools import utils
from var import crawler_type_var

from .client import KuaishouClient
from .login import KuaishouLogin


class KuaishouCrawler(AbstractCrawler):
    platform: str
    login_type: str
    crawler_type: str
    context_page: Page
    ks_client: KuaishouClient
    account_pool: AccountPool
    browser_context: BrowserContext

    def __init__(self):
        self.index_url = "https://www.kuaishou.com"
        self.user_agent = utils.get_user_agent()

    def init_config(self, platform: str, login_type: str, account_pool: AccountPool, crawler_type: str):
        self.platform = platform
        self.login_type = login_type
        self.account_pool = account_pool
        self.crawler_type = crawler_type

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
            await self.context_page.goto(f"{self.index_url}?isHome=1")

            # Create a client to interact with the kuaishou website.
            self.ks_client = await self.create_ks_client(httpx_proxy)
            if not await self.ks_client.pong():
                login_obj = KuaishouLogin(
                    login_type=self.login_type,
                    login_phone=account_phone,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()
                await self.ks_client.update_cookies(browser_context=self.browser_context)

            crawler_type_var.set(self.crawler_type)
            if self.crawler_type == "search":
                # Search for notes and retrieve their comment information.
                await self.search()
            elif self.crawler_type == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_notes()
            else:
                pass

            utils.logger.info("Kuaishou Crawler finished ...")

    async def search(self):
        await asyncio.Event().wait()


    async def get_specified_notes(self):
        pass

    def create_proxy_info(self) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        """Create proxy info for playwright and httpx"""
        # phone: 13012345671  ip_proxy: 111.122.xx.xx1:8888
        phone, ip_proxy = self.account_pool.get_account()
        if not config.ENABLE_IP_PROXY:
            return phone, None, None
        utils.logger.info("Begin proxy info for playwright and httpx ...")
        playwright_proxy = {
            "server": f"{config.IP_PROXY_PROTOCOL}{ip_proxy}",
            "username": config.IP_PROXY_USER,
            "password": config.IP_PROXY_PASSWORD,
        }
        httpx_proxy = f"{config.IP_PROXY_PROTOCOL}{config.IP_PROXY_USER}:{config.IP_PROXY_PASSWORD}@{ip_proxy}"
        return phone, playwright_proxy, httpx_proxy

    async def create_ks_client(self, httpx_proxy: Optional[str]) -> KuaishouClient:
        """Create xhs client"""
        utils.logger.info("Begin create kuaishou API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        xhs_client_obj = KuaishouClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": self.index_url,
                "Referer": self.index_url,
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return xhs_client_obj

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("Begin create browser context ...")
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
        utils.logger.info("Browser context closed ...")