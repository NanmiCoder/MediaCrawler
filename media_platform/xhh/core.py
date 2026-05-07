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
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    async_playwright,
)

import config
from base.base_crawler import AbstractCrawler
from store import xhh as xhh_store
from tools import utils

from .login import XiaoHeiHeLogin


class XiaoHeiHeCrawler(AbstractCrawler):
    """小黑盒（XiaoHeiHe）爬虫核心类

    支持 detail 模式：抓取指定 link_id 帖子的详情（标题、正文、图片、作者等）。

    技术方案：
    - 使用 Playwright 渲染页面，通过拦截 /bbs/app/link/tree API 获取结构化数据
    - 登录态通过 Cookie 文件（~/.xhh_cookies.json）或二维码扫码维持
    - 二维码登录：打开首页点击登录按鈕触发 get_qrcode_url API，弹出 PIL 图片窗口供扫码
    - 签名算法（hkey）由 Playwright 页面 JS 自动处理，无需手动实现
    """

    context_page: Page
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.index_url = "https://www.xiaoheihe.cn/app/bbs/home"
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )

    async def start(self) -> None:
        """启动爬虫主流程"""
        async with async_playwright() as playwright:
            self.browser_context = await self.launch_browser(
                playwright.chromium,
                None,
                self.user_agent,
                headless=config.HEADLESS,
            )

            # 注入反检测脚本
            stealth_js = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "libs", "stealth.min.js",
            )
            if os.path.exists(stealth_js):
                await self.browser_context.add_init_script(path=stealth_js)

            self.context_page = await self.browser_context.new_page()

            # 拦截 get_qrcode_url API，将 qr_url 注入页面全局变量供 login.py 读取
            await self.context_page.route(
                "**/account/get_qrcode_url/**",
                self._handle_qrcode_url,
            )

            # 登录
            login_obj = XiaoHeiHeLogin(
                login_type=config.LOGIN_TYPE,
                browser_context=self.browser_context,
                context_page=self.context_page,
            )
            await login_obj.begin()

            # 保存登录态
            if config.SAVE_LOGIN_STATE:
                await self._save_login_state()

            utils.logger.info(
                f"[XiaoHeiHeCrawler.start] Login OK, crawler_type={config.CRAWLER_TYPE}"
            )

            if config.CRAWLER_TYPE == "detail":
                await self.get_specified_posts()
            else:
                utils.logger.warning(
                    f"[XiaoHeiHeCrawler.start] Unsupported crawler_type={config.CRAWLER_TYPE}. "
                    "Only 'detail' is supported for xiaoheihe."
                )

            await self.context_page.close()
            await self.browser_context.close()

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

    async def _save_login_state(self) -> None:
        """保存登录 Cookie 到 XHH_COOKIE_FILE"""
        cookie_file = Path(os.path.expanduser(config.XHH_COOKIE_FILE))
        cookies = await self.browser_context.cookies()
        cookie_file.write_text(json.dumps(cookies, ensure_ascii=False, indent=2))
        utils.logger.info(f"[XiaoHeiHeCrawler] Login state saved to {cookie_file}")

    async def search(self) -> None:
        """关键词搜索（小黑盒暂不支持）"""
        utils.logger.warning(
            "[XiaoHeiHeCrawler.search] Keyword search not supported for xiaoheihe."
        )

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

        # 顺序抓取（小黑盒风控较严，避免并发触发验证码）
        for link_id in link_id_list:
            result = await self.fetch_post_detail(link_id)
            if result:
                await xhh_store.update_xhh_post(result)
            await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

    async def fetch_post_detail(self, link_id: str) -> Optional[Dict]:
        """抓取单个帖子详情

        使用 expect_response() 同步等待 /bbs/app/link/tree API 响应。
        登录态由浏览器 Cookie 自动携带，无需手动签名。

        Args:
            link_id: 小黑盒帖子 ID（URL 末段数字）

        Returns:
            规范化的帖子字典，失败时返回 None
        """
        utils.logger.info(
            f"[XiaoHeiHeCrawler.fetch_post_detail] Fetching link_id={link_id}"
        )
        url = f"https://www.xiaoheihe.cn/app/bbs/link/{link_id}"

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

            post_data = body.get("result", {})
            normalized = _normalize_post(post_data, link_id)
            utils.logger.info(
                f"[XiaoHeiHeCrawler.fetch_post_detail] "
                f"title={normalized.get('title', '')[:40]}"
            )
            return normalized

        except Exception as e:
            utils.logger.warning(
                f"[XiaoHeiHeCrawler.fetch_post_detail] "
                f"Failed for link_id={link_id}: {e}"
            )
            return None

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """启动 Chromium 浏览器"""
        utils.logger.info(
            f"[XiaoHeiHeCrawler.launch_browser] "
            f"headless={headless}, proxy={'yes' if playwright_proxy else 'no'}"
        )
        browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
        return await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=user_agent,
        )

    async def close(self) -> None:
        await self.browser_context.close()


# ─── 数据规范化 ────────────────────────────────────────────────────────────────────────────

def _normalize_post(api_result: Dict, link_id: str) -> Dict:
    """将小黑盒 link/tree API 返回结构规范化为统一存储字段

    Args:
        api_result: API response["result"] 字典
        link_id:    帖子 ID

    Returns:
        扁平化的帖子字典，供 store.xhh.update_xhh_post 存储
    """
    post = (
        api_result.get("post_data")
        or api_result.get("heylink")
        or api_result.get("link")
        or api_result.get("data")
        or api_result
    )

    # 标题
    title = post.get("title") or post.get("topic") or post.get("name") or ""

    # 作者
    author_nickname = ""
    author_id = ""
    for key in ("user", "author", "creator"):
        author_obj = post.get(key, {})
        if isinstance(author_obj, dict):
            author_nickname = author_obj.get("nickname") or author_obj.get("name") or ""
            author_id = str(author_obj.get("user_id") or author_obj.get("id") or "")
            if author_nickname:
                break

    # 正文 & 图片（富文本块格式：[{"type": "html"|"img"|"text", ...}]）
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

    # 从其他字段补充图片列表
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

    content_type = (
        "video" if (post.get("video") or post.get("video_url"))
        else "image_text" if images
        else "article"
    )

    interact = post.get("interact_info") or post.get("stats") or {}

    return {
        "link_id": str(link_id),
        "title": title,
        "content": "\n\n".join(content_parts),
        "content_type": content_type,
        "image_list": ",".join(images),
        "author_id": author_id,
        "author_nickname": author_nickname,
        "like_count": str(interact.get("like_count") or interact.get("liked_count") or 0),
        "comment_count": str(interact.get("comment_count") or 0),
        "share_count": str(interact.get("share_count") or 0),
        "post_time": str(post.get("create_time") or post.get("time") or 0),
        "url": f"https://www.xiaoheihe.cn/app/bbs/link/{link_id}",
        "last_modify_ts": str(utils.get_current_timestamp()),
    }
