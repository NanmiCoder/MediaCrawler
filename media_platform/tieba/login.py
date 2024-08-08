import asyncio
import functools
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import (RetryError, retry, retry_if_result, stop_after_attempt,
                      wait_fixed)

import config
from base.base_crawler import AbstractLogin
from tools import utils


class BaiduTieBaLogin(AbstractLogin):

    def __init__(self,
                 login_type: str,
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",
                 cookie_str: str = ""
                 ):
        config.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self) -> bool:
        """
        轮训检查登录状态是否成功，成功返回True否则返回False

        Returns:

        """
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        stoken = cookie_dict.get("STOKEN")
        ptoken = cookie_dict.get("PTOKEN")
        if stoken or ptoken:
            return True
        return False

    async def begin(self):
        """Start login baidutieba"""
        utils.logger.info("[BaiduTieBaLogin.begin] Begin login baidutieba ...")
        if config.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "phone":
            await self.login_by_mobile()
        elif config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError("[BaiduTieBaLogin.begin]Invalid Login Type Currently only supported qrcode or phone or cookies ...")

    async def login_by_mobile(self):
        """Login baidutieba by mobile"""
        pass

    async def login_by_qrcode(self):
        """login baidutieba website and keep webdriver login state"""
        utils.logger.info("[BaiduTieBaLogin.login_by_qrcode] Begin login baidutieba by qrcode ...")
        qrcode_img_selector = "xpath=//img[@class='tang-pass-qrcode-img']"
        # find login qrcode
        base64_qrcode_img = await utils.find_login_qrcode(
            self.context_page,
            selector=qrcode_img_selector
        )
        if not base64_qrcode_img:
            utils.logger.info("[BaiduTieBaLogin.login_by_qrcode] login failed , have not found qrcode please check ....")
            # if this website does not automatically popup login dialog box, we will manual click login button
            await asyncio.sleep(0.5)
            login_button_ele = self.context_page.locator("xpath=//li[@class='u_login']")
            await login_button_ele.click()
            base64_qrcode_img = await utils.find_login_qrcode(
                self.context_page,
                selector=qrcode_img_selector
            )
            if not base64_qrcode_img:
                utils.logger.info("[BaiduTieBaLogin.login_by_qrcode] login failed , have not found qrcode please check ....")
                sys.exit()

        # show login qrcode
        # fix issue #12
        # we need to use partial function to call show_qrcode function and run in executor
        # then current asyncio event loop will not be blocked
        partial_show_qrcode = functools.partial(utils.show_qrcode, base64_qrcode_img)
        asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)

        utils.logger.info(f"[BaiduTieBaLogin.login_by_qrcode] waiting for scan code login, remaining time is 120s")
        try:
            await self.check_login_state()
        except RetryError:
            utils.logger.info("[BaiduTieBaLogin.login_by_qrcode] Login baidutieba failed by qrcode login method ...")
            sys.exit()

        wait_redirect_seconds = 5
        utils.logger.info(f"[BaiduTieBaLogin.login_by_qrcode] Login successful then wait for {wait_redirect_seconds} seconds redirect ...")
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_cookies(self):
        """login baidutieba website by cookies"""
        utils.logger.info("[BaiduTieBaLogin.login_by_cookies] Begin login baidutieba by cookie ...")
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".baidu.com",
                'path': "/"
            }])
