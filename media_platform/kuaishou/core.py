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
import os
import random
import time
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import BrowserContext, BrowserType, Page, Playwright, async_playwright

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import kuaishou as kuaishou_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import comment_tasks_var, crawler_type_var, source_keyword_var

from .client import KuaiShouClient
from .exception import DataFetchError
from .help import resolve_any_video_url_to_id, resolve_any_creator_url_to_id
from .login import KuaishouLogin


class KuaishouCrawler(AbstractCrawler):
    context_page: Page
    ks_client: KuaiShouClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self):
        self.index_url = "https://www.kuaishou.com"
        self.user_agent = utils.get_user_agent()
        self.cdp_manager = None

    async def start(self):
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(
                config.IP_PROXY_POOL_COUNT, enable_validate_ip=True
            )
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(
                ip_proxy_info
            )

        async with async_playwright() as playwright:
            # 根据配置选择启动模式
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[KuaishouCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright, playwright_proxy_format, self.user_agent,
                    headless=config.CDP_HEADLESS
                )
            else:
                utils.logger.info("[KuaishouCrawler] 使用标准模式启动浏览器")
                # Launch a browser context.
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium, None, self.user_agent, headless=config.HEADLESS
                )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(f"{self.index_url}?isHome=1")

            # Create a client to interact with the kuaishou website.
            self.ks_client = await self.create_ks_client(httpx_proxy_format)
            if not await self.ks_client.pong():
                login_obj = KuaishouLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone=httpx_proxy_format,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await self.ks_client.update_cookies(
                    browser_context=self.browser_context
                )

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for videos and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_videos()
            elif config.CRAWLER_TYPE == "creator":
                # Get creator's information and their videos and comments
                await self.get_creators_and_videos()
            else:
                pass

            utils.logger.info("[KuaishouCrawler.start] Kuaishou Crawler finished ...")

    async def search(self):
        utils.logger.info("[KuaishouCrawler.search] Begin search kuaishou keywords")
        
        # 检查是否有搜索关键词，如果没有则提示用户交互式输入
        if not config.KEYWORDS or config.KEYWORDS.strip() == "":
            await self._interactive_search_input()
        
        ks_limit_count = 20  # kuaishou limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < ks_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = ks_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            search_session_id = ""
            source_keyword_var.set(keyword)
            utils.logger.info(
                f"[KuaishouCrawler.search] Current search keyword: {keyword}"
            )
            page = 1
            while (
                page - start_page + 1
            ) * ks_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[KuaishouCrawler.search] Skip page: {page}")
                    page += 1
                    continue
                utils.logger.info(
                    f"[KuaishouCrawler.search] search kuaishou keyword: {keyword}, page: {page}"
                )
                video_id_list: List[str] = []
                videos_res = await self.ks_client.search_info_by_keyword(
                    keyword=keyword,
                    pcursor=str(page),
                    search_session_id=search_session_id,
                )
                if not videos_res:
                    utils.logger.error(
                        f"[KuaishouCrawler.search] search info by keyword:{keyword} not found data"
                    )
                    continue

                vision_search_photo: Dict = videos_res.get("visionSearchPhoto")
                if vision_search_photo.get("result") != 1:
                    utils.logger.error(
                        f"[KuaishouCrawler.search] search info by keyword:{keyword} not found data "
                    )
                    continue
                search_session_id = vision_search_photo.get("searchSessionId", "")
                for video_detail in vision_search_photo.get("feeds"):
                    video_id_list.append(video_detail.get("photo", {}).get("id"))
                    await kuaishou_store.update_kuaishou_video(video_item=video_detail)

                # batch fetch video comments
                page += 1
                await self.batch_get_video_comments(video_id_list)

    async def get_specified_videos(self):
        """Get the information and comments of the specified post"""
        
        # 检查是否有配置的视频信息，如果没有则提示用户交互式输入
        if not config.KS_SPECIFIED_ID_LIST:
            await self._interactive_detail_input()
        
        # 智能解析视频输入
        resolved_video_ids = []
        for video_input in config.KS_SPECIFIED_ID_LIST:
            video_id = await self._process_video_input(video_input)
            if video_id:
                resolved_video_ids.append(video_id)
        
        # 去重处理
        resolved_video_ids = list(set(resolved_video_ids))
        utils.logger.info(f"[KuaishouCrawler.get_specified_videos] 解析得到的视频ID: {resolved_video_ids}")
        
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_video_info_task(video_id=video_id, semaphore=semaphore)
            for video_id in resolved_video_ids
        ]
        video_details = await asyncio.gather(*task_list)
        for video_detail in video_details:
            if video_detail is not None:
                await kuaishou_store.update_kuaishou_video(video_detail)
        await self.batch_get_video_comments(resolved_video_ids)

    async def get_video_info_task(
        self, video_id: str, semaphore: asyncio.Semaphore
    ) -> Optional[Dict]:
        """Get video detail task"""
        async with semaphore:
            try:
                result = await self.ks_client.get_video_info(video_id)
                utils.logger.info(
                    f"[KuaishouCrawler.get_video_info_task] Get video_id:{video_id} info result: {result} ..."
                )
                return result.get("visionVideoDetail")
            except DataFetchError as ex:
                utils.logger.error(
                    f"[KuaishouCrawler.get_video_info_task] Get video detail error: {ex}"
                )
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[KuaishouCrawler.get_video_info_task] have not fund video detail video_id:{video_id}, err: {ex}"
                )
                return None

    async def batch_get_video_comments(self, video_id_list: List[str]):
        """
        batch get video comments
        :param video_id_list:
        :return:
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(
                f"[KuaishouCrawler.batch_get_video_comments] Crawling comment mode is not enabled"
            )
            return

        utils.logger.info(
            f"[KuaishouCrawler.batch_get_video_comments] video ids:{video_id_list}"
        )
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for video_id in video_id_list:
            task = asyncio.create_task(
                self.get_comments(video_id, semaphore), name=video_id
            )
            task_list.append(task)

        comment_tasks_var.set(task_list)
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
                    f"[KuaishouCrawler.get_comments] begin get video_id: {video_id} comments ..."
                )
                await self.ks_client.get_video_all_comments(
                    photo_id=video_id,
                    crawl_interval=random.random(),
                    callback=kuaishou_store.batch_update_ks_video_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )
            except DataFetchError as ex:
                utils.logger.error(
                    f"[KuaishouCrawler.get_comments] get video_id: {video_id} comment error: {ex}"
                )
            except Exception as e:
                utils.logger.error(
                    f"[KuaishouCrawler.get_comments] may be been blocked, err:{e}"
                )
                # use time.sleeep block main coroutine instead of asyncio.sleep and cacel running comment task
                # maybe kuaishou block our request, we will take a nap and update the cookie again
                current_running_tasks = comment_tasks_var.get()
                for task in current_running_tasks:
                    task.cancel()
                time.sleep(20)
                await self.context_page.goto(f"{self.index_url}?isHome=1")
                await self.ks_client.update_cookies(
                    browser_context=self.browser_context
                )

    @staticmethod
    def format_proxy_info(
        ip_proxy_info: IpInfoModel,
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """format proxy info for playwright and httpx"""
        playwright_proxy = {
            "server": f"{ip_proxy_info.protocol}{ip_proxy_info.ip}:{ip_proxy_info.port}",
            "username": ip_proxy_info.user,
            "password": ip_proxy_info.password,
        }
        httpx_proxy = {
            f"{ip_proxy_info.protocol}": f"http://{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"
        }
        return playwright_proxy, httpx_proxy

    async def create_ks_client(self, httpx_proxy: Optional[str]) -> KuaiShouClient:
        """Create ks client"""
        utils.logger.info(
            "[KuaishouCrawler.create_ks_client] Begin create kuaishou API client ..."
        )
        cookie_str, cookie_dict = utils.convert_cookies(
            await self.browser_context.cookies()
        )
        ks_client_obj = KuaiShouClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": self.index_url,
                "Referer": self.index_url,
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return ks_client_obj

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info(
            "[KuaishouCrawler.launch_browser] Begin create browser context ..."
        )
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(
                os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM
            )  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}, user_agent=user_agent
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
            utils.logger.info(f"[KuaishouCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[KuaishouCrawler] CDP模式启动失败，回退到标准模式: {e}")
            # 回退到标准模式
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def get_creators_and_videos(self) -> None:
        """Get creator's videos and retrieve their comment information."""
        utils.logger.info(
            "[KuaiShouCrawler.get_creators_and_videos] Begin get kuaishou creators"
        )
        
        # 检查是否有配置的创作者信息，如果没有则提示用户交互式输入
        if not config.KS_CREATOR_ID_LIST:
            await self._interactive_creator_input()
        
        # 智能解析创作者输入
        resolved_creator_ids = []
        for creator_input in config.KS_CREATOR_ID_LIST:
            creator_id = await self._process_creator_input(creator_input)
            if creator_id:
                resolved_creator_ids.append(creator_id)
        
        # 去重处理
        resolved_creator_ids = list(set(resolved_creator_ids))
        utils.logger.info(f"[KuaiShouCrawler.get_creators_and_videos] 解析得到的创作者ID: {resolved_creator_ids}")
        
        for user_id in resolved_creator_ids:
            # get creator detail info from web html content
            createor_info: Dict = await self.ks_client.get_creator_info(user_id=user_id)
            if createor_info:
                await kuaishou_store.save_creator(user_id, creator=createor_info)

            # Get all video information of the creator
            all_video_list = await self.ks_client.get_all_videos_by_creator(
                user_id=user_id,
                crawl_interval=random.random(),
                callback=self.fetch_creator_video_detail,
            )

            video_ids = [
                video_item.get("photo", {}).get("id") for video_item in all_video_list
            ]
            await self.batch_get_video_comments(video_ids)

    async def _process_video_input(self, video_input: str) -> str:
        """
        处理视频输入，支持智能URL解析
        如果解析失败，回退到基础解析
        """
        try:
            utils.logger.info(f"[KuaiShouCrawler._process_video_input] 开始解析视频输入: {video_input}")
            
            # 如果是短链接，给出提示但继续尝试解析
            if 'v.kuaishou.com' in video_input or 'chenzhongtech.com' in video_input:
                utils.logger.info(f"[KuaiShouCrawler._process_video_input] 检测到短链接，尝试解析: {video_input}")
                # 注意：短链接解析可能失败，如果经常失败可以考虑直接使用完整URL或video_id
            
            video_id = await resolve_any_video_url_to_id(video_input, self.context_page)
            if video_id:
                utils.logger.info(f"[KuaiShouCrawler._process_video_input] 解析成功，video_id: {video_id}")
                return video_id
            else:
                # 回退到基础解析
                utils.logger.info(f"[KuaiShouCrawler._process_video_input] 智能解析失败，尝试基础解析")
                from .help import extract_video_id_from_url
                basic_video_id = extract_video_id_from_url(video_input)
                if basic_video_id:
                    utils.logger.info(f"[KuaiShouCrawler._process_video_input] 基础解析成功，video_id: {basic_video_id}")
                    return basic_video_id
                    
                utils.logger.warning(f"[KuaiShouCrawler._process_video_input] 无法解析视频输入: {video_input}")
                return ""
        except Exception as e:
            utils.logger.error(f"[KuaiShouCrawler._process_video_input] 解析视频输入时发生错误: {e}")
            # 尝试基础解析作为后备
            try:
                from .help import extract_video_id_from_url
                basic_video_id = extract_video_id_from_url(video_input)
                if basic_video_id:
                    utils.logger.info(f"[KuaiShouCrawler._process_video_input] 后备解析成功，video_id: {basic_video_id}")
                    return basic_video_id
            except:
                pass
            return ""

    async def _process_creator_input(self, creator_input: str) -> str:
        """
        处理创作者输入，支持智能URL解析
        如果解析失败，回退到基础解析
        """
        try:
            utils.logger.info(f"[KuaiShouCrawler._process_creator_input] 开始解析创作者输入: {creator_input}")
            
            # 如果是短链接，给出提示但继续尝试解析
            if 'v.kuaishou.com' in creator_input or 'chenzhongtech.com' in creator_input:
                utils.logger.info(f"[KuaiShouCrawler._process_creator_input] 检测到短链接，尝试解析: {creator_input}")
                # 注意：短链接解析可能失败，如果经常失败可以考虑直接使用完整URL或creator_id
            
            creator_id = await resolve_any_creator_url_to_id(creator_input, self.context_page)
            if creator_id:
                utils.logger.info(f"[KuaiShouCrawler._process_creator_input] 解析成功，creator_id: {creator_id}")
                return creator_id
            else:
                # 回退到基础解析
                utils.logger.info(f"[KuaiShouCrawler._process_creator_input] 智能解析失败，尝试基础解析")
                from .help import extract_creator_id_from_url
                basic_creator_id = extract_creator_id_from_url(creator_input)
                if basic_creator_id:
                    utils.logger.info(f"[KuaiShouCrawler._process_creator_input] 基础解析成功，creator_id: {basic_creator_id}")
                    return basic_creator_id
                    
                utils.logger.warning(f"[KuaiShouCrawler._process_creator_input] 无法解析创作者输入: {creator_input}")
                return ""
        except Exception as e:
            utils.logger.error(f"[KuaiShouCrawler._process_creator_input] 解析创作者输入时发生错误: {e}")
            # 尝试基础解析作为后备
            try:
                from .help import extract_creator_id_from_url
                basic_creator_id = extract_creator_id_from_url(creator_input)
                if basic_creator_id:
                    utils.logger.info(f"[KuaiShouCrawler._process_creator_input] 后备解析成功，creator_id: {basic_creator_id}")
                    return basic_creator_id
            except:
                pass
            return ""

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        """
        Concurrently obtain the specified post list and save the data
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_video_info_task(post_item.get("photo", {}).get("id"), semaphore)
            for post_item in video_list
        ]

        video_details = await asyncio.gather(*task_list)
        for video_detail in video_details:
            if video_detail is not None:
                await kuaishou_store.update_kuaishou_video(video_detail)

    async def close(self):
        """Close browser context"""
        # 如果使用CDP模式，需要特殊处理
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[KuaishouCrawler.close] Browser context closed ...")
    
    async def _interactive_search_input(self) -> None:
        """
        交互式输入搜索关键词
        """
        print("\n" + "="*60)
        print("🔍 快手搜索模式")
        print("="*60)
        print("请输入搜索关键词：")
        print("1. 支持单个关键词：美食")
        print("2. 支持多个关键词（空格分隔）：美食 旅游 音乐")
        print("-"*60)
        
        user_input = input("请输入搜索关键词 (回车键结束): ").strip()
        
        if user_input:
            config.KEYWORDS = user_input.replace(" ", ",")
            utils.logger.info(f"[KuaishouCrawler._interactive_search_input] 已设置搜索关键词: {config.KEYWORDS}")
        else:
            utils.logger.warning("[KuaishouCrawler._interactive_search_input] 未输入任何搜索关键词，将退出程序")
            raise ValueError("未输入任何搜索关键词")
    
    async def _interactive_detail_input(self) -> None:
        """
        交互式输入视频详情信息
        """
        print("\n" + "="*60)
        print("📹 快手视频详情爬取模式")
        print("="*60)
        print("请输入视频信息，支持以下格式：")
        print("1. 完整URL: https://www.kuaishou.com/short-video/3xf8enb8dbj6uig")
        print("2. 短链接: https://v.kuaishou.com/2F50ZXj")
        print("3. video_id: 3xf8enb8dbj6uig")
        print("4. 多个URL用空格分隔")
        print("-"*60)
        
        user_input = input("请输入视频URL或video_id (回车键结束): ").strip()
        
        if user_input:
            # 分割多个URL
            video_inputs = user_input.split()
            config.KS_SPECIFIED_ID_LIST.extend(video_inputs)
            utils.logger.info(f"[KuaishouCrawler._interactive_detail_input] 已添加 {len(video_inputs)} 个视频")
        else:
            utils.logger.warning("[KuaishouCrawler._interactive_detail_input] 未输入任何视频信息，将退出程序")
            raise ValueError("未输入任何视频信息")
    
    async def _interactive_creator_input(self) -> None:
        """
        交互式输入创作者信息
        """
        print("\n" + "="*60)
        print("🎯 快手创作者爬取模式")
        print("="*60)
        print("请输入创作者信息，支持以下格式：")
        print("1. 完整URL: https://www.kuaishou.com/profile/3xqrp5h7gg392vg")
        print("2. 直播URL: https://live.kuaishou.com/profile/3xqrp5h7gg392vg")
        print("3. 短链接: https://v.kuaishou.com/2HJ1YXC")
        print("4. creator_id: 3xqrp5h7gg392vg")
        print("5. 多个URL用空格分隔")
        print("-"*60)
        
        user_input = input("请输入创作者URL或creator_id (回车键结束): ").strip()
        
        if user_input:
            # 分割多个URL
            creator_inputs = user_input.split()
            config.KS_CREATOR_ID_LIST.extend(creator_inputs)
            utils.logger.info(f"[KuaishouCrawler._interactive_creator_input] 已添加 {len(creator_inputs)} 个创作者")
        else:
            utils.logger.warning("[KuaishouCrawler._interactive_creator_input] 未输入任何创作者信息，将退出程序")
            raise ValueError("未输入任何创作者信息")
