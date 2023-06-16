import sys
import random
import asyncio
from asyncio import Task
from typing import Optional, List, Dict

import aioredis
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_result
)
from playwright.async_api import Page
from playwright.async_api import Cookie
from playwright.async_api import BrowserContext
from playwright.async_api import async_playwright

import utils
import config
from .client import XHSClient
from base_crawler import Crawler
from models import xhs as xhs_model


class XiaoHongShuCrawler(Crawler):
    def __init__(self):
        self.login_phone = None
        self.login_type = None
        self.keywords = None
        self.cookies: Optional[List[Cookie]] = None
        self.browser_context: Optional[BrowserContext] = None
        self.context_page: Optional[Page] = None
        self.proxy: Optional[Dict] = None
        self.user_agent = utils.get_user_agent()
        self.xhs_client: Optional[XHSClient] = None
        self.index_url = "https://www.xiaohongshu.com"

    def init_config(self, **kwargs):
        self.keywords = kwargs.get("keywords")
        self.login_type = kwargs.get("login_type")
        self.login_phone = kwargs.get("login_phone")

    async def update_cookies(self):
        self.cookies = await self.browser_context.cookies()

    async def start(self):
        async with async_playwright() as playwright:
            # launch browser and create single browser context
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
            await self.context_page.goto(self.index_url)

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
            await self.search_posts()

            # block main crawler coroutine
            await asyncio.Event().wait()

    async def login(self):
        """login xiaohongshu website and keep webdriver login state"""
        # There are two ways to log in:
        # 1. Semi-automatic: Log in by scanning the QR code.
        # 2. Fully automatic: Log in using forwarded text message notifications
        #  which includes mobile phone number and verification code.
        if self.login_type == "qrcode":
            await self.login_by_qrcode()
        elif self.login_type == "phone":
            await self.login_by_mobile()
        else:
            pass

    async def login_by_mobile(self):
        print("Start executing mobile phone number + verification code login on Xiaohongshu. ...")
        login_container_ele = await self.context_page.wait_for_selector("div.login-container")
        # Fill login phone
        input_ele = await login_container_ele.query_selector("label.phone > input")
        await input_ele.fill(self.login_phone)
        await asyncio.sleep(0.5)

        # Click to send verification code and fill it from redis server.
        send_btn_ele = await login_container_ele.query_selector("label.auth-code > span")
        await send_btn_ele.click()
        sms_code_input_ele = await login_container_ele.query_selector("label.auth-code > input")
        submit_btn_ele = await login_container_ele.query_selector("div.input-container > button")
        redis_obj = aioredis.from_url(url=config.redis_db_host, password=config.redis_db_pwd, decode_responses=True)
        max_get_sms_code_time = 60 * 2
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        no_logged_in_session = cookie_dict.get("web_session")
        while max_get_sms_code_time > 0:
            print(f"get sms code from redis remaining time {max_get_sms_code_time}s ...")
            await asyncio.sleep(1)
            sms_code_key = f"xhs_{self.login_phone}"
            sms_code_value = await redis_obj.get(sms_code_key)
            if not sms_code_value:
                max_get_sms_code_time -= 1
                continue

            await sms_code_input_ele.fill(value=sms_code_value)  # Enter SMS verification code.
            await asyncio.sleep(0.5)
            agree_privacy_ele = self.context_page.locator("xpath=//div[@class='agreements']//*[local-name()='svg']")
            await agree_privacy_ele.click()  # Click "Agree" to the privacy policy.
            await asyncio.sleep(0.5)

            await submit_btn_ele.click()  # Click login button
            # todo ... It is necessary to check the correctness of the verification code,
            #  as it is possible that the entered verification code is incorrect.
            break

        login_flag: bool = await self.check_login_state(no_logged_in_session)
        if not login_flag:
            print("login failed please confirm sms code ...")
            sys.exit()

        wait_redirect_seconds = 5
        print(f"Login successful then wait for {wait_redirect_seconds} seconds redirect ...")
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_qrcode(self):
        """login xiaohongshu website and keep webdriver login state"""
        print("Start scanning QR code to log in to Xiaohongshu. ...")

        # find login qrcode
        base64_qrcode_img = await utils.find_login_qrcode(
            self.context_page,
            selector="div.login-container > div.left > div.qrcode > img"
        )
        if not base64_qrcode_img:
            # todo ...if this website does not automatically popup login dialog box, we will manual click login button
            print("login failed , have not found qrcode please check ....")
            sys.exit()

        # get not logged session
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        no_logged_in_session = cookie_dict.get("web_session")

        # show login qrcode
        utils.show_qrcode(base64_qrcode_img)
        print(f"waiting for scan code login, remaining time is 20s")
        login_flag: bool = await self.check_login_state(no_logged_in_session)
        if not login_flag:
            print("login failed please confirm ...")
            sys.exit()

        wait_redirect_seconds = 5
        print(f"Login successful then wait for {wait_redirect_seconds} seconds redirect ...")
        await asyncio.sleep(wait_redirect_seconds)

    @retry(stop=stop_after_attempt(30), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self, no_logged_in_session: str) -> bool:
        """Check if the current login status is successful and return True otherwise return False"""
        # If login is unsuccessful, a retry exception will be thrown.
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        current_web_session = cookie_dict.get("web_session")
        if current_web_session != no_logged_in_session:
            return True
        return False

    async def search_posts(self):
        print("Begin search xiaohongshu keywords")
        # It is possible to modify the source code to allow for the passing of a batch of keywords.
        for keyword in [self.keywords]:
            note_list: List[str] = []
            max_note_len = 10
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
                    note_detail = await self.xhs_client.get_note_by_id(note_id)
                    await xhs_model.update_xhs_note(note_detail)
                    await asyncio.sleep(0.05)
                    note_list.append(note_id)
            print(f"keyword:{keyword}, note_list:{note_list}")
            await self.batch_get_note_comments(note_list)

    async def batch_get_note_comments(self, note_list: List[str]):
        task_list: List[Task] = []
        for note_id in note_list:
            task = asyncio.create_task(self.get_comments(note_id), name=note_id)
            task_list.append(task)
        await asyncio.wait(task_list)

    async def get_comments(self, note_id: str):
        print("Begin get note id comments ", note_id)
        all_comments = await self.xhs_client.get_note_all_comments(note_id=note_id, crawl_interval=random.random())
        for comment in all_comments:
            await xhs_model.update_xhs_note_comment(note_id=note_id, comment_item=comment)
