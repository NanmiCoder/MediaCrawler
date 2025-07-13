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
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 18:44
# @Desc    : B站爬虫

import asyncio
import os
import random
from asyncio import Task
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import pandas as pd

from playwright.async_api import (BrowserContext, BrowserType, Page, Playwright, async_playwright)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import bilibili as bilibili_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import BilibiliClient
from .exception import DataFetchError
from .field import SearchOrderType
from .help import resolve_any_video_url_to_id, resolve_any_user_url_to_id
from .login import BilibiliLogin


class BilibiliCrawler(AbstractCrawler):
    context_page: Page
    bili_client: BilibiliClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self):
        self.index_url = "https://www.bilibili.com"
        self.user_agent = utils.get_user_agent()
        self.cdp_manager = None

    async def start(self):
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(
                ip_proxy_info)

        async with async_playwright() as playwright:
            # 根据配置选择启动模式
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[BilibiliCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright, playwright_proxy_format, self.user_agent,
                    headless=config.CDP_HEADLESS
                )
            else:
                utils.logger.info("[BilibiliCrawler] 使用标准模式启动浏览器")
                # Launch a browser context.
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    None,
                    self.user_agent,
                    headless=config.HEADLESS
                )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            # Create a client to interact with the xiaohongshu website.
            self.bili_client = await self.create_bilibili_client(httpx_proxy_format)
            if not await self.bili_client.pong():
                login_obj = BilibiliLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # your phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()
                await self.bili_client.update_cookies(browser_context=self.browser_context)

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for video and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_videos()
            elif config.CRAWLER_TYPE == "creator":
                # 检查是否有配置的创作者信息，如果没有则提示用户交互式输入
                if not config.BILI_CREATOR_ID_LIST:
                    await self._interactive_creator_input()
                
                # 智能解析创作者输入
                resolved_creator_ids = []
                for creator_input in config.BILI_CREATOR_ID_LIST:
                    creator_id = await self._process_creator_input(creator_input)
                    if creator_id:
                        resolved_creator_ids.append(creator_id)
                
                # 去重处理
                resolved_creator_ids = list(set(resolved_creator_ids))
                utils.logger.info(f"[BilibiliCrawler.creator] 解析得到的创作者ID: {resolved_creator_ids}")
                
                if config.CREATOR_MODE:
                    for creator_id in resolved_creator_ids:
                        await self.get_creator_videos(int(creator_id))
                else:
                    # 转换为int类型的列表
                    creator_int_ids = [int(cid) for cid in resolved_creator_ids if cid.isdigit()]
                    await self.get_all_creator_details(creator_int_ids)
            else:
                pass
            utils.logger.info(
                "[BilibiliCrawler.start] Bilibili Crawler finished ...")

    @staticmethod
    async def get_pubtime_datetime(start: str = config.START_DAY, end: str = config.END_DAY) -> Tuple[str, str]:
        """
        获取 bilibili 作品发布日期起始时间戳 pubtime_begin_s 与发布日期结束时间戳 pubtime_end_s
        ---
        :param start: 发布日期起始时间，YYYY-MM-DD
        :param end: 发布日期结束时间，YYYY-MM-DD
        
        Note
        ---
        - 搜索的时间范围为 start 至 end，包含 start 和 end
        - 若要搜索同一天的内容，为了包含 start 当天的搜索内容，则 pubtime_end_s 的值应该为 pubtime_begin_s 的值加上一天再减去一秒，即 start 当天的最后一秒
            - 如仅搜索 2024-01-05 的内容，pubtime_begin_s = 1704384000，pubtime_end_s = 1704470399
              转换为可读的 datetime 对象：pubtime_begin_s = datetime.datetime(2024, 1, 5, 0, 0)，pubtime_end_s = datetime.datetime(2024, 1, 5, 23, 59, 59)
        - 若要搜索 start 至 end 的内容，为了包含 end 当天的搜索内容，则 pubtime_end_s 的值应该为 pubtime_end_s 的值加上一天再减去一秒，即 end 当天的最后一秒
            - 如搜索 2024-01-05 - 2024-01-06 的内容，pubtime_begin_s = 1704384000，pubtime_end_s = 1704556799
              转换为可读的 datetime 对象：pubtime_begin_s = datetime.datetime(2024, 1, 5, 0, 0)，pubtime_end_s = datetime.datetime(2024, 1, 6, 23, 59, 59)
        """
        # 转换 start 与 end 为 datetime 对象
        start_day: datetime = datetime.strptime(start, '%Y-%m-%d')
        end_day: datetime = datetime.strptime(end, '%Y-%m-%d')
        if start_day > end_day:
            raise ValueError('Wrong time range, please check your start and end argument, to ensure that the start cannot exceed end')
        elif start_day == end_day:  # 搜索同一天的内容
            end_day = start_day + timedelta(days=1) - timedelta(seconds=1)  # 则将 end_day 设置为 start_day + 1 day - 1 second
        else:  # 搜索 start 至 end
            end_day = end_day + timedelta(days=1) - timedelta(seconds=1)  # 则将 end_day 设置为 end_day + 1 day - 1 second
        # 将其重新转换为时间戳
        return str(int(start_day.timestamp())), str(int(end_day.timestamp()))

    async def search(self):
        """
        search bilibili video with keywords
        :return:
        """
        utils.logger.info("[BilibiliCrawler.search] Begin search bilibli keywords")
        
        # 检查是否有搜索关键词，如果没有则提示用户交互式输入
        if not config.KEYWORDS or config.KEYWORDS.strip() == "":
            await self._interactive_search_input()
        
        bili_limit_count = 20  # bilibili limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < bili_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = bili_limit_count
        start_page = config.START_PAGE  # start page number
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[BilibiliCrawler.search] Current search keyword: {keyword}")
            # 每个关键词最多返回 1000 条数据
            if not config.ALL_DAY:
                page = 1
                while (page - start_page + 1) * bili_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                    if page < start_page:
                        utils.logger.info(f"[BilibiliCrawler.search] Skip page: {page}")
                        page += 1
                        continue

                    utils.logger.info(f"[BilibiliCrawler.search] search bilibili keyword: {keyword}, page: {page}")
                    video_id_list: List[str] = []
                    videos_res = await self.bili_client.search_video_by_keyword(
                        keyword=keyword,
                        page=page,
                        page_size=bili_limit_count,
                        order=SearchOrderType.DEFAULT,
                        pubtime_begin_s=0,  # 作品发布日期起始时间戳
                        pubtime_end_s=0  # 作品发布日期结束日期时间戳
                    )
                    video_list: List[Dict] = videos_res.get("result")

                    semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                    task_list = []
                    try:
                        task_list = [self.get_video_info_task(aid=video_item.get("aid"), bvid="", semaphore=semaphore) for video_item in video_list]
                    except Exception as e:
                        utils.logger.warning(f"[BilibiliCrawler.search] error in the task list. The video for this page will not be included. {e}")
                    video_items = await asyncio.gather(*task_list)
                    for video_item in video_items:
                        if video_item:
                            video_id_list.append(video_item.get("View").get("aid"))
                            await bilibili_store.update_bilibili_video(video_item)
                            await bilibili_store.update_up_info(video_item)
                            await self.get_bilibili_video(video_item, semaphore)
                    page += 1
                    await self.batch_get_video_comments(video_id_list)
            # 按照 START_DAY 至 END_DAY 按照每一天进行筛选，这样能够突破 1000 条视频的限制，最大程度爬取该关键词下每一天的所有视频
            else:
                for day in pd.date_range(start=config.START_DAY, end=config.END_DAY, freq='D'):
                    # 按照每一天进行爬取的时间戳参数
                    pubtime_begin_s, pubtime_end_s = await self.get_pubtime_datetime(start=day.strftime('%Y-%m-%d'), end=day.strftime('%Y-%m-%d'))
                    page = 1
                    #!该段 while 语句在发生异常时（通常情况下为当天数据为空时）会自动跳转到下一天，以实现最大程度爬取该关键词下当天的所有视频
                    #!除了仅保留现在原有的 try, except Exception 语句外，不要再添加其他的异常处理！！！否则将使该段代码失效，使其仅能爬取当天一天数据而无法跳转到下一天
                    #!除非将该段代码的逻辑进行重构以实现相同的功能，否则不要进行修改！！！
                    while (page - start_page + 1) * bili_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                        #! Catch any error if response return nothing, go to next day
                        try:
                            #! Don't skip any page, to make sure gather all video in one day
                            # if page < start_page:
                            #     utils.logger.info(f"[BilibiliCrawler.search] Skip page: {page}")
                            #     page += 1
                            #     continue

                            utils.logger.info(f"[BilibiliCrawler.search] search bilibili keyword: {keyword}, date: {day.ctime()}, page: {page}")
                            video_id_list: List[str] = []
                            videos_res = await self.bili_client.search_video_by_keyword(
                                keyword=keyword,
                                page=page,
                                page_size=bili_limit_count,
                                order=SearchOrderType.DEFAULT,
                                pubtime_begin_s=pubtime_begin_s,  # 作品发布日期起始时间戳
                                pubtime_end_s=pubtime_end_s  # 作品发布日期结束日期时间戳
                            )
                            video_list: List[Dict] = videos_res.get("result")

                            semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                            task_list = [self.get_video_info_task(aid=video_item.get("aid"), bvid="", semaphore=semaphore) for video_item in video_list]
                            video_items = await asyncio.gather(*task_list)
                            for video_item in video_items:
                                if video_item:
                                    video_id_list.append(video_item.get("View").get("aid"))
                                    await bilibili_store.update_bilibili_video(video_item)
                                    await bilibili_store.update_up_info(video_item)
                                    await self.get_bilibili_video(video_item, semaphore)
                            page += 1
                            await self.batch_get_video_comments(video_id_list)
                        # go to next day
                        except Exception as e:
                            print(e)
                            break

    async def batch_get_video_comments(self, video_id_list: List[str]):
        """
        batch get video comments
        :param video_id_list:
        :return:
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(
                f"[BilibiliCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        utils.logger.info(
            f"[BilibiliCrawler.batch_get_video_comments] video ids:{video_id_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for video_id in video_id_list:
            task = asyncio.create_task(self.get_comments(
                video_id, semaphore), name=video_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments(self, video_id: str, semaphore: asyncio.Semaphore):
        """
        get comment for video id
        :param video_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                utils.logger.info(
                    f"[BilibiliCrawler.get_comments] begin get video_id: {video_id} comments ...")
                await self.bili_client.get_video_all_comments(
                    video_id=video_id,
                    crawl_interval=random.random(),
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=bilibili_store.batch_update_bilibili_video_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_comments] get video_id: {video_id} comment error: {ex}")
            except Exception as e:
                utils.logger.error(
                    f"[BilibiliCrawler.get_comments] may be been blocked, err:{e}")

    async def get_creator_videos(self, creator_id: int):
        """
        get videos for a creator
        :return:
        """
        ps = 30
        pn = 1
        while True:
            result = await self.bili_client.get_creator_videos(creator_id, pn, ps)
            video_bvids_list = [video["bvid"] for video in result["list"]["vlist"]]
            await self.get_specified_videos(video_bvids_list)
            if int(result["page"]["count"]) <= pn * ps:
                break
            await asyncio.sleep(random.random())
            pn += 1

    async def get_specified_videos(self, bvids_list: List[str] = None):
        """
        get specified videos info
        :return:
        """
        # 如果没有传入参数，使用配置中的列表
        if bvids_list is None:
            # 检查是否有配置的视频信息，如果没有则提示用户交互式输入
            if not config.BILI_SPECIFIED_ID_LIST:
                await self._interactive_detail_input()
            
            # 智能解析视频输入
            resolved_video_ids = []
            for video_input in config.BILI_SPECIFIED_ID_LIST:
                video_id = await self._process_video_input(video_input)
                if video_id:
                    resolved_video_ids.append(video_id)
            
            # 去重处理
            resolved_video_ids = list(set(resolved_video_ids))
            utils.logger.info(f"[BilibiliCrawler.get_specified_videos] 解析得到的视频ID: {resolved_video_ids}")
            bvids_list = resolved_video_ids
        
        if not bvids_list:
            utils.logger.warning("[BilibiliCrawler.get_specified_videos] No valid video IDs resolved")
            return
        
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_video_info_task(aid=0, bvid=video_id, semaphore=semaphore) for video_id in
            bvids_list
        ]
        video_details = await asyncio.gather(*task_list)
        video_aids_list = []
        for video_detail in video_details:
            if video_detail is not None:
                video_item_view: Dict = video_detail.get("View")
                video_aid: str = video_item_view.get("aid")
                if video_aid:
                    video_aids_list.append(video_aid)
                await bilibili_store.update_bilibili_video(video_detail)
                await bilibili_store.update_up_info(video_detail)
                await self.get_bilibili_video(video_detail, semaphore)
        await self.batch_get_video_comments(video_aids_list)

    async def get_video_info_task(self, aid: int, bvid: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """
        Get video detail task
        :param aid:
        :param bvid:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                result = await self.bili_client.get_video_info(aid=aid, bvid=bvid)
                return result
            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_video_info_task] Get video detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_video_info_task] have not fund note detail video_id:{bvid}, err: {ex}")
                return None

    async def get_video_play_url_task(self, aid: int, cid: int, semaphore: asyncio.Semaphore) -> Union[Dict, None]:
        """
                Get video play url
                :param aid:
                :param cid:
                :param semaphore:
                :return:
                """
        async with semaphore:
            try:
                result = await self.bili_client.get_video_play_url(aid=aid, cid=cid)
                return result
            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_video_play_url_task] Get video play url error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_video_play_url_task] have not fund play url from :{aid}|{cid}, err: {ex}")
                return None

    async def create_bilibili_client(self, httpx_proxy: Optional[str]) -> BilibiliClient:
        """
        create bilibili client
        :param httpx_proxy: httpx proxy
        :return: bilibili client
        """
        utils.logger.info(
            "[BilibiliCrawler.create_bilibili_client] Begin create bilibili API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        bilibili_client_obj = BilibiliClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://www.bilibili.com",
                "Referer": "https://www.bilibili.com",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return bilibili_client_obj

    @staticmethod
    def format_proxy_info(ip_proxy_info: IpInfoModel) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        format proxy info for playwright and httpx
        :param ip_proxy_info: ip proxy info
        :return: playwright proxy, httpx proxy
        """
        playwright_proxy = {
            "server": f"{ip_proxy_info.protocol}{ip_proxy_info.ip}:{ip_proxy_info.port}",
            "username": ip_proxy_info.user,
            "password": ip_proxy_info.password,
        }
        httpx_proxy = {
            f"{ip_proxy_info.protocol}": f"http://{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"
        }
        return playwright_proxy, httpx_proxy

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """ 
        launch browser and create browser context
        :param chromium: chromium browser
        :param playwright_proxy: playwright proxy
        :param user_agent: user agent
        :param headless: headless mode
        :return: browser context
        """
        utils.logger.info(
            "[BilibiliCrawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
            # feat issue #14
            # we will save login state to avoid login every time
            user_data_dir = os.path.join(os.getcwd(), "browser_data",
                                         config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context
        else:
            # type: ignore
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context

    async def launch_browser_with_cdp(self, playwright: Playwright, playwright_proxy: Optional[Dict],
                                     user_agent: Optional[str], headless: bool = True) -> BrowserContext:
        """
        使用CDP模式启动浏览器
        """
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless
            )

            # 显示浏览器信息
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[BilibiliCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[BilibiliCrawler] CDP模式启动失败，回退到标准模式: {e}")
            # 回退到标准模式
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self):
        """Close browser context"""
        # 如果使用CDP模式，需要特殊处理
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[BilibiliCrawler.close] Browser context closed ...")

    async def get_bilibili_video(self, video_item: Dict, semaphore: asyncio.Semaphore):
        """
        download bilibili video
        :param video_item:
        :param semaphore:
        :return:
        """
        if not config.ENABLE_GET_IMAGES:
            utils.logger.info(f"[BilibiliCrawler.get_bilibili_video] Crawling image mode is not enabled")
            return
        video_item_view: Dict = video_item.get("View")
        aid = video_item_view.get("aid")
        cid = video_item_view.get("cid")
        result = await self.get_video_play_url_task(aid, cid, semaphore)
        if result is None:
            utils.logger.info("[BilibiliCrawler.get_bilibili_video] get video play url failed")
            return
        durl_list = result.get("durl")
        max_size = -1
        video_url = ""
        for durl in durl_list:
            size = durl.get("size")
            if size > max_size:
                max_size = size
                video_url = durl.get("url")
        if video_url == "":
            utils.logger.info("[BilibiliCrawler.get_bilibili_video] get video url failed")
            return

        content = await self.bili_client.get_video_media(video_url)
        if content is None:
            return
        extension_file_name = f"video.mp4"
        await bilibili_store.store_video(aid, content, extension_file_name)

    async def get_all_creator_details(self, creator_id_list: List[int]):
        """
        creator_id_list: get details for creator from creator_id_list
        """
        utils.logger.info(
            f"[BilibiliCrawler.get_creator_details] Crawling the detalis of creator")
        utils.logger.info(
            f"[BilibiliCrawler.get_creator_details] creator ids:{creator_id_list}")

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        try:
            for creator_id in creator_id_list:
                task = asyncio.create_task(self.get_creator_details(
                    creator_id, semaphore), name=creator_id)
                task_list.append(task)
        except Exception as e:
            utils.logger.warning(
                f"[BilibiliCrawler.get_all_creator_details] error in the task list. The creator will not be included. {e}")

        await asyncio.gather(*task_list)

    async def get_creator_details(self, creator_id: int, semaphore: asyncio.Semaphore):
        """
        get details for creator id
        :param creator_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            creator_unhandled_info: Dict = await self.bili_client.get_creator_info(creator_id)
            creator_info: Dict = {
                "id": creator_id,
                "name": creator_unhandled_info.get("name"),
                "sign": creator_unhandled_info.get("sign"),
                "avatar": creator_unhandled_info.get("face"),
            }
        await self.get_fans(creator_info, semaphore)
        await self.get_followings(creator_info, semaphore)
        await self.get_dynamics(creator_info, semaphore)

    async def get_fans(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """
        get fans for creator id
        :param creator_info:
        :param semaphore:
        :return:
        """
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                utils.logger.info(
                    f"[BilibiliCrawler.get_fans] begin get creator_id: {creator_id} fans ...")
                await self.bili_client.get_creator_all_fans(
                    creator_info=creator_info,
                    crawl_interval=random.random(),
                    callback=bilibili_store.batch_update_bilibili_creator_fans,
                    max_count=config.CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_fans] get creator_id: {creator_id} fans error: {ex}")
            except Exception as e:
                utils.logger.error(
                    f"[BilibiliCrawler.get_fans] may be been blocked, err:{e}")

    async def get_followings(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """
        get followings for creator id
        :param creator_info:
        :param semaphore:
        :return:
        """
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                utils.logger.info(
                    f"[BilibiliCrawler.get_followings] begin get creator_id: {creator_id} followings ...")
                await self.bili_client.get_creator_all_followings(
                    creator_info=creator_info,
                    crawl_interval=random.random(),
                    callback=bilibili_store.batch_update_bilibili_creator_followings,
                    max_count=config.CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_followings] get creator_id: {creator_id} followings error: {ex}")
            except Exception as e:
                utils.logger.error(
                    f"[BilibiliCrawler.get_followings] may be been blocked, err:{e}")

    async def get_dynamics(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """
        get dynamics for creator id
        :param creator_info:
        :param semaphore:
        :return:
        """
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                utils.logger.info(
                    f"[BilibiliCrawler.get_dynamics] begin get creator_id: {creator_id} dynamics ...")
                await self.bili_client.get_creator_all_dynamics(
                    creator_info=creator_info,
                    crawl_interval=random.random(),
                    callback=bilibili_store.batch_update_bilibili_creator_dynamics,
                    max_count=config.CRAWLER_MAX_DYNAMICS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_dynamics] get creator_id: {creator_id} dynamics error: {ex}")
            except Exception as e:
                utils.logger.error(
                    f"[BilibiliCrawler.get_dynamics] may be been blocked, err:{e}")
    
    async def _interactive_search_input(self) -> None:
        """
        交互式输入搜索关键词
        """
        print("\n" + "="*60)
        print("🔍 B站搜索模式")
        print("="*60)
        print("请输入搜索关键词：")
        print("1. 支持单个关键词：编程")
        print("2. 支持多个关键词（空格分隔）：编程 科技 教程")
        print("-"*60)
        
        user_input = input("请输入搜索关键词 (回车键结束): ").strip()
        
        if user_input:
            config.KEYWORDS = user_input.replace(" ", ",")
            utils.logger.info(f"[BilibiliCrawler._interactive_search_input] 已设置搜索关键词: {config.KEYWORDS}")
        else:
            utils.logger.warning("[BilibiliCrawler._interactive_search_input] 未输入任何搜索关键词，将退出程序")
            raise ValueError("未输入任何搜索关键词")
    
    async def _interactive_detail_input(self) -> None:
        """
        交互式输入视频详情信息
        """
        print("\n" + "="*60)
        print("📹 B站视频详情爬取模式")
        print("="*60)
        print("请输入视频信息，支持以下格式：")
        print("1. 完整URL: https://www.bilibili.com/video/BV1Q2MXzgEgW")
        print("2. 短链接: https://b23.tv/B6gPE4M")
        print("3. BVID: BV1Q2MXzgEgW")
        print("4. AID: 12345678")
        print("5. 多个URL用空格分隔")
        print("-"*60)
        
        user_input = input("请输入视频URL或ID (回车键结束): ").strip()
        
        if user_input:
            # 分割多个URL
            video_inputs = user_input.split()
            config.BILI_SPECIFIED_ID_LIST.extend(video_inputs)
            utils.logger.info(f"[BilibiliCrawler._interactive_detail_input] 已添加 {len(video_inputs)} 个视频")
        else:
            utils.logger.warning("[BilibiliCrawler._interactive_detail_input] 未输入任何视频信息，将退出程序")
            raise ValueError("未输入任何视频信息")
    
    async def _interactive_creator_input(self) -> None:
        """
        交互式输入创作者信息
        """
        print("\n" + "="*60)
        print("🎯 B站创作者爬取模式")
        print("="*60)
        print("请输入创作者信息，支持以下格式：")
        print("1. 完整URL: https://space.bilibili.com/449342345")
        print("2. 短链接: https://b23.tv/9ljhRio")
        print("3. UID: 449342345")
        print("4. 多个URL用空格分隔")
        print("-"*60)
        
        user_input = input("请输入创作者URL或UID (回车键结束): ").strip()
        
        if user_input:
            # 分割多个URL
            creator_inputs = user_input.split()
            config.BILI_CREATOR_ID_LIST.extend(creator_inputs)
            utils.logger.info(f"[BilibiliCrawler._interactive_creator_input] 已添加 {len(creator_inputs)} 个创作者")
        else:
            utils.logger.warning("[BilibiliCrawler._interactive_creator_input] 未输入任何创作者信息，将退出程序")
            raise ValueError("未输入任何创作者信息")

    async def _process_video_input(self, video_input: str) -> str:
        """
        处理视频输入，支持智能URL解析
        如果解析失败，回退到基础解析
        """
        try:
            utils.logger.info(f"[BilibiliCrawler._process_video_input] 开始解析视频输入: {video_input}")
            
            # 智能解析
            video_id = await resolve_any_video_url_to_id(video_input, self.context_page)
            if video_id:
                utils.logger.info(f"[BilibiliCrawler._process_video_input] 解析成功，video_id: {video_id}")
                return video_id
            else:
                # 回退到基础解析
                utils.logger.info(f"[BilibiliCrawler._process_video_input] 智能解析失败，尝试基础解析")
                from .help import extract_bvid_from_url, extract_aid_from_url
                basic_bvid = extract_bvid_from_url(video_input)
                if basic_bvid:
                    utils.logger.info(f"[BilibiliCrawler._process_video_input] 基础解析成功，BVID: {basic_bvid}")
                    return basic_bvid
                    
                basic_aid = extract_aid_from_url(video_input)
                if basic_aid:
                    utils.logger.info(f"[BilibiliCrawler._process_video_input] 基础解析成功，AID: {basic_aid}")
                    return basic_aid
                    
                utils.logger.warning(f"[BilibiliCrawler._process_video_input] 无法解析视频输入: {video_input}")
                return ""
        except Exception as e:
            utils.logger.error(f"[BilibiliCrawler._process_video_input] 解析视频输入时发生错误: {e}")
            # 尝试基础解析作为后备
            try:
                from .help import extract_bvid_from_url, extract_aid_from_url
                basic_bvid = extract_bvid_from_url(video_input)
                if basic_bvid:
                    utils.logger.info(f"[BilibiliCrawler._process_video_input] 后备解析成功，BVID: {basic_bvid}")
                    return basic_bvid
                    
                basic_aid = extract_aid_from_url(video_input)
                if basic_aid:
                    utils.logger.info(f"[BilibiliCrawler._process_video_input] 后备解析成功，AID: {basic_aid}")
                    return basic_aid
            except:
                pass
            return ""

    async def _process_creator_input(self, creator_input: str) -> str:
        """
        处理创作者输入，支持智能URL解析
        如果解析失败，回退到基础解析
        """
        try:
            utils.logger.info(f"[BilibiliCrawler._process_creator_input] 开始解析创作者输入: {creator_input}")
            
            # 智能解析
            creator_id = await resolve_any_user_url_to_id(creator_input, self.context_page)
            if creator_id:
                utils.logger.info(f"[BilibiliCrawler._process_creator_input] 解析成功，creator_id: {creator_id}")
                return creator_id
            else:
                # 回退到基础解析
                utils.logger.info(f"[BilibiliCrawler._process_creator_input] 智能解析失败，尝试基础解析")
                from .help import extract_uid_from_url
                basic_creator_id = extract_uid_from_url(creator_input)
                if basic_creator_id:
                    utils.logger.info(f"[BilibiliCrawler._process_creator_input] 基础解析成功，creator_id: {basic_creator_id}")
                    return basic_creator_id
                    
                utils.logger.warning(f"[BilibiliCrawler._process_creator_input] 无法解析创作者输入: {creator_input}")
                return ""
        except Exception as e:
            utils.logger.error(f"[BilibiliCrawler._process_creator_input] 解析创作者输入时发生错误: {e}")
            # 尝试基础解析作为后备
            try:
                from .help import extract_uid_from_url
                basic_creator_id = extract_uid_from_url(creator_input)
                if basic_creator_id:
                    utils.logger.info(f"[BilibiliCrawler._process_creator_input] 后备解析成功，creator_id: {basic_creator_id}")
                    return basic_creator_id
            except:
                pass
            return ""
