# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tools/session_check.py
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

"""
会话预检 (session preflight)：开爬之前先确认登录态与代理是否可用。

三条设计约束：

1. 只发一次平台请求。预检不该给平台增加压力，也不做自动登录或 token 刷新。
2. 要能说出原因。各平台 client 的 pong() 把异常吞掉只返回 bool，所以这里直接调用
   pong() 内部的那一个请求，让异常冒出来再归类（cookie 失效 / 代理不通 / 被限流
   / 响应异常）。
3. 登录态从用户实际使用的地方读：优先 config.COOKIES（--cookies 传入），否则读
   qrcode 登录留下的浏览器 profile（browser_data/），两条路径都只发一次请求。

抖音与百度贴吧的 pong() 读的是浏览器 localStorage / cookie，没有真正的登录态接口，
所以这两个平台只给 cookie 层面的线索，结果标记为 unknown 而不是伪装成功。
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import httpx

import config
from tools import utils

# 单平台预检的最长等待时间，避免代理不通时卡住。
CHECK_TIMEOUT_SECONDS = 20

# 无需浏览器即可联网验证登录态的平台。
NETWORK_CHECKABLE_PLATFORMS = ("xhs", "bili", "wb", "zhihu", "ks")
# pong() 只读浏览器状态、无法在预检里联网验证的平台。
BROWSER_ONLY_PLATFORMS = ("dy", "tieba")

PLATFORM_LABELS: Dict[str, str] = {
    "xhs": "xiaohongshu",
    "dy": "douyin",
    "ks": "kuaishou",
    "bili": "bilibili",
    "wb": "weibo",
    "tieba": "tieba",
    "zhihu": "zhihu",
}

# 缺少这些 cookie 时，请求还没发出去就会失败，先拦下来给出更准确的提示：
# xhs 的 sign_with_xhshow 缺 a1 会抛 ValueError；zhihu 的 _pre_headers 缺 d_c0 会抛异常。
REQUIRED_COOKIE_KEYS: Dict[str, Tuple[str, ...]] = {
    "xhs": ("a1",),
    "zhihu": ("d_c0",),
}

STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_UNKNOWN = "unknown"

CAUSE_NO_SESSION = "no saved session"
CAUSE_MISSING_COOKIE_KEYS = "cookie is missing required fields"
CAUSE_EXPIRED = "session expired or cookie is invalid"
CAUSE_PROXY = "proxy is not usable"
CAUSE_NETWORK = "network unreachable"
CAUSE_BLOCKED = "blocked or rate limited by the platform"
CAUSE_TIMEOUT = "request timed out"
CAUSE_UNEXPECTED = "unexpected response"
CAUSE_BROWSER_REQUIRED = "needs a browser to verify"


@dataclass
class SessionCheckResult:
    """单个平台的预检结果。"""

    platform: str
    status: str
    cause: str = ""
    detail: str = ""

    @property
    def label(self) -> str:
        return PLATFORM_LABELS.get(self.platform, self.platform)

    def render(self) -> str:
        icon = {STATUS_OK: "[ OK ]", STATUS_FAILED: "[FAIL]", STATUS_UNKNOWN: "[ ?? ]"}.get(self.status, "[ ?? ]")
        line = f"{icon} {self.platform:<6} {self.label:<12} {self.status}"
        if self.cause:
            line = f"{line} - {self.cause}"
        if self.detail:
            line = f"{line} ({self.detail})"
        return line


def _classify_exception(exc: BaseException) -> Tuple[str, str]:
    """把探测过程中的异常归类成 (原因, 细节)。"""

    if isinstance(exc, asyncio.TimeoutError):
        return CAUSE_TIMEOUT, f"no answer within {CHECK_TIMEOUT_SECONDS}s"

    if isinstance(exc, httpx.ProxyError):
        return CAUSE_PROXY, str(exc) or exc.__class__.__name__

    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout)):
        cause = CAUSE_PROXY if config.ENABLE_IP_PROXY else CAUSE_NETWORK
        return cause, exc.__class__.__name__

    # 各平台异常类名相同但定义在不同模块，按名字归类比逐个 import 更省事。
    exc_name = exc.__class__.__name__
    if exc_name in ("IPBlockError", "PlatformAccessError", "ForbiddenError"):
        return CAUSE_BLOCKED, exc_name

    if exc_name == "RetryError":
        # tenacity 重试耗尽后包了一层，取最后一次的真实异常再归类。
        last_exc = _unwrap_retry_error(exc)
        if last_exc is not None and last_exc is not exc:
            return _classify_exception(last_exc)
        return (CAUSE_PROXY if config.ENABLE_IP_PROXY else CAUSE_NETWORK), exc_name

    if exc_name == "DataFetchError":
        return CAUSE_UNEXPECTED, str(exc) or exc_name

    return CAUSE_UNEXPECTED, f"{exc_name}: {exc}"


def _unwrap_retry_error(exc: BaseException) -> Optional[BaseException]:
    """取出 tenacity RetryError 内部最后一次失败的异常。"""

    last_attempt = getattr(exc, "last_attempt", None)
    if last_attempt is None:
        return None
    try:
        if last_attempt.failed:
            return last_attempt.exception()
    except Exception:  # noqa: BLE001 - 拿不到就按 RetryError 本身处理
        return None
    return None


async def _resolve_proxy() -> Optional[str]:
    """按当前配置取一个可用代理，返回 httpx 可用的代理地址。

    只取一个 IP，不预热整个代理池——预检要保持轻量。
    """

    if not config.ENABLE_IP_PROXY:
        return None

    from proxy.proxy_ip_pool import create_ip_pool

    ip_pool = await create_ip_pool(1, enable_validate_ip=True)
    ip_proxy_info = await ip_pool.get_proxy()
    _, httpx_proxy = utils.format_proxy_info(ip_proxy_info)
    return httpx_proxy


def _user_data_dir(platform: str) -> str:
    """qrcode 登录后保存登录态的浏览器 profile 目录。

    与 media_platform/*/core.py 的 launch_browser 和 tools/cdp_browser.py:255-263
    保持一致：CDP 模式多一个 cdp_ 前缀。
    """

    dir_name = config.USER_DATA_DIR % platform
    if config.ENABLE_CDP_MODE:
        dir_name = f"cdp_{dir_name}"
    return os.path.join(os.getcwd(), "browser_data", dir_name)


async def _cookies_from_browser_profile(platform: str) -> str:
    """从已保存的浏览器 profile 里读出 cookie，读完立刻关闭浏览器。

    默认的 `--lt qrcode` 流程不会往 config.COOKIES 写任何东西，登录态只存在于
    browser_data/ 里，所以不读这里的话预检对大多数用户都只会说“没有 cookie”。
    """

    from playwright.async_api import async_playwright

    user_data_dir = _user_data_dir(platform)
    async with async_playwright() as playwright:
        browser_context = await playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            accept_downloads=True,
            headless=True,
            viewport={"width": 1920, "height": 1080},
            user_agent=utils.get_user_agent(),
        )
        try:
            cookie_str, _ = await utils.convert_browser_context_cookies(browser_context)
        finally:
            await browser_context.close()

    return cookie_str


async def _load_cookie_str(platform: str) -> Tuple[str, str]:
    """返回 (cookie 字符串, 来源描述)。取不到就返回空串。"""

    if config.COOKIES.strip():
        return config.COOKIES, "config.COOKIES"

    user_data_dir = _user_data_dir(platform)
    if not os.path.isdir(user_data_dir):
        return "", ""

    cookie_str = await _cookies_from_browser_profile(platform)
    return cookie_str, f"browser_data/{os.path.basename(user_data_dir)}"


def _build_client(platform: str, cookie_str: str, httpx_proxy: Optional[str]):
    """按平台构造一个仅用于预检的 API client。

    header 与各平台 create_*_client 的关键字段保持一致，尤其是 Cookie 的大小写：
    xhs 读 headers["Cookie"]，zhihu 读 default_headers["cookie"]。
    """

    cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)

    if platform == "xhs":
        from media_platform.xhs.client import XiaoHongShuClient

        index_url = "https://www.rednote.com" if config.XHS_INTERNATIONAL else "https://www.xiaohongshu.com"
        return XiaoHongShuClient(
            proxy=httpx_proxy,
            headers={
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9",
                "content-type": "application/json;charset=UTF-8",
                "origin": index_url,
                "referer": f"{index_url}/",
                "user-agent": utils.get_user_agent(),
                "Cookie": cookie_str,
            },
            playwright_page=None,
            cookie_dict=cookie_dict,
        )

    if platform == "bili":
        from media_platform.bilibili.client import BilibiliClient

        return BilibiliClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": utils.get_user_agent(),
                "Cookie": cookie_str,
                "Origin": "https://www.bilibili.com",
                "Referer": "https://www.bilibili.com",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=None,
            cookie_dict=cookie_dict,
        )

    if platform == "wb":
        from media_platform.weibo.client import WeiboClient

        return WeiboClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": utils.get_mobile_user_agent(),
                "Cookie": cookie_str,
                "Origin": "https://m.weibo.cn",
                "Referer": "https://m.weibo.cn",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=None,
            cookie_dict=cookie_dict,
        )

    if platform == "zhihu":
        from media_platform.zhihu.client import ZhiHuClient

        return ZhiHuClient(
            proxy=httpx_proxy,
            headers={
                "accept": "*/*",
                "accept-language": "zh-CN,zh;q=0.9",
                "cookie": cookie_str,
                "priority": "u=1, i",
                "referer": "https://www.zhihu.com/",
                "user-agent": utils.get_user_agent(),
                "x-api-version": "3.0.91",
                "x-app-za": "OS=Web",
                "x-requested-with": "fetch",
                "x-zse-93": "101_3_3.0",
            },
            playwright_page=None,
            cookie_dict=cookie_dict,
        )

    if platform == "ks":
        from media_platform.kuaishou.client import KuaiShouClient

        return KuaiShouClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": utils.get_user_agent(),
                "Cookie": cookie_str,
                "Origin": "https://www.kuaishou.com",
                "Referer": "https://www.kuaishou.com",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=None,
            cookie_dict=cookie_dict,
        )

    raise ValueError(f"platform {platform!r} does not support a browserless session check")


