# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/xhs/cookie_manager.py
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


import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from tools import utils


class CookieManager:
    """管理小红书的Cookie持久化存储和加载"""

    def __init__(self, cookie_dir: str = "cookies"):
        """
        初始化Cookie管理器

        Args:
            cookie_dir: Cookie存储目录
        """
        self.cookie_dir = Path(cookie_dir)
        self.cookie_dir.mkdir(parents=True, exist_ok=True)
        self.cookie_file = self.cookie_dir / "xhs_cookies.json"

    def save_cookies(self, cookies: List[Dict]) -> bool:
        """
        保存cookies到文件

        Args:
            cookies: Playwright格式的cookie列表

        Returns:
            bool: 保存是否成功
        """
        try:
            # 添加保存时间戳
            cookie_data = {
                "cookies": cookies,
                "saved_at": time.time(),
                "saved_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)

            utils.logger.info(
                f"[CookieManager.save_cookies] Successfully saved {len(cookies)} cookies to {self.cookie_file}"
            )
            return True

        except Exception as e:
            utils.logger.error(
                f"[CookieManager.save_cookies] Failed to save cookies: {e}"
            )
            return False

    def load_cookies(self) -> Optional[List[Dict]]:
        """
        从文件加载cookies

        Returns:
            Optional[List[Dict]]: Playwright格式的cookie列表，如果文件不存在或加载失败则返回None
        """
        if not self.cookie_file.exists():
            utils.logger.info(
                f"[CookieManager.load_cookies] Cookie file not found: {self.cookie_file}"
            )
            return None

        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)

            cookies = cookie_data.get("cookies", [])
            saved_at = cookie_data.get("saved_at", 0)
            saved_time = cookie_data.get("saved_time", "Unknown")

            # 检查cookie是否过期（30天）
            if time.time() - saved_at > 30 * 24 * 3600:
                utils.logger.warning(
                    f"[CookieManager.load_cookies] Cookies are older than 30 days (saved at {saved_time}), may be expired"
                )

            utils.logger.info(
                f"[CookieManager.load_cookies] Successfully loaded {len(cookies)} cookies from {self.cookie_file} (saved at {saved_time})"
            )
            return cookies

        except Exception as e:
            utils.logger.error(
                f"[CookieManager.load_cookies] Failed to load cookies: {e}"
            )
            return None

    def clear_cookies(self) -> bool:
        """
        清除保存的cookies文件

        Returns:
            bool: 清除是否成功
        """
        try:
            if self.cookie_file.exists():
                self.cookie_file.unlink()
                utils.logger.info(
                    f"[CookieManager.clear_cookies] Successfully cleared cookies file: {self.cookie_file}"
                )
            return True

        except Exception as e:
            utils.logger.error(
                f"[CookieManager.clear_cookies] Failed to clear cookies: {e}"
            )
            return False

    def get_cookie_info(self) -> Optional[Dict]:
        """
        获取保存的cookie信息（不包含实际cookie数据）

        Returns:
            Optional[Dict]: Cookie信息字典，包含保存时间、数量等
        """
        if not self.cookie_file.exists():
            return None

        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)

            return {
                "saved_at": cookie_data.get("saved_at", 0),
                "saved_time": cookie_data.get("saved_time", "Unknown"),
                "cookie_count": len(cookie_data.get("cookies", [])),
                "file_path": str(self.cookie_file)
            }

        except Exception as e:
            utils.logger.error(
                f"[CookieManager.get_cookie_info] Failed to get cookie info: {e}"
            )
            return None
