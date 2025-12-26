# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/zhihu/client.py
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
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from httpx import Response
from playwright.async_api import BrowserContext, Page
from tenacity import retry, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractApiClient
from constant import zhihu as zhihu_constant
from model.m_zhihu import ZhihuComment, ZhihuContent, ZhihuCreator
from proxy.proxy_mixin import ProxyRefreshMixin
from tools import utils

if TYPE_CHECKING:
    from proxy.proxy_ip_pool import ProxyIpPool

from .exception import DataFetchError, ForbiddenError
from .field import SearchSort, SearchTime, SearchType
from .help import ZhihuExtractor, sign


class ZhiHuClient(AbstractApiClient, ProxyRefreshMixin):

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
        self.default_headers = headers
        self.cookie_dict = cookie_dict
        self._extractor = ZhihuExtractor()
        # Initialize proxy pool (from ProxyRefreshMixin)
        self.init_proxy_pool(proxy_ip_pool)

    async def _pre_headers(self, url: str) -> Dict:
        """
        Sign request headers
        Args:
            url: Request URL with query parameters
        Returns:

        """
        d_c0 = self.cookie_dict.get("d_c0")
        if not d_c0:
            raise Exception("d_c0 not found in cookies")
        sign_res = sign(url, self.default_headers["cookie"])
        headers = self.default_headers.copy()
        headers['x-zst-81'] = sign_res["x-zst-81"]
        headers['x-zse-96'] = sign_res["x-zse-96"]
        return headers

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def request(self, method, url, **kwargs) -> Union[str, Any]:
        """
        Wrapper for httpx common request method with response handling
        Args:
            method: Request method
            url: Request URL
            **kwargs: Other request parameters such as headers, body, etc.

        Returns:

        """
        # Check if proxy is expired before each request
        await self._refresh_proxy_if_expired()

        # return response.text
        return_response = kwargs.pop('return_response', False)

        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if response.status_code != 200:
            utils.logger.error(f"[ZhiHuClient.request] Requset Url: {url}, Request error: {response.text}")
            if response.status_code == 403:
                raise ForbiddenError(response.text)
            elif response.status_code == 404:  # Content without comments also returns 404
                return {}

            raise DataFetchError(response.text)

        if return_response:
            return response.text
        try:
            data: Dict = response.json()
            if data.get("error"):
                utils.logger.error(f"[ZhiHuClient.request] Request error: {data}")
                raise DataFetchError(data.get("error", {}).get("message"))
            return data
        except json.JSONDecodeError:
            utils.logger.error(f"[ZhiHuClient.request] Request error: {response.text}")
            raise DataFetchError(response.text)

    async def get(self, uri: str, params=None, **kwargs) -> Union[Response, Dict, str]:
        """
        GET request with header signing
        Args:
            uri: Request URI
            params: Request parameters

        Returns:

        """
        final_uri = uri
        if isinstance(params, dict):
            final_uri += '?' + urlencode(params)
        headers = await self._pre_headers(final_uri)
        base_url = (zhihu_constant.ZHIHU_URL if "/p/" not in uri else zhihu_constant.ZHIHU_ZHUANLAN_URL)
        return await self.request(method="GET", url=base_url + final_uri, headers=headers, **kwargs)

    async def pong(self) -> bool:
        """
        Check if login status is still valid
        Returns:

        """
        utils.logger.info("[ZhiHuClient.pong] Begin to pong zhihu...")
        ping_flag = False
        try:
            res = await self.get_current_user_info()
            if res.get("uid") and res.get("name"):
                ping_flag = True
                utils.logger.info("[ZhiHuClient.pong] Ping zhihu successfully")
            else:
                utils.logger.error(f"[ZhiHuClient.pong] Ping zhihu failed, response data: {res}")
        except Exception as e:
            utils.logger.error(f"[ZhiHuClient.pong] Ping zhihu failed: {e}, and try to login again...")
            ping_flag = False
        return ping_flag

    async def update_cookies(self, browser_context: BrowserContext):
        """
        Update cookies method provided by API client, typically called after successful login
        Args:
            browser_context: Browser context object

        Returns:

        """
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.default_headers["cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def get_current_user_info(self) -> Dict:
        """
        Get current logged-in user information
        Returns:

        """
        params = {"include": "email,is_active,is_bind_phone"}
        return await self.get("/api/v4/me", params)

    async def get_note_by_keyword(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        sort: SearchSort = SearchSort.DEFAULT,
        note_type: SearchType = SearchType.DEFAULT,
        search_time: SearchTime = SearchTime.DEFAULT,
    ) -> List[ZhihuContent]:
        """
        Search by keyword
        Args:
            keyword: Search keyword
            page: Page number
            page_size: Page size
            sort: Sorting method
            note_type: Search result type
            search_time: Time range for search results

        Returns:

        """
        uri = "/api/v4/search_v3"
        params = {
            "gk_version": "gz-gaokao",
            "t": "general",
            "q": keyword,
            "correction": 1,
            "offset": (page - 1) * page_size,
            "limit": page_size,
            "filter_fields": "",
            "lc_idx": (page - 1) * page_size,
            "show_all_topics": 0,
            "search_source": "Filter",
            "time_interval": search_time.value,
            "sort": sort.value,
            "vertical": note_type.value,
        }
        search_res = await self.get(uri, params)
        utils.logger.info(f"[ZhiHuClient.get_note_by_keyword] Search result: {search_res}")
        return self._extractor.extract_contents_from_search(search_res)

    async def get_root_comments(
        self,
        content_id: str,
        content_type: str,
        offset: str = "",
        limit: int = 10,
        order_by: str = "score",
    ) -> Dict:
        """
        Get root-level comments for content
        Args:
            content_id: Content ID
            content_type: Content type (answer, article, zvideo)
            offset:
            limit:
            order_by:

        Returns:

        """
        uri = f"/api/v4/comment_v5/{content_type}s/{content_id}/root_comment"
        params = {"order": order_by, "offset": offset, "limit": limit}
        return await self.get(uri, params)
        # uri = f"/api/v4/{content_type}s/{content_id}/root_comments"
        # params = {
        #     "order": order_by,
        #     "offset": offset,
        #     "limit": limit
        # }
        # return await self.get(uri, params)

    async def get_child_comments(
        self,
        root_comment_id: str,
        offset: str = "",
        limit: int = 10,
        order_by: str = "sort",
    ) -> Dict:
        """
        Get child comments under a root comment
        Args:
            root_comment_id:
            offset:
            limit:
            order_by:

        Returns:

        """
        uri = f"/api/v4/comment_v5/comment/{root_comment_id}/child_comment"
        params = {
            "order": order_by,
            "offset": offset,
            "limit": limit,
        }
        return await self.get(uri, params)

    async def get_note_all_comments(
        self,
        content: ZhihuContent,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[ZhihuComment]:
        """
        Get all root-level comments for a specified post, this method will retrieve all comment information under a post
        Args:
            content: Content detail object (question|article|video)
            crawl_interval: Crawl delay interval in seconds
            callback: Callback after completing one crawl

        Returns:

        """
        result: List[ZhihuComment] = []
        is_end: bool = False
        offset: str = ""
        limit: int = 10
        while not is_end:
            root_comment_res = await self.get_root_comments(content.content_id, content.content_type, offset, limit)
            if not root_comment_res:
                break
            paging_info = root_comment_res.get("paging", {})
            is_end = paging_info.get("is_end")
            offset = self._extractor.extract_offset(paging_info)
            comments = self._extractor.extract_comments(content, root_comment_res.get("data"))

            if not comments:
                break

            if callback:
                await callback(comments)

            result.extend(comments)
            await self.get_comments_all_sub_comments(content, comments, crawl_interval=crawl_interval, callback=callback)
            await asyncio.sleep(crawl_interval)
        return result

    async def get_comments_all_sub_comments(
        self,
        content: ZhihuContent,
        comments: List[ZhihuComment],
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[ZhihuComment]:
        """
        Get all sub-comments under specified comments
        Args:
            content: Content detail object (question|article|video)
            comments: Comment list
            crawl_interval: Crawl delay interval in seconds
            callback: Callback after completing one crawl

        Returns:

        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            return []

        all_sub_comments: List[ZhihuComment] = []
        for parment_comment in comments:
            if parment_comment.sub_comment_count == 0:
                continue

            is_end: bool = False
            offset: str = ""
            limit: int = 10
            while not is_end:
                child_comment_res = await self.get_child_comments(parment_comment.comment_id, offset, limit)
                if not child_comment_res:
                    break
                paging_info = child_comment_res.get("paging", {})
                is_end = paging_info.get("is_end")
                offset = self._extractor.extract_offset(paging_info)
                sub_comments = self._extractor.extract_comments(content, child_comment_res.get("data"))

                if not sub_comments:
                    break

                if callback:
                    await callback(sub_comments)

                all_sub_comments.extend(sub_comments)
                await asyncio.sleep(crawl_interval)
        return all_sub_comments

    async def get_creator_info(self, url_token: str) -> Optional[ZhihuCreator]:
        """
        Get creator information
        Args:
            url_token:

        Returns:

        """
        uri = f"/people/{url_token}"
        html_content: str = await self.get(uri, return_response=True)
        return self._extractor.extract_creator(url_token, html_content)

    async def get_creator_answers(self, url_token: str, offset: int = 0, limit: int = 20) -> Dict:
        """
        Get creator's answers
        Args:
            url_token:
            offset:
            limit:

        Returns:


        """
        uri = f"/api/v4/members/{url_token}/answers"
        params = {
            "include":
            "data[*].is_normal,admin_closed_comment,reward_info,is_collapsed,annotation_action,annotation_detail,collapse_reason,collapsed_by,suggest_edit,comment_count,can_comment,content,editable_content,attachment,voteup_count,reshipment_settings,comment_permission,created_time,updated_time,review_info,excerpt,paid_info,reaction_instruction,is_labeled,label_info,relationship.is_authorized,voting,is_author,is_thanked,is_nothelp;data[*].vessay_info;data[*].author.badge[?(type=best_answerer)].topics;data[*].author.vip_info;data[*].question.has_publishing_draft,relationship",
            "offset": offset,
            "limit": limit,
            "order_by": "created"
        }
        return await self.get(uri, params)

    async def get_creator_articles(self, url_token: str, offset: int = 0, limit: int = 20) -> Dict:
        """
        Get creator's articles
        Args:
            url_token:
            offset:
            limit:

        Returns:

        """
        uri = f"/api/v4/members/{url_token}/articles"
        params = {
            "include":
            "data[*].comment_count,suggest_edit,is_normal,thumbnail_extra_info,thumbnail,can_comment,comment_permission,admin_closed_comment,content,voteup_count,created,updated,upvoted_followees,voting,review_info,reaction_instruction,is_labeled,label_info;data[*].vessay_info;data[*].author.badge[?(type=best_answerer)].topics;data[*].author.vip_info;",
            "offset": offset,
            "limit": limit,
            "order_by": "created"
        }
        return await self.get(uri, params)

    async def get_creator_videos(self, url_token: str, offset: int = 0, limit: int = 20) -> Dict:
        """
        Get creator's videos
        Args:
            url_token:
            offset:
            limit:

        Returns:

        """
        uri = f"/api/v4/members/{url_token}/zvideos"
        params = {
            "include": "similar_zvideo,creation_relationship,reaction_instruction",
            "offset": offset,
            "limit": limit,
            "similar_aggregation": "true",
        }
        return await self.get(uri, params)

    async def get_all_anwser_by_creator(self, creator: ZhihuCreator, crawl_interval: float = 1.0, callback: Optional[Callable] = None) -> List[ZhihuContent]:
        """
        Get all answers by creator
        Args:
            creator: Creator information
            crawl_interval: Crawl delay interval in seconds
            callback: Callback after completing one crawl

        Returns:

        """
        all_contents: List[ZhihuContent] = []
        is_end: bool = False
        offset: int = 0
        limit: int = 20
        while not is_end:
            res = await self.get_creator_answers(creator.url_token, offset, limit)
            if not res:
                break
            utils.logger.info(f"[ZhiHuClient.get_all_anwser_by_creator] Get creator {creator.url_token} answers: {res}")
            paging_info = res.get("paging", {})
            is_end = paging_info.get("is_end")
            contents = self._extractor.extract_content_list_from_creator(res.get("data"))
            if callback:
                await callback(contents)
            all_contents.extend(contents)
            offset += limit
            await asyncio.sleep(crawl_interval)
        return all_contents

    async def get_all_articles_by_creator(
        self,
        creator: ZhihuCreator,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[ZhihuContent]:
        """
        Get all articles by creator
        Args:
            creator:
            crawl_interval:
            callback:

        Returns:

        """
        all_contents: List[ZhihuContent] = []
        is_end: bool = False
        offset: int = 0
        limit: int = 20
        while not is_end:
            res = await self.get_creator_articles(creator.url_token, offset, limit)
            if not res:
                break
            paging_info = res.get("paging", {})
            is_end = paging_info.get("is_end")
            contents = self._extractor.extract_content_list_from_creator(res.get("data"))
            if callback:
                await callback(contents)
            all_contents.extend(contents)
            offset += limit
            await asyncio.sleep(crawl_interval)
        return all_contents

    async def get_all_videos_by_creator(
        self,
        creator: ZhihuCreator,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[ZhihuContent]:
        """
        Get all videos by creator
        Args:
            creator:
            crawl_interval:
            callback:

        Returns:

        """
        all_contents: List[ZhihuContent] = []
        is_end: bool = False
        offset: int = 0
        limit: int = 20
        while not is_end:
            res = await self.get_creator_videos(creator.url_token, offset, limit)
            if not res:
                break
            paging_info = res.get("paging", {})
            is_end = paging_info.get("is_end")
            contents = self._extractor.extract_content_list_from_creator(res.get("data"))
            if callback:
                await callback(contents)
            all_contents.extend(contents)
            offset += limit
            await asyncio.sleep(crawl_interval)
        return all_contents

    async def get_answer_info(
        self,
        question_id: str,
        answer_id: str,
    ) -> Optional[ZhihuContent]:
        """
        Get answer information
        Args:
            question_id:
            answer_id:

        Returns:

        """
        uri = f"/question/{question_id}/answer/{answer_id}"
        response_html = await self.get(uri, return_response=True)
        return self._extractor.extract_answer_content_from_html(response_html)

    async def get_article_info(self, article_id: str) -> Optional[ZhihuContent]:
        """
        Get article information
        Args:
            article_id:

        Returns:

        """
        uri = f"/p/{article_id}"
        response_html = await self.get(uri, return_response=True)
        return self._extractor.extract_article_content_from_html(response_html)

    async def get_video_info(self, video_id: str) -> Optional[ZhihuContent]:
        """
        Get video information
        Args:
            video_id:

        Returns:

        """
        uri = f"/zvideo/{video_id}"
        response_html = await self.get(uri, return_response=True)
        return self._extractor.extract_zvideo_content_from_html(response_html)
