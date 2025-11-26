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
# @Desc    : 代理自动刷新 Mixin 类，供各平台 client 使用

from typing import TYPE_CHECKING, Optional

from tools import utils

if TYPE_CHECKING:
    from proxy.proxy_ip_pool import ProxyIpPool


class ProxyRefreshMixin:
    """
    代理自动刷新 Mixin 类

    使用方法：
    1. 让 client 类继承此 Mixin
    2. 在 client 的 __init__ 中调用 init_proxy_pool(proxy_ip_pool)
    3. 在每次 request 方法调用前调用 await _refresh_proxy_if_expired()

    要求：
    - client 类必须有 self.proxy 属性来存储当前代理URL
    """

    _proxy_ip_pool: Optional["ProxyIpPool"] = None

    def init_proxy_pool(self, proxy_ip_pool: Optional["ProxyIpPool"]) -> None:
        """
        初始化代理池引用
        Args:
            proxy_ip_pool: 代理IP池实例
        """
        self._proxy_ip_pool = proxy_ip_pool

    async def _refresh_proxy_if_expired(self) -> None:
        """
        检测代理是否过期，如果过期则自动刷新
        每次发起请求前调用此方法来确保代理有效
        """
        if self._proxy_ip_pool is None:
            return

        if self._proxy_ip_pool.is_current_proxy_expired():
            utils.logger.info(
                f"[{self.__class__.__name__}._refresh_proxy_if_expired] Proxy expired, refreshing..."
            )
            new_proxy = await self._proxy_ip_pool.get_or_refresh_proxy()
            # 更新 httpx 代理URL
            if new_proxy.user and new_proxy.password:
                self.proxy = f"http://{new_proxy.user}:{new_proxy.password}@{new_proxy.ip}:{new_proxy.port}"
            else:
                self.proxy = f"http://{new_proxy.ip}:{new_proxy.port}"
            utils.logger.info(
                f"[{self.__class__.__name__}._refresh_proxy_if_expired] New proxy: {new_proxy.ip}:{new_proxy.port}"
            )
