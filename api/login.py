"""
api.login — 抖音扫码登录路由
==============================
实现二维码登录流程，供前端 Web UI 调用。

端点：
  POST /login/qrcode/start          — 启动浏览器，返回二维码图片（base64）
  GET  /login/qrcode/status/{sid}   — 轮询登录状态
  POST /login/logout                — 登出（清除 Cookie）
  GET  /login/status                — 查询当前登录状态

设计要点：
  - 使用 playwright.async_api 异步操作，兼容 FastAPI async 路由
  - session 超时 120 秒自动清理
  - 最多 1 个并发登录 session（避免资源竞争）
  - Cookie 持久化到 /app/data/douyin_cookie.txt
  - 全局内存 Cookie 缓存，供采集任务复用
"""

import asyncio
import base64
import logging
import os
import time as _time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger("douyin_scraper.api.login")

router = APIRouter(prefix="/login", tags=["login"])

# ═══════════════════════════════════════════════════════════════
# 常量与持久化路径
# ═══════════════════════════════════════════════════════════════

COOKIE_FILE = Path("/app/data/douyin_cookie.txt")
SESSION_TIMEOUT_SECONDS = 120

# Chromium 可执行路径（Docker 容器内由环境变量指定）
CHROMIUM_EXECUTABLE = os.environ.get(
    "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", ""
)

# ═══════════════════════════════════════════════════════════════
# 全局状态
# ═══════════════════════════════════════════════════════════════

# 内存中缓存的 Cookie 字符串（复用给采集任务）
_memory_cookie: str = ""

# 当前活跃的登录 session（最多 1 个）
# 结构: {session_id: {"playwright": ..., "browser": ..., "context": ..., "page": ..., "expires_at": datetime, "status": str}}
_active_sessions: Dict[str, Dict[str, Any]] = {}

# 全局锁，防止并发创建 session
_session_lock = asyncio.Lock()


# ═══════════════════════════════════════════════════════════════
# 内部辅助函数
# ═══════════════════════════════════════════════════════════════

def _load_cookie_from_file() -> str:
    """从持久化文件读取 Cookie，失败返回空字符串。"""
    try:
        if COOKIE_FILE.exists():
            content = COOKIE_FILE.read_text(encoding="utf-8").strip()
            if content:
                return content
    except OSError as exc:
        logger.warning("读取 Cookie 文件失败: %s", exc)
    return ""


def _save_cookie_to_file(cookie_str: str) -> None:
    """将 Cookie 字符串写入持久化文件，自动创建父目录。"""
    try:
        COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        COOKIE_FILE.write_text(cookie_str, encoding="utf-8")
        logger.info("Cookie 已写入 %s (长度: %d)", COOKIE_FILE, len(cookie_str))
    except OSError as exc:
        logger.error("写入 Cookie 文件失败: %s", exc)


def _sync_cookie_to_browser_data(cookie_str: str) -> None:
    """
    ★ Fix 6: 将 Cookie 同步写入 browser_data 目录 ★
    供 Playwright persistent context 使用，确保子进程采集任务
    能够使用登录 session 中获取的 Cookie。
    写入 Netscape 格式的 Cookie 文件，兼容 Playwright。
    """
    try:
        browser_data_dir = Path("/app/browser_data/dy_user_data_dir")
        browser_data_dir.mkdir(parents=True, exist_ok=True)
        # 将 Cookie 以 Netscape 格式写入（Playwright 兼容）
        cookie_path = browser_data_dir / "Cookies"
        lines = ["# Netscape HTTP Cookie File\n"]
        # 解析 key=value; key=value 格式为 Netscape 行
        for pair in cookie_str.split("; "):
            if "=" not in pair:
                continue
            name, _, value = pair.partition("=")
            if not name.strip():
                continue
            # Netscape Cookie 格式：domain\tflag\tpath\tsecure\texpiration\tname\tvalue
            # 使用 .douyin.com 作为 domain，使 Playwright 在访问抖音时生效
            line = f".douyin.com\tTRUE\t/\tFALSE\t{int(_time.time()) + 86400}\t{name.strip()}\t{value.strip()}\n"
            lines.append(line)
        cookie_path.write_text("".join(lines), encoding="utf-8")
        logger.info("Cookie 已同步到 browser_data: %s (%d 条)", browser_data_dir, len(lines) - 1)
    except Exception as exc:
        logger.warning("写入 browser_data 失败（非阻塞）: %s", exc)


