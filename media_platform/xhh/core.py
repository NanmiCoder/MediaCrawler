# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
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
import os
import random
import re
from typing import Dict, List, Optional

import httpx
from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    async_playwright,
)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import xhh as xhh_store
from tools import utils
from var import crawler_type_var

from .login import XiaoHeiHeLogin


class XiaoHeiHeCrawler(AbstractCrawler):
    """小黑盒（XiaoHeiHe）爬虫核心类

    支持三种爬取模式：
    - detail:  抓取 XHH_SPECIFIED_ID_LIST 中指定帖子的详情
    - search:  按 KEYWORDS 关键词搜索帖子
    - creator: 抓取 XHH_CREATOR_ID_LIST 中创作者的全部帖子

    技术方案：
    - 使用 Playwright 持久化浏览器上下文（browser_data/xhh_user_data_dir/）维持登录态
    - 所有 API 调用通过 page.route 拦截 + expect_response + page.goto/reload 实现
    - 小黑盒 API 需要 hkey 签名，由浏览器 JS 自动处理，无需 Python 侧实现
    """

    context_page: Page
    browser_context: BrowserContext

    # page.route 拦截器使用的可变状态（通过 list 实现 Python 闭包可变引用）
    _comment_page: List[int]   # [目标评论页码]
    _search_offset: List[int]  # [目标搜索 offset]
    _creator_offset: List[int] # [目标创作者帖子 offset]

    def __init__(self) -> None:
        self.index_url = "https://www.xiaoheihe.cn/app/bbs/home"
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
        self._comment_page = [1]
        self._search_offset = [0]
        self._creator_offset = [0]
        self.ip_proxy_pool = None

    async def start(self) -> None:
        """启动爬虫主流程"""
        playwright_proxy_format = None
        if config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(
                config.IP_PROXY_POOL_COUNT, enable_validate_ip=True
            )
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, _ = utils.format_proxy_info(ip_proxy_info)
            utils.logger.info(
                f"[XiaoHeiHeCrawler.start] Using proxy: {ip_proxy_info.ip}:{ip_proxy_info.port}"
            )

        async with async_playwright() as playwright:
            self.browser_context = await self.launch_browser(
                playwright.chromium,
                playwright_proxy_format,
                self.user_agent,
                headless=config.HEADLESS,
            )
            await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()

            # 注册 page.route 拦截器（评论翻页、搜索翻页、创作者帖子翻页）
            await self._register_routes()

            # 拦截 get_qrcode_url API，将 qr_url 注入页面全局变量供 login.py 读取
            await self.context_page.route(
                "**/account/get_qrcode_url/**",
                self._handle_qrcode_url,
            )

            # 先导航到首页，触发登录态检测
            await self.context_page.goto(self.index_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1)

            # 检查是否已登录（是否有 heybox_id cookie）
            cookies = await self.browser_context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            if not cookie_dict.get("heybox_id"):
                login_obj = XiaoHeiHeLogin(
                    login_type=config.LOGIN_TYPE,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()

            crawler_type_var.set(config.CRAWLER_TYPE)
            utils.logger.info(
                f"[XiaoHeiHeCrawler.start] Login OK, crawler_type={config.CRAWLER_TYPE}"
            )

            if config.CRAWLER_TYPE == "detail":
                await self.get_specified_posts()
            elif config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE == "creator":
                await self.get_creators_and_posts()
            else:
                raise ValueError(
                    f"[XiaoHeiHeCrawler.start] Unsupported crawler_type={config.CRAWLER_TYPE!r}. "
                    "Supported values: detail | search | creator"
                )

            utils.logger.info("[XiaoHeiHeCrawler.start] Crawler finished ...")
            await self.context_page.close()
            await self.browser_context.close()

    # ─── route 拦截器注册 ──────────────────────────────────────────────────

    async def _register_routes(self) -> None:
        """注册所有 API 拦截路由（修改翻页参数）"""

        async def intercept_link_tree(route, request):
            """评论翻页：替换 link/tree 请求的 page 参数"""
            url = request.url
            pg = self._comment_page[0]
            new_url = re.sub(r"([?&])page=\d+", lambda m: f"{m.group(1)}page={pg}", url)
            if "page=" not in url:
                sep = "&" if "?" in url else "?"
                new_url = url + f"{sep}page={pg}"
            await route.continue_(url=new_url)

        async def intercept_search(route, request):
            """搜索翻页：替换 general/search/v1 请求的 offset 参数"""
            url = request.url
            offset = self._search_offset[0]
            new_url = re.sub(r"([?&])offset=\d+", lambda m: f"{m.group(1)}offset={offset}", url)
            if "offset=" not in url:
                sep = "&" if "?" in url else "?"
                new_url = url + f"{sep}offset={offset}"
            await route.continue_(url=new_url)

        async def intercept_creator_links(route, request):
            """创作者帖子翻页：替换 profile/user/link/list 请求的 offset 参数"""
            url = request.url
            offset = self._creator_offset[0]
            new_url = re.sub(r"([?&])offset=\d+", lambda m: f"{m.group(1)}offset={offset}", url)
            if "offset=" not in url:
                sep = "&" if "?" in url else "?"
                new_url = url + f"{sep}offset={offset}"
            await route.continue_(url=new_url)

        await self.context_page.route("**/bbs/app/link/tree**", intercept_link_tree)
        await self.context_page.route("**/bbs/app/api/general/search/v1**", intercept_search)
        await self.context_page.route("**/bbs/app/profile/user/link/list**", intercept_creator_links)

    async def _handle_qrcode_url(self, route, request) -> None:
        """拦截 get_qrcode_url API，将 qr_url 写入页面 JS 全局变量"""
        response = await route.fetch()
        try:
            body = await response.json()
            qr_url = body.get("result", {}).get("qr_url", "")
            if qr_url:
                await self.context_page.evaluate(
                    f"() => {{ window.__xhh_qr_url__ = {json.dumps(qr_url)}; }}"
                )
        except Exception:
            pass
        await route.fulfill(response=response)

    # ─── detail 模式 ───────────────────────────────────────────────────

    async def get_specified_posts(self) -> None:
        """抓取 XHH_SPECIFIED_ID_LIST 中指定的帖子详情"""
        link_id_list: List[str] = config.XHH_SPECIFIED_ID_LIST
        if not link_id_list:
            utils.logger.warning(
                "[XiaoHeiHeCrawler.get_specified_posts] "
                "XHH_SPECIFIED_ID_LIST is empty. Please set it in config/xhh_config.py"
            )
            return

        utils.logger.info(
            f"[XiaoHeiHeCrawler.get_specified_posts] Fetching {len(link_id_list)} posts ..."
        )
        for link_id in link_id_list:
            await self._fetch_and_store_post(link_id)
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

    # ─── search 模式 ───────────────────────────────────────────────────

    async def search(self) -> None:
        """按关键词搜索帖子（通过 page.route 拦截 offset 参数翻页）"""
        utils.logger.info("[XiaoHeiHeCrawler.search] Begin search xiaoheihe keywords")
        # 先在首页自然停留一会，模拟正常用户行为
        await self.context_page.goto(self.index_url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)
        for keyword in config.KEYWORDS.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue
            utils.logger.info(f"[XiaoHeiHeCrawler.search] Current keyword: {keyword}")

            # 导航到搜索页并在 expect_response 内输入关键词触发 API
            fetched = 0
            offset = 0
            limit = 30

            while fetched < config.CRAWLER_MAX_NOTES_COUNT:
                self._search_offset[0] = offset

                try:
                    async with self.context_page.expect_response(
                        lambda r: "general/search/v1" in r.url and r.status == 200,
                        timeout=20000,
                    ) as resp_info:
                        if offset == 0:
                            # 第一页：导航 + 输入关键词触发搜索
                            await self.context_page.goto(
                                "https://www.xiaoheihe.cn/app/bbs/search",
                                wait_until="domcontentloaded",
                                timeout=15000,
                            )
                            await asyncio.sleep(1)
                            await self.context_page.fill('input[type="text"]', keyword)
                            await self.context_page.keyboard.press("Enter")
                        else:
                            # 翻页：reload 触发重新请求
                            await self.context_page.reload(wait_until="domcontentloaded")
                    resp = await resp_info.value
                except Exception as e:
                    utils.logger.warning(
                        f"[XiaoHeiHeCrawler.search] No search response at offset={offset}: {e}"
                    )
                    break

                body = await resp.json()
                result = body.get("result", {})
                items = result.get("items", [])

                link_ids = [
                    str(item["info"]["linkid"])
                    for item in items
                    if isinstance(item.get("info"), dict) and item["info"].get("linkid")
                ]

                if not link_ids:
                    utils.logger.info(
                        f"[XiaoHeiHeCrawler.search] No more posts for keyword={keyword}"
                    )
                    break

                for link_id in link_ids:
                    if fetched >= config.CRAWLER_MAX_NOTES_COUNT:
                        break
                    await self._fetch_and_store_post(link_id)
                    fetched += 1
                    await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

                if result.get("no_more") or len(link_ids) < limit:
                    break
                offset += limit

    # ─── creator 模式 ──────────────────────────────────────────────────

    async def get_creators_and_posts(self) -> None:
        """抓取 XHH_CREATOR_ID_LIST 中创作者的信息和全部帖子"""
        utils.logger.info("[XiaoHeiHeCrawler.get_creators_and_posts] Begin get xiaoheihe creators")
        # 先在首页自然停留一会，模拟正常用户行为，降低风控触发概率
        await self.context_page.goto(self.index_url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)
        for user_id in config.XHH_CREATOR_ID_LIST:
            user_id = str(user_id)
            await self._fetch_creator_and_posts(user_id)
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

    async def _fetch_creator_and_posts(self, user_id: str) -> None:
        """获取创作者信息和全部帖子

        第一次 goto 用户主页时，profile/user/profile 和 profile/user/link/list
        两个 API 同时触发，用 on_response 回调立即读取，避免 body 被浏览器回收。
        翻页通过 reload 重新触发 link/list。
        """
        offset = 0
        limit = 30
        fetched = 0

        while fetched < config.CRAWLER_MAX_NOTES_COUNT:
            self._creator_offset[0] = offset

            captured_profile: Dict = {}
            captured_links: Dict = {}
            profile_event = asyncio.Event()
            links_event = asyncio.Event()

            async def on_response(resp):
                if "profile/user/profile" in resp.url and resp.status == 200 and not captured_profile:
                    try:
                        captured_profile["body"] = await resp.json()
                    except Exception:
                        captured_profile["body"] = {}
                    profile_event.set()
                elif "profile/user/link/list" in resp.url and resp.status == 200:
                    try:
                        captured_links["body"] = await resp.json()
                    except Exception:
                        captured_links["body"] = {}
                    links_event.set()

            self.context_page.on("response", on_response)
            try:
                if offset == 0:
                    await self.context_page.goto(
                        f"https://www.xiaoheihe.cn/app/user/profile/{user_id}",
                        wait_until="domcontentloaded",
                        timeout=20000,
                    )
                else:
                    await self.context_page.reload(wait_until="domcontentloaded")

                # 等待 link/list 响应（最多 15 秒）
                try:
                    await asyncio.wait_for(links_event.wait(), timeout=15)
                except asyncio.TimeoutError:
                    utils.logger.warning(
                        f"[XiaoHeiHeCrawler._fetch_creator_and_posts] "
                        f"Timeout waiting for link/list at offset={offset} for user_id={user_id}"
                    )
                    break
            finally:
                self.context_page.remove_listener("response", on_response)

            # 第一页同时保存创作者信息
            if offset == 0 and captured_profile.get("body"):
                account_detail = captured_profile["body"].get("result", {}).get("account_detail")
                if account_detail:
                    await xhh_store.update_xhh_creator(account_detail)

            posts = captured_links.get("body", {}).get("post_links", [])
            api_status = captured_links.get("body", {}).get("status", "")
            if not posts:
                if api_status == "show_captcha":
                    utils.logger.warning(
                        f"[XiaoHeiHeCrawler._fetch_creator_and_posts] "
                        f"show_captcha for link/list at offset={offset}, user_id={user_id}"
                    )
                else:
                    utils.logger.info(
                        f"[XiaoHeiHeCrawler._fetch_creator_and_posts] "
                        f"No more posts at offset={offset}, user_id={user_id}"
                    )
                break

            for post in posts:
                if fetched >= config.CRAWLER_MAX_NOTES_COUNT:
                    break
                # profile/user/link/list 接口返回 "linkid"，
                # 但部分旧版 API / 搜索接口返回 "link_id"，两者均需兼容
                link_id = str(post.get("linkid") or post.get("link_id") or "")
                if not link_id:
                    continue
                await self._fetch_and_store_post(link_id)
                fetched += 1
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            if len(posts) < limit:
                break
            offset += limit

    # ─── 评论抓取 ────────────────────────────────────────────────────

    async def get_comments(
        self,
        link_id: str,
        start_page: int = 2,
        total_page: int = 1,
        already_collected: int = 0,
    ) -> None:
        """抓取指定帖子的评论（从 start_page 开始翻页，第 1 页由 fetch_post_detail 已提取）"""
        if not config.ENABLE_GET_COMMENTS:
            return
        if start_page > total_page:
            return

        utils.logger.info(
            f"[XiaoHeiHeCrawler.get_comments] Fetching comments for link_id={link_id} "
            f"from page={start_page}/{total_page}"
        )

        max_count = config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES
        total_collected = already_collected

        for pg in range(start_page, total_page + 1):
            if total_collected >= max_count:
                break

            self._comment_page[0] = pg

            resp = None
            for attempt in range(3):
                try:
                    async with self.context_page.expect_response(
                        lambda r: "/bbs/app/link/tree" in r.url and r.status == 200,
                        timeout=20000,
                    ) as resp_info:
                        await self.context_page.reload(wait_until="domcontentloaded")
                    resp = await resp_info.value
                    break
                except Exception as e:
                    wait = 2 ** attempt
                    utils.logger.warning(
                        f"[XiaoHeiHeCrawler.get_comments] "
                        f"Attempt {attempt + 1}/3 failed at page={pg} for link_id={link_id}: {e}. "
                        f"Retrying in {wait}s ..."
                    )
                    if attempt < 2:
                        await asyncio.sleep(wait)
            if resp is None:
                utils.logger.warning(
                    f"[XiaoHeiHeCrawler.get_comments] "
                    f"All retries exhausted at page={pg} for link_id={link_id}, stopping."
                )
                break

            body = await resp.json()
            result = body.get("result", {})

            floors = result.get("comments", [])
            main_comments = []
            for floor in floors:
                comments_in_floor = floor.get("comment", [])
                if not comments_in_floor:
                    continue
                if config.ENABLE_GET_SUB_COMMENTS:
                    main_comments.extend(comments_in_floor)
                else:
                    main_comments.append(comments_in_floor[0])

            remaining = max_count - total_collected
            to_store = main_comments[:remaining]

            if to_store:
                await xhh_store.batch_update_xhh_post_comments(link_id, to_store)
                total_collected += len(to_store)

            utils.logger.info(
                f"[XiaoHeiHeCrawler.get_comments] "
                f"link_id={link_id} page={pg}/{total_page} stored={total_collected}"
            )

            if pg < total_page and total_collected < max_count:
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

        utils.logger.info(
            f"[XiaoHeiHeCrawler.get_comments] "
            f"Done link_id={link_id}, total comments stored={total_collected}"
        )

    # ─── 通用：抓取 + 存储单个帖子（含评论） ────────────────────────────

    async def _fetch_and_store_post(self, link_id: str) -> None:
        """抓取单个帖子详情并存储（含评论和媒体文件）
        
        优化：fetch_post_detail 的 goto 已经触发了 link/tree page=1 请求，
        同时包含帖子内容和第 1 页评论，直接提取复用，评论从第 2 页开始翻页。
        """
        detail_result = await self.fetch_post_detail(link_id)
        if not detail_result:
            return

        post_data, first_page_comments, comment_total_page = detail_result
        await xhh_store.update_xhh_post(post_data)
        await self.get_notice_media(post_data)

        # 存储第 1 页评论
        if first_page_comments:
            await xhh_store.batch_update_xhh_post_comments(link_id, first_page_comments)

        # 从第 2 页开始继续抓取评论
        await self.get_comments(
            link_id,
            start_page=2,
            total_page=comment_total_page,
            already_collected=len(first_page_comments),
        )

    # ─── 媒体下载 ────────────────────────────────────────────────────

    async def get_notice_media(self, post_item: Dict) -> None:
        """下载帖子的图片和视频到本地（受 ENABLE_GET_MEIDAS 开关控制）"""
        if not config.ENABLE_GET_MEIDAS:
            return
        await self.get_post_images(post_item)
        await self.get_notice_video(post_item)

    async def get_post_images(self, post_item: Dict) -> None:
        """下载帖子图片到 data/xhh/images/<link_id>/"""
        if not config.ENABLE_GET_MEIDAS:
            return
        link_id = post_item.get("link_id", "")
        image_list_str = post_item.get("image_list", "")
        if not image_list_str:
            return
        image_urls = [u for u in image_list_str.split(",") if u]
        for idx, url in enumerate(image_urls):
            content = await _download_media(url)
            await asyncio.sleep(random.random())
            if content is None:
                continue
            await xhh_store.update_xhh_post_image(link_id, content, f"{idx}.jpg")

    async def get_notice_video(self, post_item: Dict) -> None:
        """下载帖子视频到 data/xhh/videos/<link_id>/"""
        if not config.ENABLE_GET_MEIDAS:
            return
        link_id = post_item.get("link_id", "")
        video_url = post_item.get("video_url", "")
        if not video_url:
            return
        content = await _download_media(video_url)
        await asyncio.sleep(random.random())
        if content is None:
            return
        await xhh_store.update_xhh_post_video(link_id, content, "0.mp4")

    async def fetch_post_detail(self, link_id: str, max_retries: int = 3) -> Optional[tuple]:
        """抓取单个帖子详情（同时提取第 1 页评论，避免额外 reload）

        使用 expect_response() 同步等待 /bbs/app/link/tree API 响应（page=1）。
        该 API 同时返回帖子内容和第 1 页评论，一次请求获取全部数据。
        网络错误时自动重试，最多 max_retries 次，每次等待 2^attempt 秒。

        Args:
            link_id: 小黑盒帖子 ID
            max_retries: 最大重试次数（默认 3）

        Returns:
            (normalized_post, first_page_comments, total_page) 三元组，失败时返回 None
        """
        utils.logger.info(
            f"[XiaoHeiHeCrawler.fetch_post_detail] Fetching link_id={link_id}"
        )
        url = f"https://www.xiaoheihe.cn/app/bbs/link/{link_id}"
        self._comment_page[0] = 1  # 帖子详情始终请求第 1 页

        for attempt in range(max_retries):
            try:
                async with self.context_page.expect_response(
                    lambda r: "/bbs/app/link/tree" in r.url and r.status == 200,
                    timeout=20000,
                ) as resp_info:
                    await self.context_page.goto(
                        url, wait_until="domcontentloaded", timeout=25000
                    )

                response = await resp_info.value
                body = await response.json()

                if body.get("status") != "ok":
                    utils.logger.warning(
                        f"[XiaoHeiHeCrawler.fetch_post_detail] "
                        f"API status={body.get('status')} for link_id={link_id}"
                    )
                    return None

                result = body.get("result", {})
                normalized = _normalize_post(result, link_id)
                utils.logger.info(
                    f"[XiaoHeiHeCrawler.fetch_post_detail] "
                    f"title={normalized.get('title', '')[:40]}"
                )

                # 同时提取第 1 页评论
                first_page_comments = _extract_comments_from_result(result)
                total_page = result.get("total_page", 1)

                return (normalized, first_page_comments, total_page)

            except Exception as e:
                wait = 2 ** attempt
                utils.logger.warning(
                    f"[XiaoHeiHeCrawler.fetch_post_detail] "
                    f"Attempt {attempt + 1}/{max_retries} failed for link_id={link_id}: {e}. "
                    f"Retrying in {wait}s ..."
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait)

        utils.logger.warning(
            f"[XiaoHeiHeCrawler.fetch_post_detail] "
            f"All {max_retries} attempts failed for link_id={link_id}"
        )
        return None

    # ─── 浏览器启动 ────────────────────────────────────────────────────

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("[XiaoHeiHeCrawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(
                os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM
            )
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
            return browser_context

    async def close(self) -> None:
        await self.browser_context.close()


# ─── 评论提取工具 ────────────────────────────────────────────────────

def _extract_comments_from_result(api_result: Dict) -> List[Dict]:
    """从 link/tree API 响应中提取评论列表（受 ENABLE_GET_SUB_COMMENTS 控制）"""
    floors = api_result.get("comments", [])
    comments = []
    for floor in floors:
        comments_in_floor = floor.get("comment", [])
        if not comments_in_floor:
            continue
        if config.ENABLE_GET_SUB_COMMENTS:
            comments.extend(comments_in_floor)
        else:
            comments.append(comments_in_floor[0])
    return comments


# ─── 媒体下载工具 ────────────────────────────────────────────────────

async def _download_media(url: str, timeout: int = 30) -> Optional[bytes]:
    """下载媒体文件，返回字节内容，失败时返回 None"""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        utils.logger.warning(f"[xhh._download_media] Failed to download {url}: {e}")
        return None


# ─── 数据规范化 ──────────────────────────────────────────────────────

def _normalize_post(api_result: Dict, link_id: str) -> Dict:
    """将小黑盒 link/tree API 返回结构规范化为统一存储字段"""
    post = (
        api_result.get("post_data")
        or api_result.get("heylink")
        or api_result.get("link")
        or api_result.get("data")
        or api_result
    )

    title = post.get("title") or post.get("topic") or post.get("name") or ""

    author_nickname = ""
    author_id = ""
    for key in ("user", "author", "creator"):
        author_obj = post.get(key, {})
        if isinstance(author_obj, dict):
            author_nickname = (
                author_obj.get("username")
                or author_obj.get("nickname")
                or author_obj.get("name")
                or ""
            )
            author_id = str(
                author_obj.get("userid")
                or author_obj.get("user_id")
                or author_obj.get("id")
                or ""
            )
            if author_nickname:
                break
    if not author_id:
        author_id = str(post.get("userid") or "")

    raw_content = post.get("content") or post.get("desc") or post.get("text") or ""
    content_parts: List[str] = []
    images: List[str] = []

    def _parse_blocks(blocks: list) -> None:
        for block in blocks:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "html":
                clean = re.sub(r"<[^>]+>", "", block.get("text", "")).strip()
                clean = re.sub(r"\n{3,}", "\n\n", clean)
                if clean:
                    content_parts.append(clean)
            elif btype == "img":
                img_url = block.get("url") or block.get("src") or ""
                if img_url:
                    images.append(img_url)
            elif btype == "text":
                t = block.get("text", "").strip()
                if t:
                    content_parts.append(t)

    if isinstance(raw_content, list):
        _parse_blocks(raw_content)
    elif isinstance(raw_content, str) and raw_content.strip().startswith("["):
        try:
            _parse_blocks(json.loads(raw_content))
        except (json.JSONDecodeError, Exception):
            content_parts.append(re.sub(r"<[^>]+>", "", raw_content).strip())
    elif raw_content:
        content_parts.append(re.sub(r"<[^>]+>", "", str(raw_content)).strip())

    if not images:
        for img_key in ("image_list", "images", "pics", "image"):
            img_list = post.get(img_key, [])
            if isinstance(img_list, list) and img_list:
                for img in img_list:
                    if isinstance(img, dict):
                        for size_key in ("origin", "large", "url", "src"):
                            if img.get(size_key):
                                images.append(img[size_key])
                                break
                    elif isinstance(img, str):
                        images.append(img)
                break

    video_url = ""
    video_obj = post.get("video")
    if isinstance(video_obj, dict):
        video_url = (
            video_obj.get("url")
            or video_obj.get("play_url")
            or video_obj.get("src")
            or ""
        )
    elif isinstance(video_obj, str):
        video_url = video_obj
    if not video_url:
        video_url = post.get("video_url") or ""

    content_type = (
        "video" if video_url
        else "image_text" if images
        else "article"
    )

    interact = post.get("interact_info") or post.get("stats") or {}

    return {
        "link_id": str(link_id),
        "title": title,
        "content": "\n\n".join(content_parts),
        "content_type": content_type,
        "video_url": video_url,
        "image_list": ",".join(images),
        "author_id": author_id,
        "author_nickname": author_nickname,
        "like_count": str(
            post.get("up")
            or interact.get("like_count")
            or interact.get("liked_count")
            or 0
        ),
        "comment_count": str(
            post.get("comment_num")
            or interact.get("comment_count")
            or 0
        ),
        "share_count": str(
            post.get("forward_num")
            or interact.get("share_count")
            or 0
        ),
        "collect_count": str(post.get("favour_count") or 0),
        "post_time": str(
            post.get("create_at")
            or post.get("create_time")
            or post.get("time")
            or 0
        ),
        "url": f"https://www.xiaoheihe.cn/app/bbs/link/{link_id}",
        "last_modify_ts": str(utils.get_current_timestamp()),
    }