async def _probe(platform: str, client) -> bool:
    """发出各平台 pong() 内部的那一个请求，异常交给调用方归类。

    刻意不复用 pong()：它内部 `except Exception: return False`，一旦复用，代理不通、
    被限流、响应异常全都会被报成“cookie 失效”。
    """

    if platform == "xhs":
        # 走 client.get()（而不是 query_self()）：前者经过 request()，
        # 403/429 会抛 PlatformAccessError，风控码会抛 IPBlockError。
        data = await client.get("/api/sns/web/v1/user/selfinfo", {})
        return bool((data or {}).get("result", {}).get("success"))

    if platform == "bili":
        data = await client.get("/x/web-interface/nav")
        return bool((data or {}).get("isLogin"))

    if platform == "wb":
        # 绕开 WeiboClient.request()：它带 5 次重试（一次预检要 12s 以上），
        # 而且响应不是 JSON 时会去解引用 playwright_page（这里是 None）。
        from tools.httpx_util import make_async_client

        async with make_async_client(proxy=client.proxy) as http_client:
            response = await http_client.get(
                f"{client._host}/api/config",
                headers=client.headers,
                timeout=client.timeout,
            )
        payload = response.json()
        return bool(payload.get("data", {}).get("login"))

    if platform == "zhihu":
        data = await client.get_current_user_info()
        return bool(data.get("uid") and data.get("name"))

    if platform == "ks":
        data = await client.post(
            "",
            {
                "operationName": "visionProfileUserList",
                "variables": {"ftype": 1},
                "query": client.graphql.get("vision_profile_user_list"),
            },
        )
        return (data or {}).get("visionProfileUserList", {}).get("result") == 1

    raise ValueError(f"platform {platform!r} does not support a browserless session check")


