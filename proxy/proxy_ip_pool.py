# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 13:45
# @Desc    : ip代理池实现
import json
import pathlib
import random
from typing import List

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from tools import utils

from .proxy_ip_provider import IpInfoModel, IpProxy


class ProxyIpPool:
    def __init__(self, ip_pool_count: int, enable_validate_ip: bool) -> None:
        self.valid_ip_url = "https://httpbin.org/ip"  # 验证 IP 是否有效的地址
        self.ip_pool_count = ip_pool_count
        self.enable_validate_ip = enable_validate_ip
        self.proxy_list: List[IpInfoModel] = []

    async def load_proxies(self) -> None:
        """
        解析
        :return:
        """
        self.proxy_list = await IpProxy.get_proxies(self.ip_pool_count)

    async def is_valid_proxy(self, proxy: IpInfoModel) -> bool:
        """
        验证代理IP是否有效
        :param proxy:
        :return:
        """

        utils.logger.info(f"[ProxyIpPool.is_valid_proxy] testing {proxy.ip} is it valid ")
        try:
            httpx_proxy = {
                f"{proxy.protocol}": f"http://{proxy.user}:{proxy.password}@{proxy.ip}:{proxy.port}"
            }
            async with httpx.AsyncClient(proxies=httpx_proxy) as client:
                response = await client.get(self.valid_ip_url)
            if response.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            utils.logger.info(f"[ProxyIpPool.is_valid_proxy] testing {proxy.ip} err: {e}")
            raise e

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_proxy(self) -> IpInfoModel:
        """
        从代理池中随机提取一个代理IP
        :return:
        """
        if len(self.proxy_list) == 0:
            await self.reload_proxies()

        proxy = random.choice(self.proxy_list)
        if self.enable_validate_ip:
            if not await self.is_valid_proxy(proxy):
                raise Exception("[ProxyIpPool.get_proxy] current ip invalid and again get it")
        self.proxy_list.remove(proxy)
        return proxy

    async def reload_proxies(self):
        """
        # 重新加载代理池
        :return:
        """
        self.proxy_list = []
        await self.load_proxies()


async def create_ip_pool(ip_pool_count: int, enable_validate_ip) -> ProxyIpPool:
    """
     创建 IP 代理池
    :param ip_pool_count:
    :param enable_validate_ip:
    :return:
    """
    pool = ProxyIpPool(ip_pool_count, enable_validate_ip)
    await pool.load_proxies()
    return pool


if __name__ == '__main__':
    pass
