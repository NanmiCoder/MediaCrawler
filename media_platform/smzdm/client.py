# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/smzdm/client.py
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

from typing import Dict
from playwright.async_api import BrowserContext
from base.base_crawler import AbstractApiClient


class SmzdmClient(AbstractApiClient):
    def __init__(self, headers: Dict[str, str], cookieDict: Dict[str, str]):
        self.defaultHeaders = headers
        self.cookieDict = cookieDict

    async def request(self, method, url, **kwargs):
        pass

    async def update_cookies(self, browser_context: BrowserContext):
        """
        更新客户端保存的 Cookie
        """
        from tools import utils
        cookieStr, cookieDict = await utils.convert_browser_context_cookies(
            browser_context, urls=["https://www.smzdm.com", "https://post.smzdm.com"]
        )
        self.defaultHeaders["cookie"] = cookieStr
        self.cookieDict = cookieDict

    async def pong(self) -> bool:
        """
        检查登录态是否存活
        """
        return "smzdm_user" in self.cookieDict or "smzdm_id" in self.cookieDict
