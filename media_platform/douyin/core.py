import logging
import asyncio
from asyncio import Task
from typing import Optional, List, Dict

from playwright.async_api import async_playwright
from playwright.async_api import Page
from playwright.async_api import Cookie
from playwright.async_api import BrowserContext

import utils
from .client import DOUYINClient
from .exception import DataFetchError
from base_crawler import Crawler
from models import douyin


class DouYinCrawler(Crawler):
    def __init__(self):
        self.keywords: Optional[str] = None
        self.cookies: Optional[List[Cookie]] = None
        self.browser_context: Optional[BrowserContext] = None
        self.context_page: Optional[Page] = None
        self.proxy: Optional[Dict] = None
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"  # fixed
        self.dy_client: Optional[DOUYINClient] = None

    def init_config(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def start(self):
        async with async_playwright() as playwright:
            chromium = playwright.chromium
            browser = await chromium.launch(headless=True)
            self.browser_context = await browser.new_context(
                viewport={"width": 1800, "height": 900},
                user_agent=self.user_agent,
                proxy=self.proxy
            )
            # execute JS to bypass anti automation/crawler detection
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto("https://www.douyin.com", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # scan qrcode login
            # await self.login()
            await self.update_cookies()

            # init request client
            cookie_str, cookie_dict = utils.convert_cookies(self.cookies)
            self.dy_client = DOUYINClient(
                proxies=self.proxy,
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

            # search_posts
            await self.search_posts()

            # block main crawler coroutine
            await asyncio.Event().wait()

    async def update_cookies(self):
        self.cookies = await self.browser_context.cookies()

    async def login(self):
        """login douyin website and keep webdriver login state"""
        print("Begin login douyin ...")
        # todo ...

    async def check_login_state(self) -> bool:
        """Check if the current login status is successful and return True otherwise return False"""
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        if cookie_dict.get("LOGIN_STATUS") == "1":
            return True
        return False

    async def search_posts(self):
        # It is possible to modify the source code to allow for the passing of a batch of keywords.
        for keyword in [self.keywords]:
            print("Begin search douyin keywords: ", keyword)
            aweme_list: List[str] = []
            max_note_len = 20
            page = 0
            while max_note_len > 0:
                try:
                    posts_res = await self.dy_client.search_info_by_keyword(keyword=keyword, offset=page * 10)
                except DataFetchError:
                    logging.error(f"search douyin keyword: {keyword} failed")
                    break
                page += 1
                max_note_len -= 10
                for post_item in posts_res.get("data"):
                    try:
                        aweme_info: Dict = post_item.get("aweme_info") or \
                                           post_item.get("aweme_mix_info", {}).get("mix_items")[0]
                    except TypeError:
                        continue
                    aweme_list.append(aweme_info.get("aweme_id"))
                    await douyin.update_douyin_aweme(aweme_item=aweme_info)
            print(f"keyword:{keyword}, aweme_list:{aweme_list}")
            await self.batch_get_note_comments(aweme_list)

    async def batch_get_note_comments(self, aweme_list: List[str]):
        task_list: List[Task] = []
        for aweme_id in aweme_list:
            task = asyncio.create_task(self.get_comments(aweme_id), name=aweme_id)
            task_list.append(task)
        await asyncio.wait(task_list)

    async def get_comments(self, aweme_id: str):
        try:
            await self.dy_client.get_aweme_all_comments(
                aweme_id=aweme_id,
                callback=douyin.batch_update_dy_aweme_comments
            )
            print(f"aweme_id: {aweme_id} comments have all been obtained completed ...")
        except DataFetchError as e:
            logging.error(f"aweme_id: {aweme_id} get comments failed, error: {e}")