def _delete_cookie_file() -> None:
    """删除持久化 Cookie 文件。"""
    try:
        if COOKIE_FILE.exists():
            COOKIE_FILE.unlink()
            logger.info("Cookie 文件已删除: %s", COOKIE_FILE)
    except OSError as exc:
        logger.warning("删除 Cookie 文件失败: %s", exc)


async def _close_session(session_id: str) -> None:
    """关闭并清理指定 session 占用的 Playwright 资源。"""
    session = _active_sessions.pop(session_id, None)
    if session is None:
        return
    try:
        browser = session.get("browser")
        if browser:
            await browser.close()
        pw = session.get("playwright")
        if pw:
            await pw.stop()
        logger.info("[session=%s] 浏览器资源已释放", session_id)
    except Exception as exc:
        logger.warning("[session=%s] 释放资源时出错: %s", session_id, exc)


async def _session_watchdog(session_id: str, timeout: float) -> None:
    """
    后台看门狗：等待 timeout 秒后，若 session 仍存在则强制清理。
    防止用户忘记扫码导致浏览器进程泄漏。
    """
    await asyncio.sleep(timeout)
    if session_id in _active_sessions:
        logger.info("[session=%s] 超时 %ds，自动清理", session_id, int(timeout))
        _active_sessions[session_id]["status"] = "expired"
        await _close_session(session_id)


async def _extract_cookies_from_context(context: Any) -> str:
    """
    从 Playwright BrowserContext 中提取抖音相关 Cookie，
    返回 `key=value; key=value` 格式字符串。
    """
    cookies = await context.cookies(
        urls=["https://www.douyin.com", "https://www.tiktok.com"]
    )
    if not cookies:
        # 回退：提取全部 cookies
        cookies = await context.cookies()
    cookie_str = "; ".join(
        f"{c['name']}={c['value']}" for c in cookies if c.get("name")
    )
    return cookie_str


async def _check_login_state(page: Any, context: Any) -> bool:
    """
    检测抖音是否已完成扫码登录。
    检测优先级：
      1. localStorage.HasUserLogin === "1"
      2. Cookie: LOGIN_STATUS === "1"
    """
    # 检查 localStorage
    try:
        local_storage: Dict[str, Any] = await page.evaluate(
            "() => { try { return Object.fromEntries(Object.entries(window.localStorage)); } catch(e) { return {}; } }"
        )
        if isinstance(local_storage, dict) and local_storage.get("HasUserLogin") == "1":
            return True
    except Exception as exc:
        logger.debug("localStorage 检查失败: %s", exc)

    # 检查 Cookie
    try:
        cookies = await context.cookies(urls=["https://www.douyin.com"])
        for c in cookies:
            if c.get("name") == "LOGIN_STATUS" and c.get("value") == "1":
                return True
    except Exception as exc:
        logger.debug("Cookie 检查失败: %s", exc)

    return False


# ═══════════════════════════════════════════════════════════════
# 路由端点
# ═══════════════════════════════════════════════════════════════


