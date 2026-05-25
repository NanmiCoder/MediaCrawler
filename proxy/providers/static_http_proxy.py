# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/proxy/providers/static_http_proxy.py
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
# @Time    : 2026/3/26
# @Desc    : Static HTTP proxy provider implementation
from typing import List
from urllib.parse import urlparse

import config

from proxy import ProxyProvider
from proxy.types import IpInfoModel, ProviderNameEnum


def parse_static_http_proxy(proxy_url: str) -> IpInfoModel:
    normalized = proxy_url.strip()
    if not normalized:
        raise ValueError("--static_proxy is empty")
    if "://" not in normalized:
        normalized = f"http://{normalized}"

    parsed = urlparse(normalized)
    if parsed.scheme not in ("http",):
        raise ValueError("--static_proxy must use the http scheme")
    if not parsed.hostname or not parsed.port:
        raise ValueError("--static_proxy must include host and port")

    return IpInfoModel(
        ip=parsed.hostname,
        port=parsed.port,
        user=parsed.username or "",
        password=parsed.password or "",
        protocol="http://",
        expired_time_ts=None,
    )


def parse_static_http_proxies(proxy_urls: str) -> List[IpInfoModel]:
    proxies = [
        parse_static_http_proxy(item)
        for item in proxy_urls.split(",")
        if item.strip()
    ]
    if not proxies:
        raise ValueError("--static_proxy is empty")
    return proxies


class StaticHttpProxy(ProxyProvider):
    def __init__(self):
        self.proxy_brand_name = ProviderNameEnum.STATIC_HTTP_PROVIDER.value

    async def get_proxy(self, num: int) -> List[IpInfoModel]:
        del num
        return parse_static_http_proxies(getattr(config, "STATIC_PROXY_URL", ""))


def new_static_http_proxy() -> StaticHttpProxy:
    return StaticHttpProxy()
