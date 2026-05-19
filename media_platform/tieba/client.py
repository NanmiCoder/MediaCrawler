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
import hashlib
import json
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode, quote, parse_qs, unquote, urlparse

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

PC_SIGN_SECRET = "36770b1f34c9bbf2e7d1a99d2b82fa9e"


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
        self.cookie_urls = [self._host]
        self._page_extractor = TieBaExtractor()
        self.default_ip_proxy = default_ip_proxy
        self.playwright_page = playwright_page  # Playwright page object
        self._pc_tbs = ""

    @staticmethod
    def _sign_pc_params(params: Dict[str, Any]) -> str:
        sign_text = ""
        for key in sorted(params):
            if key in {"sign", "sig"} or params[key] is None:
                continue
            sign_text += f"{key}={params[key]}"
        sign_text += PC_SIGN_SECRET
        return hashlib.md5(sign_text.encode("utf-8")).hexdigest()

    async def _ensure_tieba_origin(self) -> None:
        if not self.playwright_page:
            raise Exception("playwright_page is required for tieba PC API requests")
        if not self.playwright_page.url.startswith(self._host):
            await self.playwright_page.goto(self._host, wait_until="domcontentloaded")

    async def _fetch_json_by_browser(
        self,
        uri: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        use_sign: bool = False,
    ) -> Dict:
        """
        Fetch current Tieba PC JSON APIs from the browser context.
        These APIs rely on logged-in browser cookies and Baidu's PC signing
        convention, while Python requests can be blocked by local proxy/TLS.
        """
        await self._ensure_tieba_origin()
        params = {k: v for k, v in (params or {}).items() if v is not None}
        data = {k: v for k, v in (data or {}).items() if v is not None}
        if use_sign:
            sign_source = data if method.upper() == "POST" else params
            sign_source.setdefault("subapp_type", "pc")
            sign_source.setdefault("_client_type", "20")
            sign_source["sign"] = self._sign_pc_params(sign_source)

        url = f"{self._host}{uri}"
        if params:
            url = f"{url}?{urlencode(params)}"
        body = urlencode(data) if data else ""
        response = await self.playwright_page.evaluate(
            """async ({ url, method, body }) => {
                const headers = { "Accept": "application/json, text/plain, */*" };
                const options = { method, credentials: "include", headers };
                if (method === "POST") {
                    headers["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8";
                    options.body = body;
                }
                const resp = await fetch(url, options);
                const text = await resp.text();
                return { status: resp.status, text };
            }""",
            {"url": url, "method": method.upper(), "body": body},
        )
        if response["status"] != 200:
            raise Exception(f"Tieba PC API failed, status={response['status']}, url={url}")
        try:
            json_data = json.loads(response["text"])
        except json.JSONDecodeError as exc:
            raise Exception(f"Tieba PC API returned non-JSON, url={url}, body={response['text'][:500]}") from exc
        error_code = json_data.get("error_code", json_data.get("no", 0))
        if str(error_code) not in {"0", "None"}:
            raise Exception(f"Tieba PC API error, url={url}, response={json_data}")
        return json_data

    async def _get_pc_tbs(self) -> str:
        if self._pc_tbs:
            return self._pc_tbs
        sync_data = await self._fetch_json_by_browser(
            "/c/s/pc/sync",
            params={"subapp_type": "pc", "_client_type": "20"},
            use_sign=True,
        )
        self._pc_tbs = (
            sync_data.get("data", {})
            .get("anti", {})
            .get("tbs", "")
        )
        if not self._pc_tbs:
            raise Exception(f"Can not get Tieba tbs from pc sync API: {sync_data}")
        return self._pc_tbs

    async def _get_pc_page_data(self, note_id: str, page: int = 1) -> Dict:
        tbs = await self._get_pc_tbs()
        return await self._fetch_json_by_browser(
            "/c/f/pb/page_pc",
            method="POST",
            data={
                "pn": page,
                "lz": 0,
                "r": 2,
                "mark_type": 0,
                "back": 0,
                "fr": "",
                "kz": note_id,
                "session_request_times": 1,
                "tbs": tbs,
                "subapp_type": "pc",
                "_client_type": "20",
            },
            use_sign=True,
        )

    @staticmethod
    def _extract_creator_portrait(creator_url: str) -> str:
        creator_url = (creator_url or "").strip()
        if not creator_url:
            return ""
        if not creator_url.startswith(("http://", "https://")):
            return creator_url.split("?")[0]
        parsed = urlparse(creator_url)
        query = parse_qs(parsed.query)
        portrait = (
            query.get("id", [""])[0]
            or query.get("portrait", [""])[0]
            or query.get("un", [""])[0]
        )
        return unquote(portrait).split("?")[0]

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
            _, cookie_dict = await utils.convert_browser_context_cookies(
                browser_context,
                urls=self.cookie_urls,
            )

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

    async def update_cookies(self, browser_context: BrowserContext, urls: Optional[list[str]] = None):
        """
        Update cookies method provided by API client, usually called after successful login
        Args:
            browser_context: Browser context object

        Returns:

        """
        cookie_str, cookie_dict = await utils.convert_browser_context_cookies(
            browser_context,
            urls=urls or self.cookie_urls,
        )
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

        params = {
            "rn": max(page_size, 20),
            "st": sort.value,
            "word": keyword,
            "needbrand": 1,
            "sug_type": 2,
            "pn": page,
            "come_from": "search",
            "subapp_type": "pc",
            "_client_type": "20",
        }
        utils.logger.info(
            f"[BaiduTieBaClient.get_notes_by_keyword] Accessing search API: "
            f"{self._host}/mo/q/search/multsearch?{urlencode(params)}"
        )

        try:
            api_data = await self._fetch_json_by_browser(
                "/mo/q/search/multsearch",
                params=params,
                use_sign=True,
            )
            notes = self._page_extractor.extract_search_note_list_from_api(api_data)[:page_size]
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

        utils.logger.info(f"[BaiduTieBaClient.get_note_by_id] Accessing post detail API, note_id: {note_id}")

        try:
            api_data = await self._get_pc_page_data(note_id=note_id, page=1)
            note_detail = self._page_extractor.extract_note_detail_from_api(api_data)
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
            utils.logger.info(
                f"[BaiduTieBaClient.get_note_all_comments] Accessing comment API, "
                f"note_id: {note_detail.note_id}, page: {current_page}"
            )

            try:
                api_data = await self._get_pc_page_data(note_id=note_detail.note_id, page=current_page)
                comments = self._page_extractor.extract_tieba_note_parent_comments_from_api(
                    api_data, note_detail=note_detail
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
        Get post list by Tieba name from current PC forum JSON API.
        Args:
            tieba_name: Tieba name
            page_num: Page number

        Returns:
            List[TiebaNote]: Post list
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_notes_by_tieba_name] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based tieba note fetching")

        page_size = 30
        api_page = page_num // page_size + 1
        tbs = await self._get_pc_tbs()
        utils.logger.info(
            f"[BaiduTieBaClient.get_notes_by_tieba_name] Accessing Tieba FRS API, "
            f"tieba_name: {tieba_name}, page: {api_page}"
        )

        try:
            api_data = await self._fetch_json_by_browser(
                "/c/f/frs/page_pc",
                method="POST",
                data={
                    "kw": quote(tieba_name),
                    "pn": api_page,
                    "sort_type": -1,
                    "is_newfrs": 1,
                    "is_newfeed": 1,
                    "rn": page_size,
                    "rn_need": 10,
                    "tbs": tbs,
                    "subapp_type": "pc",
                    "_client_type": "20",
                },
                use_sign=True,
            )
            notes = self._page_extractor.extract_tieba_note_list_from_frs_api(api_data)[:page_size]
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_tieba_name] Extracted {len(notes)} posts")
            return notes

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_notes_by_tieba_name] Failed to get Tieba post list: {e}")
            raise

    async def get_creator_info_by_url(self, creator_url: str) -> TiebaCreator:
        """
        Get creator information by creator URL from current PC JSON API.
        Args:
            creator_url: Creator homepage URL

        Returns:
            TiebaCreator: Creator information
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_creator_info_by_url] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based creator info fetching")

        portrait = self._extract_creator_portrait(creator_url)
        if not portrait:
            raise Exception(f"Can not extract Tieba creator portrait from url: {creator_url}")

        utils.logger.info(
            f"[BaiduTieBaClient.get_creator_info_by_url] Accessing creator info API, portrait: {portrait}"
        )

        try:
            api_data = await self._fetch_json_by_browser(
                "/c/u/pc/homeSidebarRight",
                params={
                    "portrait": portrait,
                    "un": "",
                    "subapp_type": "pc",
                    "_client_type": "20",
                },
                use_sign=True,
            )
            return self._page_extractor.extract_creator_info_from_api(api_data)

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_creator_info_by_url] Failed to get creator info: {e}")
            raise

    async def get_notes_by_creator_portrait(
        self, portrait: str, page_number: int, page_size: int = 20
    ) -> Dict:
        """
        Get creator's thread feed by creator portrait from current PC JSON API.
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_notes_by_creator_portrait] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based creator notes fetching")

        utils.logger.info(
            f"[BaiduTieBaClient.get_notes_by_creator_portrait] Accessing creator feed API, "
            f"portrait: {portrait}, page: {page_number}"
        )
        return await self._fetch_json_by_browser(
            "/c/u/feed/myThread",
            params={
                "pn": page_number,
                "rn": page_size,
                "portrait": portrait,
                "type": 1,
                "un": "",
                "subapp_type": "pc",
                "_client_type": "20",
            },
            use_sign=True,
        )

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
                utils.logger.error(f"[TieBaClient.get_notes_by_creator] got user_name:{user_name} notes failed, notes_res: {notes_res}")
                break
            notes_data = notes_res.get("data")
            notes_has_more = notes_data.get("has_more")
            notes = notes_data["thread_list"]
            utils.logger.info(f"[TieBaClient.get_all_notes_by_creator] got user_name:{user_name} notes len : {len(notes)}")

            note_detail_task = [self.get_note_by_id(note['thread_id']) for note in notes]
            notes = await asyncio.gather(*note_detail_task)
            if callback:
                await callback(notes)
            await asyncio.sleep(crawl_interval)
            result.extend(notes)
            page_number += 1
            total_get_count += page_per_count
        return result

    async def get_all_notes_by_creator_url(
        self,
        creator_url: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_note_count: int = 0,
    ) -> List[TiebaNote]:
        """
        Get all creator posts by current PC creator feed API.
        """
        portrait = self._extract_creator_portrait(creator_url)
        if not portrait:
            raise Exception(f"Can not extract Tieba creator portrait from url: {creator_url}")

        result: List[TiebaNote] = []
        page_number = 1
        page_size = 20

        while max_note_count == 0 or len(result) < max_note_count:
            notes_res = await self.get_notes_by_creator_portrait(
                portrait=portrait,
                page_number=page_number,
                page_size=page_size,
            )
            thread_id_list = self._page_extractor.extract_creator_thread_id_list_from_api(notes_res)
            if not thread_id_list:
                utils.logger.info(
                    f"[BaiduTieBaClient.get_all_notes_by_creator_url] "
                    f"Creator portrait:{portrait} page:{page_number} has no threads"
                )
                break

            if max_note_count:
                thread_id_list = thread_id_list[: max_note_count - len(result)]

            utils.logger.info(
                f"[BaiduTieBaClient.get_all_notes_by_creator_url] "
                f"got portrait:{portrait} thread ids len: {len(thread_id_list)}"
            )
            note_detail_task = [self.get_note_by_id(thread_id) for thread_id in thread_id_list]
            notes = await asyncio.gather(*note_detail_task)
            notes = [note for note in notes if note]
            if callback and notes:
                await callback(notes)
            result.extend(notes)

            data = notes_res.get("data", {})
            has_more = int(data.get("has_more") or 0)
            if not has_more:
                break

            await asyncio.sleep(crawl_interval)
            page_number += 1

        return result