@router.post("/qrcode/start", summary="启动扫码登录，返回二维码图片")
async def start_qrcode_login() -> Dict[str, Any]:
    """
    启动 Playwright 无头浏览器，打开抖音并截取登录二维码。

    返回：
      - session_id: 用于后续轮询的唯一标识
      - qrcode: base64 编码的二维码 PNG 图片（data URL 格式）
      - expires_at: session 过期时间（ISO 8601）
    """
    global _active_sessions

    async with _session_lock:
        # 最多允许 1 个活跃 session
        if _active_sessions:
            old_sid = next(iter(_active_sessions))
            logger.info("已有活跃 session [%s]，先关闭再新建", old_sid)
            await _close_session(old_sid)

        session_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=SESSION_TIMEOUT_SECONDS)

        logger.info("[session=%s] 启动扫码登录流程", session_id)

        try:
            from playwright.async_api import async_playwright

            pw = await async_playwright().start()

            # 构建浏览器启动参数
            launch_kwargs: Dict[str, Any] = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-setuid-sandbox",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-extensions",
                ],
            }
            if CHROMIUM_EXECUTABLE:
                launch_kwargs["executable_path"] = CHROMIUM_EXECUTABLE
                logger.info("使用指定 Chromium: %s", CHROMIUM_EXECUTABLE)

            browser = await pw.chromium.launch(**launch_kwargs)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            page = await context.new_page()

            # 导航到抖音主页
            logger.info("[session=%s] 打开 https://www.douyin.com", session_id)
            await page.goto("https://www.douyin.com", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 触发登录弹窗：等待弹窗自动出现，否则手动点击"登录"按钮
            dialog_selector = "xpath=//div[@id='login-panel-new']"
            try:
                await page.wait_for_selector(dialog_selector, timeout=10000)
                logger.info("[session=%s] 登录弹窗已自动弹出", session_id)
            except Exception:
                logger.info("[session=%s] 登录弹窗未自动弹出，尝试手动点击", session_id)
                try:
                    login_btn = page.locator("xpath=//p[text()='登录']")
                    await login_btn.click(timeout=5000)
                    await asyncio.sleep(1)
                    await page.wait_for_selector(dialog_selector, timeout=8000)
                    logger.info("[session=%s] 手动触发登录弹窗成功", session_id)
                except Exception as click_exc:
                    logger.warning("[session=%s] 手动点击登录失败: %s，继续尝试截图", session_id, click_exc)

            # 等待并截取二维码
            qrcode_b64: str = ""
            qrcode_selector = "xpath=//div[@id='animate_qrcode_container']//img"
            try:
                qrcode_locator = page.locator(qrcode_selector)
                await qrcode_locator.wait_for(timeout=15000)
                qrcode_element = await qrcode_locator.element_handle()
                if qrcode_element:
                    screenshot_bytes = await qrcode_element.screenshot()
                    qrcode_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                    logger.info("[session=%s] 二维码截取成功 (%d bytes)", session_id, len(screenshot_bytes))
            except Exception as qr_exc:
                logger.warning(
                    "[session=%s] 未找到二维码元素 (%s)，降级为全页面截图",
                    session_id, qr_exc,
                )
                try:
                    full_screenshot = await page.screenshot(full_page=False)
                    qrcode_b64 = base64.b64encode(full_screenshot).decode("utf-8")
                    logger.info("[session=%s] 全页面截图完成 (%d bytes)", session_id, len(full_screenshot))
                except Exception as ss_exc:
                    logger.error("[session=%s] 全页面截图也失败: %s", session_id, ss_exc)
                    await browser.close()
                    await pw.stop()
                    raise HTTPException(
                        status_code=500,
                        detail=f"无法获取二维码图片: {ss_exc}",
                    )

            # 存储 session
            _active_sessions[session_id] = {
                "playwright": pw,
                "browser": browser,
                "context": context,
                "page": page,
                "expires_at": expires_at,
                "status": "pending",
            }

            # 启动看门狗
            asyncio.create_task(_session_watchdog(session_id, SESSION_TIMEOUT_SECONDS))

            return {
                "session_id": session_id,
                "qrcode": f"data:image/png;base64,{qrcode_b64}",
                "expires_at": expires_at.isoformat(),
                "message": "请使用抖音 App 扫描二维码登录",
            }

        except HTTPException:
            raise
        except Exception as exc:
            logger.error("[session=%s] 启动登录流程失败: %s", session_id, exc, exc_info=True)
            # 清理残留资源
            _active_sessions.pop(session_id, None)
            raise HTTPException(
                status_code=500,
                detail=f"启动浏览器失败: {exc}",
            )


@router.get("/qrcode/status/{session_id}", summary="轮询扫码登录状态")
async def poll_qrcode_status(session_id: str) -> Dict[str, Any]:
    """
    轮询扫码登录状态。

    返回 status：
      - pending:  等待扫码
      - scanned:  已扫码，等待确认
      - success:  登录成功（Cookie 已保存）
      - expired:  session 已过期
      - not_found: session 不存在
    """
    global _memory_cookie

    session = _active_sessions.get(session_id)
    if session is None:
        # 检查是否之前已成功（session 被清理）
        return {"status": "not_found", "message": "session 不存在或已过期"}

    # 检查超时
    if datetime.now(timezone.utc) > session["expires_at"]:
        session["status"] = "expired"
        await _close_session(session_id)
        return {"status": "expired", "message": "二维码已过期，请重新获取"}

    current_status = session.get("status", "pending")
    if current_status in ("expired", "success"):
        return {"status": current_status}

    page = session.get("page")
    context = session.get("context")

    # 检测登录状态
    try:
        logged_in = await _check_login_state(page, context)
    except Exception as exc:
        logger.warning("[session=%s] 检测登录状态失败: %s", session_id, exc)
        logged_in = False

    if logged_in:
        logger.info("[session=%s] 检测到登录成功！", session_id)
        session["status"] = "success"

        # 提取 Cookie
        try:
            cookie_str = await _extract_cookies_from_context(context)
            if cookie_str:
                _memory_cookie = cookie_str
                _save_cookie_to_file(cookie_str)
                # ★ Fix 6: 同步 Cookie 到 browser_data 目录 ★
                _sync_cookie_to_browser_data(cookie_str)
                logger.info("[session=%s] Cookie 已保存，长度: %d", session_id, len(cookie_str))
            else:
                logger.warning("[session=%s] 登录成功但 Cookie 为空", session_id)
        except Exception as exc:
            logger.error("[session=%s] 提取 Cookie 失败: %s", session_id, exc)

        # 关闭浏览器 session
        await _close_session(session_id)

        return {
            "status": "success",
            "message": "登录成功！Cookie 已保存",
            "cookie_saved": bool(_memory_cookie),
        }

    # 尝试检测"已扫码未确认"状态（抖音扫码后会出现确认页面）
    try:
        # 页面标题或 URL 变化可作为"已扫码"的信号
        current_url = page.url
        if "confirm" in current_url or "auth" in current_url:
            session["status"] = "scanned"
            return {"status": "scanned", "message": "已扫码，请在手机端确认登录"}
    except Exception:
        pass

    return {
        "status": "pending",
        "message": "等待扫码...",
        "expires_at": session["expires_at"].isoformat(),
    }


@router.post("/logout", summary="登出（清除 Cookie）")
async def logout() -> Dict[str, Any]:
    """
    清除保存的登录 Cookie（持久化文件 + 内存缓存）。
    同时关闭所有活跃的登录 session。
    """
    global _memory_cookie

    # 关闭所有活跃 session
    for sid in list(_active_sessions.keys()):
        await _close_session(sid)

    # 删除持久化 Cookie 文件
    _delete_cookie_file()

    # 清空内存缓存
    _memory_cookie = ""

    logger.info("已登出，Cookie 已清除")
    return {"ok": True, "message": "已登出，Cookie 已清除"}


@router.get("/status", summary="查询当前登录状态")
async def get_login_status() -> Dict[str, Any]:
    """
    查询当前是否有有效的登录 Cookie。

    返回：
      - logged_in: 是否已登录
      - cookie_preview: Cookie 的前 30 个字符（用于确认是哪个账号）
      - source: Cookie 来源（file / memory / none）
    """
    global _memory_cookie

    # 优先使用内存缓存
    cookie_str = _memory_cookie

    # 内存为空时尝试从文件加载
    if not cookie_str:
        cookie_str = _load_cookie_from_file()
        if cookie_str:
            _memory_cookie = cookie_str  # 同步到内存缓存
            source = "file"
        else:
            source = "none"
    else:
        source = "memory"

    logged_in = bool(cookie_str)
    preview = cookie_str[:30] + "..." if len(cookie_str) > 30 else cookie_str

    return {
        "logged_in": logged_in,
        "cookie_preview": preview if logged_in else "",
        "source": source,
        "active_sessions": len(_active_sessions),
    }


def get_memory_cookie() -> str:
    """★ Fix 6: 获取内存中缓存的 Cookie（供采集任务复用）★"""
    global _memory_cookie
    # 内存为空时尝试从文件加载
    if not _memory_cookie:
        _memory_cookie = _load_cookie_from_file()
    return _memory_cookie
