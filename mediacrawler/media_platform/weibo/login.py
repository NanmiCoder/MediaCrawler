# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/23 15:42
# @Desc    : 微博登录实现

import asyncio
import functools
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import (RetryError, retry, retry_if_result, stop_after_attempt,
                      wait_fixed)

from base.base_crawler import AbstractLogin
from tools import utils


class WeiboLogin(AbstractLogin):
    def __init__(self,
                 login_type: str,
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",
                 cookie_str: str = ""
                 ):
        self.login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

    async def begin(self):
        """Start login weibo"""
        utils.logger.info("[WeiboLogin.begin] Begin login weibo ...")
        if self.login_type == "qrcode":
            await self.login_by_qrcode()
        elif self.login_type == "phone":
            await self.login_by_mobile()
        elif self.login_type == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError(
                "[WeiboLogin.begin] Invalid Login Type Currently only supported qrcode or phone or cookie ...")


    @retry(stop=stop_after_attempt(20), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self, no_logged_in_session: str) -> bool:
        """
            Check if the current login status is successful and return True otherwise return False
            retry decorator will retry 20 times if the return value is False, and the retry interval is 1 second
            if max retry times reached, raise RetryError
        """
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        current_web_session = cookie_dict.get("WBPSESS")
        if current_web_session != no_logged_in_session:
            return True
        return False

    async def popup_login_dialog(self):
        """If the login dialog box does not pop up automatically, we will manually click the login button"""
        dialog_selector = "xpath=//div[@class='woo-modal-main']"
        try:
            # check dialog box is auto popup and wait for 4 seconds
            await self.context_page.wait_for_selector(dialog_selector, timeout=1000 * 4)
        except Exception as e:
            utils.logger.error(
                f"[WeiboLogin.popup_login_dialog] login dialog box does not pop up automatically, error: {e}")
            utils.logger.info(
                "[WeiboLogin.popup_login_dialog] login dialog box does not pop up automatically, we will manually click the login button")

            # 向下滚动1000像素
            await self.context_page.mouse.wheel(0,500)
            await asyncio.sleep(0.5)

            try:
                # click login button
                login_button_ele = self.context_page.locator(
                    "xpath=//a[text()='登录']",
                )
                await login_button_ele.click()
                await asyncio.sleep(0.5)
            except Exception as e:
                utils.logger.info(f"[WeiboLogin.popup_login_dialog] manually click the login button faield maybe login dialog Appear：{e}")

    async def login_by_qrcode(self):
        """login weibo website and keep webdriver login state"""
        utils.logger.info("[WeiboLogin.login_by_qrcode] Begin login weibo by qrcode ...")

        await self.popup_login_dialog()

        # find login qrcode
        qrcode_img_selector = "//div[@class='woo-modal-main']//img"
        base64_qrcode_img = await utils.find_login_qrcode(
            self.context_page,
            selector=qrcode_img_selector
        )
        if not base64_qrcode_img:
            utils.logger.info("[WeiboLogin.login_by_qrcode] login failed , have not found qrcode please check ....")
            sys.exit()

        # show login qrcode
        partial_show_qrcode = functools.partial(utils.show_qrcode, base64_qrcode_img)
        asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)

        utils.logger.info(f"[WeiboLogin.login_by_qrcode] Waiting for scan code login, remaining time is 20s")

        # get not logged session
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        no_logged_in_session = cookie_dict.get("WBPSESS")

        try:
            await self.check_login_state(no_logged_in_session)
        except RetryError:
            utils.logger.info("[WeiboLogin.login_by_qrcode] Login weibo failed by qrcode login method ...")
            sys.exit()

        wait_redirect_seconds = 5
        utils.logger.info(
            f"[WeiboLogin.login_by_qrcode] Login successful then wait for {wait_redirect_seconds} seconds redirect ...")
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_mobile(self):
        pass

    async def login_by_cookies(self):
        utils.logger.info("[WeiboLogin.login_by_qrcode] Begin login weibo by cookie ...")
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".weibo.cn",
                'path': "/"
            }])
