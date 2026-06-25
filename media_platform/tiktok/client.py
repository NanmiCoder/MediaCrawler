# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/tiktok/client.py
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
import copy
import json
import urllib.parse
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Union, Optional

import httpx
from playwright.async_api import BrowserContext, Page

from base.base_crawler import AbstractApiClient
from proxy.proxy_mixin import ProxyRefreshMixin
from tools import utils
from tools.httpx_util import make_async_client
from constant.tiktok_constant import TIKTOK_BASE_URL, COMMON_PARAMS
from media_platform.tiktok.exception import DataFetchError

if TYPE_CHECKING:
    from proxy.proxy_ip_pool import ProxyIpPool


class TikTokClient(AbstractApiClient, ProxyRefreshMixin):
    def __init__(
        self,
        timeout=30,
        proxy=None,
        *,
        headers: Dict,
        playwright_page: Optional[Page],
        cookie_dict: Dict,
        proxy_ip_pool: Optional["ProxyIpPool"] = None,
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.headers = headers
        self._host = TIKTOK_BASE_URL
        self.cookie_urls = [
            "https://tiktok.com",
            self._host,
        ]
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        self.init_proxy_pool(proxy_ip_pool)

    async def request(self, method: str, uri: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        """
        Request TikTok API. Uses playwright page context fetch, falling back to httpx if it fails.
        """
        await self._refresh_proxy_if_expired()

        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        clean_params.setdefault("aid", "1988")

        url = f"{self._host}{uri}"
        url_with_params = f"{url}?{urllib.parse.urlencode(clean_params)}"
        body = json.dumps(data) if data else ""

        if self.playwright_page:
            try:
                response = await self.playwright_page.evaluate(
                    """async ({ url, method, body }) => {
                        const headers = { "Accept": "application/json, text/plain, */*" };
                        const options = { method, credentials: "include", headers };
                        if (method === "POST") {
                            headers["Content-Type"] = "application/json;charset=UTF-8";
                            options.body = body;
                        }
                        const resp = await fetch(url, options);
                        const text = await resp.text();
                        return { status: resp.status, text };
                    }""",
                    {"url": url_with_params, "method": method.upper(), "body": body},
                )

                if response["status"] == 200:
                    try:
                        json_data = json.loads(response["text"])
                        return json_data
                    except json.JSONDecodeError as jde:
                        utils.logger.error(f"[TikTokClient.request] JSON decode failed for response (showing first 500 chars): {response['text'][:500]}")
                        raise jde
                else:
                    utils.logger.warn(f"[TikTokClient.request] Browser fetch status={response['status']}, falling back to httpx...")
            except Exception as e:
                utils.logger.error(f"[TikTokClient.request] Browser fetch failed: {e}, falling back to httpx...")

        return await self.request_by_httpx(method, url_with_params, headers=self.headers, data=data)

    async def request_by_httpx(self, method: str, url: str, headers: Dict, data: Optional[Dict] = None) -> Dict:
        cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookie_dict.items())
        req_headers = {
            **headers,
            "Cookie": cookie_str,
            "Referer": "https://www.tiktok.com/",
            "User-Agent": headers.get("User-Agent") or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        async with make_async_client(proxy=self.proxy) as client:
            resp = await client.request(
                method,
                url,
                headers=req_headers,
                json=data if method.upper() == "POST" else None,
                timeout=self.timeout
            )
            if resp.status_code != 200:
                raise DataFetchError(f"Request failed with status {resp.status_code}: {resp.text}")
            return resp.json()

    async def pong(self, browser_context: BrowserContext) -> bool:
        # Check if profile icon is visible in the page DOM
        if self.playwright_page:
            try:
                profile_icon = self.playwright_page.locator('[data-e2e="profile-icon"]')
                if await profile_icon.is_visible():
                    utils.logger.info("[TikTokClient.pong] Profile icon is visible. Already logged in.")
                    return True
            except Exception:
                pass

        # Check cookies as a fallback, but make sure it is a valid session ID (not guest cookies)
        _, cookie_dict = await utils.convert_browser_context_cookies(
            browser_context,
            urls=self.cookie_urls,
        )
        utils.logger.info(f"[TikTokClient.pong] Current cookies keys: {list(cookie_dict.keys())}")
        session_id = cookie_dict.get("sessionid") or cookie_dict.get("sessionid_ss")
        if session_id and len(session_id) > 15:
            return True
        return False


    async def update_cookies(self, browser_context: BrowserContext, urls: Optional[List[str]] = None):
        cookie_str, cookie_dict = await utils.convert_browser_context_cookies(
            browser_context,
            urls=urls or self.cookie_urls,
        )
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def search_video_by_keyword(self, keyword: str, offset: int = 0, count: int = 20):
        return await self.request(
            "GET",
            "/api/search/general/full/",
            params={"keyword": keyword, "offset": offset, "count": count}
        )

    async def get_video_by_id(self, video_id: str):
        return await self.request(
            "GET",
            "/api/item/detail/",
            params={"itemId": video_id}
        )

    async def get_video_comments(self, video_id: str, cursor: int = 0, count: int = 20):
        return await self.request(
            "GET",
            "/api/comment/list/",
            params={"aweme_id": video_id, "cursor": cursor, "count": count}
        )

    async def get_sub_comments(self, video_id: str, comment_id: str, cursor: int = 0, count: int = 20):
        return await self.request(
            "GET",
            "/api/comment/reply/list/",
            params={"item_id": video_id, "comment_id": comment_id, "cursor": cursor, "count": count}
        )

    async def get_user_info(self, unique_id: str):
        return await self.request(
            "GET",
            "/api/user/detail/",
            params={"uniqueId": unique_id}
        )

    async def get_user_aweme_posts(self, sec_user_id: str, max_cursor: str = "", count: int = 18):
        return await self.request(
            "GET",
            "/api/post/item_list/",
            params={"secUid": sec_user_id, "cursor": max_cursor, "count": count}
        )

    async def get_all_user_aweme_posts(self, sec_user_id: str, callback: Optional[Callable] = None) -> List[Dict]:
        result = []
        has_more = True
        max_cursor = "0"
        while has_more:
            res = await self.get_user_aweme_posts(sec_user_id, max_cursor)
            has_more = res.get("hasMore") or res.get("has_more") or False
            max_cursor = str(res.get("cursor", "0"))
            items = res.get("itemList") or res.get("items") or []
            if not items:
                break
            result.extend(items)
            if callback:
                await callback(items)
            await asyncio.sleep(1.0)
        return result

    async def get_hashtag_detail(self, hashtag: str):
        return await self.request(
            "GET",
            "/api/challenge/detail/",
            params={"challengeName": hashtag}
        )

    async def get_hashtag_videos(self, hashtag_id: str, cursor: int = 0, count: int = 20):
        return await self.request(
            "GET",
            "/api/challenge/item_list/",
            params={"challengeID": hashtag_id, "cursor": cursor, "count": count}
        )

    async def get_aweme_media(self, url: str) -> Optional[bytes]:
        try:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookie_dict.items())
            req_headers = {
                "User-Agent": self.headers.get("User-Agent") or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                "Referer": "https://www.tiktok.com/",
                "Cookie": cookie_str
            }
            async with make_async_client(proxy=self.proxy) as client:
                resp = await client.get(url, headers=req_headers, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp.content
                utils.logger.error(f"[TikTokClient.get_aweme_media] download failed status={resp.status_code}")
                return None
        except Exception as e:
            utils.logger.error(f"[TikTokClient.get_aweme_media] download error: {e}")
            return None

    async def resolve_short_url(self, url: str) -> Optional[str]:
        try:
            async with make_async_client(proxy=self.proxy, follow_redirects=False) as client:
                resp = await client.get(url, timeout=self.timeout)
                if resp.status_code in (301, 302):
                    return resp.headers.get("Location")
                return url
        except Exception as e:
            utils.logger.error(f"[TikTokClient.resolve_short_url] error: {e}")
            return None

    async def get_aweme_all_comments(
        self,
        aweme_id: str,
        crawl_interval: float = 1.0,
        is_fetch_sub_comments=False,
        callback: Optional[Callable] = None,
        max_count: int = 10,
    ):
        result = []
        comments_has_more = 1
        comments_cursor = 0
        while comments_has_more and len(result) < max_count:
            comments_res = await self.get_video_comments(aweme_id, comments_cursor)
            comments_has_more = comments_res.get("has_more") or comments_res.get("hasMore") or 0
            comments_cursor = comments_res.get("cursor", 0)
            comments = comments_res.get("comments", [])
            if not comments:
                break
            if len(result) + len(comments) > max_count:
                comments = comments[:max_count - len(result)]
            result.extend(comments)
            if callback:
                await callback(aweme_id, comments)

            await asyncio.sleep(crawl_interval)
            if not is_fetch_sub_comments:
                continue

            for comment in comments:
                reply_comment_total = comment.get("reply_comment_total") or comment.get("replyCommentTotal") or 0
                if reply_comment_total > 0:
                    comment_id = comment.get("cid") or comment.get("comment_id")
                    sub_comments_has_more = 1
                    sub_comments_cursor = 0

                    while sub_comments_has_more:
                        sub_comments_res = await self.get_sub_comments(aweme_id, comment_id, sub_comments_cursor)
                        sub_comments_has_more = sub_comments_res.get("has_more") or sub_comments_res.get("hasMore") or 0
                        sub_comments_cursor = sub_comments_res.get("cursor", 0)
                        sub_comments = sub_comments_res.get("comments", [])

                        if not sub_comments:
                            break
                        result.extend(sub_comments)
                        if callback:
                            await callback(aweme_id, sub_comments)
                        await asyncio.sleep(crawl_interval)
        return result
