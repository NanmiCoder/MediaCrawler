# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/proxy/providers/wandou_http_proxy.py
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
# @Time    : 2025/7/31
# @Desc    : WanDou HTTP proxy IP implementation
import os
from typing import Dict, List
from urllib.parse import urlencode

import httpx

from proxy import IpCache, IpGetError, ProxyProvider
from proxy.types import IpInfoModel
from tools import utils


class WanDouHttpProxy(ProxyProvider):

    def __init__(self, app_key: str, num: int = 100):
        """
        WanDou HTTP proxy IP implementation
        :param app_key: Open app_key, can be obtained through user center
        :param num: Number of IPs extracted at once, maximum 100
        """
        self.proxy_brand_name = "WANDOUHTTP"
        self.api_path = "https://api.wandouapp.com/"
        self.params = {
            "app_key": app_key,
            "num": num,
        }
        self.ip_cache = IpCache()

    async def get_proxy(self, num: int) -> List[IpInfoModel]:
        """
        :param num:
        :return:
        """

        # Prioritize getting IP from cache
        ip_cache_list = self.ip_cache.load_all_ip(
            proxy_brand_name=self.proxy_brand_name
        )
        if len(ip_cache_list) >= num:
            return ip_cache_list[:num]

        # If the quantity in cache is insufficient, get from IP provider to supplement, then store in cache
        need_get_count = num - len(ip_cache_list)
        self.params.update({"num": min(need_get_count, 100)})  # Maximum 100
        ip_infos = []
        async with httpx.AsyncClient() as client:
            url = self.api_path + "?" + urlencode(self.params)
            utils.logger.info(f"[WanDouHttpProxy.get_proxy] get ip proxy url:{url}")
            response = await client.get(
                url,
                headers={
                    "User-Agent": "MediaCrawler https://github.com/NanmiCoder/MediaCrawler",
                },
            )
            res_dict: Dict = response.json()
            if res_dict.get("code") == 200:
                data: List[Dict] = res_dict.get("data", [])
                current_ts = utils.get_unix_timestamp()
                for ip_item in data:
                    ip_info_model = IpInfoModel(
                        ip=ip_item.get("ip"),
                        port=ip_item.get("port"),
                        user="",  # WanDou HTTP does not require username password authentication
                        password="",
                        expired_time_ts=utils.get_unix_time_from_time_str(
                            ip_item.get("expire_time")
                        ),
                    )
                    ip_key = f"WANDOUHTTP_{ip_info_model.ip}_{ip_info_model.port}"
                    ip_value = ip_info_model.model_dump_json()
                    ip_infos.append(ip_info_model)
                    self.ip_cache.set_ip(
                        ip_key, ip_value, ex=ip_info_model.expired_time_ts - current_ts
                    )
            else:
                error_msg = res_dict.get("msg", "unknown error")
                # Handle specific error codes
                error_code = res_dict.get("code")
                if error_code == 10001:
                    error_msg = "General error, check msg content for specific error information"
                elif error_code == 10048:
                    error_msg = "No available package"
                raise IpGetError(f"{error_msg} (code: {error_code})")
        return ip_cache_list + ip_infos


def new_wandou_http_proxy() -> WanDouHttpProxy:
    """
    Construct WanDou HTTP instance
    Supports two environment variable naming formats:
    1. Uppercase format: WANDOU_APP_KEY
    2. Lowercase format: wandou_app_key
    Prioritize uppercase format, use lowercase format if not exists
    Returns:

    """
    # Support both uppercase and lowercase environment variable formats, prioritize uppercase
    app_key = os.getenv("WANDOU_APP_KEY") or os.getenv("wandou_app_key", "your_wandou_http_app_key")

    return WanDouHttpProxy(app_key=app_key)
