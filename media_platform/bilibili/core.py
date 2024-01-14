# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 18:44
# @Desc    : B站爬虫

import asyncio
import os
import random
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import bilibili as bilibili_store
from tools import utils
from var import crawler_type_var

from .client import BilibiliClient
from .exception import DataFetchError
from .field import SearchOrderType
from .login import BilibiliLogin


class BilibiliCrawler(AbstractCrawler):
    platform: str
    login_type: str
    crawler_type: str
    context_page: Page
    bili_client: BilibiliClient
    browser_context: BrowserContext

    def __init__(self):
        self.index_url = "https://www.bilibili.com"
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
            self.bili_client = await self.create_bilibili_client(httpx_proxy_format)
            if not await self.bili_client.pong():
                login_obj = BilibiliLogin(
                    login_type=self.login_type,
                    login_phone="",  # your phone number
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
            utils.logger.info("[BilibiliCrawler.start] Bilibili Crawler finished ...")

    async def search(self):
        """
        search bilibili video with keywords
        :return:
        """
        utils.logger.info("[BilibiliCrawler.search] Begin search bilibli keywords")
        bili_limit_count = 20  # bilibili limit page fixed value
        for keyword in config.KEYWORDS.split(","):
            utils.logger.info(f"[BilibiliCrawler.search] Current search keyword: {keyword}")
            page = 1
            while page * bili_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                video_id_list: List[str] = []
                videos_res = await self.bili_client.search_video_by_keyword(
                    keyword=keyword,
                    page=page,
                    page_size=bili_limit_count,
                    order=SearchOrderType.DEFAULT,
                )
                video_list: List[Dict] = videos_res.get("result")

                semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                task_list = [
                    self.get_video_info_task(aid=video_item.get("aid"), bvid="", semaphore=semaphore)
                    for video_item in video_list
                ]
                video_items = await asyncio.gather(*task_list)
                for video_item in video_items:
                    if video_item:
                        video_id_list.append(video_item.get("View").get("aid"))
                        await bilibili_store.update_bilibili_video(video_item)

                page += 1
                await self.batch_get_video_comments(video_id_list)

    async def batch_get_video_comments(self, video_id_list: List[str]):
        """
        batch get video comments
        :param video_id_list:
        :return:
        """
        utils.logger.info(f"[BilibiliCrawler.batch_get_video_comments] video ids:{video_id_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for video_id in video_id_list:
            task = asyncio.create_task(self.get_comments(video_id, semaphore), name=video_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments(self, video_id: str, semaphore: asyncio.Semaphore):
        """
        get comment for video id
        :param video_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                utils.logger.info(f"[BilibiliCrawler.get_comments] begin get video_id: {video_id} comments ...")
                await self.bili_client.get_video_all_comments(
                    video_id=video_id,
                    crawl_interval=random.random(),
                    callback=bilibili_store.batch_update_bilibili_video_comments
                )

            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_comments] get video_id: {video_id} comment error: {ex}")
            except Exception as e:
                utils.logger.error(f"[BilibiliCrawler.get_comments] may be been blocked, err:{e}")

    async def get_specified_videos(self):
        """
        get specified videos info
        :return:
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_video_info_task(aid=0, bvid=video_id, semaphore=semaphore) for video_id in
            config.BILI_SPECIFIED_ID_LIST
        ]
        video_details = await asyncio.gather(*task_list)
        video_aids_list = []
        for video_detail in video_details:
            if video_detail is not None:
                video_item_view: Dict = video_detail.get("View")
                video_aid: str = video_item_view.get("aid")
                if video_aid:
                    video_aids_list.append(video_aid)
                await bilibili_store.update_bilibili_video(video_detail)
        await self.batch_get_video_comments(video_aids_list)

    async def get_video_info_task(self, aid: int, bvid: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """
        Get video detail task
        :param aid:
        :param bvid:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                result = await self.bili_client.get_video_info(aid=aid, bvid=bvid)
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_video_info_task] Get video detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_video_info_task] have not fund note detail video_id:{bvid}, err: {ex}")
                return None

    async def create_bilibili_client(self, httpx_proxy: Optional[str]) -> BilibiliClient:
        """Create xhs client"""
        utils.logger.info("[BilibiliCrawler.create_bilibili_client] Begin create bilibili API client ...")
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

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("[BilibiliCrawler.launch_browser] Begin create browser context ...")
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
