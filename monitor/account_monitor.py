"""
账号监控爬虫

功能：
1. 监控指定账号的新内容
2. 支持增量抓取（只抓新内容）
3. 自动识别爆款
"""

import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime

from playwright.async_api import async_playwright

import config
from media_platform.xhs.core import XiaoHongShuCrawler
from media_platform.xhs.client import XiaoHongShuClient
from media_platform.xhs.help import parse_creator_info_from_url
from model.m_xiaohongshu import CreatorUrlInfo
from database.mongodb_store_base import MongoDBStoreBase
from store import xhs as xhs_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager

from config.monitor_config import (
    MONITOR_MAX_NOTES_PER_ACCOUNT,
    MONITOR_REQUEST_INTERVAL,
    MONITOR_INCREMENTAL
)
from .hot_content_detector import HotContentDetector, HotLevel


class AccountMonitor:
    """
    账号监控器

    复用 XiaoHongShuCrawler 的浏览器和客户端能力，
    专注于账号监控和增量抓取。
    """

    def __init__(self):
        self.xhs_client: Optional[XiaoHongShuClient] = None
        self.browser_context = None
        self.context_page = None
        self.cdp_manager: Optional[CDPBrowserManager] = None
        self._initialized = False

        # 已抓取的笔记ID缓存（内存）
        self._crawled_note_ids: Set[str] = set()

        # MongoDB 存储
        self.mongo_store = MongoDBStoreBase(collection_prefix="monitor")

        # 爆款识别器
        self.hot_detector = HotContentDetector()

        # 索引 URL
        self.index_url = "https://www.xiaohongshu.com"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    async def init(self) -> bool:
        """
        初始化监控器（启动浏览器和客户端）

        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True

        try:
            utils.logger.info("[AccountMonitor] Initializing monitor...")

            # 启动 playwright
            self._playwright = await async_playwright().start()

            # 使用 CDP 模式启动浏览器
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[AccountMonitor] Launching browser using CDP mode")
                self.cdp_manager = CDPBrowserManager()
                self.browser_context = await self.cdp_manager.launch_and_connect(
                    playwright=self._playwright,
                    playwright_proxy=None,
                    user_agent=self.user_agent,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[AccountMonitor] Launching browser using standard mode")
                chromium = self._playwright.chromium
                browser = await chromium.launch(headless=config.HEADLESS)
                self.browser_context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=self.user_agent
                )
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            # 创建页面
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            # 创建 XHS 客户端
            self.xhs_client = await self._create_xhs_client()

            # 验证客户端
            if not await self.xhs_client.pong():
                utils.logger.warning("[AccountMonitor] XHS client pong failed, may need login")
                # 这里可以尝试使用保存的 cookie 登录
                # 暂时跳过，假设已经登录

            self._initialized = True
            utils.logger.info("[AccountMonitor] Monitor initialized successfully")
            return True

        except Exception as e:
            utils.logger.error(f"[AccountMonitor] Init failed: {e}")
            return False

    async def _create_xhs_client(self) -> XiaoHongShuClient:
        """创建 XHS 客户端"""
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        xhs_client = XiaoHongShuClient(
            proxy=None,
            headers={
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9",
                "cache-control": "no-cache",
                "content-type": "application/json;charset=UTF-8",
                "origin": "https://www.xiaohongshu.com",
                "pragma": "no-cache",
                "referer": "https://www.xiaohongshu.com/",
                "user-agent": self.user_agent,
                "Cookie": cookie_str,
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return xhs_client

    async def close(self):
        """关闭监控器"""
        if self.browser_context:
            await self.browser_context.close()
        if self.cdp_manager:
            await self.cdp_manager.close()
        if hasattr(self, '_playwright') and self._playwright:
            await self._playwright.stop()
        self._initialized = False
        utils.logger.info("[AccountMonitor] Monitor closed")

    async def monitor_accounts(
        self,
        account_urls: List[str],
        only_new: bool = True,
        max_notes: int = None
    ) -> List[Dict]:
        """
        监控账号列表，抓取内容

        Args:
            account_urls: 账号URL列表
            only_new: 是否只抓取新内容（增量模式）
            max_notes: 每个账号最多抓取笔记数

        Returns:
            抓取到的笔记列表
        """
        if not self._initialized:
            await self.init()

        max_notes = max_notes or MONITOR_MAX_NOTES_PER_ACCOUNT
        all_notes = []

        for creator_url in account_urls:
            try:
                utils.logger.info(f"[AccountMonitor] Monitoring account: {creator_url}")

                # 解析 URL 获取用户信息
                creator_info: CreatorUrlInfo = parse_creator_info_from_url(creator_url)
                user_id = creator_info.user_id

                # 获取创作者最新笔记
                notes = await self._fetch_creator_notes(
                    user_id=user_id,
                    xsec_token=creator_info.xsec_token,
                    xsec_source=creator_info.xsec_source,
                    max_notes=max_notes,
                    only_new=only_new and MONITOR_INCREMENTAL
                )

                if notes:
                    utils.logger.info(f"[AccountMonitor] Got {len(notes)} notes from {user_id}")
                    all_notes.extend(notes)

                    # 更新账号的最后抓取时间
                    await self._update_account_crawl_time(user_id)

                # 请求间隔
                await asyncio.sleep(MONITOR_REQUEST_INTERVAL)

            except Exception as e:
                utils.logger.error(f"[AccountMonitor] Failed to monitor {creator_url}: {e}")
                continue

        return all_notes

    async def _fetch_creator_notes(
        self,
        user_id: str,
        xsec_token: str,
        xsec_source: str,
        max_notes: int,
        only_new: bool
    ) -> List[Dict]:
        """
        获取创作者笔记

        Args:
            user_id: 用户ID
            xsec_token: 安全 token
            xsec_source: 安全 source
            max_notes: 最大笔记数
            only_new: 是否只获取新内容

        Returns:
            笔记列表
        """
        notes = []
        cursor = ""
        page_count = 0

        while len(notes) < max_notes:
            try:
                # 调用 API 获取笔记列表
                response = await self.xhs_client.get_notes_by_creator(
                    creator=user_id,
                    cursor=cursor,
                    page_size=min(20, max_notes - len(notes)),
                    xsec_token=xsec_token,
                    xsec_source=xsec_source
                )

                if not response or "notes" not in response:
                    break

                note_list = response.get("notes", [])
                if not note_list:
                    break

                for note in note_list:
                    note_id = note.get("note_id")

                    # 增量抓取：跳过已抓取的笔记
                    if only_new and await self._is_note_crawled(note_id):
                        continue

                    # 获取笔记详情
                    detail = await self._fetch_note_detail(
                        note_id=note_id,
                        xsec_source=note.get("xsec_source", xsec_source),
                        xsec_token=note.get("xsec_token", xsec_token)
                    )

                    if detail:
                        detail["source_user_id"] = user_id
                        notes.append(detail)

                        # 记录已抓取
                        await self._mark_note_crawled(note_id, user_id)

                        # 存储到 MongoDB
                        await self._save_note(detail)

                    if len(notes) >= max_notes:
                        break

                # 检查是否有更多
                if not response.get("has_more", False):
                    break

                cursor = response.get("cursor", "")
                page_count += 1

                # 避免翻页过多
                if page_count >= 5:
                    break

                await asyncio.sleep(MONITOR_REQUEST_INTERVAL)

            except Exception as e:
                utils.logger.error(f"[AccountMonitor] Fetch notes error: {e}")
                break

        return notes

    async def _fetch_note_detail(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str
    ) -> Optional[Dict]:
        """获取笔记详情"""
        try:
            detail = await self.xhs_client.get_note_by_id(
                note_id=note_id,
                xsec_source=xsec_source,
                xsec_token=xsec_token
            )

            if detail:
                detail.update({
                    "xsec_token": xsec_token,
                    "xsec_source": xsec_source
                })
                return detail

            # 如果 API 失败，尝试从 HTML 获取
            detail = await self.xhs_client.get_note_by_id_from_html(
                note_id=note_id,
                xsec_source=xsec_source,
                xsec_token=xsec_token,
                enable_cookie=True
            )

            if detail:
                detail.update({
                    "xsec_token": xsec_token,
                    "xsec_source": xsec_source
                })

            return detail

        except Exception as e:
            utils.logger.error(f"[AccountMonitor] Get note detail error: {e}")
            return None

    async def _is_note_crawled(self, note_id: str) -> bool:
        """检查笔记是否已抓取"""
        # 先检查内存缓存
        if note_id in self._crawled_note_ids:
            return True

        # 再检查数据库
        record = await self.mongo_store.find_one(
            "crawl_history",
            {"note_id": note_id}
        )
        if record:
            self._crawled_note_ids.add(note_id)
            return True

        return False

    async def _mark_note_crawled(self, note_id: str, source_user_id: str):
        """标记笔记已抓取"""
        self._crawled_note_ids.add(note_id)

        await self.mongo_store.save_or_update(
            "crawl_history",
            {"note_id": note_id},
            {
                "note_id": note_id,
                "source_user_id": source_user_id,
                "crawled_at": datetime.now().isoformat()
            }
        )

    async def _save_note(self, note: Dict):
        """保存笔记到 MongoDB"""
        note_id = note.get("note_id")

        # 识别爆款等级
        level, analysis = self.hot_detector.detect(note)
        note["hot_analysis"] = analysis

        # 保存到监控笔记集合
        await self.mongo_store.save_or_update(
            "notes",
            {"note_id": note_id},
            {
                **note,
                "crawled_at": datetime.now().isoformat()
            }
        )

        # 如果是爆款，单独保存到爆款集合
        if level != HotLevel.NORMAL:
            await self.mongo_store.save_or_update(
                "hot_notes",
                {"note_id": note_id},
                {
                    "note_id": note_id,
                    "title": note.get("title"),
                    "user_id": note.get("user_id"),
                    "nickname": note.get("nickname"),
                    "hot_level": level.value,
                    "hot_score": analysis.get("hot_score"),
                    "liked_count": analysis.get("liked_count"),
                    "collected_count": analysis.get("collected_count"),
                    "comment_count": analysis.get("comment_count"),
                    "detected_at": datetime.now().isoformat()
                }
            )

        # 同时保存到原有的 xhs_store（兼容现有系统）
        try:
            await xhs_store.update_xhs_note(note)
        except Exception:
            pass  # 忽略错误

    async def _update_account_crawl_time(self, user_id: str):
        """更新账号的最后抓取时间"""
        await self.mongo_store.save_or_update(
            "accounts",
            {"user_id": user_id},
            {
                "last_crawl_time": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        )

    async def detect_hot_notes(
        self,
        notes: List[Dict],
        min_level: HotLevel = HotLevel.TRENDING
    ) -> List[Dict]:
        """
        识别爆款笔记

        Args:
            notes: 笔记列表
            min_level: 最低爆款等级

        Returns:
            爆款笔记列表
        """
        return self.hot_detector.batch_detect(notes, min_level)


# 全局单例（延迟初始化）
_monitor_instance: Optional[AccountMonitor] = None


async def get_monitor() -> AccountMonitor:
    """获取监控器单例"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = AccountMonitor()
    return _monitor_instance
