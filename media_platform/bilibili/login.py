# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/bilibili/login.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 18:44
# @Desc    : bilibili login implementation class

import asyncio
import functools
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import (RetryError, retry, retry_if_result, stop_after_attempt,
                      wait_fixed)

import config
from base.base_crawler import AbstractLogin
from tools import utils

# B 站首页 header 目前新旧两套实现并行灰度，未登录时的登录入口选择器不同：
# - 新版 header：.header-avatar-unlogin-entry
# - 旧版 header：.right-entry__outside.go-login-btn 内部的 .header-login-entry
# 两者点击后都调用 mini-login-v2 的 openMiniLogin()，拉起同一个登录弹窗，
# 弹窗内的二维码仍是 .login-scan-box 里的 img，所以这里只需要兼容入口按钮。
LOGIN_ENTRY_SELECTORS = [
    ".header-avatar-unlogin-entry",
    ".right-entry__outside.go-login-btn .header-login-entry",
]


def is_login_cookie_refreshed(cookie_dict: dict, sessdata_before_login: str) -> bool:
    """判断浏览器里的 SESSDATA 是否已经是扫码换发后的新值。

    过期的 SESSDATA 同样会留在浏览器里，所以"cookie 存在"不等于"已登录"。
    只判断存在会把死会话判成登录成功：既跳过扫码，又把这份死 cookie 灌给
    API client —— B 站 playurl 依据 Cookie 决定清晰度，结果是详情和评论照常拿到
    （这两个接口不要求登录），视频却被静默限制在 480P。
    """
    sessdata = cookie_dict.get("SESSDATA", "")
    return bool(sessdata) and sessdata != sessdata_before_login


class BilibiliLogin(AbstractLogin):
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
        # 进入登录流程前浏览器里已有的 SESSDATA，用于区分"cookie 存在"与"cookie 有效"
        self._sessdata_before_login: str = ""

    async def begin(self):
        """Start login bilibili"""
        utils.logger.info("[BilibiliLogin.begin] Begin login Bilibili ...")
        if config.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "phone":
            await self.login_by_mobile()
        elif config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError(
                "[BilibiliLogin.begin] Invalid Login Type Currently only supported qrcode or phone or cookie ...")

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self) -> bool:
        """
            Check if the current login status is successful and return True otherwise return False
            retry decorator will retry 600 times if the return value is False, and the retry interval is 1 second
            if max retry times reached, raise RetryError
        """
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        return is_login_cookie_refreshed(cookie_dict, self._sessdata_before_login)

    async def login_by_qrcode(self):
        """login bilibili website and keep webdriver login state"""
        utils.logger.info("[BilibiliLogin.login_by_qrcode] Begin login bilibili by qrcode ...")

        # 记下扫码前的 SESSDATA：扫码成功后它会被换发成新值，
        # check_login_state 靠这个差值判断"真的登录了"而不是"只剩一份过期 cookie"
        _, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        self._sessdata_before_login = cookie_dict.get("SESSDATA", "")
        if self._sessdata_before_login:
            utils.logger.warning(
                "[BilibiliLogin.login_by_qrcode] 浏览器中残留了 SESSDATA，但接口校验为未登录，"
                "该会话已失效；本次必须重新扫码换发新 cookie 才会继续 ..."
            )

        # click login button
        login_entry_selector = ", ".join(LOGIN_ENTRY_SELECTORS)
        try:
            await self.context_page.wait_for_selector(
                selector=login_entry_selector,
                state="visible",
                timeout=30_000,
            )
        except PlaywrightTimeoutError:
            utils.logger.error(
                "[BilibiliLogin.login_by_qrcode] Login entry not found on the homepage, "
                f"selectors tried: {LOGIN_ENTRY_SELECTORS}. "
                "Bilibili may have changed the homepage header again, "
                "please update LOGIN_ENTRY_SELECTORS in media_platform/bilibili/login.py."
            )
            sys.exit()
        await self.context_page.locator(login_entry_selector).first.click()
        await asyncio.sleep(1)
        # find login qrcode
        qrcode_img_selector = "//div[@class='login-scan-box']//img"
        base64_qrcode_img = await utils.find_login_qrcode(
            self.context_page,
            selector=qrcode_img_selector
        )
        if not base64_qrcode_img:
            utils.logger.info("[BilibiliLogin.login_by_qrcode] login failed , have not found qrcode please check ....")
            sys.exit()

        # show login qrcode
        partial_show_qrcode = functools.partial(utils.show_qrcode, base64_qrcode_img)
        asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)

        utils.logger.info(f"[BilibiliLogin.login_by_qrcode] Waiting for scan code login, remaining time is 20s")
        try:
            await self.check_login_state()
        except RetryError:
            utils.logger.info("[BilibiliLogin.login_by_qrcode] Login bilibili failed by qrcode login method ...")
            sys.exit()

        wait_redirect_seconds = 5
        utils.logger.info(
            f"[BilibiliLogin.login_by_qrcode] Login successful then wait for {wait_redirect_seconds} seconds redirect ...")
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_mobile(self):
        pass

    async def login_by_cookies(self):
        utils.logger.info("[BilibiliLogin.login_by_qrcode] Begin login bilibili by cookie ...")
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".bilibili.com",
                'path': "/"
            }])
