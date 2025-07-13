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
from asyncio import Task
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page, Playwright,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import douyin as douyin_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import DOUYINClient
from .exception import DataFetchError
from .field import PublishTimeType
from .help import resolve_any_url_to_sec_user_id, resolve_any_video_url_to_id
from .login import DouYinLogin


class DouYinCrawler(AbstractCrawler):
    context_page: Page
    dy_client: DOUYINClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = "https://www.douyin.com"
        self.cdp_manager = None

    async def start(self) -> None:
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # 根据配置选择启动模式
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[DouYinCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright, playwright_proxy_format, None,
                    headless=config.CDP_HEADLESS
                )
            else:
                utils.logger.info("[DouYinCrawler] 使用标准模式启动浏览器")
                # Launch a browser context.
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    playwright_proxy_format,
                    user_agent=None,
                    headless=config.HEADLESS
                )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            self.dy_client = await self.create_douyin_client(httpx_proxy_format)
            if not await self.dy_client.pong(browser_context=self.browser_context):
                login_obj = DouYinLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # you phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()
                await self.dy_client.update_cookies(browser_context=self.browser_context)
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for notes and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_awemes()
            elif config.CRAWLER_TYPE == "creator":
                # Get the information and comments of the specified creator
                await self.get_creators_and_videos()

            utils.logger.info("[DouYinCrawler.start] Douyin Crawler finished ...")

    async def search(self) -> None:
        utils.logger.info("[DouYinCrawler.search] Begin search douyin keywords")
        
        # 检查是否有搜索关键词，如果没有则提示用户交互式输入
        if not config.KEYWORDS or config.KEYWORDS.strip() == "":
            await self._interactive_search_input()
        
        dy_limit_count = 10  # douyin limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < dy_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = dy_limit_count
        start_page = config.START_PAGE  # start page number
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[DouYinCrawler.search] Current keyword: {keyword}")
            aweme_list: List[str] = []
            page = 0
            dy_search_id = ""
            while (page - start_page + 1) * dy_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[DouYinCrawler.search] Skip {page}")
                    page += 1
                    continue
                try:
                    utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page}")
                    posts_res = await self.dy_client.search_info_by_keyword(keyword=keyword,
                                                                            offset=page * dy_limit_count - dy_limit_count,
                                                                            publish_time=PublishTimeType(config.PUBLISH_TIME_TYPE),
                                                                            search_id=dy_search_id
                                                                            )
                    if posts_res.get("data") is None or posts_res.get("data") == []:
                        utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page} is empty,{posts_res.get('data')}`")
                        break
                except DataFetchError:
                    utils.logger.error(f"[DouYinCrawler.search] search douyin keyword: {keyword} failed")
                    break

                page += 1
                if "data" not in posts_res:
                    utils.logger.error(
                        f"[DouYinCrawler.search] search douyin keyword: {keyword} failed，账号也许被风控了。")
                    break
                dy_search_id = posts_res.get("extra", {}).get("logid", "")
                for post_item in posts_res.get("data"):
                    try:
                        aweme_info: Dict = post_item.get("aweme_info") or \
                                           post_item.get("aweme_mix_info", {}).get("mix_items")[0]
                    except TypeError:
                        continue
                    aweme_list.append(aweme_info.get("aweme_id", ""))
                    await douyin_store.update_douyin_aweme(aweme_item=aweme_info)
            utils.logger.info(f"[DouYinCrawler.search] keyword:{keyword}, aweme_list:{aweme_list}")
            await self.batch_get_note_comments(aweme_list)

    async def get_specified_awemes(self):
        """Get the information and comments of the specified post"""
        utils.logger.info("[DouYinCrawler.get_specified_awemes] Begin get specified videos")
        
        # 检查是否有配置的视频信息，如果没有则提示用户交互式输入
        if not config.DY_SPECIFIED_ID_LIST:
            await self._interactive_detail_input()
        
        # 解析所有视频输入，支持URL和纯ID
        resolved_video_ids = []
        for video_input in config.DY_SPECIFIED_ID_LIST:
            if video_input and video_input.strip():
                video_id = await self._process_video_input(video_input)
                if video_id:
                    resolved_video_ids.append(video_id)
        
        if not resolved_video_ids:
            utils.logger.warning("[DouYinCrawler.get_specified_awemes] No valid video IDs resolved")
            return
        
        utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Resolved {len(resolved_video_ids)} video IDs: {resolved_video_ids}")
        
        # 并发获取视频详情
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_aweme_detail(aweme_id=video_id, semaphore=semaphore) for video_id in resolved_video_ids
        ]
        aweme_details = await asyncio.gather(*task_list)
        
        # 保存视频详情
        for aweme_detail in aweme_details:
            if aweme_detail is not None:
                await douyin_store.update_douyin_aweme(aweme_detail)
        
        # 获取评论
        await self.batch_get_note_comments(resolved_video_ids)
        
    async def _process_video_input(self, video_input: str) -> str:
        """
        统一处理视频输入（支持video_id、完整URL、短链接）
        """
        try:
            utils.logger.info(f"[DouYinCrawler._process_video_input] 处理视频输入: {video_input}")
            
            # 使用统一的解析函数
            video_id = await resolve_any_video_url_to_id(video_input, self.context_page)
            if not video_id:
                utils.logger.error(f"[DouYinCrawler._process_video_input] 无法解析视频输入: {video_input}")
                return ""
            
            utils.logger.info(f"[DouYinCrawler._process_video_input] 解析成功: {video_input} -> {video_id}")
            return video_id
            
        except Exception as e:
            utils.logger.error(f"[DouYinCrawler._process_video_input] 处理视频输入失败: {video_input}, 错误: {e}")
            return ""

    async def get_aweme_detail(self, aweme_id: str, semaphore: asyncio.Semaphore) -> Any:
        """Get note detail"""
        async with semaphore:
            try:
                return await self.dy_client.get_video_by_id(aweme_id)
            except DataFetchError as ex:
                utils.logger.error(f"[DouYinCrawler.get_aweme_detail] Get aweme detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[DouYinCrawler.get_aweme_detail] have not fund note detail aweme_id:{aweme_id}, err: {ex}")
                return None

    async def batch_get_note_comments(self, aweme_list: List[str]) -> None:
        """
        Batch get note comments
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        task_list: List[Task] = []
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        for aweme_id in aweme_list:
            task = asyncio.create_task(
                self.get_comments(aweme_id, semaphore), name=aweme_id)
            task_list.append(task)
        if len(task_list) > 0:
            await asyncio.wait(task_list)

    async def get_comments(self, aweme_id: str, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            try:
                # 将关键词列表传递给 get_aweme_all_comments 方法
                await self.dy_client.get_aweme_all_comments(
                    aweme_id=aweme_id,
                    crawl_interval=random.random(),
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=douyin_store.batch_update_dy_aweme_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES
                )
                utils.logger.info(
                    f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} comments have all been obtained and filtered ...")
            except DataFetchError as e:
                utils.logger.error(f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} get comments failed, error: {e}")

    async def get_creators_and_videos(self) -> None:
        """
        Get the information and videos of the specified creator
        """
        utils.logger.info("[DouYinCrawler.get_creators_and_videos] Begin get douyin creators")
        
        # 检查是否有配置的创作者信息
        has_config_creators = bool(config.DY_CREATOR_ID_LIST or config.DY_CREATOR_URL_LIST)
        
        # 如果没有配置创作者信息，则提示用户交互式输入
        if not has_config_creators:
            await self._interactive_creator_input()
        
        # 用于去重的集合，记录已处理的sec_user_id
        processed_creators = set()
        
        # 合并处理所有输入（传统的ID列表和新的URL列表）
        all_creator_inputs = []
        all_creator_inputs.extend(config.DY_CREATOR_ID_LIST)
        all_creator_inputs.extend(config.DY_CREATOR_URL_LIST)
        
        # 统一处理所有输入
        for creator_input in all_creator_inputs:
            if creator_input and creator_input.strip():
                await self._process_creator_input(creator_input, processed_creators)
            
    async def _interactive_creator_input(self) -> None:
        """
        交互式输入创作者信息
        """
        print("\n" + "="*60)
        print("🎯 抖音创作者爬取模式")
        print("="*60)
        print("请输入创作者信息，支持以下格式：")
        print("1. 完整URL: https://www.douyin.com/user/MS4wLjABAAAA...")
        print("2. 短链接: https://v.douyin.com/iXXXXXX/")  
        print("3. sec_user_id: MS4wLjABAAAA...")
        print("4. 多个URL用空格分隔")
        print("-"*60)
        
        user_input = input("请输入创作者URL或sec_user_id (回车键结束): ").strip()
        
        if user_input:
            # 分割多个URL
            creator_inputs = user_input.split()
            config.DY_CREATOR_URL_LIST.extend(creator_inputs)
            utils.logger.info(f"[DouYinCrawler._interactive_creator_input] 已添加 {len(creator_inputs)} 个创作者")
        else:
            utils.logger.warning("[DouYinCrawler._interactive_creator_input] 未输入任何创作者信息，将退出程序")
            raise ValueError("未输入任何创作者信息")
    
    async def _interactive_search_input(self) -> None:
        """
        交互式输入搜索关键词
        """
        print("\n" + "="*60)
        print("🔍 抖音搜索模式")
        print("="*60)
        print("请输入搜索关键词：")
        print("1. 支持单个关键词：美食")
        print("2. 支持多个关键词（空格分隔）：美食 旅游 音乐")
        print("-"*60)
        
        user_input = input("请输入搜索关键词 (回车键结束): ").strip()
        
        if user_input:
            config.KEYWORDS = user_input.replace(" ", ",")
            utils.logger.info(f"[DouYinCrawler._interactive_search_input] 已设置搜索关键词: {config.KEYWORDS}")
        else:
            utils.logger.warning("[DouYinCrawler._interactive_search_input] 未输入任何搜索关键词，将退出程序")
            raise ValueError("未输入任何搜索关键词")
    
    async def _interactive_detail_input(self) -> None:
        """
        交互式输入视频详情信息
        """
        print("\n" + "="*60)
        print("📹 抖音视频详情爬取模式")
        print("="*60)
        print("请输入视频信息，支持以下格式：")
        print("1. 完整URL: https://www.douyin.com/video/7525082444551310602")
        print("2. 短链接: https://v.douyin.com/iXXXXXX/")
        print("3. video_id: 7525082444551310602")
        print("4. 多个URL用空格分隔")
        print("-"*60)
        
        user_input = input("请输入视频URL或video_id (回车键结束): ").strip()
        
        if user_input:
            # 分割多个URL
            video_inputs = user_input.split()
            config.DY_SPECIFIED_ID_LIST.extend(video_inputs)
            utils.logger.info(f"[DouYinCrawler._interactive_detail_input] 已添加 {len(video_inputs)} 个视频")
        else:
            utils.logger.warning("[DouYinCrawler._interactive_detail_input] 未输入任何视频信息，将退出程序")
            raise ValueError("未输入任何视频信息")
            
    async def _process_creator_input(self, creator_input: str, processed_creators: set) -> None:
        """
        统一处理创作者输入（支持sec_user_id、完整URL、短链接）
        """
        try:
            utils.logger.info(f"[DouYinCrawler._process_creator_input] 处理创作者输入: {creator_input}")
            
            # 使用统一的解析函数
            sec_user_id = await resolve_any_url_to_sec_user_id(creator_input, self.context_page, self.dy_client)
            if not sec_user_id:
                utils.logger.error(f"[DouYinCrawler._process_creator_input] 无法解析输入: {creator_input}")
                return
            
            # 去重检查
            if sec_user_id in processed_creators:
                utils.logger.info(f"[DouYinCrawler._process_creator_input] 跳过重复的创作者: {sec_user_id}")
                return
            
            # 添加到已处理集合
            processed_creators.add(sec_user_id)
            
            # 处理创作者
            utils.logger.info(f"[DouYinCrawler._process_creator_input] 开始处理创作者: {sec_user_id}")
            await self._process_creator_by_sec_id(sec_user_id)
            
        except Exception as e:
            utils.logger.error(f"[DouYinCrawler._process_creator_input] 处理创作者输入失败: {creator_input}, 错误: {e}")

    async def _process_creator_by_sec_id(self, sec_user_id: str) -> None:
        """
        通过sec_user_id处理创作者信息和视频
        注意：传入的必须是纯净的sec_user_id
        """
        utils.logger.info(f"[DouYinCrawler._process_creator_by_sec_id] 处理创作者: {sec_user_id}")
        
        try:
            # 获取创作者信息
            creator_info: Dict = await self.dy_client.get_user_info(sec_user_id)
            if creator_info:
                await douyin_store.save_creator(sec_user_id, creator=creator_info)
            else:
                utils.logger.warning(f"[DouYinCrawler._process_creator_by_sec_id] 未获取到创作者信息: {sec_user_id}")

            # 获取创作者的所有视频
            all_video_list = await self.dy_client.get_all_user_aweme_posts(
                sec_user_id=sec_user_id,
                callback=self.fetch_creator_video_detail
            )

            # 爬取视频评论
            video_ids = [video_item.get("aweme_id") for video_item in all_video_list]
            await self.batch_get_note_comments(video_ids)
            
            utils.logger.info(f"[DouYinCrawler._process_creator_by_sec_id] 创作者处理完成: {sec_user_id}, 视频数量: {len(video_ids)}")
            
        except Exception as e:
            utils.logger.error(f"[DouYinCrawler._process_creator_by_sec_id] 处理创作者失败: {sec_user_id}, 错误: {e}")

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        """
        Concurrently obtain the specified post list and save the data
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_aweme_detail(post_item.get("aweme_id"), semaphore) for post_item in video_list
        ]

        note_details = await asyncio.gather(*task_list)
        for aweme_item in note_details:
            if aweme_item is not None:
                await douyin_store.update_douyin_aweme(aweme_item)

    @staticmethod
    def format_proxy_info(ip_proxy_info: IpInfoModel) -> Tuple[Optional[Dict], Optional[Dict]]:
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

    async def create_douyin_client(self, httpx_proxy: Optional[str]) -> DOUYINClient:
        """Create douyin client"""
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())  # type: ignore
        douyin_client = DOUYINClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": await self.context_page.evaluate("() => navigator.userAgent"),
                "Cookie": cookie_str,
                "Host": "www.douyin.com",
                "Origin": "https://www.douyin.com/",
                "Referer": "https://www.douyin.com/",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return douyin_client

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data",
                                         config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )  # type: ignore
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
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

            # 添加反检测脚本
            await self.cdp_manager.add_stealth_script()

            # 显示浏览器信息
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[DouYinCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[DouYinCrawler] CDP模式启动失败，回退到标准模式: {e}")
            # 回退到标准模式
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self) -> None:
        """Close browser context"""
        # 如果使用CDP模式，需要特殊处理
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[DouYinCrawler.close] Browser context closed ...")
