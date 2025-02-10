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

from playwright.async_api import (BrowserContext, BrowserType, Page, async_playwright)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import bilibili as bilibili_store
from tools import utils
from var import crawler_type_var, source_keyword_var

from .client import BilibiliClient
from .exception import DataFetchError
from .field import SearchOrderType
from .login import BilibiliLogin


class BilibiliCrawler(AbstractCrawler):
    context_page: Page
    bili_client: BilibiliClient
    browser_context: BrowserContext

    def __init__(self):
        self.index_url = "https://www.bilibili.com"
        self.user_agent = utils.get_user_agent()

    async def start(self):
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(
                ip_proxy_info)

        async with async_playwright() as playwright:
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
                await self.get_specified_videos(config.BILI_SPECIFIED_ID_LIST)
            elif config.CRAWLER_TYPE == "creator":
                for creator_id in config.BILI_CREATOR_ID_LIST:
                    await self.get_creator_videos(int(creator_id))
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
            # 按照 START_DAY 至 END_DAY 按照每一天进行筛选，这样能够突破 1000 条视频的限制，最大程度爬取该关键词下的所有视频
            else:
                for day in pd.date_range(start=config.START_DAY, end=config.END_DAY, freq='D'):
                    # 按照每一天进行爬取的时间戳参数
                    pubtime_begin_s, pubtime_end_s = await self.get_pubtime_datetime(start=day.strftime('%Y-%m-%d'), end=day.strftime('%Y-%m-%d'))
                    page = 1
                    while (page - start_page + 1) * bili_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                        # ! Catch any error if response return nothing, go to next day
                        try:
                            # ! Don't skip any page, to make sure gather all video in one day
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
        video_bvids_list = []
        while True:
            result = await self.bili_client.get_creator_videos(creator_id, pn, ps)
            for video in result["list"]["vlist"]:
                video_bvids_list.append(video["bvid"])
            if (int(result["page"]["count"]) <= pn * ps):
                break
            await asyncio.sleep(random.random())
            pn += 1
        await self.get_specified_videos(video_bvids_list)

    async def get_specified_videos(self, bvids_list: List[str]):
        """
        get specified videos info
        :return:
        """
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

