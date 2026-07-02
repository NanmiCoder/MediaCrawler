# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/tiktok/core.py
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
import os
import random
import urllib.parse
import json
from asyncio import Task
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)

import config
from config import tiktok_config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import tiktok as tiktok_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import TikTokClient
from .exception import DataFetchError
from .help import parse_video_info_from_url, parse_creator_info_from_url
from .login import TikTokLogin


class TikTokCrawler(AbstractCrawler):
    context_page: Page
    tiktok_client: TikTokClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = "https://www.tiktok.com"
        self.cookie_urls = [
            "https://tiktok.com",
            self.index_url,
        ]
        self.cdp_manager = None
        self.ip_proxy_pool = None

    async def get_universal_data_from_page(self) -> Optional[Dict]:
        try:
            universal_json_str = await self.context_page.evaluate(
                """() => {
                    const s = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
                    return s ? s.textContent : null;
                }"""
            )
            if universal_json_str:
                return json.loads(universal_json_str)
        except Exception as e:
            utils.logger.error(f"[TikTokCrawler] Failed to parse __UNIVERSAL_DATA_FOR_REHYDRATION__: {e}")
        return None

    async def get_aweme_detail_from_html(self, aweme_id: str) -> Optional[Dict]:
        video_url = f"https://www.tiktok.com/@x/video/{aweme_id}"
        utils.logger.info(f"[TikTokCrawler] Navigating to: {video_url} to parse video detail")
        try:
            await self.context_page.goto(video_url)
            await asyncio.sleep(random.uniform(4.0, 6.0))
            
            data = await self.get_universal_data_from_page()
            if data:
                detail_scope = data.get("__DEFAULT_SCOPE__", {}).get("webapp.video-detail", {})
                item_info = detail_scope.get("itemInfo", {})
                item_struct = item_info.get("itemStruct")
                if item_struct:
                    utils.logger.info(f"[TikTokCrawler] Successfully parsed video detail for {aweme_id} from HTML")
                    return item_struct
        except Exception as e:
            utils.logger.error(f"[TikTokCrawler] Failed to get video detail from HTML for {aweme_id}: {e}")
        
        # Fallback to API if HTML parse failed
        utils.logger.warn(f"[TikTokCrawler] HTML parse failed or empty for {aweme_id}, falling back to API")
        try:
            return await self.tiktok_client.get_video_by_id(aweme_id)
        except Exception as api_err:
            utils.logger.error(f"[TikTokCrawler] API fallback failed for {aweme_id}: {api_err}")
            return None

    async def get_creator_detail_from_html(self, unique_id: str) -> Tuple[Optional[Dict], Optional[List[Dict]]]:
        creator_url = f"https://www.tiktok.com/@{unique_id}"
        utils.logger.info(f"[TikTokCrawler] Navigating to: {creator_url} to parse creator detail")
        try:
            await self.context_page.goto(creator_url)
            await asyncio.sleep(random.uniform(4.0, 6.0))
            
            data = await self.get_universal_data_from_page()
            if data:
                user_scope = data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {})
                user_info = user_scope.get("userInfo", {})
                user_detail = user_info.get("user")
                if user_detail:
                    utils.logger.info(f"[TikTokCrawler] Successfully parsed creator profile for {unique_id} from HTML")
                    stats = user_info.get("stats", {})
                    stats_v2 = user_info.get("statsV2", {})
                    creator_data = {
                        "userInfo": {
                            "user": user_detail,
                            "stats": stats,
                            "statsV2": stats_v2
                        }
                    }
                    item_list = user_info.get("itemList", [])
                    return creator_data, item_list
        except Exception as e:
            utils.logger.error(f"[TikTokCrawler] Failed to get creator profile from HTML for {unique_id}: {e}")
            
        # Fallback to API
        utils.logger.warn(f"[TikTokCrawler] HTML parse failed or empty for creator {unique_id}, falling back to API")
        try:
            creator_data = await self.tiktok_client.get_user_info(unique_id)
            user_info = creator_data.get("userInfo") or creator_data
            user_detail = user_info.get("user", {})
            user_id = user_detail.get("id") or user_detail.get("uid")
            item_list = []
            if user_id:
                item_list = await self.tiktok_client.get_all_user_aweme_posts(sec_user_id=user_id)
            return creator_data, item_list
        except Exception as api_err:
            utils.logger.error(f"[TikTokCrawler] API fallback failed for creator {unique_id}: {api_err}")
            return None, None

    async def start(self) -> None:
        # Clean up any orphaned Playwright browser processes to release user data directory lock
        if os.name == 'nt':
            try:
                import subprocess
                subprocess.run(
                    'powershell -Command "Get-CimInstance Win32_Process -Filter \\"ExecutablePath like \'%ms-playwright%\'\\" | Remove-CimInstance"',
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                utils.logger.info("[TikTokCrawler] Cleaned up orphaned Playwright browser processes.")
            except Exception as e:
                utils.logger.warn(f"[TikTokCrawler] Failed to clean up orphaned processes: {e}")

        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[TikTokCrawler] Starting browser in CDP mode")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    None,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[TikTokCrawler] Starting browser in standard mode")
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    playwright_proxy_format,
                    user_agent=None,
                    headless=config.HEADLESS,
                )
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url, wait_until="domcontentloaded")

            # Wait for page to initialize fully
            await asyncio.sleep(3)

            self.tiktok_client = await self.create_tiktok_client(httpx_proxy_format)
            if not await self.tiktok_client.pong(browser_context=self.browser_context):
                login_obj = TikTokLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await self.tiktok_client.update_cookies(
                    browser_context=self.browser_context,
                    urls=self.cookie_urls,
                )
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                await self.get_specified_awemes()
            elif config.CRAWLER_TYPE == "creator":
                await self.get_creators_and_videos()

            utils.logger.info("[TikTokCrawler.start] TikTok Crawler finished ...")

    async def search(self) -> None:
        utils.logger.info("[TikTokCrawler.search] Begin search TikTok keywords")
        limit_count = 20
        start_page = config.START_PAGE
        if config.CRAWLER_MAX_NOTES_COUNT < limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = limit_count

        
        keywords_str = config.KEYWORDS or ",".join(tiktok_config.TIKTOK_KEYWORD_LIST)
        for keyword in keywords_str.split(","):
            if not keyword.strip():
                continue
            source_keyword_var.set(keyword)
            utils.logger.info(f"[TikTokCrawler.search] Current keyword: {keyword}")
            
            # Navigate to TikTok search page to initialize context and tokens for this search query
            search_page_url = f"https://www.tiktok.com/search?q={urllib.parse.quote(keyword)}"
            utils.logger.info(f"[TikTokCrawler.search] Navigating to search page: {search_page_url}")
            try:
                await self.context_page.goto(search_page_url)
                await asyncio.sleep(random.uniform(5.0, 7.0))
            except Exception as e:
                utils.logger.error(f"[TikTokCrawler.search] Navigation to search page failed: {e}")

            aweme_list: List[str] = []
            page = 0
            while (page - start_page + 1) * limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[TikTokCrawler.search] Skip page {page}")
                    page += 1
                    continue
                try:
                    utils.logger.info(f"[TikTokCrawler.search] Searching TikTok keyword: {keyword}, page: {page}")
                    posts_res = await self.tiktok_client.search_video_by_keyword(
                        keyword=keyword,
                        offset=page * limit_count - limit_count,
                        count=limit_count,
                    )
                    utils.logger.info(f"[TikTokCrawler.search] Raw API response: {posts_res}")
                    
                    # Supports various nested layouts of TikTok search API
                    videos = posts_res.get("data") or posts_res.get("itemList") or posts_res.get("item_list")
                    if not videos:
                        utils.logger.info(f"[TikTokCrawler.search] Search TikTok keyword: {keyword}, page: {page} is empty")
                        break
                except DataFetchError as e:
                    utils.logger.error(f"[TikTokCrawler.search] Search TikTok keyword: {keyword} failed: {e}")
                    break

                page += 1
                page_aweme_list = []
                for post_item in videos:
                    # TikTok returns itemStruct directly in list or inside container
                    aweme_info = post_item.get("itemStruct") or post_item.get("item") or post_item
                    aweme_id = aweme_info.get("id") or aweme_info.get("aweme_id")
                    if not aweme_id:
                        continue
                    aweme_list.append(str(aweme_id))
                    page_aweme_list.append(str(aweme_id))
                    
                    await tiktok_store.update_tiktok_aweme(aweme_item=aweme_info)
                    await self.get_aweme_media(aweme_item=aweme_info)

                await self.batch_get_note_comments(page_aweme_list)
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            utils.logger.info(f"[TikTokCrawler.search] keyword:{keyword}, aweme_list:{aweme_list}")

    async def get_specified_awemes(self) -> None:
        utils.logger.info("[TikTokCrawler.get_specified_awemes] Parsing video URLs...")
        aweme_id_list = []
        
        # Load from command line arguments or tiktok_config.py
        video_id_list = getattr(config, "TIKTOK_VIDEO_ID_LIST", None) or tiktok_config.TIKTOK_VIDEO_ID_LIST
        for video_url in video_id_list:
            try:
                video_info = parse_video_info_from_url(video_url)
                if video_info.url_type == "short":
                    utils.logger.info(f"[TikTokCrawler.get_specified_awemes] Resolving short link: {video_url}")
                    resolved_url = await self.tiktok_client.resolve_short_url(video_url)
                    if resolved_url:
                        video_info = parse_video_info_from_url(resolved_url)
                        utils.logger.info(f"[TikTokCrawler.get_specified_awemes] Short link resolved to: {video_info.video_id}")
                    else:
                        utils.logger.error(f"[TikTokCrawler.get_specified_awemes] Failed to resolve short link: {video_url}")
                        continue
                aweme_id_list.append(video_info.video_id)
            except ValueError as e:
                utils.logger.error(f"[TikTokCrawler.get_specified_awemes] Failed to parse video URL: {e}")
                continue

        for aweme_id in aweme_id_list:
            try:
                aweme_detail = await self.get_aweme_detail_from_html(aweme_id)
                if aweme_detail is not None:
                    # Supports detail endpoints that wrap detail inside itemInfo
                    item = aweme_detail.get("itemInfo", {}).get("itemStruct") or aweme_detail.get("itemStruct") or aweme_detail
                    await tiktok_store.update_tiktok_aweme(aweme_item=item)
                    await self.get_aweme_media(aweme_item=item)
            except Exception as e:
                utils.logger.error(f"[TikTokCrawler.get_specified_awemes] Error processing aweme_id {aweme_id}: {e}")
        await self.batch_get_note_comments(aweme_id_list)

    async def batch_get_note_comments(self, aweme_list: List[str]) -> None:
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[TikTokCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        for aweme_id in aweme_list:
            await self.get_comments(aweme_id)

    async def get_comments(self, aweme_id: str) -> None:
        try:
            # Navigate to the video detail page first to establish context for comment list fetch
            video_url = f"https://www.tiktok.com/@x/video/{aweme_id}"
            utils.logger.info(f"[TikTokCrawler.get_comments] Navigating to: {video_url}")
            await self.context_page.goto(video_url)
            await asyncio.sleep(random.uniform(3.0, 5.0))

            crawl_interval = config.CRAWLER_MAX_SLEEP_SEC
            max_comments = config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES or tiktok_config.TIKTOK_MAX_COMMENTS_PER_VIDEO
            await self.tiktok_client.get_aweme_all_comments(
                aweme_id=aweme_id,
                crawl_interval=crawl_interval,
                is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                callback=tiktok_store.batch_update_tiktok_comments,
                max_count=max_comments,
            )
            await asyncio.sleep(crawl_interval)
            utils.logger.info(f"[TikTokCrawler.get_comments] aweme_id: {aweme_id} comments obtained...")
        except Exception as e:
            utils.logger.error(f"[TikTokCrawler.get_comments] aweme_id: {aweme_id} get comments failed: {e}")
            try:
                current_url = self.context_page.url
                utils.logger.info(f"[TikTokCrawler.get_comments] Current page URL on failure: {current_url}")
                screenshot_path = os.path.join(
                    r"C:\Users\Admin\.gemini\antigravity\brain\0aaec311-5a6a-49ca-bc03-e251daf363bd",
                    f"error_{aweme_id}.png"
                )
                await self.context_page.screenshot(path=screenshot_path)
                utils.logger.info(f"[TikTokCrawler.get_comments] Saved error screenshot to: {screenshot_path}")
            except Exception as se:
                utils.logger.error(f"[TikTokCrawler.get_comments] Failed to take screenshot: {se}")

    async def get_creators_and_videos(self) -> None:
        utils.logger.info("[TikTokCrawler.get_creators_and_videos] Begin get TikTok creators")
        
        creator_id_list = getattr(config, "TIKTOK_CREATOR_ID_LIST", None) or tiktok_config.TIKTOK_CREATOR_ID_LIST
        for creator_url in creator_id_list:
            try:
                creator_info_parsed = parse_creator_info_from_url(creator_url)
                unique_id = creator_info_parsed.unique_id
                utils.logger.info(f"[TikTokCrawler.get_creators_and_videos] Parsed unique_id: {unique_id} from {creator_url}")
            except ValueError as e:
                utils.logger.error(f"[TikTokCrawler.get_creators_and_videos] Failed to parse creator URL: {e}")
                continue

            creator_info, video_list = await self.get_creator_detail_from_html(unique_id)
            if not creator_info:
                continue

            user_info = creator_info.get("userInfo") or creator_info
            user_detail = user_info.get("user", {})
            user_id = user_detail.get("id") or user_detail.get("uid")
            
            if user_info:
                await tiktok_store.save_creator(user_id, creator=user_info)

            if video_list:
                await self.fetch_creator_video_detail(video_list)
                video_ids = [str(video_item.get("id") or video_item.get("aweme_id")) for video_item in video_list]
                await self.batch_get_note_comments(video_ids)

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        for post_item in video_list:
            aweme_id = str(post_item.get("id") or post_item.get("aweme_id"))
            try:
                aweme_detail = await self.get_aweme_detail_from_html(aweme_id)
                if aweme_detail is not None:
                    item = aweme_detail.get("itemInfo", {}).get("itemStruct") or aweme_detail.get("itemStruct") or aweme_detail
                    await tiktok_store.update_tiktok_aweme(aweme_item=item)
                    await self.get_aweme_media(aweme_item=item)
            except Exception as e:
                utils.logger.error(f"[TikTokCrawler.fetch_creator_video_detail] Error processing aweme_id {aweme_id}: {e}")

    async def create_tiktok_client(self, httpx_proxy: Optional[str]) -> TikTokClient:
        cookie_str, cookie_dict = await utils.convert_browser_context_cookies(
            self.browser_context,
            urls=self.cookie_urls,
        )
        tiktok_client = TikTokClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": await self.context_page.evaluate("() => navigator.userAgent"),
                "Cookie": cookie_str,
                "Host": "www.tiktok.com",
                "Origin": "https://www.tiktok.com/",
                "Referer": "https://www.tiktok.com/",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,
        )
        return tiktok_client

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)
            return browser_context

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )
            await self.cdp_manager.add_stealth_script()
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[TikTokCrawler] CDP browser info: {browser_info}")
            return browser_context
        except Exception as e:
            utils.logger.error(f"[TikTokCrawler] CDP startup failed, falling back to standard: {e}")
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self) -> None:
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[TikTokCrawler.close] Browser context closed ...")

    async def get_aweme_media(self, aweme_item: Dict):
        if not config.ENABLE_GET_MEIDAS:
            return
        video_download_url = _extract_video_download_url(aweme_item)
        if video_download_url:
            await self.get_aweme_video(aweme_item)

    async def get_aweme_video(self, aweme_item: Dict):
        if not config.ENABLE_GET_MEIDAS:
            return
        aweme_id = aweme_item.get("id") or aweme_item.get("aweme_id")
        video_download_url = _extract_video_download_url(aweme_item)
        if not video_download_url:
            return
        content = await self.tiktok_client.get_aweme_media(video_download_url)
        await asyncio.sleep(random.random())
        if content is None:
            return
        extension_file_name = "video.mp4"
        await tiktok_store.update_tiktok_video(aweme_id, content, extension_file_name)


def _extract_video_download_url(item: Dict) -> str:
    return item.get("video", {}).get("playAddr", "")
