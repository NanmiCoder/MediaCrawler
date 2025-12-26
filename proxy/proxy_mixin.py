# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
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


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2025/11/25
# @Desc    : Auto-refresh proxy Mixin class for use by various platform clients

from typing import TYPE_CHECKING, Optional

from tools import utils

if TYPE_CHECKING:
    from proxy.proxy_ip_pool import ProxyIpPool


class ProxyRefreshMixin:
    """
    Auto-refresh proxy Mixin class

    Usage:
    1. Let client class inherit this Mixin
    2. Call init_proxy_pool(proxy_ip_pool) in client's __init__
    3. Call await _refresh_proxy_if_expired() before each request method call

    Requirements:
    - client class must have self.proxy attribute to store current proxy URL
    """

    _proxy_ip_pool: Optional["ProxyIpPool"] = None

    def init_proxy_pool(self, proxy_ip_pool: Optional["ProxyIpPool"]) -> None:
        """
        Initialize proxy pool reference
        Args:
            proxy_ip_pool: Proxy IP pool instance
        """
        self._proxy_ip_pool = proxy_ip_pool

    async def _refresh_proxy_if_expired(self) -> None:
        """
        Check if proxy has expired, automatically refresh if so
        Call this method before each request to ensure proxy is valid
        """
        if self._proxy_ip_pool is None:
            return

        if self._proxy_ip_pool.is_current_proxy_expired():
            utils.logger.info(
                f"[{self.__class__.__name__}._refresh_proxy_if_expired] Proxy expired, refreshing..."
            )
            new_proxy = await self._proxy_ip_pool.get_or_refresh_proxy()
            # Update httpx proxy URL
            if new_proxy.user and new_proxy.password:
                self.proxy = f"http://{new_proxy.user}:{new_proxy.password}@{new_proxy.ip}:{new_proxy.port}"
            else:
                self.proxy = f"http://{new_proxy.ip}:{new_proxy.port}"
            utils.logger.info(
                f"[{self.__class__.__name__}._refresh_proxy_if_expired] New proxy: {new_proxy.ip}:{new_proxy.port}"
            )
