# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/proxy/providers/kuaidl_proxy.py
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
# @Time    : 2024/4/5 09:43
# @Desc    : 快代理HTTP实现，官方文档：https://www.kuaidaili.com/?ref=ldwkjqipvz6c
import os
import re
from typing import Dict, List

import httpx
from pydantic import BaseModel, Field

from proxy import IpCache, IpInfoModel, ProxyProvider
from proxy.types import ProviderNameEnum
from tools import utils

# 快代理的IP代理过期时间向前推移5秒，避免临界时间使用失败
DELTA_EXPIRED_SECOND = 5


class KuaidailiProxyModel(BaseModel):
    ip: str = Field("ip")
    port: int = Field("端口")
    expire_ts: int = Field("过期时间，单位秒，多少秒后过期")


def parse_kuaidaili_proxy(proxy_info: str) -> KuaidailiProxyModel:
    """
    解析快代理的IP信息
    Args:
        proxy_info:

    Returns:

    """
    proxies: List[str] = proxy_info.split(":")
    if len(proxies) != 2:
        raise Exception("not invalid kuaidaili proxy info")

    pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5}),(\d+)'
    match = re.search(pattern, proxy_info)
    if not match.groups():
        raise Exception("not match kuaidaili proxy info")

    return KuaidailiProxyModel(
        ip=match.groups()[0],
        port=int(match.groups()[1]),
        expire_ts=int(match.groups()[2])
    )


class KuaiDaiLiProxy(ProxyProvider):
    def __init__(self, kdl_user_name: str, kdl_user_pwd: str, kdl_secret_id: str, kdl_signature: str):
        """

        Args:
            kdl_user_name:
            kdl_user_pwd:
        """
        self.kdl_user_name = kdl_user_name
        self.kdl_user_pwd = kdl_user_pwd
        self.api_base = "https://dps.kdlapi.com/"
        self.secret_id = kdl_secret_id
        self.signature = kdl_signature
        self.ip_cache = IpCache()
        self.proxy_brand_name = ProviderNameEnum.KUAI_DAILI_PROVIDER.value
        self.params = {
            "secret_id": self.secret_id,
            "signature": self.signature,
            "pt": 1,
            "format": "json",
            "sep": 1,
            "f_et": 1,
        }

    async def get_proxy(self, num: int) -> List[IpInfoModel]:
        """
        快代理实现
        Args:
            num:

        Returns:

        """
        uri = "/api/getdps/"

        # 优先从缓存中拿 IP
        ip_cache_list = self.ip_cache.load_all_ip(proxy_brand_name=self.proxy_brand_name)
        if len(ip_cache_list) >= num:
            return ip_cache_list[:num]

        # 如果缓存中的数量不够，从IP代理商获取补上，再存入缓存中
        need_get_count = num - len(ip_cache_list)
        self.params.update({"num": need_get_count})

        ip_infos: List[IpInfoModel] = []
        async with httpx.AsyncClient() as client:
            response = await client.get(self.api_base + uri, params=self.params)

            if response.status_code != 200:
                utils.logger.error(f"[KuaiDaiLiProxy.get_proxies] statuc code not 200 and response.txt:{response.text}, status code: {response.status_code}")
                raise Exception("get ip error from proxy provider and status code not 200 ...")

            ip_response: Dict = response.json()
            if ip_response.get("code") != 0:
                utils.logger.error(f"[KuaiDaiLiProxy.get_proxies]  code not 0 and msg:{ip_response.get('msg')}")
                raise Exception("get ip error from proxy provider and  code not 0 ...")

            proxy_list: List[str] = ip_response.get("data", {}).get("proxy_list")
            for proxy in proxy_list:
                proxy_model = parse_kuaidaili_proxy(proxy)
                # expire_ts是相对时间（秒数），需要转换为绝对时间戳
                # 提前DELTA_EXPIRED_SECOND秒认为过期，避免临界时间使用失败
                ip_info_model = IpInfoModel(
                    ip=proxy_model.ip,
                    port=proxy_model.port,
                    user=self.kdl_user_name,
                    password=self.kdl_user_pwd,
                    expired_time_ts=proxy_model.expire_ts + utils.get_unix_timestamp() - DELTA_EXPIRED_SECOND,

                )
                ip_key = f"{self.proxy_brand_name}_{ip_info_model.ip}_{ip_info_model.port}"
                # 缓存过期时间使用相对时间（秒数），也需要减去缓冲时间
                self.ip_cache.set_ip(ip_key, ip_info_model.model_dump_json(), ex=proxy_model.expire_ts - DELTA_EXPIRED_SECOND)
                ip_infos.append(ip_info_model)

        return ip_cache_list + ip_infos


def new_kuai_daili_proxy() -> KuaiDaiLiProxy:
    """
    构造快代理HTTP实例
    支持两种环境变量命名格式：
    1. 大写格式：KDL_SECERT_ID, KDL_SIGNATURE, KDL_USER_NAME, KDL_USER_PWD
    2. 小写格式：kdl_secret_id, kdl_signature, kdl_user_name, kdl_user_pwd
    优先使用大写格式，如果不存在则使用小写格式
    Returns:

    """
    # 支持大小写两种环境变量格式，优先使用大写
    kdl_secret_id = os.getenv("KDL_SECERT_ID") or os.getenv("kdl_secret_id", "你的快代理secert_id")
    kdl_signature = os.getenv("KDL_SIGNATURE") or os.getenv("kdl_signature", "你的快代理签名")
    kdl_user_name = os.getenv("KDL_USER_NAME") or os.getenv("kdl_user_name", "你的快代理用户名")
    kdl_user_pwd = os.getenv("KDL_USER_PWD") or os.getenv("kdl_user_pwd", "你的快代理密码")

    return KuaiDaiLiProxy(
        kdl_secret_id=kdl_secret_id,
        kdl_signature=kdl_signature,
        kdl_user_name=kdl_user_name,
        kdl_user_pwd=kdl_user_pwd,
    )
