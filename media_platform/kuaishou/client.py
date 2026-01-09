# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/kuaishou/client.py
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
import asyncio
import json
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from playwright.async_api import BrowserContext, Page

import config
from base.base_crawler import AbstractApiClient
from proxy.proxy_mixin import ProxyRefreshMixin
from tools import utils

if TYPE_CHECKING:
    from proxy.proxy_ip_pool import ProxyIpPool

from .exception import DataFetchError
from .graphql import KuaiShouGraphQL


class KuaiShouClient(AbstractApiClient, ProxyRefreshMixin):
    def __init__(
        self,
        timeout=10,
        proxy=None,
        *,
        headers: Dict[str, str],
        playwright_page: Page,
        cookie_dict: Dict[str, str],
        proxy_ip_pool: Optional["ProxyIpPool"] = None,
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.headers = headers
        self._host = "https://www.kuaishou.com/graphql"
        self._rest_host = "https://www.kuaishou.com"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        self.graphql = KuaiShouGraphQL()
        # Initialize proxy pool (from ProxyRefreshMixin)
        self.init_proxy_pool(proxy_ip_pool)

    async def request(self, method, url, **kwargs) -> Any:
        # Check if proxy is expired before each request
        await self._refresh_proxy_if_expired()

        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)
        data: Dict = response.json()
        if data.get("errors"):
            raise DataFetchError(data.get("errors", "unkonw error"))
        else:
            return data.get("data", {})

    async def get(self, uri: str, params=None) -> Dict:
        final_uri = uri
        if isinstance(params, dict):
            final_uri = f"{uri}?" f"{urlencode(params)}"
        return await self.request(
            method="GET", url=f"{self._host}{final_uri}", headers=self.headers
        )

    async def post(self, uri: str, data: dict) -> Dict:
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return await self.request(
            method="POST", url=f"{self._host}{uri}", data=json_str, headers=self.headers
        )

    async def request_rest_v2(self, uri: str, data: dict) -> Dict:
        """
        Make REST API V2 request (for comment endpoints)
        :param uri: API endpoint path
        :param data: request body
        :return: response data
        """
        await self._refresh_proxy_if_expired()

        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(
                method="POST",
                url=f"{self._rest_host}{uri}",
                data=json_str,
                timeout=self.timeout,
                headers=self.headers,
            )
        result: Dict = response.json()
        if result.get("result") != 1:
            raise DataFetchError(f"REST API V2 error: {result}")
        return result

    async def pong(self) -> bool:
        """get a note to check if login state is ok"""
        utils.logger.info("[KuaiShouClient.pong] Begin pong kuaishou...")
        ping_flag = False
        try:
            post_data = {
                "operationName": "visionProfileUserList",
                "variables": {
                    "ftype": 1,
                },
                "query": self.graphql.get("vision_profile_user_list"),
            }
            res = await self.post("", post_data)
            if res.get("visionProfileUserList", {}).get("result") == 1:
                ping_flag = True
        except Exception as e:
            utils.logger.error(
                f"[KuaiShouClient.pong] Pong kuaishou failed: {e}, and try to login again..."
            )
            ping_flag = False
        return ping_flag

    async def update_cookies(self, browser_context: BrowserContext):
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def search_info_by_keyword(
        self, keyword: str, pcursor: str, search_session_id: str = ""
    ):
        """
        KuaiShou web search api
        :param keyword: search keyword
        :param pcursor: limite page curson
        :param search_session_id: search session id
        :return:
        """
        post_data = {
            "operationName": "visionSearchPhoto",
            "variables": {
                "keyword": keyword,
                "pcursor": pcursor,
                "page": "search",
                "searchSessionId": search_session_id,
            },
            "query": self.graphql.get("search_query"),
        }
        return await self.post("", post_data)

    async def get_video_info(self, photo_id: str) -> Dict:
        """
        Kuaishou web video detail api
        :param photo_id:
        :return:
        """
        post_data = {
            "operationName": "visionVideoDetail",
            "variables": {"photoId": photo_id, "page": "search"},
            "query": self.graphql.get("video_detail"),
        }
        return await self.post("", post_data)

    async def get_video_comments(self, photo_id: str, pcursor: str = "") -> Dict:
        """Get video first-level comments using REST API V2
        :param photo_id: video id you want to fetch
        :param pcursor: pagination cursor, defaults to ""
        :return: dict with rootCommentsV2, pcursorV2, commentCountV2
        """
        post_data = {
            "photoId": photo_id,
            "pcursor": pcursor,
        }
        return await self.request_rest_v2("/rest/v/photo/comment/list", post_data)

    async def get_video_sub_comments(
        self, photo_id: str, root_comment_id: int, pcursor: str = ""
    ) -> Dict:
        """Get video second-level comments using REST API V2
        :param photo_id: video id you want to fetch
        :param root_comment_id: parent comment id (must be int type)
        :param pcursor: pagination cursor, defaults to ""
        :return: dict with subCommentsV2, pcursorV2
        """
        post_data = {
            "photoId": photo_id,
            "pcursor": pcursor,
            "rootCommentId": root_comment_id,  # Must be int type for V2 API
        }
        return await self.request_rest_v2("/rest/v/photo/comment/sublist", post_data)

    async def get_creator_profile(self, userId: str) -> Dict:
        post_data = {
            "operationName": "visionProfile",
            "variables": {"userId": userId},
            "query": self.graphql.get("vision_profile"),
        }
        return await self.post("", post_data)

    async def get_video_by_creater(self, userId: str, pcursor: str = "") -> Dict:
        post_data = {
            "operationName": "visionProfilePhotoList",
            "variables": {"page": "profile", "pcursor": pcursor, "userId": userId},
            "query": self.graphql.get("vision_profile_photo_list"),
        }
        return await self.post("", post_data)

    async def get_video_all_comments(
        self,
        photo_id: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_count: int = 10,
    ):
        """
        Get video all comments including sub comments (V2 REST API)
        :param photo_id: video id
        :param crawl_interval: delay between requests (seconds)
        :param callback: callback function for processing comments
        :param max_count: max number of comments to fetch
        :return: list of all comments
        """

        result = []
        pcursor = ""

        while pcursor != "no_more" and len(result) < max_count:
            comments_res = await self.get_video_comments(photo_id, pcursor)
            # V2 API returns data at top level, not nested in visionCommentList
            pcursor = comments_res.get("pcursorV2", "no_more")
            comments = comments_res.get("rootCommentsV2", [])
            if len(result) + len(comments) > max_count:
                comments = comments[: max_count - len(result)]
            if callback:  # If there is a callback function, execute the callback function
                await callback(photo_id, comments)
            result.extend(comments)
            await asyncio.sleep(crawl_interval)
            sub_comments = await self.get_comments_all_sub_comments(
                comments, photo_id, crawl_interval, callback
            )
            result.extend(sub_comments)
        return result

    async def get_comments_all_sub_comments(
        self,
        comments: List[Dict],
        photo_id,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """
        Get all second-level comments under specified first-level comments (V2 REST API)
        Args:
            comments: Comment list
            photo_id: Video ID
            crawl_interval: Delay unit for crawling comments once (seconds)
            callback: Callback after one comment crawl ends
        Returns:
            List of sub comments
        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            utils.logger.info(
                f"[KuaiShouClient.get_comments_all_sub_comments] Crawling sub_comment mode is not enabled"
            )
            return []

        result = []
        for comment in comments:
            # V2 API uses hasSubComments (boolean) instead of subCommentsPcursor (string)
            has_sub_comments = comment.get("hasSubComments", False)
            if not has_sub_comments:
                continue

            # V2 API uses comment_id (int) instead of commentId (string)
            root_comment_id = comment.get("comment_id")
            if not root_comment_id:
                continue

            sub_comment_pcursor = ""

            while sub_comment_pcursor != "no_more":
                comments_res = await self.get_video_sub_comments(
                    photo_id, root_comment_id, sub_comment_pcursor
                )
                # V2 API returns data at top level
                sub_comment_pcursor = comments_res.get("pcursorV2", "no_more")
                sub_comments = comments_res.get("subCommentsV2", [])

                if callback and sub_comments:
                    await callback(photo_id, sub_comments)
                await asyncio.sleep(crawl_interval)
                result.extend(sub_comments)
        return result

    async def get_creator_info(self, user_id: str) -> Dict:
        """
        eg: https://www.kuaishou.com/profile/3x4jtnbfter525a
        Kuaishou user homepage
        """

        visionProfile = await self.get_creator_profile(user_id)
        return visionProfile.get("userProfile")

    async def get_all_videos_by_creator(
        self,
        user_id: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """
        Get all posts published by the specified user, this method will continue to find all post information under a user
        Args:
            user_id: User ID
            crawl_interval: Delay unit for crawling once (seconds)
            callback: Update callback function after one page crawl ends
        Returns:

        """
        result = []
        pcursor = ""

        while pcursor != "no_more":
            videos_res = await self.get_video_by_creater(user_id, pcursor)
            if not videos_res:
                utils.logger.error(
                    f"[KuaiShouClient.get_all_videos_by_creator] The current creator may have been banned by ks, so they cannot access the data."
                )
                break

            vision_profile_photo_list = videos_res.get("visionProfilePhotoList", {})
            pcursor = vision_profile_photo_list.get("pcursor", "")

            videos = vision_profile_photo_list.get("feeds", [])
            utils.logger.info(
                f"[KuaiShouClient.get_all_videos_by_creator] got user_id:{user_id} videos len : {len(videos)}"
            )

            if callback:
                await callback(videos)
            await asyncio.sleep(crawl_interval)
            result.extend(videos)
        return result
