# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 18:44
# @Desc    : B站爬虫

import asyncio
import os
import random
import time
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from models import kuaishou
from proxy.proxy_account_pool import AccountPool
from tools import utils
from var import comment_tasks_var, crawler_type_var

from .client import BilibiliClient
from .exception import DataFetchError
from .login import BilibiliLogin


class BilibiliCrawler(AbstractCrawler):
    platform: str
    login_type: str
    crawler_type: str
    context_page: Page
    bili_client: BilibiliClient
    account_pool: AccountPool
    browser_context: BrowserContext

    def __init__(self):
        self.index_url = "https://www.bilibili.com"
        self.user_agent = utils.get_user_agent()

    def init_config(self, platform: str, login_type: str, account_pool: AccountPool, crawler_type: str):
        self.platform = platform
        self.login_type = login_type
        self.account_pool = account_pool
        self.crawler_type = crawler_type

    async def start(self):
        pass

    async def search(self):
        pass
