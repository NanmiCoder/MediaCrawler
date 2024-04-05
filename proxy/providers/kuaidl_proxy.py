# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/4/5 09:43
# @Desc    : 快代理HTTP实现，官方文档：https://www.kuaidaili.com/?ref=ldwkjqipvz6c
from typing import Dict, List

from proxy import IpGetError, IpInfoModel, ProxyProvider, RedisDbIpCache


class KuaiDaiLiProxy(ProxyProvider):
    async def get_proxies(self, num: int) -> List[Dict]:
        pass


def new_kuai_daili_proxy() -> KuaiDaiLiProxy:
    """
    构造快代理HTTP实例
    Returns:

    """
    return KuaiDaiLiProxy()
