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
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import RetryError, retry, retry_if_result, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractLogin
from tools import utils


class XiaoHeiHeLogin(AbstractLogin):
    """小黑盒登录实现

    支持两种登录方式：
    - qrcode: 弹出二维码图片，用小黑盒 APP 扫码登录
    - cookie: 使用 config.COOKIES 字符串中的 heybox_user cookie
    """

    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        login_phone: Optional[str] = "",
        cookie_str: str = "",
    ):
        config.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

    @retry(
        stop=stop_after_attempt(300),
        wait=wait_fixed(1),
        retry=retry_if_result(lambda v: v is False),
    )
    async def check_login_state(self, no_logged_in_session: str) -> bool:
        """轮询检测登录态：检查 heybox_id cookie 是否出现"""
        current_cookies = await self.browser_context.cookies()
        cookie_dict = {c["name"]: c["value"] for c in current_cookies}
        heybox_id = cookie_dict.get("heybox_id", "")
        if heybox_id and heybox_id != no_logged_in_session:
            utils.logger.info(
                "[XiaoHeiHeLogin.check_login_state] Login confirmed by heybox_id cookie."
            )
            return True
        return False

    async def begin(self):
        """Start login xiaoheihe"""
        utils.logger.info("[XiaoHeiHeLogin.begin] Begin login xiaoheihe ...")
        if config.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError(
                "[XiaoHeiHeLogin.begin] Invalid login type. Supported: qrcode | cookie"
            )

    async def login_by_mobile(self):
        """小黑盒不支持手机验证码登录，留空实现接口"""
        utils.logger.warning(
            "[XiaoHeiHeLogin.login_by_mobile] Mobile login not supported for xiaoheihe."
        )

    async def login_by_qrcode(self):
        """通过扫码登录小黑盒

        流程：
        1. 打开小黑盒首页并点击登录按钮，触发 get_qrcode_url API
        2. 拦截 API 获取 qr_url（小黑盒 APP 可识别的格式）
        3. 生成二维码图片弹窗（PIL）供用户扫码
        4. 轮询检测 heybox_id cookie 出现，确认登录成功
        """
        utils.logger.info(
            "[XiaoHeiHeLogin.login_by_qrcode] Begin login xiaoheihe by qrcode ..."
        )

        # 导航到首页并点击登录
        home_url = "https://www.xiaoheihe.cn/app/bbs/home"
        try:
            await self.context_page.goto(home_url, wait_until="networkidle", timeout=20000)
            await asyncio.sleep(0.5)
            await self.context_page.click(".user-box__login")
        except Exception as e:
            utils.logger.warning(
                f"[XiaoHeiHeLogin.login_by_qrcode] Failed to click login button: {e}"
            )

        # 等待 get_qrcode_url API 响应（最多 8 秒）
        qr_url = None
        for _ in range(16):
            await asyncio.sleep(0.5)
            # 从拦截到的 API 响应中取 qr_url（由 core.py 在启动时注入到 page 对象）
            qr_url = await self.context_page.evaluate(
                "() => window.__xhh_qr_url__ || null"
            )
            if qr_url:
                break

        if not qr_url:
            utils.logger.error(
                "[XiaoHeiHeLogin.login_by_qrcode] Failed to get qr_url from API."
            )
            sys.exit(1)

        utils.logger.info(
            f"[XiaoHeiHeLogin.login_by_qrcode] Got qr_url, generating QR code ..."
        )

        # 生成二维码图片并弹窗（在线程池中运行，不阻塞事件循环）
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _show_qrcode, qr_url)

        # 获取登录前的 heybox_id（可能为空）
        current_cookies = await self.browser_context.cookies()
        cookie_dict = {c["name"]: c["value"] for c in current_cookies}
        no_logged_in_session = cookie_dict.get("heybox_id", "")

        utils.logger.info(
            "[XiaoHeiHeLogin.login_by_qrcode] Waiting for QR code scan (max 120s) ..."
        )
        try:
            await self.check_login_state(no_logged_in_session)
        except RetryError:
            utils.logger.error(
                "[XiaoHeiHeLogin.login_by_qrcode] Login timed out. Please retry."
            )
            sys.exit(1)

        wait_redirect_seconds = 3
        utils.logger.info(
            f"[XiaoHeiHeLogin.login_by_qrcode] Login successful, "
            f"waiting {wait_redirect_seconds}s for redirect ..."
        )
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_cookies(self):
        """login xiaoheihe by cookies"""
        utils.logger.info(
            "[XiaoHeiHeLogin.login_by_cookies] Begin login xiaoheihe by cookie ..."
        )
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            if key != "heybox_user":  # Only set heybox_user cookie attribute
                continue
            await self.browser_context.add_cookies([{
                "name": key,
                "value": value,
                "domain": ".xiaoheihe.cn",
                "path": "/",
            }])


def _show_qrcode(qr_url: str) -> None:
    """生成二维码图片并弹窗显示（同步函数，在线程池中调用）"""
    try:
        import qrcode as qrcode_lib
        from PIL import Image
    except ImportError:
        utils.logger.warning(
            "[XiaoHeiHeLogin] qrcode or PIL not installed. "
            "Install with: pip install qrcode[pil] pillow"
        )
        utils.logger.info(f"[XiaoHeiHeLogin] Please scan this URL manually: {qr_url}")
        return

    qr = qrcode_lib.QRCode(box_size=8, border=3)
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    w, h = qr_img.size
    canvas = Image.new("RGB", (w, h + 16), color=(255, 255, 255))
    canvas.paste(qr_img, (0, 0))
    canvas.show(title="小黑盒扫码登录 — 打开小黑盒 APP 扫一扫")
    utils.logger.info("[XiaoHeiHeLogin] QR code window opened. Please scan with xiaoheihe APP.")
