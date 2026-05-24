# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/smzdm/core.py
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

import asyncio
import os
from typing import Dict, List, Optional
from playwright.async_api import BrowserContext, Page, Playwright, async_playwright
import config
from base.base_crawler import AbstractCrawler
from store import smzdm as smzdm_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var
from .client import SmzdmClient
from .login import SmzdmLogin
from .help import SmzdmExtractor


class SmzdmCrawler(AbstractCrawler):
    context_page: Page
    smzdm_client: SmzdmClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.indexUrl = "https://www.smzdm.com"
        self.userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self._extractor = SmzdmExtractor()
        self.cdp_manager = None

    async def start(self) -> None:
        """
        开始运行什么值得买爬虫流程
        """
        async with async_playwright() as playwright:
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[SmzdmCrawler] Launching in CDP mode")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright, None, self.userAgent, headless=config.CDP_HEADLESS
                )
            else:
                utils.logger.info("[SmzdmCrawler] Launching in standard mode")
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium, None, self.userAgent, headless=config.HEADLESS
                )
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.indexUrl, wait_until="domcontentloaded")

            cookieStr, cookieDict = await utils.convert_browser_context_cookies(
                self.browser_context, urls=[self.indexUrl]
            )
            self.smzdm_client = SmzdmClient(
                headers={"user-agent": self.userAgent, "cookie": cookieStr},
                cookieDict=cookieDict
            )

            if not await self.smzdm_client.pong():
                loginObj = SmzdmLogin(
                    loginType=config.LOGIN_TYPE,
                    browserContext=self.browser_context,
                    contextPage=self.context_page,
                    cookieStr=config.COOKIES
                )
                await loginObj.begin()
                await self.smzdm_client.update_cookies(self.browser_context)

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "detail":
                await self.get_specified_notes()
            else:
                utils.logger.info(f"[SmzdmCrawler] Crawler type {config.CRAWLER_TYPE} not supported for smzdm")

            utils.logger.info("[SmzdmCrawler] finished ...")

    async def get_specified_notes(self):
        """
        获取指定的商品/文章详情页及评论信息
        """
        for fullUrl in config.SMZDM_SPECIFIED_ID_LIST:
            utils.logger.info(f"[SmzdmCrawler] Processing URL: {fullUrl}")
            postId = [x for x in fullUrl.split("/") if x][-1]

            try:
                await self.context_page.goto(fullUrl, wait_until="domcontentloaded")
                await asyncio.sleep(5)
            except Exception as e:
                utils.logger.error(f"[SmzdmCrawler] Failed to load url {fullUrl}: {e}")
                continue

            utils.logger.info("[SmzdmCrawler] Scrolling down to load comments...")
            for i in range(8):
                try:
                    await self.context_page.evaluate("window.scrollBy(0, 1000)")
                except Exception as e:
                    utils.logger.warning(f"[SmzdmCrawler] Scroll warning: {e}")
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            html = await self.context_page.content()
            postData = self._extractor.extract_post(postId, fullUrl, html)
            await smzdm_store.updateSmzdmPost(postData)

            if config.ENABLE_GET_COMMENTS:
                comments = self._extractor.extract_comments_from_html(postId, html)
                utils.logger.info(f"[SmzdmCrawler] Extracted {len(comments)} comments")
                await smzdm_store.batchUpdateSmzdmComments(comments)

                page = 2
                while page <= 10:
                    nextBtn = self.context_page.locator("a.next, li.next a, li.pagedown a, a:has-text('下一页')").first
                    if await nextBtn.is_visible():
                        utils.logger.info(f"[SmzdmCrawler] Clicking next page button (page {page})...")
                        await nextBtn.click()
                        await asyncio.sleep(3)
                        for _ in range(3):
                            try:
                                await self.context_page.evaluate("window.scrollBy(0, 500)")
                            except Exception as e:
                                utils.logger.warning(f"[SmzdmCrawler] Paging scroll warning: {e}")
                            await asyncio.sleep(1)

                        html = await self.context_page.content()
                        pageComments = self._extractor.extract_comments_from_html(postId, html)
                        if pageComments:
                            await smzdm_store.batchUpdateSmzdmComments(pageComments)
                        page += 1
                    else:
                        break

    async def search(self):
        """
        实现抽象类要求的 search 方法
        """
        pass

    async def launch_browser(self, chromium, proxy, user_agent, headless=True) -> BrowserContext:
        if config.SAVE_LOGIN_STATE:
            userDataDir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)
            browserContext = await chromium.launch_persistent_context(
                user_data_dir=userDataDir,
                accept_downloads=True,
                headless=headless,
                proxy=proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
                channel="chrome"
            )
            return browserContext
        else:
            browser = await chromium.launch(headless=headless, proxy=proxy, channel="chrome")
            browserContext = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)
            return browserContext

    async def launch_browser_with_cdp(self, playwright, proxy, user_agent, headless=True) -> BrowserContext:
        try:
            self.cdp_manager = CDPBrowserManager()
            browserContext = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=proxy,
                user_agent=user_agent,
                headless=headless
            )
            return browserContext
        except Exception as e:
            utils.logger.error(f"[SmzdmCrawler] CDP mode failed, fallback: {e}")
            return await self.launch_browser(playwright.chromium, proxy, user_agent, headless)
