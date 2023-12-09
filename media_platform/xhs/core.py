import asyncio
import os
import random
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from models import xiaohongshu as xhs_model
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from tools import utils
from var import crawler_type_var

from .client import XHSClient
from .exception import DataFetchError
from .login import XHSLogin


class XiaoHongShuCrawler(AbstractCrawler):
    platform: str
    login_type: str
    crawler_type: str
    context_page: Page
    xhs_client: XHSClient
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.index_url = "https://www.xiaohongshu.com"
        self.user_agent = utils.get_user_agent()

    def init_config(self, platform: str, login_type: str, crawler_type: str) -> None:
        self.platform = platform
        self.login_type = login_type
        self.crawler_type = crawler_type

    async def start(self) -> None:
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
            # add a cookie attribute webId to avoid the appearance of a sliding captcha on the webpage
            await self.browser_context.add_cookies([{
                'name': "webId",
                'value': "xxx123",  # any value
                'domain': ".xiaohongshu.com",
                'path': "/"
            }])
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            # Create a client to interact with the xiaohongshu website.
            self.xhs_client = await self.create_xhs_client(httpx_proxy_format)
            if not await self.xhs_client.pong():
                login_obj = XHSLogin(
                    login_type=self.login_type,
                    login_phone="",  # input your phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()
                await self.xhs_client.update_cookies(browser_context=self.browser_context)

            crawler_type_var.set(self.crawler_type)
            if self.crawler_type == "search":
                # Search for notes and retrieve their comment information.
                await self.search()
            elif self.crawler_type == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_notes()
            else:
                pass

            utils.logger.info("Xhs Crawler finished ...")

    async def search(self) -> None:
        """Search for notes and retrieve their comment information."""
        utils.logger.info("Begin search xiaohongshu keywords")
        xhs_limit_count = 20  # xhs limit page fixed value
        for keyword in config.KEYWORDS.split(","):
            utils.logger.info(f"Current search keyword: {keyword}")
            page = 1
            while page * xhs_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                note_id_list: List[str] = []
                notes_res = await self.xhs_client.get_note_by_keyword(
                    keyword=keyword,
                    page=page,
                )
                semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                task_list = [
                    self.get_note_detail(post_item.get("id"), semaphore)
                    for post_item in notes_res.get("items", {})
                    if post_item.get('model_type') not in ('rec_query', 'hot_query')
                ]
                note_details = await asyncio.gather(*task_list)
                for note_detail in note_details:
                    if note_detail is not None:
                        await xhs_model.update_xhs_note(note_detail)
                        note_id_list.append(note_detail.get("note_id"))
                page += 1
                utils.logger.info(f"Note details: {note_details}")
                await self.batch_get_note_comments(note_id_list)

    async def get_specified_notes(self):
        """Get the information and comments of the specified post"""
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_detail(note_id=note_id, semaphore=semaphore) for note_id in config.XHS_SPECIFIED_ID_LIST
        ]
        note_details = await asyncio.gather(*task_list)
        for note_detail in note_details:
            if note_detail is not None:
                await xhs_model.update_xhs_note(note_detail)
        await self.batch_get_note_comments(config.XHS_SPECIFIED_ID_LIST)

    async def get_note_detail(self, note_id: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """Get note detail"""
        async with semaphore:
            try:
                return await self.xhs_client.get_note_by_id(note_id)
            except DataFetchError as ex:
                utils.logger.error(f"Get note detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"have not fund note detail note_id:{note_id}, err: {ex}")
                return None

    async def batch_get_note_comments(self, note_list: List[str]):
        """Batch get note comments"""
        utils.logger.info(f"Begin batch get note comments, note list: {note_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for note_id in note_list:
            task = asyncio.create_task(self.get_comments(note_id, semaphore), name=note_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments(self, note_id: str, semaphore: asyncio.Semaphore):
        """Get note comments"""
        async with semaphore:
            utils.logger.info(f"Begin get note id comments {note_id}")
            all_comments = await self.xhs_client.get_note_all_comments(note_id=note_id, crawl_interval=random.random())
            for comment in all_comments:
                await xhs_model.update_xhs_note_comment(note_id=note_id, comment_item=comment)

    @staticmethod
    def format_proxy_info(ip_proxy_info: IpInfoModel) -> Tuple[Optional[Dict], Optional[Dict]]:
        """format proxy info for playwright and httpx"""
        playwright_proxy = {
            "server": f"{ip_proxy_info.protocol}{ip_proxy_info.ip}:{ip_proxy_info.port}",
            "username": ip_proxy_info.user,
            "password": ip_proxy_info.password,
        }
        httpx_proxy = {
            f"{ip_proxy_info.protocol}{ip_proxy_info.ip}":f"{ip_proxy_info.protocol}{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"
        }
        return playwright_proxy, httpx_proxy

    async def create_xhs_client(self, httpx_proxy: Optional[str]) -> XHSClient:
        """Create xhs client"""
        utils.logger.info("Begin create xiaohongshu API client ...")
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

    async def close(self):
        """Close browser context"""
        await self.browser_context.close()
        utils.logger.info("Browser context closed ...")
