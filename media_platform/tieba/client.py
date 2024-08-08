import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from playwright.async_api import BrowserContext
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractApiClient
from model.m_baidu_tieba import TiebaComment, TiebaNote
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
    ):
        self.ip_pool: Optional[ProxyIpPool] = ip_pool
        self.timeout = timeout
        self.headers = {
            "User-Agent": utils.get_user_agent(),
            "Cookies": "",
        }
        self._host = "https://tieba.baidu.com"
        self._page_extractor = TieBaExtractor()
        self.default_ip_proxy = default_ip_proxy

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def request(self, method, url, return_ori_content=False, proxies=None, **kwargs) -> Union[str, Any]:
        """
        封装httpx的公共请求方法，对请求响应做一些处理
        Args:
            method: 请求方法
            url: 请求的URL
            return_ori_content: 是否返回原始内容
            proxies: 代理IP
            **kwargs: 其他请求参数，例如请求头、请求体等

        Returns:

        """
        actual_proxies = proxies if proxies else self.default_ip_proxy
        async with httpx.AsyncClient(proxies=actual_proxies) as client:
            response = await client.request(
                method, url, timeout=self.timeout,
                headers=self.headers, **kwargs
            )

        if response.status_code != 200:
            utils.logger.error(f"Request failed, method: {method}, url: {url}, status code: {response.status_code}")
            utils.logger.error(f"Request failed, response: {response.text}")
            raise Exception(f"Request failed, method: {method}, url: {url}, status code: {response.status_code}")

        if response.text == "" or response.text == "blocked":
            utils.logger.error(f"request params incrr, response.text: {response.text}")
            raise Exception("account blocked")

        if return_ori_content:
            return response.text

        return response.json()

    async def get(self, uri: str, params=None, return_ori_content=False, **kwargs) -> Any:
        """
        GET请求，对请求头签名
        Args:
            uri: 请求路由
            params: 请求参数
            return_ori_content: 是否返回原始内容

        Returns:

        """
        final_uri = uri
        if isinstance(params, dict):
            final_uri = (f"{uri}?"
                         f"{urlencode(params)}")
        try:
            res = await self.request(method="GET", url=f"{self._host}{final_uri}",
                                     return_ori_content=return_ori_content,
                                     **kwargs)
            return res
        except RetryError as e:
            if self.ip_pool:
                proxie_model = await self.ip_pool.get_proxy()
                _, proxies = utils.format_proxy_info(proxie_model)
                res = await self.request(method="GET", url=f"{self._host}{final_uri}",
                                         return_ori_content=return_ori_content,
                                         proxies=proxies,
                                         **kwargs)
                self.default_ip_proxy = proxies
                return res

            utils.logger.error(f"[BaiduTieBaClient.get] 达到了最大重试次数，IP已经被Block，请尝试更换新的IP代理: {e}")
            raise Exception(f"[BaiduTieBaClient.get] 达到了最大重试次数，IP已经被Block，请尝试更换新的IP代理: {e}")

    async def post(self, uri: str, data: dict, **kwargs) -> Dict:
        """
        POST请求，对请求头签名
        Args:
            uri: 请求路由
            data: 请求体参数

        Returns:

        """
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        return await self.request(method="POST", url=f"{self._host}{uri}",
                                  data=json_str, **kwargs)

    async def pong(self) -> bool:
        """
        用于检查登录态是否失效了
        Returns:

        """
        utils.logger.info("[BaiduTieBaClient.pong] Begin to pong tieba...")
        try:
            uri = "/mo/q/sync"
            res: Dict = await self.get(uri)
            utils.logger.info(f"[BaiduTieBaClient.pong] res: {res}")
            if res and res.get("no") == 0:
                ping_flag = True
            else:
                utils.logger.info(f"[BaiduTieBaClient.pong] user not login, will try to login again...")
                ping_flag = False
        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.pong] Ping tieba failed: {e}, and try to login again...")
            ping_flag = False
        return ping_flag

    async def update_cookies(self, browser_context: BrowserContext):
        """
        API客户端提供的更新cookies方法，一般情况下登录成功后会调用此方法
        Args:
            browser_context: 浏览器上下文对象

        Returns:

        """
        pass

    async def get_notes_by_keyword(
            self, keyword: str,
            page: int = 1,
            page_size: int = 10,
            sort: SearchSortType = SearchSortType.TIME_DESC,
            note_type: SearchNoteType = SearchNoteType.FIXED_THREAD,
    ) -> List[TiebaNote]:
        """
        根据关键词搜索贴吧帖子
        Args:
            keyword: 关键词
            page: 分页第几页
            page_size: 每页大小
            sort: 结果排序方式
            note_type: 帖子类型（主题贴｜主题+回复混合模式）
        Returns:

        """
        uri = "/f/search/res"
        params = {
            "isnew": 1,
            "qw": keyword,
            "rn": page_size,
            "pn": page,
            "sm": sort.value,
            "only_thread": note_type.value
        }
        page_content = await self.get(uri, params=params, return_ori_content=True)
        return self._page_extractor.extract_search_note_list(page_content)

    async def get_note_by_id(self, note_id: str) -> TiebaNote:
        """
        根据帖子ID获取帖子详情
        Args:
            note_id:

        Returns:

        """
        uri = f"/p/{note_id}"
        page_content = await self.get(uri, return_ori_content=True)
        return self._page_extractor.extract_note_detail(page_content)

    async def get_note_all_comments(self, note_detail: TiebaNote, crawl_interval: float = 1.0,
                                    callback: Optional[Callable] = None) -> List[TiebaComment]:
        """
        获取指定帖子下的所有一级评论，该方法会一直查找一个帖子下的所有评论信息
        Args:
            note_detail: 帖子详情对象
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后

        Returns:

        """
        uri = f"/p/{note_detail.note_id}"
        result: List[TiebaComment] = []
        current_page = 1
        while note_detail.total_replay_page >= current_page:
            params = {
                "pn": current_page
            }
            page_content = await self.get(uri, params=params, return_ori_content=True)
            comments = self._page_extractor.extract_tieba_note_parment_comments(page_content,
                                                                                note_id=note_detail.note_id)
            if not comments:
                break
            if callback:
                await callback(note_detail.note_id, comments)
            result.extend(comments)
            # 获取所有子评论
            await self.get_comments_all_sub_comments(comments, crawl_interval=crawl_interval, callback=callback)
            await asyncio.sleep(crawl_interval)
            current_page += 1
        return result

    async def get_comments_all_sub_comments(self, comments: List[TiebaComment], crawl_interval: float = 1.0,
                                            callback: Optional[Callable] = None) -> List[TiebaComment]:
        """
        获取指定评论下的所有子评论
        Args:
            comments: 评论列表
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后

        Returns:

        """
        uri = "/p/comment"
        if not config.ENABLE_GET_SUB_COMMENTS:
            return []

        # # 贴吧获取所有子评论需要登录态
        # if self.headers.get("Cookies") == "" or not self.pong():
        #     raise Exception(f"[BaiduTieBaClient.pong] Cookies is empty, please login first...")

        all_sub_comments: List[TiebaComment] = []
        for parment_comment in comments:
            if parment_comment.sub_comment_count == 0:
                continue

            current_page = 1
            max_sub_page_num = parment_comment.sub_comment_count // 10 + 1
            while max_sub_page_num >= current_page:
                params = {
                    "tid": parment_comment.note_id,  # 帖子ID
                    "pid": parment_comment.comment_id,  # 父级评论ID
                    "fid": parment_comment.tieba_id,  # 贴吧ID
                    "pn": current_page  # 页码
                }
                page_content = await self.get(uri, params=params, return_ori_content=True)
                sub_comments = self._page_extractor.extract_tieba_note_sub_comments(page_content,
                                                                                    parent_comment=parment_comment)

                if not sub_comments:
                    break
                if callback:
                    await callback(parment_comment.note_id, sub_comments)
                all_sub_comments.extend(sub_comments)
                await asyncio.sleep(crawl_interval)
                current_page += 1
        return all_sub_comments



    async def get_notes_by_tieba_name(self, tieba_name: str, page_num: int) -> List[TiebaNote]:
        """
        根据贴吧名称获取帖子列表
        Args:
            tieba_name: 贴吧名称
            page_num: 分页数量

        Returns:

        """
        uri = f"/f?kw={tieba_name}&pn={page_num}"
        page_content = await self.get(uri, return_ori_content=True)
        return self._page_extractor.extract_tieba_note_list(page_content)
