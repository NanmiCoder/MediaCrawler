# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/tiktok/login.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习 and 研究目的使用。使用者应遵守以下原则：
# 1. 不得用于 any 商业用途。
# 2. 使用时应遵守目标平台的使用条款 and robots.txt规则。
# 3. 不得进行大规模爬取 or 对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于 any 非法 or 不当 the 用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE file。
# 使用本代码即表示您同意遵守上述原则 and LICENSE中的所有条款。

import asyncio
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import (RetryError, retry, retry_if_result, stop_after_attempt,
                      wait_fixed)

import config
from base.base_crawler import AbstractLogin
from tools import utils


class TikTokLogin(AbstractLogin):
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

    async def begin(self):
        """Start login TikTok website"""
        utils.logger.info("[TikTokLogin.begin] Begin login TikTok ...")
        if config.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError(
                "[TikTokLogin.begin] Invalid Login Type Currently only supported qrcode or cookie ...")

        # check login state
        utils.logger.info(f"[TikTokLogin.begin] login finished then check login state ...")
        try:
            await self.check_login_state()
        except RetryError:
            utils.logger.info("[TikTokLogin.begin] login failed please confirm ...")
            sys.exit()

        # wait for redirect
        wait_redirect_seconds = 5
        utils.logger.info(f"[TikTokLogin.begin] Login successful then wait for {wait_redirect_seconds} seconds redirect ...")
        await asyncio.sleep(wait_redirect_seconds)

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self) -> bool:
        """
        Check if the current login status is successful and return True otherwise return False
        """
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        if cookie_dict.get("sessionid") or cookie_dict.get("sessionid_ss"):
            return True

        for page in self.browser_context.pages:
            try:
                profile_icon = page.locator('[data-e2e="profile-icon"]')
                if await profile_icon.is_visible():
                    return True
            except Exception:
                pass
        return False

    async def login_by_qrcode(self):
        """login TikTok website by qrcode scan"""
        utils.logger.info("[TikTokLogin.login_by_qrcode] Begin login TikTok by qrcode ...")
        await self.context_page.goto("https://www.tiktok.com/login")
        await asyncio.sleep(5)  # Wait for page to load

        # Try to click "Use QR code" if it exists
        try:
            qr_btn = self.context_page.locator("xpath=//div[contains(text(), 'Use QR code') or contains(text(), 'Quét mã QR') or contains(text(), 'Scan with QR code')]")
            if await qr_btn.is_visible():
                await qr_btn.click()
                await asyncio.sleep(2)
        except Exception:
            pass

        # Try to locate the QR code canvas or container to show/save
        try:
            canvas_element = self.context_page.locator("canvas").first
            if await canvas_element.is_visible():
                screenshot = await canvas_element.screenshot()
                import base64
                base64_image = base64.b64encode(screenshot).decode('utf-8')
                
                import functools
                partial_show_qrcode = functools.partial(utils.show_qrcode, base64_image)
                asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)
                utils.logger.info("[TikTokLogin.login_by_qrcode] QR Code window opened. Please scan it.")
        except Exception as e:
            utils.logger.warn(f"[TikTokLogin.login_by_qrcode] Could not extract canvas QR code: {e}")

        # Always save a full screenshot of the page to the root directory as a backup
        try:
            screenshot_path = "qrcode.png"
            await self.context_page.screenshot(path=screenshot_path)
            utils.logger.info(f"[TikTokLogin.login_by_qrcode] Saved full login page screenshot to {screenshot_path}. Please check your workspace directory to scan it if no window popped up!")
        except Exception as e:
            utils.logger.error(f"[TikTokLogin.login_by_qrcode] Failed to take page screenshot: {e}")


    async def login_by_cookies(self):
        """login TikTok website by adding cookies"""
        utils.logger.info("[TikTokLogin.login_by_cookies] Begin login TikTok by cookie ...")
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".tiktok.com",
                'path': "/"
            }])

    async def login_by_mobile(self):
        """Mobile login is not supported for TikTok"""
        raise NotImplementedError("Mobile login is not supported for TikTok. Please use Cookie or QR Code login.")

