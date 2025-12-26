# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/tieba/client.py
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

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode, quote

import requests
from playwright.async_api import BrowserContext, Page
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractApiClient
from model.m_baidu_tieba import TiebaComment, TiebaCreator, TiebaNote
from proxy.proxy_ip_pool import ProxyIpPool
from tools import utils

from .field import SearchNoteType, SearchSortType
from .help import TieBaExtractor


class BaiduTieBaClient(AbstractApiClient):

    def __init__(
        self,
        timeout=10,
        ip_pool=None,
        default_ip_proxy=None,
        headers: Dict[str, str] = None,
        playwright_page: Optional[Page] = None,
    ):
        self.ip_pool: Optional[ProxyIpPool] = ip_pool
        self.timeout = timeout
        # Use provided headers (including real browser UA) or default headers
        self.headers = headers or {
            "User-Agent": utils.get_user_agent(),
            "Cookie": "",
        }
        self._host = "https://tieba.baidu.com"
        self._page_extractor = TieBaExtractor()
        self.default_ip_proxy = default_ip_proxy
        self.playwright_page = playwright_page  # Playwright page object

    def _sync_request(self, method, url, proxy=None, **kwargs):
        """
        Synchronous requests method
        Args:
            method: Request method
            url: Request URL
            proxy: Proxy IP
            **kwargs: Other request parameters

        Returns:
            Response object
        """
        # Construct proxy dictionary
        proxies = None
        if proxy:
            proxies = {
                "http": proxy,
                "https": proxy,
            }

        # Send request
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            proxies=proxies,
            timeout=self.timeout,
            **kwargs
        )
        return response

    async def _refresh_proxy_if_expired(self) -> None:
        """
        Check if proxy is expired and automatically refresh if necessary
        """
        if self.ip_pool is None:
            return

        if self.ip_pool.is_current_proxy_expired():
            utils.logger.info(
                "[BaiduTieBaClient._refresh_proxy_if_expired] Proxy expired, refreshing..."
            )
            new_proxy = await self.ip_pool.get_or_refresh_proxy()
            # Update proxy URL
            _, self.default_ip_proxy = utils.format_proxy_info(new_proxy)
            utils.logger.info(
                f"[BaiduTieBaClient._refresh_proxy_if_expired] New proxy: {new_proxy.ip}:{new_proxy.port}"
            )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def request(self, method, url, return_ori_content=False, proxy=None, **kwargs) -> Union[str, Any]:
        """
        Common request method wrapper for requests, handles request responses
        Args:
            method: Request method
            url: Request URL
            return_ori_content: Whether to return original content
            proxy: Proxy IP
            **kwargs: Other request parameters, such as headers, request body, etc.

        Returns:

        """
        # Check if proxy is expired before each request
        await self._refresh_proxy_if_expired()

        actual_proxy = proxy if proxy else self.default_ip_proxy

        # Execute synchronous requests in thread pool
        response = await asyncio.to_thread(
            self._sync_request,
            method,
            url,
            actual_proxy,
            **kwargs
        )

        if response.status_code != 200:
            utils.logger.error(f"Request failed, method: {method}, url: {url}, status code: {response.status_code}")
            utils.logger.error(f"Request failed, response: {response.text}")
            raise Exception(f"Request failed, method: {method}, url: {url}, status code: {response.status_code}")

        if response.text == "" or response.text == "blocked":
            utils.logger.error(f"request params incorrect, response.text: {response.text}")
            raise Exception("account blocked")

        if return_ori_content:
            return response.text

        return response.json()

    async def get(self, uri: str, params=None, return_ori_content=False, **kwargs) -> Any:
        """
        GET request with header signing
        Args:
            uri: Request route
            params: Request parameters
            return_ori_content: Whether to return original content

        Returns:

        """
        final_uri = uri
        if isinstance(params, dict):
            final_uri = (f"{uri}?"
                         f"{urlencode(params)}")
        try:
            res = await self.request(method="GET", url=f"{self._host}{final_uri}", return_ori_content=return_ori_content, **kwargs)
            return res
        except RetryError as e:
            if self.ip_pool:
                proxie_model = await self.ip_pool.get_proxy()
                _, proxy = utils.format_proxy_info(proxie_model)
                res = await self.request(method="GET", url=f"{self._host}{final_uri}", return_ori_content=return_ori_content, proxy=proxy, **kwargs)
                self.default_ip_proxy = proxy
                return res

            utils.logger.error(f"[BaiduTieBaClient.get] Reached maximum retry attempts, IP is blocked, please try a new IP proxy: {e}")
            raise Exception(f"[BaiduTieBaClient.get] Reached maximum retry attempts, IP is blocked, please try a new IP proxy: {e}")

    async def post(self, uri: str, data: dict, **kwargs) -> Dict:
        """
        POST request with header signing
        Args:
            uri: Request route
            data: Request body parameters

        Returns:

        """
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        return await self.request(method="POST", url=f"{self._host}{uri}", data=json_str, **kwargs)

    async def pong(self, browser_context: BrowserContext = None) -> bool:
        """
        Check if login state is still valid
        Uses Cookie detection instead of API calls to avoid detection
        Args:
            browser_context: Browser context object

        Returns:
            bool: True if logged in, False if not logged in
        """
        utils.logger.info("[BaiduTieBaClient.pong] Begin to check tieba login state by cookies...")

        if not browser_context:
            utils.logger.warning("[BaiduTieBaClient.pong] browser_context is None, assume not logged in")
            return False

        try:
            # Get cookies from browser and check key login cookies
            _, cookie_dict = utils.convert_cookies(await browser_context.cookies())

            # Baidu Tieba login identifiers: STOKEN or PTOKEN
            stoken = cookie_dict.get("STOKEN")
            ptoken = cookie_dict.get("PTOKEN")
            bduss = cookie_dict.get("BDUSS")  # Baidu universal login cookie

            if stoken or ptoken or bduss:
                utils.logger.info(f"[BaiduTieBaClient.pong] Login state verified by cookies (STOKEN: {bool(stoken)}, PTOKEN: {bool(ptoken)}, BDUSS: {bool(bduss)})")
                return True
            else:
                utils.logger.info("[BaiduTieBaClient.pong] No valid login cookies found, need to login")
                return False

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.pong] Check login state failed: {e}, assume not logged in")
            return False

    async def update_cookies(self, browser_context: BrowserContext):
        """
        Update cookies method provided by API client, usually called after successful login
        Args:
            browser_context: Browser context object

        Returns:

        """
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        utils.logger.info("[BaiduTieBaClient.update_cookies] Cookie has been updated")

    async def get_notes_by_keyword(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 10,
        sort: SearchSortType = SearchSortType.TIME_DESC,
        note_type: SearchNoteType = SearchNoteType.FIXED_THREAD,
    ) -> List[TiebaNote]:
        """
        Search Tieba posts by keyword (uses Playwright to access page, avoiding API detection)
        Args:
            keyword: Keyword
            page: Page number
            page_size: Page size
            sort: Result sort method
            note_type: Post type (main thread | main thread + reply mixed mode)
        Returns:

        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_notes_by_keyword] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based search")

        # Construct search URL
        # Example: https://tieba.baidu.com/f/search/res?ie=utf-8&qw=keyword
        search_url = f"{self._host}/f/search/res"
        params = {
            "ie": "utf-8",
            "qw": keyword,
            "rn": page_size,
            "pn": page,
            "sm": sort.value,
            "only_thread": note_type.value,
        }

        # Concatenate full URL
        full_url = f"{search_url}?{urlencode(params)}"
        utils.logger.info(f"[BaiduTieBaClient.get_notes_by_keyword] Accessing search page: {full_url}")

        try:
            # Use Playwright to access search page
            await self.playwright_page.goto(full_url, wait_until="domcontentloaded")

            # Wait for page loading, using delay setting from config file
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # Get page HTML content
            page_content = await self.playwright_page.content()
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_keyword] Successfully retrieved search page HTML, length: {len(page_content)}")

            # Extract search results
            notes = self._page_extractor.extract_search_note_list(page_content)
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_keyword] Extracted {len(notes)} posts")
            return notes

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_notes_by_keyword] Search failed: {e}")
            raise

    async def get_note_by_id(self, note_id: str) -> TiebaNote:
        """
        Get post details by post ID (uses Playwright to access page, avoiding API detection)
        Args:
            note_id: Post ID

        Returns:
            TiebaNote: Post detail object
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_note_by_id] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based note detail fetching")

        # Construct post detail URL
        note_url = f"{self._host}/p/{note_id}"
        utils.logger.info(f"[BaiduTieBaClient.get_note_by_id] Accessing post detail page: {note_url}")

        try:
            # Use Playwright to access post detail page
            await self.playwright_page.goto(note_url, wait_until="domcontentloaded")

            # Wait for page loading, using delay setting from config file
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # Get page HTML content
            page_content = await self.playwright_page.content()
            utils.logger.info(f"[BaiduTieBaClient.get_note_by_id] Successfully retrieved post detail HTML, length: {len(page_content)}")

            # Extract post details
            note_detail = self._page_extractor.extract_note_detail(page_content)
            return note_detail

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_note_by_id] Failed to get post details: {e}")
            raise

    async def get_note_all_comments(
        self,
        note_detail: TiebaNote,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_count: int = 10,
    ) -> List[TiebaComment]:
        """
        Get all first-level comments for specified post (uses Playwright to access page, avoiding API detection)
        Args:
            note_detail: Post detail object
            crawl_interval: Crawl delay interval in seconds
            callback: Callback function after one post crawl completes
            max_count: Maximum number of comments to crawl per post
        Returns:
            List[TiebaComment]: Comment list
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_note_all_comments] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based comment fetching")

        result: List[TiebaComment] = []
        current_page = 1

        while note_detail.total_replay_page >= current_page and len(result) < max_count:
            # Construct comment page URL
            comment_url = f"{self._host}/p/{note_detail.note_id}?pn={current_page}"
            utils.logger.info(f"[BaiduTieBaClient.get_note_all_comments] Accessing comment page: {comment_url}")

            try:
                # Use Playwright to access comment page
                await self.playwright_page.goto(comment_url, wait_until="domcontentloaded")

                # Wait for page loading, using delay setting from config file
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

                # Get page HTML content
                page_content = await self.playwright_page.content()

                # Extract comments
                comments = self._page_extractor.extract_tieba_note_parment_comments(
                    page_content, note_id=note_detail.note_id
                )

                if not comments:
                    utils.logger.info(f"[BaiduTieBaClient.get_note_all_comments] Page {current_page} has no comments, stopping crawl")
                    break

                # Limit comment count
                if len(result) + len(comments) > max_count:
                    comments = comments[:max_count - len(result)]

                if callback:
                    await callback(note_detail.note_id, comments)

                result.extend(comments)

                # Get all sub-comments
                await self.get_comments_all_sub_comments(
                    comments, crawl_interval=crawl_interval, callback=callback
                )

                await asyncio.sleep(crawl_interval)
                current_page += 1

            except Exception as e:
                utils.logger.error(f"[BaiduTieBaClient.get_note_all_comments] Failed to get page {current_page} comments: {e}")
                break

        utils.logger.info(f"[BaiduTieBaClient.get_note_all_comments] Total retrieved {len(result)} first-level comments")
        return result

    async def get_comments_all_sub_comments(
        self,
        comments: List[TiebaComment],
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[TiebaComment]:
        """
        Get all sub-comments for specified comments (uses Playwright to access page, avoiding API detection)
        Args:
            comments: Comment list
            crawl_interval: Crawl delay interval in seconds
            callback: Callback function after one post crawl completes

        Returns:
            List[TiebaComment]: Sub-comment list
        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            return []

        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_comments_all_sub_comments] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based sub-comment fetching")

        all_sub_comments: List[TiebaComment] = []

        for parment_comment in comments:
            if parment_comment.sub_comment_count == 0:
                continue

            current_page = 1
            max_sub_page_num = parment_comment.sub_comment_count // 10 + 1

            while max_sub_page_num >= current_page:
                # Construct sub-comment URL
                sub_comment_url = (
                    f"{self._host}/p/comment?"
                    f"tid={parment_comment.note_id}&"
                    f"pid={parment_comment.comment_id}&"
                    f"fid={parment_comment.tieba_id}&"
                    f"pn={current_page}"
                )
                utils.logger.info(f"[BaiduTieBaClient.get_comments_all_sub_comments] Accessing sub-comment page: {sub_comment_url}")

                try:
                    # Use Playwright to access sub-comment page
                    await self.playwright_page.goto(sub_comment_url, wait_until="domcontentloaded")

                    # Wait for page loading, using delay setting from config file
                    await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

                    # Get page HTML content
                    page_content = await self.playwright_page.content()

                    # Extract sub-comments
                    sub_comments = self._page_extractor.extract_tieba_note_sub_comments(
                        page_content, parent_comment=parment_comment
                    )

                    if not sub_comments:
                        utils.logger.info(
                            f"[BaiduTieBaClient.get_comments_all_sub_comments] "
                            f"Comment {parment_comment.comment_id} page {current_page} has no sub-comments, stopping crawl"
                        )
                        break

                    if callback:
                        await callback(parment_comment.note_id, sub_comments)

                    all_sub_comments.extend(sub_comments)
                    await asyncio.sleep(crawl_interval)
                    current_page += 1

                except Exception as e:
                    utils.logger.error(
                        f"[BaiduTieBaClient.get_comments_all_sub_comments] "
                        f"Failed to get comment {parment_comment.comment_id} page {current_page} sub-comments: {e}"
                    )
                    break

        utils.logger.info(f"[BaiduTieBaClient.get_comments_all_sub_comments] Total retrieved {len(all_sub_comments)} sub-comments")
        return all_sub_comments

    async def get_notes_by_tieba_name(self, tieba_name: str, page_num: int) -> List[TiebaNote]:
        """
        Get post list by Tieba name (uses Playwright to access page, avoiding API detection)
        Args:
            tieba_name: Tieba name
            page_num: Page number

        Returns:
            List[TiebaNote]: Post list
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_notes_by_tieba_name] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based tieba note fetching")

        # Construct Tieba post list URL
        tieba_url = f"{self._host}/f?kw={quote(tieba_name)}&pn={page_num}"
        utils.logger.info(f"[BaiduTieBaClient.get_notes_by_tieba_name] Accessing Tieba page: {tieba_url}")

        try:
            # Use Playwright to access Tieba page
            await self.playwright_page.goto(tieba_url, wait_until="domcontentloaded")

            # Wait for page loading, using delay setting from config file
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # Get page HTML content
            page_content = await self.playwright_page.content()
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_tieba_name] Successfully retrieved Tieba page HTML, length: {len(page_content)}")

            # Extract post list
            notes = self._page_extractor.extract_tieba_note_list(page_content)
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_tieba_name] Extracted {len(notes)} posts")
            return notes

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_notes_by_tieba_name] Failed to get Tieba post list: {e}")
            raise

    async def get_creator_info_by_url(self, creator_url: str) -> str:
        """
        Get creator information by creator URL (uses Playwright to access page, avoiding API detection)
        Args:
            creator_url: Creator homepage URL

        Returns:
            str: Page HTML content
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_creator_info_by_url] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based creator info fetching")

        utils.logger.info(f"[BaiduTieBaClient.get_creator_info_by_url] Accessing creator homepage: {creator_url}")

        try:
            # Use Playwright to access creator homepage
            await self.playwright_page.goto(creator_url, wait_until="domcontentloaded")

            # Wait for page loading, using delay setting from config file
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # Get page HTML content
            page_content = await self.playwright_page.content()
            utils.logger.info(f"[BaiduTieBaClient.get_creator_info_by_url] Successfully retrieved creator homepage HTML, length: {len(page_content)}")

            return page_content

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_creator_info_by_url] Failed to get creator homepage: {e}")
            raise

    async def get_notes_by_creator(self, user_name: str, page_number: int) -> Dict:
        """
        Get creator's posts by creator (uses Playwright to access page, avoiding API detection)
        Args:
            user_name: Creator username
            page_number: Page number

        Returns:
            Dict: Dictionary containing post data
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_notes_by_creator] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based creator notes fetching")

        # Construct creator post list URL
        creator_url = f"{self._host}/home/get/getthread?un={quote(user_name)}&pn={page_number}&id=utf-8&_={utils.get_current_timestamp()}"
        utils.logger.info(f"[BaiduTieBaClient.get_notes_by_creator] Accessing creator post list: {creator_url}")

        try:
            # Use Playwright to access creator post list page
            await self.playwright_page.goto(creator_url, wait_until="domcontentloaded")

            # Wait for page loading, using delay setting from config file
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # Get page content (this API returns JSON)
            page_content = await self.playwright_page.content()

            # Extract JSON data (page will contain <pre> tag or is directly JSON)
            try:
                # Try to extract JSON from page
                json_text = await self.playwright_page.evaluate("() => document.body.innerText")
                result = json.loads(json_text)
                utils.logger.info(f"[BaiduTieBaClient.get_notes_by_creator] Successfully retrieved creator post data")
                return result
            except json.JSONDecodeError as e:
                utils.logger.error(f"[BaiduTieBaClient.get_notes_by_creator] JSON parsing failed: {e}")
                utils.logger.error(f"[BaiduTieBaClient.get_notes_by_creator] Page content: {page_content[:500]}")
                raise Exception(f"Failed to parse JSON from creator notes page: {e}")

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_notes_by_creator] Failed to get creator post list: {e}")
            raise

    async def get_all_notes_by_creator_user_name(
        self,
        user_name: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_note_count: int = 0,
        creator_page_html_content: str = None,
    ) -> List[TiebaNote]:
        """
        Get all creator posts by creator username
        Args:
            user_name: Creator username
            crawl_interval: Crawl delay interval in seconds
            callback: Callback function after one post crawl completes, an awaitable function
            max_note_count: Maximum number of posts to retrieve, if 0 then get all
            creator_page_html_content: Creator homepage HTML content

        Returns:

        """
        # Baidu Tieba is special, the first 10 posts are directly displayed on the homepage and need special handling, cannot be obtained through API
        result: List[TiebaNote] = []
        if creator_page_html_content:
            thread_id_list = (self._page_extractor.extract_tieba_thread_id_list_from_creator_page(creator_page_html_content))
            utils.logger.info(f"[BaiduTieBaClient.get_all_notes_by_creator] got user_name:{user_name} thread_id_list len : {len(thread_id_list)}")
            note_detail_task = [self.get_note_by_id(thread_id) for thread_id in thread_id_list]
            notes = await asyncio.gather(*note_detail_task)
            if callback:
                await callback(notes)
            result.extend(notes)

        notes_has_more = 1
        page_number = 1
        page_per_count = 20
        total_get_count = 0
        while notes_has_more == 1 and (max_note_count == 0 or total_get_count < max_note_count):
            notes_res = await self.get_notes_by_creator(user_name, page_number)
            if not notes_res or notes_res.get("no") != 0:
                utils.logger.error(f"[WeiboClient.get_notes_by_creator] got user_name:{user_name} notes failed, notes_res: {notes_res}")
                break
            notes_data = notes_res.get("data")
            notes_has_more = notes_data.get("has_more")
            notes = notes_data["thread_list"]
            utils.logger.info(f"[WeiboClient.get_all_notes_by_creator] got user_name:{user_name} notes len : {len(notes)}")

            note_detail_task = [self.get_note_by_id(note['thread_id']) for note in notes]
            notes = await asyncio.gather(*note_detail_task)
            if callback:
                await callback(notes)
            await asyncio.sleep(crawl_interval)
            result.extend(notes)
            page_number += 1
            total_get_count += page_per_count
        return result