def _browser_only_result(platform: str, cookie_str: str) -> SessionCheckResult:
    """dy / tieba：pong() 读的是浏览器状态，预检只能给 cookie 层面的线索。"""

    cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)

    if platform == "dy":
        # DouYinClient.pong 先看 localStorage.HasUserLogin，cookie 只是兜底，
        # 所以 cookie 里没有这个标记并不能证明未登录。
        signal = cookie_dict.get("LOGIN_STATUS") == "1"
        hint = "LOGIN_STATUS=1 in cookies" if signal else "no LOGIN_STATUS=1 in cookies"
    else:  # tieba
        signal = any(key in cookie_dict for key in ("BDUSS", "STOKEN", "PTOKEN"))
        hint = "BDUSS/STOKEN/PTOKEN present" if signal else "no BDUSS/STOKEN/PTOKEN in cookies"

    return SessionCheckResult(
        platform=platform,
        status=STATUS_UNKNOWN,
        cause=CAUSE_BROWSER_REQUIRED,
        detail=f"{hint}; this platform has no login-state endpoint to probe",
    )


async def check_platform_session(platform: str, cookie_str: Optional[str] = None) -> SessionCheckResult:
    """对单个平台做一次登录态预检。"""

    source = "explicit cookie"
    if cookie_str is None:
        try:
            cookie_str, source = await _load_cookie_str(platform)
        except Exception as exc:  # noqa: BLE001 - 读不到登录态本身就是一种预检结果
            return SessionCheckResult(
                platform=platform,
                status=STATUS_FAILED,
                cause=CAUSE_NO_SESSION,
                detail=f"could not read the saved browser session: {exc.__class__.__name__}: {exc}",
            )

    if not cookie_str.strip():
        return SessionCheckResult(
            platform=platform,
            status=STATUS_FAILED,
            cause=CAUSE_NO_SESSION,
            detail="config.COOKIES is empty and no saved browser profile was found; pass --cookies or log in once",
        )

    cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)
    missing = [key for key in REQUIRED_COOKIE_KEYS.get(platform, ()) if key not in cookie_dict]
    if missing:
        return SessionCheckResult(
            platform=platform,
            status=STATUS_FAILED,
            cause=CAUSE_MISSING_COOKIE_KEYS,
            detail=f"missing {', '.join(missing)} (source: {source}); the cookie may belong to another platform",
        )

    if platform in BROWSER_ONLY_PLATFORMS:
        return _browser_only_result(platform, cookie_str)

    try:
        httpx_proxy = await _resolve_proxy()
    except Exception as exc:  # noqa: BLE001 - 代理拿不到也是一种预检结果
        return SessionCheckResult(
            platform=platform,
            status=STATUS_FAILED,
            cause=CAUSE_PROXY,
            detail=f"could not obtain a proxy: {exc.__class__.__name__}: {exc}",
        )

    try:
        client = _build_client(platform, cookie_str, httpx_proxy)
    except ValueError as exc:
        return SessionCheckResult(
            platform=platform,
            status=STATUS_UNKNOWN,
            cause=CAUSE_BROWSER_REQUIRED,
            detail=str(exc),
        )

    try:
        alive = await asyncio.wait_for(_probe(platform, client), timeout=CHECK_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001 - 归类后上报，预检不把异常抛给调用方
        cause, detail = _classify_exception(exc)
        return SessionCheckResult(platform=platform, status=STATUS_FAILED, cause=cause, detail=detail)

    if alive:
        return SessionCheckResult(platform=platform, status=STATUS_OK, detail=f"source: {source}")

    return SessionCheckResult(
        platform=platform,
        status=STATUS_FAILED,
        cause=CAUSE_EXPIRED,
        detail=f"the platform answered 'not logged in' (source: {source})",
    )


async def run_session_check(platforms: List[str], cookie_str: Optional[str] = None) -> int:
    """预检若干平台，打印结果并返回进程退出码。

    返回 0 表示没有失败；只要有一个 failed 就返回 1。unknown 不算失败，否则
    dy / tieba 的定时任务会永远是红的。
    """

    print("=" * 72)
    print("Session preflight")
    print(f"proxy: {'on' if config.ENABLE_IP_PROXY else 'off'}")
    print("=" * 72)

    results: List[SessionCheckResult] = []
    for platform in platforms:
        result = await check_platform_session(platform, cookie_str=cookie_str)
        results.append(result)
        print(result.render())

    failed = [r for r in results if r.status == STATUS_FAILED]
    unknown = [r for r in results if r.status == STATUS_UNKNOWN]
    print("=" * 72)
    print(f"ok {len(results) - len(failed) - len(unknown)} / failed {len(failed)} / unknown {len(unknown)}")

    return 1 if failed else 0
