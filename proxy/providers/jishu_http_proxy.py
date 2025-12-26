# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/proxy/providers/jishu_http_proxy.py
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
# @Time    : 2024/4/5 09:32
# @Desc    : Deprecated!!!!! Shut down!!! JiSu HTTP proxy IP implementation. Please use KuaiDaili implementation (proxy/providers/kuaidl_proxy.py)
import os
from typing import Dict, List
from urllib.parse import urlencode

import httpx

from proxy import IpCache, IpGetError, ProxyProvider
from proxy.types import IpInfoModel
from tools import utils


class JiSuHttpProxy(ProxyProvider):

    def __init__(self, key: str, crypto: str, time_validity_period: int):
        """
        JiSu HTTP proxy IP implementation
        :param key: Extraction key value (obtain after registering on the official website)
        :param crypto: Encryption signature (obtain after registering on the official website)
        """
        self.proxy_brand_name = "JISUHTTP"
        self.api_path = "https://api.jisuhttp.com"
        self.params = {
            "key": key,
            "crypto": crypto,
            "time": time_validity_period,  # IP usage duration, supports 3, 5, 10, 15, 30 minute validity
            "type": "json",  # Data result is json
            "port": "2",  # IP protocol: 1:HTTP, 2:HTTPS, 3:SOCKS5
            "pw": "1",  # Whether to use account password authentication, 1: yes, 0: no, no means whitelist authentication; default is 0
            "se": "1",  # Whether to show IP expiration time when returning JSON format, 1: show, 0: don't show; default is 0
        }
        self.ip_cache = IpCache()

    async def get_proxy(self, num: int) -> List[IpInfoModel]:
        """
        :param num:
        :return:
        """

        # Prioritize getting IP from cache
        ip_cache_list = self.ip_cache.load_all_ip(proxy_brand_name=self.proxy_brand_name)
        if len(ip_cache_list) >= num:
            return ip_cache_list[:num]

        # If the quantity in cache is insufficient, get from IP provider to supplement, then store in cache
        need_get_count = num - len(ip_cache_list)
        self.params.update({"num": need_get_count})
        ip_infos = []
        async with httpx.AsyncClient() as client:
            url = self.api_path + "/fetchips" + '?' + urlencode(self.params)
            utils.logger.info(f"[JiSuHttpProxy.get_proxy] get ip proxy url:{url}")
            response = await client.get(url, headers={
                "User-Agent": "MediaCrawler https://github.com/NanmiCoder/MediaCrawler",
            })
            res_dict: Dict = response.json()
            if res_dict.get("code") == 0:
                data: List[Dict] = res_dict.get("data")
                current_ts = utils.get_unix_timestamp()
                for ip_item in data:
                    ip_info_model = IpInfoModel(
                        ip=ip_item.get("ip"),
                        port=ip_item.get("port"),
                        user=ip_item.get("user"),
                        password=ip_item.get("pass"),
                        expired_time_ts=utils.get_unix_time_from_time_str(ip_item.get("expire")),
                    )
                    ip_key = f"JISUHTTP_{ip_info_model.ip}_{ip_info_model.port}_{ip_info_model.user}_{ip_info_model.password}"
                    ip_value = ip_info_model.json()
                    ip_infos.append(ip_info_model)
                    self.ip_cache.set_ip(ip_key, ip_value, ex=ip_info_model.expired_time_ts - current_ts)
            else:
                raise IpGetError(res_dict.get("msg", "unkown err"))
        return ip_cache_list + ip_infos


def new_jisu_http_proxy() -> JiSuHttpProxy:
    """
    Construct JiSu HTTP instance
    Returns:

    """
    return JiSuHttpProxy(
        key=os.getenv("jisu_key", ""),  # Get JiSu HTTP IP extraction key value through environment variable
        crypto=os.getenv("jisu_crypto", ""),  # Get JiSu HTTP IP extraction encryption signature through environment variable
        time_validity_period=30  # 30 minutes (maximum validity)
    )
