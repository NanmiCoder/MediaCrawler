# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/smzdm/login.py
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

import asyncio
import sys
from playwright.async_api import BrowserContext, Page
from tenacity import retry, retry_if_result, stop_after_attempt, wait_fixed
import config
from base.base_crawler import AbstractLogin
from tools import utils


class SmzdmLogin(AbstractLogin):
    def __init__(self, loginType: str, browserContext: BrowserContext, contextPage: Page, cookieStr: str = ""):
        self.loginType = loginType
        self.browserContext = browserContext
        self.contextPage = contextPage
        self.cookieStr = cookieStr

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self) -> bool:
        """
        检查浏览器 Cookie 是否包含登录标识
        """
        currentCookie = await self.browserContext.cookies()
        _, cookieDict = utils.convert_cookies(currentCookie)
        if "smzdm_user" in cookieDict or "smzdm_id" in cookieDict:
            return True
        return False

    async def begin(self):
        """
        启动什么值得买登录流程
        """
        utils.logger.info("[SmzdmLogin.begin] Begin login smzdm...")
        if self.loginType == "cookie":
            await self.login_by_cookies()
        else:
            await self.login_by_qrcode()

    async def login_by_mobile(self):
        pass

    async def login_by_qrcode(self):
        """
        使用扫码/交互式方式进行登录
        """
        utils.logger.info("[SmzdmLogin.login_by_qrcode] Opening login page...")
        await self.contextPage.goto("https://zhiyou.smzdm.com/user/login")
        utils.logger.info("[SmzdmLogin.login_by_qrcode] Please scan QR code or log in manually in 120s...")
        try:
            await self.check_login_state()
            utils.logger.info("[SmzdmLogin.login_by_qrcode] Login successful!")
            await asyncio.sleep(5)
        except Exception:
            utils.logger.error("[SmzdmLogin.login_by_qrcode] Login timeout or failed.")
            sys.exit()

    async def login_by_cookies(self):
        """
        使用预置 Cookie 进行登录
        """
        utils.logger.info("[SmzdmLogin.login_by_cookies] Loading cookies...")
        for key, value in utils.convert_str_cookie_to_dict(self.cookieStr).items():
            await self.browserContext.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".smzdm.com",
                'path': "/"
            }])
