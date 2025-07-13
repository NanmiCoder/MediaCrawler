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
# @Time    : 2023/12/23 15:41
# @Desc    : 微博爬虫主流程代码


import asyncio
import os
import random
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page, Playwright,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import weibo as weibo_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import WeiboClient
from .exception import DataFetchError
from .field import SearchType
from .help import filter_search_result_card, resolve_any_post_url_to_id, resolve_any_user_url_to_id
from .login import WeiboLogin


class WeiboCrawler(AbstractCrawler):
    context_page: Page
    wb_client: WeiboClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self):
        self.index_url = "https://www.weibo.com"
        self.mobile_index_url = "https://m.weibo.cn"
        self.user_agent = utils.get_user_agent()
        self.mobile_user_agent = utils.get_mobile_user_agent()
        self.cdp_manager = None

    async def start(self):
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # 根据配置选择启动模式
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[WeiboCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright, playwright_proxy_format, self.mobile_user_agent,
                    headless=config.CDP_HEADLESS
                )
            else:
                utils.logger.info("[WeiboCrawler] 使用标准模式启动浏览器")
                # Launch a browser context.
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    None,
                    self.mobile_user_agent,
                    headless=config.HEADLESS
                )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.mobile_index_url)

            # Create a client to interact with the xiaohongshu website.
            self.wb_client = await self.create_weibo_client(httpx_proxy_format)
            if not await self.wb_client.pong():
                login_obj = WeiboLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # your phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()

                # 登录成功后重定向到手机端的网站，再更新手机端登录成功的cookie
                utils.logger.info("[WeiboCrawler.start] redirect weibo mobile homepage and update cookies on mobile platform")
                await self.context_page.goto(self.mobile_index_url)
                await asyncio.sleep(2)
                await self.wb_client.update_cookies(browser_context=self.browser_context)

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for video and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_notes()
            elif config.CRAWLER_TYPE == "creator":
                # Get creator's information and their notes and comments
                await self.get_creators_and_notes()
            else:
                pass
            utils.logger.info("[WeiboCrawler.start] Weibo Crawler finished ...")

    async def search(self):
        """
        search weibo note with keywords
        :return:
        """
        utils.logger.info("[WeiboCrawler.search] Begin search weibo keywords")
        
        # 检查是否有搜索关键词，如果没有则提示用户交互式输入
        if not config.KEYWORDS or config.KEYWORDS.strip() == "":
            await self._interactive_search_input()
        
        weibo_limit_count = 10  # weibo limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < weibo_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = weibo_limit_count
        start_page = config.START_PAGE

        # Set the search type based on the configuration for weibo
        if config.WEIBO_SEARCH_TYPE == "default":
            search_type = SearchType.DEFAULT
        elif config.WEIBO_SEARCH_TYPE == "real_time":
            search_type = SearchType.REAL_TIME
        elif config.WEIBO_SEARCH_TYPE == "popular":
            search_type = SearchType.POPULAR
        elif config.WEIBO_SEARCH_TYPE == "video":
            search_type = SearchType.VIDEO
        else:
            utils.logger.error(f"[WeiboCrawler.search] Invalid WEIBO_SEARCH_TYPE: {config.WEIBO_SEARCH_TYPE}")
            return

        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[WeiboCrawler.search] Current search keyword: {keyword}")
            page = 1
            while (page - start_page + 1) * weibo_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[WeiboCrawler.search] Skip page: {page}")
                    page += 1
                    continue
                utils.logger.info(f"[WeiboCrawler.search] search weibo keyword: {keyword}, page: {page}")
                search_res = await self.wb_client.get_note_by_keyword(
                    keyword=keyword,
                    page=page,
                    search_type=search_type
                )
                note_id_list: List[str] = []
                note_list = filter_search_result_card(search_res.get("cards"))
                for note_item in note_list:
                    if note_item:
                        mblog: Dict = note_item.get("mblog")
                        if mblog:
                            note_id_list.append(mblog.get("id"))
                            await weibo_store.update_weibo_note(note_item)
                            await self.get_note_images(mblog)

                page += 1
                await self.batch_get_notes_comments(note_id_list)

    async def get_specified_notes(self):
        """
        get specified notes info
        :return:
        """
        
        # 检查是否有配置的帖子信息，如果没有则提示用户交互式输入
        if not config.WEIBO_SPECIFIED_ID_LIST:
            await self._interactive_detail_input()
        
        # 智能解析帖子输入
        resolved_post_ids = []
        for post_input in config.WEIBO_SPECIFIED_ID_LIST:
            post_id = await self._process_post_input(post_input)
            if post_id:
                resolved_post_ids.append(post_id)
        
        # 去重处理
        resolved_post_ids = list(set(resolved_post_ids))
        utils.logger.info(f"[WeiboCrawler.get_specified_notes] 解析得到的帖子ID: {resolved_post_ids}")
        
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_info_task(note_id=note_id, semaphore=semaphore) for note_id in
            resolved_post_ids
        ]
        video_details = await asyncio.gather(*task_list)
        for note_item in video_details:
            if note_item:
                await weibo_store.update_weibo_note(note_item)
        await self.batch_get_notes_comments(resolved_post_ids)

    async def get_note_info_task(self, note_id: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """
        Get note detail task
        :param note_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                result = await self.wb_client.get_note_info_by_id(note_id)
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[WeiboCrawler.get_note_info_task] Get note detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[WeiboCrawler.get_note_info_task] have not fund note detail note_id:{note_id}, err: {ex}")
                return None

    async def batch_get_notes_comments(self, note_id_list: List[str]):
        """
        batch get notes comments
        :param note_id_list:
        :return:
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[WeiboCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        utils.logger.info(f"[WeiboCrawler.batch_get_notes_comments] note ids:{note_id_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for note_id in note_id_list:
            task = asyncio.create_task(self.get_note_comments(note_id, semaphore), name=note_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_note_comments(self, note_id: str, semaphore: asyncio.Semaphore):
        """
        get comment for note id
        :param note_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                utils.logger.info(f"[WeiboCrawler.get_note_comments] begin get note_id: {note_id} comments ...")
                await self.wb_client.get_note_all_comments(
                    note_id=note_id,
                    crawl_interval=random.randint(1,3), # 微博对API的限流比较严重，所以延时提高一些
                    callback=weibo_store.batch_update_weibo_note_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES
                )
            except DataFetchError as ex:
                utils.logger.error(f"[WeiboCrawler.get_note_comments] get note_id: {note_id} comment error: {ex}")
            except Exception as e:
                utils.logger.error(f"[WeiboCrawler.get_note_comments] may be been blocked, err:{e}")

    async def get_note_images(self, mblog: Dict):
        """
        get note images
        :param mblog:
        :return:
        """
        if not config.ENABLE_GET_IMAGES:
            utils.logger.info(f"[WeiboCrawler.get_note_images] Crawling image mode is not enabled")
            return
        
        pics: Dict = mblog.get("pics")
        if not pics:
            return
        for pic in pics:
            url = pic.get("url")
            if not url:
                continue
            content = await self.wb_client.get_note_image(url)
            if content != None:
                extension_file_name = url.split(".")[-1]
                await weibo_store.update_weibo_note_image(pic["pid"], content, extension_file_name)


    async def get_creators_and_notes(self) -> None:
        """
        Get creator's information and their notes and comments
        Returns:

        """
        utils.logger.info("[WeiboCrawler.get_creators_and_notes] Begin get weibo creators")
        
        # 检查是否有配置的创作者信息，如果没有则提示用户交互式输入
        if not config.WEIBO_CREATOR_ID_LIST:
            await self._interactive_creator_input()
        
        # 智能解析创作者输入
        resolved_creator_ids = []
        for creator_input in config.WEIBO_CREATOR_ID_LIST:
            creator_id = await self._process_creator_input(creator_input)
            if creator_id:
                resolved_creator_ids.append(creator_id)
        
        # 去重处理
        resolved_creator_ids = list(set(resolved_creator_ids))
        utils.logger.info(f"[WeiboCrawler.get_creators_and_notes] 解析得到的创作者ID: {resolved_creator_ids}")
        
        for user_id in resolved_creator_ids:
            createor_info_res: Dict = await self.wb_client.get_creator_info_by_id(creator_id=user_id)
            if createor_info_res:
                createor_info: Dict = createor_info_res.get("userInfo", {})
                utils.logger.info(f"[WeiboCrawler.get_creators_and_notes] creator info: {createor_info}")
                if not createor_info:
                    raise DataFetchError("Get creator info error")
                await weibo_store.save_creator(user_id, user_info=createor_info)

                # Get all note information of the creator
                all_notes_list = await self.wb_client.get_all_notes_by_creator_id(
                    creator_id=user_id,
                    container_id=createor_info_res.get("lfid_container_id"),
                    crawl_interval=0,
                    callback=weibo_store.batch_update_weibo_notes
                )

                note_ids = [note_item.get("mblog", {}).get("id") for note_item in all_notes_list if
                            note_item.get("mblog", {}).get("id")]
                await self.batch_get_notes_comments(note_ids)

            else:
                utils.logger.error(
                    f"[WeiboCrawler.get_creators_and_notes] get creator info error, creator_id:{user_id}")

    async def _process_post_input(self, post_input: str) -> str:
        """
        处理帖子输入，支持智能URL解析
        如果解析失败，回退到基础解析
        """
        try:
            utils.logger.info(f"[WeiboCrawler._process_post_input] 开始解析帖子输入: {post_input}")
            
            # 智能解析
            post_id = await resolve_any_post_url_to_id(post_input, self.context_page)
            if post_id:
                utils.logger.info(f"[WeiboCrawler._process_post_input] 解析成功，post_id: {post_id}")
                return post_id
            else:
                # 回退到基础解析
                utils.logger.info(f"[WeiboCrawler._process_post_input] 智能解析失败，尝试基础解析")
                from .help import extract_post_id_from_url
                basic_post_id = extract_post_id_from_url(post_input)
                if basic_post_id:
                    utils.logger.info(f"[WeiboCrawler._process_post_input] 基础解析成功，post_id: {basic_post_id}")
                    return basic_post_id
                    
                utils.logger.warning(f"[WeiboCrawler._process_post_input] 无法解析帖子输入: {post_input}")
                return ""
        except Exception as e:
            utils.logger.error(f"[WeiboCrawler._process_post_input] 解析帖子输入时发生错误: {e}")
            # 尝试基础解析作为后备
            try:
                from .help import extract_post_id_from_url
                basic_post_id = extract_post_id_from_url(post_input)
                if basic_post_id:
                    utils.logger.info(f"[WeiboCrawler._process_post_input] 后备解析成功，post_id: {basic_post_id}")
                    return basic_post_id
            except:
                pass
            return ""

    async def _process_creator_input(self, creator_input: str) -> str:
        """
        处理创作者输入，支持智能URL解析
        如果解析失败，回退到基础解析
        """
        try:
            utils.logger.info(f"[WeiboCrawler._process_creator_input] 开始解析创作者输入: {creator_input}")
            
            # 智能解析
            creator_id = await resolve_any_user_url_to_id(creator_input, self.context_page)
            if creator_id:
                utils.logger.info(f"[WeiboCrawler._process_creator_input] 解析成功，creator_id: {creator_id}")
                return creator_id
            else:
                # 回退到基础解析
                utils.logger.info(f"[WeiboCrawler._process_creator_input] 智能解析失败，尝试基础解析")
                from .help import extract_user_id_from_url
                basic_creator_id = extract_user_id_from_url(creator_input)
                if basic_creator_id:
                    utils.logger.info(f"[WeiboCrawler._process_creator_input] 基础解析成功，creator_id: {basic_creator_id}")
                    return basic_creator_id
                    
                utils.logger.warning(f"[WeiboCrawler._process_creator_input] 无法解析创作者输入: {creator_input}")
                return ""
        except Exception as e:
            utils.logger.error(f"[WeiboCrawler._process_creator_input] 解析创作者输入时发生错误: {e}")
            # 尝试基础解析作为后备
            try:
                from .help import extract_user_id_from_url
                basic_creator_id = extract_user_id_from_url(creator_input)
                if basic_creator_id:
                    utils.logger.info(f"[WeiboCrawler._process_creator_input] 后备解析成功，creator_id: {basic_creator_id}")
                    return basic_creator_id
            except:
                pass
            return ""

    async def create_weibo_client(self, httpx_proxy: Optional[str]) -> WeiboClient:
        """Create xhs client"""
        utils.logger.info("[WeiboCrawler.create_weibo_client] Begin create weibo API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        weibo_client_obj = WeiboClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": utils.get_mobile_user_agent(),
                "Cookie": cookie_str,
                "Origin": "https://m.weibo.cn",
                "Referer": "https://m.weibo.cn",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return weibo_client_obj

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

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("[WeiboCrawler.launch_browser] Begin create browser context ...")
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
            )
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

            # 显示浏览器信息
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[WeiboCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[WeiboCrawler] CDP模式启动失败，回退到标准模式: {e}")
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
        utils.logger.info("[WeiboCrawler.close] Browser context closed ...")
    
    async def _interactive_search_input(self) -> None:
        """
        交互式输入搜索关键词
        """
        print("\n" + "="*60)
        print("🔍 微博搜索模式")
        print("="*60)
        print("请输入搜索关键词：")
        print("1. 支持单个关键词：美食")
        print("2. 支持多个关键词（空格分隔）：美食 旅游 音乐")
        print("-"*60)
        
        user_input = input("请输入搜索关键词 (回车键结束): ").strip()
        
        if user_input:
            config.KEYWORDS = user_input.replace(" ", ",")
            utils.logger.info(f"[WeiboCrawler._interactive_search_input] 已设置搜索关键词: {config.KEYWORDS}")
        else:
            utils.logger.warning("[WeiboCrawler._interactive_search_input] 未输入任何搜索关键词，将退出程序")
            raise ValueError("未输入任何搜索关键词")
    
    async def _interactive_detail_input(self) -> None:
        """
        交互式输入帖子详情信息
        """
        print("\n" + "="*60)
        print("📝 微博帖子详情爬取模式")
        print("="*60)
        print("请输入帖子信息，支持以下格式：")
        print("1. 桌面版帖子URL: https://weibo.com/7643904561/5182160183232445")
        print("2. 手机版帖子URL: https://m.weibo.cn/detail/5182160183232445")
        print("3. 手机版状态URL: https://m.weibo.cn/status/5182160183232445")
        print("4. post_id: 5182160183232445")
        print("5. 多个URL用空格分隔")
        print("-"*60)
        
        user_input = input("请输入帖子URL或post_id (回车键结束): ").strip()
        
        if user_input:
            # 分割多个URL
            post_inputs = user_input.split()
            config.WEIBO_SPECIFIED_ID_LIST.extend(post_inputs)
            utils.logger.info(f"[WeiboCrawler._interactive_detail_input] 已添加 {len(post_inputs)} 个帖子")
        else:
            utils.logger.warning("[WeiboCrawler._interactive_detail_input] 未输入任何帖子信息，将退出程序")
            raise ValueError("未输入任何帖子信息")
    
    async def _interactive_creator_input(self) -> None:
        """
        交互式输入创作者信息
        """
        print("\n" + "="*60)
        print("🎯 微博创作者爬取模式")
        print("="*60)
        print("请输入创作者信息，支持以下格式：")
        print("1. 桌面版用户主页: https://weibo.com/u/5533390220")
        print("2. 桌面版简化格式: https://weibo.com/5533390220") 
        print("3. 手机版用户主页: https://m.weibo.cn/u/5533390220")
        print("4. 手机版个人资料: https://m.weibo.cn/profile/5533390220")
        print("5. user_id: 5533390220")
        print("6. 多个URL用空格分隔")
        print("-"*60)
        
        user_input = input("请输入创作者URL或user_id (回车键结束): ").strip()
        
        if user_input:
            # 分割多个URL
            creator_inputs = user_input.split()
            config.WEIBO_CREATOR_ID_LIST.extend(creator_inputs)
            utils.logger.info(f"[WeiboCrawler._interactive_creator_input] 已添加 {len(creator_inputs)} 个创作者")
        else:
            utils.logger.warning("[WeiboCrawler._interactive_creator_input] 未输入任何创作者信息，将退出程序")
            raise ValueError("未输入任何创作者信息")
