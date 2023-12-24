# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/23 15:41
# @Desc    : 微博爬虫主流程代码


import asyncio
import os
import random
import time
from asyncio import Task
from typing import Dict, List, Optional, Tuple, Union

from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from models import weibo
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from tools import utils
from var import comment_tasks_var, crawler_type_var

from .client import WeiboClient
from .exception import DataFetchError
from .login import WeiboLogin
from .field import SearchType
from .help import filter_search_result_card


class WeiboCrawler(AbstractCrawler):
    platform: str
    login_type: str
    crawler_type: str
    context_page: Page
    wb_client: WeiboClient
    browser_context: BrowserContext

    def __init__(self):
        self.index_url = "https://m.weibo.cn"
        self.user_agent = utils.get_user_agent()

    def init_config(self, platform: str, login_type: str, crawler_type: str):
        self.platform = platform
        self.login_type = login_type
        self.crawler_type = crawler_type

    async def start(self):
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
            await self.context_page.goto(self.index_url)

            # Create a client to interact with the xiaohongshu website.
            self.wb_client = await self.create_weibo_client(httpx_proxy_format)
            if not await self.wb_client.pong():
                login_obj = WeiboLogin(
                    login_type=self.login_type,
                    login_phone="",  # your phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()
                await self.wb_client.update_cookies(browser_context=self.browser_context)

            crawler_type_var.set(self.crawler_type)
            if self.crawler_type == "search":
                # Search for video and retrieve their comment information.
                await self.search()
            elif self.crawler_type == "detail":
                # Get the information and comments of the specified post
                pass
            else:
                pass
            utils.logger.info("[WeiboCrawler.start] Bilibili Crawler finished ...")

    async def search(self):
        """
        search weibo note with keywords
        :return:
        """
        utils.logger.info("[WeiboCrawler.search] Begin search weibo keywords")
        weibo_limit_count = 10
        for keyword in config.KEYWORDS.split(","):
            utils.logger.info(f"[WeiboCrawler.search] Current search keyword: {keyword}")
            page = 1
            while page * weibo_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                search_res = await self.wb_client.get_note_by_keyword(
                    keyword=keyword,
                    page=page,
                    search_type=SearchType.DEFAULT
                )
                note_id_list: List[str] = []
                note_list = filter_search_result_card(search_res.get("cards"))
                for note_item in note_list:
                    if note_item :
                        mblog: Dict = note_item.get("mblog")
                        note_id_list.append(mblog.get("id"))
                        await weibo.update_weibo_note(note_item)

                page += 1

    async def create_weibo_client(self, httpx_proxy: Optional[str]) -> WeiboClient:
        """Create xhs client"""
        utils.logger.info("[WeiboCrawler.create_weibo_client] Begin create weibo API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        weibo_client_obj = WeiboClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://m.weibo.cn",
                "Referer": "https://m.weibo.cn",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return weibo_client_obj

    @staticmethod
    def format_proxy_info(ip_proxy_info: IpInfoModel) -> Tuple[Optional[Dict], Optional[Dict]]:
        """format proxy info for playwright and httpx"""
        playwright_proxy = {
            "server": f"{ip_proxy_info.protocol}{ip_proxy_info.ip}:{ip_proxy_info.port}",
            "username": ip_proxy_info.user,
            "password": ip_proxy_info.password,
        }
        httpx_proxy = {
            f"{ip_proxy_info.protocol}{ip_proxy_info.ip}": f"{ip_proxy_info.protocol}{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"
        }
        return playwright_proxy, httpx_proxy

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("[WeiboCrawler.launch_browser] Begin create browser context ...")
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
