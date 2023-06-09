import sys
import asyncio
from typing import Optional, List, Dict

from playwright.async_api import Page
from playwright.async_api import Cookie
from playwright.async_api import BrowserContext
from playwright.async_api import async_playwright

import utils
from .client import XHSClient
from base_crawler import Crawler


class XiaoHongShuCrawler(Crawler):
    def __init__(self):
        self.keywords = None
        self.scan_qrcode_time = None
        self.cookies: Optional[List[Cookie]] = None
        self.browser_context: Optional[BrowserContext] = None
        self.context_page: Optional[Page] = None
        self.proxy: Optional[Dict] = None
        self.user_agent = utils.get_user_agent()
        self.xhs_client: Optional[XHSClient] = None
        self.login_url = "https://www.xiaohongshu.com"
        self.scan_qrcode_time = 20  # second

    def init_config(self, **kwargs):
        self.keywords = kwargs.get("keywords")

    async def update_cookies(self):
        self.cookies = await self.browser_context.cookies()

    async def start(self):
        async with async_playwright() as playwright:
            # launch browser and create single browser context
            chromium = playwright.chromium
            browser = await chromium.launch(headless=True)
            self.browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=self.user_agent,
                proxy=self.proxy
            )

            # execute JS to bypass anti automation/crawler detection
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.login_url)

            # scan qrcode login
            await self.login()
            await self.update_cookies()

            # init request client
            cookie_str, cookie_dict = utils.convert_cookies(self.cookies)
            self.xhs_client = XHSClient(
                proxies=self.proxy,
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

            # Search for notes and retrieve their comment information.
            note_res = await self.search_posts()
            for post_item in note_res.get("items"):
                note_id = post_item.get("id")
                await self.get_comments(note_id=note_id)
                await asyncio.sleep(1)

            # block main crawler coroutine
            await asyncio.Event().wait()

    async def login(self):
        """login xiaohongshu website and keep webdriver login state"""
        print("Begin login xiaohongshu ...")

        # find login qrcode
        base64_qrcode_img = await utils.find_login_qrcode(
            self.context_page,
            selector="div.login-container > div.left > div.qrcode > img"
        )
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        no_logged_in_session = cookie_dict.get("web_session")
        if not base64_qrcode_img:

            if await self.check_login_state(no_logged_in_session):
                return
            # todo ...if this website does not automatically popup login dialog box, we will manual click login button
            print("login failed , have not found qrcode please check ....")
            sys.exit()

        # show login qrcode
        utils.show_qrcode(base64_qrcode_img)

        while self.scan_qrcode_time > 0:
            await asyncio.sleep(1)
            self.scan_qrcode_time -= 1
            print(f"waiting for scan code login, remaining time is {self.scan_qrcode_time} seconds")
            # get login state from browser
            if await self.check_login_state(no_logged_in_session):
                # If the QR code login is successful, you need to wait for a moment.
                # Because there will be a second redirection after successful login
                # executing JS during this period may be performed in a Page that has already been destroyed.
                wait_for_seconds = 5
                print(f"Login successful then wait for {wait_for_seconds} seconds redirect ...")
                while wait_for_seconds > 0:
                    await asyncio.sleep(1)
                    print(f"remaining wait {wait_for_seconds} seconds ...")
                    wait_for_seconds -= 1
                break
        else:
            sys.exit()

    async def check_login_state(self, no_logged_in_session: str) -> bool:
        """Check if the current login status is successful and return True otherwise return False"""
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        current_web_session = cookie_dict.get("web_session")
        if current_web_session != no_logged_in_session:
            return True
        return False

    async def search_posts(self):
        # This function only retrieves the first 10 note
        # And you can continue to make requests to obtain more by checking the boolean status of "has_more".
        print("Begin search xiaohongshu keywords: ", self.keywords)
        posts_res = await self.xhs_client.get_note_by_keyword(keyword=self.keywords)
        for post_item in posts_res.get("items"):
            note_id = post_item.get("id")
            title = post_item.get("note_card", {}).get("display_title")
            print(f"Note ID:{note_id}; Title:{title}")
            # todo record note or save to db or csv
        return posts_res

    async def get_comments(self, note_id: str):
        # This function only retrieves the first 10 comments
        # And you can continue to make requests to obtain more by checking the boolean status of "has_more".
        print("Begin get note id comments ", note_id)
        res = await self.xhs_client.get_note_comments(note_id=note_id)
        # res = await self.xhs_client.get_note_all_comments(note_id=note_id)
        for comment in res.get("comments"):
            nick_name = comment.get("user_info").get("nickname")
            comment_content = comment.get("content")
            print(f"Nickname：{nick_name}; Comment content：{comment_content}")
            # todo save to db or csv
        return res
