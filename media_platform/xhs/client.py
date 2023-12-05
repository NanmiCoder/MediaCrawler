import asyncio
import json
from typing import Dict
from urllib.parse import urlencode

import httpx
from playwright.async_api import BrowserContext, Page

from tools import utils

from .exception import DataFetchError, IPBlockError
from .field import SearchNoteType, SearchSortType
from .help import get_search_id, sign


class XHSClient:
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
        self._host = "https://edith.xiaohongshu.com"
        self.IP_ERROR_STR = "网络连接异常，请检查网络设置或重启试试"
        self.IP_ERROR_CODE = 300012
        self.NOTE_ABNORMAL_STR = "笔记状态异常，请稍后查看"
        self.NOTE_ABNORMAL_CODE = -510001
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict

    async def _pre_headers(self, url: str, data=None):
        encrypt_params = await self.playwright_page.evaluate("([url, data]) => window._webmsxyw(url,data)", [url, data])
        local_storage = await self.playwright_page.evaluate("() => window.localStorage")
        signs = sign(
            a1=self.cookie_dict.get("a1", ""),
            b1=local_storage.get("b1", ""),
            x_s=encrypt_params.get("X-s", ""),
            x_t=str(encrypt_params.get("X-t", ""))
        )

        headers = {
            "X-S": signs["x-s"],
            "X-T": signs["x-t"],
            "x-S-Common": signs["x-s-common"],
            "X-B3-Traceid": signs["x-b3-traceid"]
        }
        self.headers.update(headers)
        return self.headers

    async def request(self, method, url, **kwargs) -> Dict:
        async with httpx.AsyncClient(proxies=self.proxies) as client:
            response = await client.request(
                method, url, timeout=self.timeout,
                **kwargs
            )
        data: Dict = response.json()
        if data["success"]:
            return data.get("data", data.get("success", {}))
        elif data["code"] == self.IP_ERROR_CODE:
            raise IPBlockError(self.IP_ERROR_STR)
        else:
            raise DataFetchError(data.get("msg", None))

    async def get(self, uri: str, params=None) -> Dict:
        final_uri = uri
        if isinstance(params, dict):
            final_uri = (f"{uri}?"
                         f"{urlencode(params)}")
        headers = await self._pre_headers(final_uri)
        return await self.request(method="GET", url=f"{self._host}{final_uri}", headers=headers)

    async def post(self, uri: str, data: dict) -> Dict:
        headers = await self._pre_headers(uri, data)
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        return await self.request(method="POST", url=f"{self._host}{uri}",
                                  data=json_str, headers=headers)

    async def pong(self) -> bool:
        """get a note to check if login state is ok"""
        utils.logger.info("Begin to pong xhs...")
        ping_flag = False
        try:
            note_card: Dict = await self.get_note_by_keyword(keyword="小红书")
            if note_card.get("items"):
                ping_flag = True
        except Exception as e:
            utils.logger.error(f"Ping xhs failed: {e}, and try to login again...")
            ping_flag = False
        return ping_flag

    async def update_cookies(self, browser_context: BrowserContext):
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def get_note_by_keyword(
            self, keyword: str,
            page: int = 1, page_size: int = 20,
            sort: SearchSortType = SearchSortType.GENERAL,
            note_type: SearchNoteType = SearchNoteType.ALL
    ) -> Dict:
        """search note by keyword

        :param keyword: what notes you want to search
        :param page: page number, defaults to 1
        :param page_size: page size, defaults to 20
        :param sort: sort ordering, defaults to SearchSortType.GENERAL
        :param note_type: note type, defaults to SearchNoteType.ALL
        :return: {has_more: true, items: []}
        """
        uri = "/api/sns/web/v1/search/notes"
        data = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": get_search_id(),
            "sort": sort.value,
            "note_type": note_type.value
        }
        return await self.post(uri, data)

    async def get_note_by_id(self, note_id: str) -> Dict:
        """
        :param note_id: note_id you want to fetch
        :return: {"time":1679019883000,"user":{"nickname":"nickname","avatar":"avatar","user_id":"user_id"},"image_list":[{"url":"https://sns-img-qc.xhscdn.com/c8e505ca-4e5f-44be-fe1c-ca0205a38bad","trace_id":"1000g00826s57r6cfu0005ossb1e9gk8c65d0c80","file_id":"c8e505ca-4e5f-44be-fe1c-ca0205a38bad","height":1920,"width":1440}],"tag_list":[{"id":"5be78cdfdb601f000100d0bc","name":"jk","type":"topic"}],"desc":"裙裙","interact_info":{"followed":false,"liked":false,"liked_count":"1732","collected":false,"collected_count":"453","comment_count":"30","share_count":"41"},"at_user_list":[],"last_update_time":1679019884000,"note_id":"6413cf6b00000000270115b5","type":"normal","title":"title"}
        """
        data = {"source_note_id": note_id}
        uri = "/api/sns/web/v1/feed"
        res = await self.post(uri, data)
        if res and res.get("items"):
            res_dict: Dict = res["items"][0]["note_card"]
            return res_dict
        return dict()

    async def get_note_comments(self, note_id: str, cursor: str = "") -> Dict:
        """get note comments
        :param note_id: note id you want to fetch
        :param cursor: last you get cursor, defaults to ""
        :return: {"has_more": true,"cursor": "6422442d000000000700dcdb",comments: [],"user_id": "63273a77000000002303cc9b","time": 1681566542930}
        """
        uri = "/api/sns/web/v2/comment/page"
        params = {
            "note_id": note_id,
            "cursor": cursor
        }
        return await self.get(uri, params)

    async def get_note_sub_comments(
            self, note_id: str,
            root_comment_id: str,
            num: int = 30, cursor: str = ""
    ):
        """
        get note sub comments
        :param note_id: note id you want to fetch
        :param root_comment_id: parent comment id
        :param num: recommend 30, if num greater 30, it only return 30 comments
        :param cursor: last you get cursor, defaults to ""
        :return: {"has_more": true,"cursor": "6422442d000000000700dcdb",comments: [],"user_id": "63273a77000000002303cc9b","time": 1681566542930}
        """
        uri = "/api/sns/web/v2/comment/sub/page"
        params = {
            "note_id": note_id,
            "root_comment_id": root_comment_id,
            "num": num,
            "cursor": cursor,
        }
        return await self.get(uri, params)

    async def get_note_all_comments(self, note_id: str, crawl_interval: float = 1.0, is_fetch_sub_comments=False):
        """
        get note all comments include sub comments
        :param note_id:
        :param crawl_interval:
        :param is_fetch_sub_comments:
        :return:
        """

        result = []
        comments_has_more = True
        comments_cursor = ""
        while comments_has_more:
            comments_res = await self.get_note_comments(note_id, comments_cursor)
            comments_has_more = comments_res.get("has_more", False)
            comments_cursor = comments_res.get("cursor", "")
            # Check if 'comments' key exists in the response
            if "comments" not in comments_res:
                # Handle the absence of 'comments' key appropriately
                # For example, log an error message, break from the loop, etc.
                # This is just an example:
                print(f"No 'comments' key found in response: {comments_res}")
                break
            comments = comments_res["comments"]
            if not is_fetch_sub_comments:
                result.extend(comments)
                continue
            # handle get sub comments
            for comment in comments:
                result.append(comment)
                cur_sub_comment_count = int(comment["sub_comment_count"])
                cur_sub_comments = comment["sub_comments"]
                result.extend(cur_sub_comments)
                sub_comments_has_more = comment["sub_comment_has_more"] and len(
                    cur_sub_comments) < cur_sub_comment_count
                sub_comment_cursor = comment["sub_comment_cursor"]
                while sub_comments_has_more:
                    page_num = 30
                    sub_comments_res = await self.get_note_sub_comments(note_id, comment["id"], num=page_num,
                                                                        cursor=sub_comment_cursor)
                    sub_comments = sub_comments_res["comments"]
                    sub_comments_has_more = sub_comments_res["has_more"] and len(sub_comments) == page_num
                    sub_comment_cursor = sub_comments_res["cursor"]
                    result.extend(sub_comments)
                    await asyncio.sleep(crawl_interval)
            await asyncio.sleep(crawl_interval)
        return result
