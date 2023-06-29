import logging
import asyncio
from asyncio import Task
from argparse import Namespace
from typing import Optional, List, Dict, Tuple

from playwright.async_api import async_playwright
from playwright.async_api import Page
from playwright.async_api import Cookie
from playwright.async_api import BrowserContext

import config
from tools import utils
from .client import DOUYINClient
from .exception import DataFetchError
from .login import DouYinLogin
from base.base_crawler import AbstractCrawler
from base.proxy_account_pool import AccountPool
from models import douyin


class DouYinCrawler(AbstractCrawler):
    def __init__(self):
        self.cookies: Optional[List[Cookie]] = None
        self.browser_context: Optional[BrowserContext] = None
        self.context_page: Optional[Page] = None
        self.proxy: Optional[Dict] = None
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"  # fixed
        self.dy_client: Optional[DOUYINClient] = None
        self.command_args: Optional[Namespace] = None
        self.account_pool: Optional[AccountPool] = None

    def init_config(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def create_proxy_info(self) -> Tuple[str, Dict, str]:
        """Create proxy info for playwright and httpx"""
        # phone: 13012345671
        # ip_proxy: 111.122.xx.xx1:8888
        # 手机号和IP代理都是从账号池中获取的，并且它们是固定绑定的
        phone, ip_proxy = self.account_pool.get_account()
        playwright_proxy = {
            "server": f"{config.IP_PROXY_PROTOCOL}{ip_proxy}",
            "username": config.IP_PROXY_USER,
            "password": config.IP_PROXY_PASSWORD,
        }
        httpx_proxy = f"{config.IP_PROXY_PROTOCOL}{config.IP_PROXY_USER}:{config.IP_PROXY_PASSWORD}@{ip_proxy}"
        return phone, playwright_proxy, httpx_proxy

    async def start(self):
        # phone: 1340xxxx, ip_proxy: 47.xxx.xxx.xxx:8888
        account_phone, ip_proxy = self.account_pool.get_account()

        # 抖音平台如果开启代理登录的话，会被风控，所以这里不开启代理
        playwright_proxy = None
        # playwright_proxy = {
        #    "server": f"{config.ip_proxy_protocol}{ip_proxy}",
        #    "username": config.ip_proxy_user,
        #    "password": config.ip_proxy_password,
        # }

        httpx_proxy = f"{config.IP_PROXY_PROTOCOL}{config.IP_PROXY_USER}:{config.IP_PROXY_PASSWORD}@{ip_proxy}"
        if not config.ENABLE_IP_PROXY:
            playwright_proxy = None
            httpx_proxy = None

        async with async_playwright() as playwright:
            chromium = playwright.chromium
            browser = await chromium.launch(headless=config.HEADLESS, proxy=playwright_proxy)
            self.browser_context = await browser.new_context(
                viewport={"width": 1800, "height": 900},
                user_agent=self.user_agent,
            )
            # execute JS to bypass anti automation/crawler detection
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto("https://www.douyin.com", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # begin login
            login_obj = DouYinLogin(
                login_type=self.command_args.lt,
                login_phone=account_phone,
                browser_context=self.browser_context,
                context_page=self.context_page,
                cookie_str=config.COOKIES
            )
            await login_obj.begin()

            # update cookies
            await self.update_cookies()

            # init request client
            cookie_str, cookie_dict = utils.convert_cookies(self.cookies)
            self.dy_client = DOUYINClient(
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

            # search_posts
            await self.search_posts()

            # block main crawler coroutine
            await asyncio.Event().wait()

    async def update_cookies(self):
        self.cookies = await self.browser_context.cookies()

    async def search_posts(self):
        logging.info("Begin search douyin keywords")
        for keyword in config.KEYWORDS.split(","):
            logging.info(f"Current keyword: {keyword}")
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
