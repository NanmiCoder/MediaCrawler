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
        # 使用传入的headers(包含真实浏览器UA)或默认headers
        self.headers = headers or {
            "User-Agent": utils.get_user_agent(),
            "Cookie": "",
        }
        self._host = "https://tieba.baidu.com"
        self._page_extractor = TieBaExtractor()
        self.default_ip_proxy = default_ip_proxy
        self.playwright_page = playwright_page  # Playwright页面对象

    def _sync_request(self, method, url, proxy=None, **kwargs):
        """
        同步的requests请求方法
        Args:
            method: 请求方法
            url: 请求的URL
            proxy: 代理IP
            **kwargs: 其他请求参数

        Returns:
            response对象
        """
        # 构造代理字典
        proxies = None
        if proxy:
            proxies = {
                "http": proxy,
                "https": proxy,
            }

        # 发送请求
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            proxies=proxies,
            timeout=self.timeout,
            **kwargs
        )
        return response

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def request(self, method, url, return_ori_content=False, proxy=None, **kwargs) -> Union[str, Any]:
        """
        封装requests的公共请求方法，对请求响应做一些处理
        Args:
            method: 请求方法
            url: 请求的URL
            return_ori_content: 是否返回原始内容
            proxy: 代理IP
            **kwargs: 其他请求参数，例如请求头、请求体等

        Returns:

        """
        actual_proxy = proxy if proxy else self.default_ip_proxy

        # 在线程池中执行同步的requests请求
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
            res = await self.request(method="GET", url=f"{self._host}{final_uri}", return_ori_content=return_ori_content, **kwargs)
            return res
        except RetryError as e:
            if self.ip_pool:
                proxie_model = await self.ip_pool.get_proxy()
                _, proxy = utils.format_proxy_info(proxie_model)
                res = await self.request(method="GET", url=f"{self._host}{final_uri}", return_ori_content=return_ori_content, proxy=proxy, **kwargs)
                self.default_ip_proxy = proxy
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
        return await self.request(method="POST", url=f"{self._host}{uri}", data=json_str, **kwargs)

    async def pong(self, browser_context: BrowserContext = None) -> bool:
        """
        用于检查登录态是否失效了
        使用Cookie检测而非API调用,避免被检测
        Args:
            browser_context: 浏览器上下文对象

        Returns:
            bool: True表示已登录,False表示未登录
        """
        utils.logger.info("[BaiduTieBaClient.pong] Begin to check tieba login state by cookies...")

        if not browser_context:
            utils.logger.warning("[BaiduTieBaClient.pong] browser_context is None, assume not logged in")
            return False

        try:
            # 从浏览器获取cookies并检查关键登录cookie
            _, cookie_dict = utils.convert_cookies(await browser_context.cookies())

            # 百度贴吧的登录标识: STOKEN 或 PTOKEN
            stoken = cookie_dict.get("STOKEN")
            ptoken = cookie_dict.get("PTOKEN")
            bduss = cookie_dict.get("BDUSS")  # 百度通用登录cookie

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
        API客户端提供的更新cookies方法，一般情况下登录成功后会调用此方法
        Args:
            browser_context: 浏览器上下文对象

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
        根据关键词搜索贴吧帖子 (使用Playwright访问页面,避免API检测)
        Args:
            keyword: 关键词
            page: 分页第几页
            page_size: 每页大小
            sort: 结果排序方式
            note_type: 帖子类型（主题贴｜主题+回复混合模式）
        Returns:

        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_notes_by_keyword] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based search")

        # 构造搜索URL
        # 示例: https://tieba.baidu.com/f/search/res?ie=utf-8&qw=编程
        search_url = f"{self._host}/f/search/res"
        params = {
            "ie": "utf-8",
            "qw": keyword,
            "rn": page_size,
            "pn": page,
            "sm": sort.value,
            "only_thread": note_type.value,
        }

        # 拼接完整URL
        full_url = f"{search_url}?{urlencode(params)}"
        utils.logger.info(f"[BaiduTieBaClient.get_notes_by_keyword] 访问搜索页面: {full_url}")

        try:
            # 使用Playwright访问搜索页面
            await self.playwright_page.goto(full_url, wait_until="domcontentloaded")

            # 等待页面加载,使用配置文件中的延时设置
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # 获取页面HTML内容
            page_content = await self.playwright_page.content()
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_keyword] 成功获取搜索页面HTML,长度: {len(page_content)}")

            # 提取搜索结果
            notes = self._page_extractor.extract_search_note_list(page_content)
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_keyword] 提取到 {len(notes)} 条帖子")
            return notes

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_notes_by_keyword] 搜索失败: {e}")
            raise

    async def get_note_by_id(self, note_id: str) -> TiebaNote:
        """
        根据帖子ID获取帖子详情 (使用Playwright访问页面,避免API检测)
        Args:
            note_id: 帖子ID

        Returns:
            TiebaNote: 帖子详情对象
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_note_by_id] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based note detail fetching")

        # 构造帖子详情URL
        note_url = f"{self._host}/p/{note_id}"
        utils.logger.info(f"[BaiduTieBaClient.get_note_by_id] 访问帖子详情页面: {note_url}")

        try:
            # 使用Playwright访问帖子详情页面
            await self.playwright_page.goto(note_url, wait_until="domcontentloaded")

            # 等待页面加载,使用配置文件中的延时设置
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # 获取页面HTML内容
            page_content = await self.playwright_page.content()
            utils.logger.info(f"[BaiduTieBaClient.get_note_by_id] 成功获取帖子详情HTML,长度: {len(page_content)}")

            # 提取帖子详情
            note_detail = self._page_extractor.extract_note_detail(page_content)
            return note_detail

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_note_by_id] 获取帖子详情失败: {e}")
            raise

    async def get_note_all_comments(
        self,
        note_detail: TiebaNote,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_count: int = 10,
    ) -> List[TiebaComment]:
        """
        获取指定帖子下的所有一级评论 (使用Playwright访问页面,避免API检测)
        Args:
            note_detail: 帖子详情对象
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后的回调函数
            max_count: 一次帖子爬取的最大评论数量
        Returns:
            List[TiebaComment]: 评论列表
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_note_all_comments] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based comment fetching")

        result: List[TiebaComment] = []
        current_page = 1

        while note_detail.total_replay_page >= current_page and len(result) < max_count:
            # 构造评论页URL
            comment_url = f"{self._host}/p/{note_detail.note_id}?pn={current_page}"
            utils.logger.info(f"[BaiduTieBaClient.get_note_all_comments] 访问评论页面: {comment_url}")

            try:
                # 使用Playwright访问评论页面
                await self.playwright_page.goto(comment_url, wait_until="domcontentloaded")

                # 等待页面加载,使用配置文件中的延时设置
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

                # 获取页面HTML内容
                page_content = await self.playwright_page.content()

                # 提取评论
                comments = self._page_extractor.extract_tieba_note_parment_comments(
                    page_content, note_id=note_detail.note_id
                )

                if not comments:
                    utils.logger.info(f"[BaiduTieBaClient.get_note_all_comments] 第{current_page}页没有评论,停止爬取")
                    break

                # 限制评论数量
                if len(result) + len(comments) > max_count:
                    comments = comments[:max_count - len(result)]

                if callback:
                    await callback(note_detail.note_id, comments)

                result.extend(comments)

                # 获取所有子评论
                await self.get_comments_all_sub_comments(
                    comments, crawl_interval=crawl_interval, callback=callback
                )

                await asyncio.sleep(crawl_interval)
                current_page += 1

            except Exception as e:
                utils.logger.error(f"[BaiduTieBaClient.get_note_all_comments] 获取第{current_page}页评论失败: {e}")
                break

        utils.logger.info(f"[BaiduTieBaClient.get_note_all_comments] 共获取 {len(result)} 条一级评论")
        return result

    async def get_comments_all_sub_comments(
        self,
        comments: List[TiebaComment],
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[TiebaComment]:
        """
        获取指定评论下的所有子评论 (使用Playwright访问页面,避免API检测)
        Args:
            comments: 评论列表
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后的回调函数

        Returns:
            List[TiebaComment]: 子评论列表
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
                # 构造子评论URL
                sub_comment_url = (
                    f"{self._host}/p/comment?"
                    f"tid={parment_comment.note_id}&"
                    f"pid={parment_comment.comment_id}&"
                    f"fid={parment_comment.tieba_id}&"
                    f"pn={current_page}"
                )
                utils.logger.info(f"[BaiduTieBaClient.get_comments_all_sub_comments] 访问子评论页面: {sub_comment_url}")

                try:
                    # 使用Playwright访问子评论页面
                    await self.playwright_page.goto(sub_comment_url, wait_until="domcontentloaded")

                    # 等待页面加载,使用配置文件中的延时设置
                    await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

                    # 获取页面HTML内容
                    page_content = await self.playwright_page.content()

                    # 提取子评论
                    sub_comments = self._page_extractor.extract_tieba_note_sub_comments(
                        page_content, parent_comment=parment_comment
                    )

                    if not sub_comments:
                        utils.logger.info(
                            f"[BaiduTieBaClient.get_comments_all_sub_comments] "
                            f"评论{parment_comment.comment_id}第{current_page}页没有子评论,停止爬取"
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
                        f"获取评论{parment_comment.comment_id}第{current_page}页子评论失败: {e}"
                    )
                    break

        utils.logger.info(f"[BaiduTieBaClient.get_comments_all_sub_comments] 共获取 {len(all_sub_comments)} 条子评论")
        return all_sub_comments

    async def get_notes_by_tieba_name(self, tieba_name: str, page_num: int) -> List[TiebaNote]:
        """
        根据贴吧名称获取帖子列表 (使用Playwright访问页面,避免API检测)
        Args:
            tieba_name: 贴吧名称
            page_num: 分页页码

        Returns:
            List[TiebaNote]: 帖子列表
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_notes_by_tieba_name] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based tieba note fetching")

        # 构造贴吧帖子列表URL
        tieba_url = f"{self._host}/f?kw={quote(tieba_name)}&pn={page_num}"
        utils.logger.info(f"[BaiduTieBaClient.get_notes_by_tieba_name] 访问贴吧页面: {tieba_url}")

        try:
            # 使用Playwright访问贴吧页面
            await self.playwright_page.goto(tieba_url, wait_until="domcontentloaded")

            # 等待页面加载,使用配置文件中的延时设置
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # 获取页面HTML内容
            page_content = await self.playwright_page.content()
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_tieba_name] 成功获取贴吧页面HTML,长度: {len(page_content)}")

            # 提取帖子列表
            notes = self._page_extractor.extract_tieba_note_list(page_content)
            utils.logger.info(f"[BaiduTieBaClient.get_notes_by_tieba_name] 提取到 {len(notes)} 条帖子")
            return notes

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_notes_by_tieba_name] 获取贴吧帖子列表失败: {e}")
            raise

    async def get_creator_info_by_url(self, creator_url: str) -> str:
        """
        根据创作者URL获取创作者信息 (使用Playwright访问页面,避免API检测)
        Args:
            creator_url: 创作者主页URL

        Returns:
            str: 页面HTML内容
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_creator_info_by_url] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based creator info fetching")

        utils.logger.info(f"[BaiduTieBaClient.get_creator_info_by_url] 访问创作者主页: {creator_url}")

        try:
            # 使用Playwright访问创作者主页
            await self.playwright_page.goto(creator_url, wait_until="domcontentloaded")

            # 等待页面加载,使用配置文件中的延时设置
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # 获取页面HTML内容
            page_content = await self.playwright_page.content()
            utils.logger.info(f"[BaiduTieBaClient.get_creator_info_by_url] 成功获取创作者主页HTML,长度: {len(page_content)}")

            return page_content

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_creator_info_by_url] 获取创作者主页失败: {e}")
            raise

    async def get_notes_by_creator(self, user_name: str, page_number: int) -> Dict:
        """
        根据创作者获取创作者的帖子 (使用Playwright访问页面,避免API检测)
        Args:
            user_name: 创作者用户名
            page_number: 页码

        Returns:
            Dict: 包含帖子数据的字典
        """
        if not self.playwright_page:
            utils.logger.error("[BaiduTieBaClient.get_notes_by_creator] playwright_page is None, cannot use browser mode")
            raise Exception("playwright_page is required for browser-based creator notes fetching")

        # 构造创作者帖子列表URL
        creator_url = f"{self._host}/home/get/getthread?un={quote(user_name)}&pn={page_number}&id=utf-8&_={utils.get_current_timestamp()}"
        utils.logger.info(f"[BaiduTieBaClient.get_notes_by_creator] 访问创作者帖子列表: {creator_url}")

        try:
            # 使用Playwright访问创作者帖子列表页面
            await self.playwright_page.goto(creator_url, wait_until="domcontentloaded")

            # 等待页面加载,使用配置文件中的延时设置
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            # 获取页面内容(这个接口返回JSON)
            page_content = await self.playwright_page.content()

            # 提取JSON数据(页面会包含<pre>标签或直接是JSON)
            try:
                # 尝试从页面中提取JSON
                json_text = await self.playwright_page.evaluate("() => document.body.innerText")
                result = json.loads(json_text)
                utils.logger.info(f"[BaiduTieBaClient.get_notes_by_creator] 成功获取创作者帖子数据")
                return result
            except json.JSONDecodeError as e:
                utils.logger.error(f"[BaiduTieBaClient.get_notes_by_creator] JSON解析失败: {e}")
                utils.logger.error(f"[BaiduTieBaClient.get_notes_by_creator] 页面内容: {page_content[:500]}")
                raise Exception(f"Failed to parse JSON from creator notes page: {e}")

        except Exception as e:
            utils.logger.error(f"[BaiduTieBaClient.get_notes_by_creator] 获取创作者帖子列表失败: {e}")
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
        根据创作者用户名获取创作者所有帖子
        Args:
            user_name: 创作者用户名
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后的回调函数，是一个awaitable类型的函数
            max_note_count: 帖子最大获取数量，如果为0则获取所有
            creator_page_html_content: 创作者主页HTML内容

        Returns:

        """
        # 百度贴吧比较特殊一些，前10个帖子是直接展示在主页上的，要单独处理，通过API获取不到
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
