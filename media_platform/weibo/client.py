# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/23 15:40
# @Desc    : 微博爬虫 API 请求 client

import asyncio
import copy
import json
import re
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from playwright.async_api import BrowserContext, Page

from tools import utils

from .exception import DataFetchError
from .field import SearchType


class WeiboClient:
    def __init__(
            self,
            timeout=10,
            proxies=None,
            *,
            headers: Dict[str, str],
            playwright_page: Page,
            cookie_dict: Dict[str, str],
    ):
        self.proxies = proxies
        self.timeout = timeout
        self.headers = headers
        self._host = "https://m.weibo.cn"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict

    async def request(self, method, url, **kwargs) -> Any:
        async with httpx.AsyncClient(proxies=self.proxies) as client:
            response = await client.request(
                method, url, timeout=self.timeout,
                **kwargs
            )
        data: Dict = response.json()
        if data.get("ok") != 1:
            utils.logger.error(f"[WeiboClient.request] request {method}:{url} err, res:{data}")
            raise DataFetchError(data.get("msg", "unkonw error"))
        else:
            return data.get("data", {})

    async def get(self, uri: str, params=None, headers=None) -> Dict:
        final_uri = uri
        if isinstance(params, dict):
            final_uri = (f"{uri}?"
                         f"{urlencode(params)}")

        if headers is None:
            headers = self.headers
        return await self.request(method="GET", url=f"{self._host}{final_uri}", headers=headers)

    async def post(self, uri: str, data: dict) -> Dict:
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        return await self.request(method="POST", url=f"{self._host}{uri}",
                                  data=json_str, headers=self.headers)

    async def pong(self) -> bool:
        """get a note to check if login state is ok"""
        utils.logger.info("[WeiboClient.pong] Begin pong weibo...")
        ping_flag = False
        try:
            uri  = "/api/config"
            resp_data: Dict = await self.request(method="GET", url=f"{self._host}{uri}", headers=self.headers)
            if resp_data.get("login"):
                ping_flag = True
            else:
                utils.logger.error(f"[WeiboClient.pong] cookie may be invalid and again login...")
        except Exception as e:
            utils.logger.error(f"[WeiboClient.pong] Pong weibo failed: {e}, and try to login again...")
            ping_flag = False
        return ping_flag

    async def update_cookies(self, browser_context: BrowserContext):
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def get_note_by_keyword(
            self,
            keyword: str,
            page: int = 1,
            search_type: SearchType = SearchType.DEFAULT
    ) -> Dict:
        """
        search note by keyword
        :param keyword: 微博搜搜的关键词
        :param page: 分页参数 -当前页码
        :param search_type: 搜索的类型，见 weibo/filed.py 中的枚举SearchType
        :return:
        """
        uri = "/api/container/getIndex"
        containerid = f"100103type={search_type.value}&q={keyword}"
        params = {
            "containerid": containerid,
            "page_type": "searchall",
            "page": page,
        }
        return await self.get(uri, params)

    async def get_note_comments(self, mid_id: str, max_id: int) -> Dict:
        """get notes comments
        :param mid_id: 微博ID
        :param max_id: 分页参数ID
        :return:
        """
        uri = "/comments/hotflow"
        params = {
            "id": mid_id,
            "mid": mid_id,
            "max_id_type": 0,
        }
        if max_id > 0:
            params.update({"max_id": max_id})

        referer_url = f"https://m.weibo.cn/detail/{mid_id}"
        headers = copy.copy(self.headers)
        headers["Referer"] = referer_url

        return await self.get(uri, params, headers=headers)

    async def get_note_all_comments(self, note_id: str, crawl_interval: float = 1.0, is_fetch_sub_comments=False,
                                    callback: Optional[Callable] = None, ):
        """
        get note all comments include sub comments
        :param note_id:
        :param crawl_interval:
        :param is_fetch_sub_comments:
        :param callback:
        :return:
        """

        result = []
        is_end = False
        max_id = -1
        while not is_end:
            comments_res = await self.get_note_comments(note_id, max_id)
            max_id: int = comments_res.get("max_id")
            comment_list: List[Dict] = comments_res.get("data", [])
            is_end = max_id == 0
            if callback:  # 如果有回调函数，就执行回调函数
                await callback(note_id, comment_list)
            await asyncio.sleep(crawl_interval)
            if not is_fetch_sub_comments:
                result.extend(comment_list)
                continue
            # todo handle get sub comments
        return result

    async def get_note_info_by_id(self, note_id: str) -> Dict:
        """
        根据帖子ID获取详情
        :param note_id:
        :return:
        """
        url = f"{self._host}/detail/{note_id}"
        async with httpx.AsyncClient(proxies=self.proxies) as client:
            response = await client.request(
                "GET", url, timeout=self.timeout, headers=self.headers
            )
            if response.status_code != 200:
                raise DataFetchError(f"get weibo detail err: {response.text}")
            match = re.search(r'var \$render_data = (\[.*?\])\[0\]', response.text, re.DOTALL)
            if match:
                render_data_json = match.group(1)
                render_data_dict = json.loads(render_data_json)
                note_detail = render_data_dict[0].get("status")
                note_item = {
                    "mblog": note_detail
                }
                return note_item
            else:
                utils.logger.info(f"[WeiboClient.get_note_info_by_id] 未找到$render_data的值")
                return dict()
