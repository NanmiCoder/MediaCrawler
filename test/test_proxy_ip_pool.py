# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 14:42
# @Desc    :
from unittest import IsolatedAsyncioTestCase

from proxy.proxy_ip_pool import create_ip_pool
from proxy.proxy_ip_provider import IpInfoModel


class TestIpPool(IsolatedAsyncioTestCase):
    async def test_ip_pool(self):
        pool = await create_ip_pool(ip_pool_count=30, enable_validate_ip=False)
        for i in range(30):
            ip_proxy_info: IpInfoModel = await pool.get_proxy()
            self.assertIsNotNone(ip_proxy_info.ip, msg="验证 ip 是否获取成功")
            print(ip_proxy_info)
