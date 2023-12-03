# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 18:44
# @Desc    : B站爬虫

import asyncio
import os
import random
import time
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from models import bilibili
from proxy.proxy_account_pool import AccountPool
from tools import utils
from var import comment_tasks_var, crawler_type_var


from .client import BilibiliClient
from .field import OrderType
from .login import BilibiliLogin


class BilibiliCrawler(AbstractCrawler):
    platform: str
    login_type: str
    crawler_type: str
    context_page: Page
    bili_client: BilibiliClient
    account_pool: AccountPool
    browser_context: BrowserContext

    def __init__(self):
        self.index_url = "https://www.bilibili.com"
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
            await self.context_page.goto(self.index_url)

            # Create a client to interact with the xiaohongshu website.
            self.bili_client = await self.create_bilibili_client(httpx_proxy)
            if not await self.bili_client.pong():
                login_obj = BilibiliLogin(
                    login_type=self.login_type,
                    login_phone=account_phone,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()
                await self.bili_client.update_cookies(browser_context=self.browser_context)

            crawler_type_var.set(self.crawler_type)
            if self.crawler_type == "search":
                # Search for video and retrieve their comment information.
                await self.search()
            elif self.crawler_type == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_videos()
            else:
                pass
            utils.logger.info("Bilibili Crawler finished ...")
        pass

    async def search(self):
        """
        search bilibili video with keywords
        :return:
        """
        utils.logger.info("Begin search bilibli keywords")
        bili_limit_count = 20  # bilibili limit page fixed value
        for keyword in config.KEYWORDS.split(","):
            utils.logger.info(f"Current search keyword: {keyword}")
            page = 1
            while page * bili_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                video_id_list: List[str] = []
                videos_res = await self.bili_client.search_video_by_keyword(
                    keyword=keyword,
                    page=page,
                    page_size=bili_limit_count,
                    order=OrderType.DEFAULT,
                )
                video_list: List[Dict] = videos_res.get("result")
                for video_item in video_list:
                    video_id_list.append(video_item.get("id"))
                    await bilibili.update_bilibili_video(video_item)
                page += 1

    async def get_specified_videos(self):
        """
        get specified videos info
        :return:
        """
        pass

    async def create_bilibili_client(self, httpx_proxy: Optional[str]) -> BilibiliClient:
        """Create xhs client"""
        utils.logger.info("Begin create xiaohongshu API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        bilibili_client_obj = BilibiliClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://www.bilibili.com",
                "Referer": "https://www.bilibili.com",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return bilibili_client_obj

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
            # feat issue #14
            # we will save login state to avoid login every time
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
