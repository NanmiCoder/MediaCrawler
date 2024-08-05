import asyncio
import os
import random
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool, ProxyIpPool
from store import tieba as tieba_store
from tools import utils
from tools.crawler_util import format_proxy_info
from var import crawler_type_var

from .client import BaiduTieBaClient
from .field import SearchNoteType, SearchSortType
from .login import BaiduTieBaLogin


class TieBaCrawler(AbstractCrawler):
    context_page: Page
    tieba_client: BaiduTieBaClient
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.index_url = "https://tieba.baidu.com"
        self.user_agent = utils.get_user_agent()

    async def start(self) -> None:
        """
        Start the crawler
        Returns:

        """
        ip_proxy_pool, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            utils.logger.info("[BaiduTieBaCrawler.start] Begin create ip proxy pool ...")
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            _, httpx_proxy_format = format_proxy_info(ip_proxy_info)
            utils.logger.info(f"[BaiduTieBaCrawler.start] Init default ip proxy, value: {httpx_proxy_format}")

        # Create a client to interact with the baidutieba website.
        self.tieba_client = BaiduTieBaClient(
            ip_pool=ip_proxy_pool,
            default_ip_proxy=httpx_proxy_format,
        )
        crawler_type_var.set(config.CRAWLER_TYPE)
        if config.CRAWLER_TYPE == "search":
            # Search for notes and retrieve their comment information.
            await self.search()
        elif config.CRAWLER_TYPE == "detail":
            # Get the information and comments of the specified post
            await self.get_specified_notes()
        else:
            pass

        utils.logger.info("[BaiduTieBaCrawler.start] Tieba Crawler finished ...")

    async def search(self) -> None:
        """
        Search for notes and retrieve their comment information.
        Returns:

        """

        utils.logger.info("[BaiduTieBaCrawler.search] Begin search baidutieba keywords")
        tieba_limit_count = 10  # tieba limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < tieba_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = tieba_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            utils.logger.info(f"[BaiduTieBaCrawler.search] Current search keyword: {keyword}")
            page = 1
            while (page - start_page + 1) * tieba_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[BaiduTieBaCrawler.search] Skip page {page}")
                    page += 1
                    continue
                try:
                    utils.logger.info(f"[BaiduTieBaCrawler.search] search tieba keyword: {keyword}, page: {page}")
                    note_id_list: List[str] = []
                    notes_list_res = await self.tieba_client.get_notes_by_keyword(
                        keyword=keyword,
                        page=page,
                        page_size=tieba_limit_count,
                        sort=SearchSortType.TIME_DESC,
                        note_type=SearchNoteType.FIXED_THREAD
                    )
                    utils.logger.info(f"[BaiduTieBaCrawler.search] Search notes res:{notes_list_res}")
                    if not notes_list_res:
                        break

                    for note_detail in notes_list_res:
                        if note_detail:
                            await tieba_store.update_tieba_note(note_detail)
                            note_id_list.append(note_detail.get("note_id"))
                    page += 1
                    utils.logger.info(f"[BaiduTieBaCrawler.search] Note details: {notes_list_res}")
                    await self.batch_get_note_comments(note_id_list)
                except Exception as ex:
                    utils.logger.error(f"[BaiduTieBaCrawler.search] Search note list error, err: {ex}")
                    break

    async def fetch_creator_notes_detail(self, note_list: List[Dict]):
        """
        Concurrently obtain the specified post list and save the data
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_detail(
                note_id=post_item.get("note_id"),
                semaphore=semaphore
            )
            for post_item in note_list
        ]

        note_details = await asyncio.gather(*task_list)
        for note_detail in note_details:
            if note_detail:
                await tieba_store.update_tieba_note(note_detail)

    async def get_specified_notes(self):
        """Get the information and comments of the specified post"""
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_detail(note_id=note_id, semaphore=semaphore) for note_id in config.TIEBA_SPECIFIED_ID_LIST
        ]
        note_details = await asyncio.gather(*task_list)
        for note_detail in note_details:
            if note_detail is not None:
                await tieba_store.update_tieba_note(note_detail)
        await self.batch_get_note_comments(config.TIEBA_SPECIFIED_ID_LIST)

    async def get_note_detail(self, note_id: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """Get note detail"""
        async with semaphore:
            try:
                note_detail: Dict = await self.tieba_client.get_note_by_id(note_id)
                if not note_detail:
                    utils.logger.error(
                        f"[BaiduTieBaCrawler.get_note_detail] Get note detail error, note_id: {note_id}")
                    return None
                return note_detail
            except Exception as ex:
                utils.logger.error(f"[BaiduTieBaCrawler.get_note_detail] Get note detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[BaiduTieBaCrawler.get_note_detail] have not fund note detail note_id:{note_id}, err: {ex}")
                return None

    async def batch_get_note_comments(self, note_list: List[str]):
        """Batch get note comments"""
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[BaiduTieBaCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        utils.logger.info(
            f"[BaiduTieBaCrawler.batch_get_note_comments] Begin batch get note comments, note list: {note_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for note_id in note_list:
            task = asyncio.create_task(self.get_comments(note_id, semaphore), name=note_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments(self, note_id: str, semaphore: asyncio.Semaphore):
        """Get note comments with keyword filtering and quantity limitation"""
        async with semaphore:
            utils.logger.info(f"[BaiduTieBaCrawler.get_comments] Begin get note id comments {note_id}")
            await self.tieba_client.get_note_all_comments(
                note_id=note_id,
                crawl_interval=random.random(),
                callback=tieba_store.batch_update_tieba_note_comments
            )

    async def create_tieba_client(self, ip_pool: ProxyIpPool) -> BaiduTieBaClient:
        """
        Create tieba client
        Args:
            ip_pool:

        Returns:

        """
        """Create tieba client"""
        utils.logger.info("[BaiduTieBaCrawler.create_tieba_client] Begin create baidutieba API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        tieba_client_obj = BaiduTieBaClient(
            ip_pool=ip_pool,
        )
        return tieba_client_obj

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("[BaiduTieBaCrawler.launch_browser] Begin create browser context ...")
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
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context

    async def close(self):
        """Close browser context"""
        await self.browser_context.close()
        utils.logger.info("[BaiduTieBaCrawler.close] Browser context closed ...")