# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/test/test_proxy_ip_pool.py
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
# @Time    : 2023/12/2 14:42
# @Desc    :
import time
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from proxy.proxy_ip_pool import create_ip_pool, ProxyIpPool
from proxy.types import IpInfoModel


class TestIpPool(IsolatedAsyncioTestCase):
    async def test_ip_pool(self):
        pool = await create_ip_pool(ip_pool_count=1, enable_validate_ip=True)
        print("\n")
        for _ in range(3):
            ip_proxy_info: IpInfoModel = await pool.get_proxy()
            print(ip_proxy_info)
            self.assertIsNotNone(ip_proxy_info.ip, msg="验证 ip 是否获取成功")

    async def test_ip_expiration(self):
        """测试IP代理过期检测功能"""
        print("\n=== 开始测试IP代理过期检测 ===")

        # 1. 创建IP池并获取一个代理
        pool = await create_ip_pool(ip_pool_count=2, enable_validate_ip=True)
        ip_proxy_info: IpInfoModel = await pool.get_proxy()
        print(f"获取到的代理: {ip_proxy_info.ip}:{ip_proxy_info.port}")

        # 2. 测试未过期的情况
        if ip_proxy_info.expired_time_ts:
            print(f"代理过期时间戳: {ip_proxy_info.expired_time_ts}")
            print(f"当前时间戳: {int(time.time())}")
            print(f"剩余有效时间: {ip_proxy_info.expired_time_ts - int(time.time())} 秒")

            is_expired = ip_proxy_info.is_expired(buffer_seconds=30)
            print(f"代理是否过期(缓冲30秒): {is_expired}")
            self.assertFalse(is_expired, msg="新获取的IP应该未过期")
        else:
            print("当前代理未设置过期时间，跳过过期检测")

        # 3. 测试即将过期的情况（设置为5分钟后过期）
        current_ts = int(time.time())
        five_minutes_later = current_ts + 300  # 5分钟 = 300秒
        ip_proxy_info.expired_time_ts = five_minutes_later
        print(f"\n设置代理过期时间为5分钟后: {five_minutes_later}")

        # 不应该过期（缓冲30秒）
        is_expired_30s = ip_proxy_info.is_expired(buffer_seconds=30)
        print(f"代理是否过期(缓冲30秒): {is_expired_30s}")
        self.assertFalse(is_expired_30s, msg="5分钟后过期的IP，缓冲30秒不应该过期")

        # 4. 测试已过期的情况（设置为已经过期）
        expired_ts = current_ts - 60  # 1分钟前已过期
        ip_proxy_info.expired_time_ts = expired_ts
        print(f"\n设置代理过期时间为1分钟前: {expired_ts}")

        is_expired = ip_proxy_info.is_expired(buffer_seconds=30)
        print(f"代理是否过期(缓冲30秒): {is_expired}")
        self.assertTrue(is_expired, msg="已过期的IP应该被检测为过期")

        # 5. 测试临界过期情况（29秒后过期，缓冲30秒应该认为已过期）
        almost_expired_ts = current_ts + 29
        ip_proxy_info.expired_time_ts = almost_expired_ts
        print(f"\n设置代理过期时间为29秒后: {almost_expired_ts}")

        is_expired_critical = ip_proxy_info.is_expired(buffer_seconds=30)
        print(f"代理是否过期(缓冲30秒): {is_expired_critical}")
        self.assertTrue(is_expired_critical, msg="29秒后过期的IP，缓冲30秒应该被认为已过期")

        print("\n=== IP代理过期检测测试完成 ===")

    async def test_proxy_pool_auto_refresh(self):
        """测试代理池自动刷新过期代理的功能"""
        print("\n=== 开始测试代理池自动刷新功能 ===")

        # 1. 创建IP池
        pool = await create_ip_pool(ip_pool_count=2, enable_validate_ip=True)

        # 2. 获取一个代理
        first_proxy = await pool.get_proxy()
        print(f"首次获取代理: {first_proxy.ip}:{first_proxy.port}")

        # 验证当前代理未过期
        is_expired = pool.is_current_proxy_expired(buffer_seconds=30)
        print(f"当前代理是否过期: {is_expired}")

        if first_proxy.expired_time_ts:
            print(f"当前代理过期时间戳: {first_proxy.expired_time_ts}")

            # 3. 手动设置当前代理为已过期
            current_ts = int(time.time())
            pool.current_proxy.expired_time_ts = current_ts - 60
            print(f"\n手动设置代理为已过期（1分钟前）")

            # 4. 检测是否过期
            is_expired_after = pool.is_current_proxy_expired(buffer_seconds=30)
            print(f"设置后代理是否过期: {is_expired_after}")
            self.assertTrue(is_expired_after, msg="手动设置过期后应该被检测为过期")

            # 5. 使用 get_or_refresh_proxy 自动刷新
            print("\n调用 get_or_refresh_proxy 自动刷新过期代理...")
            refreshed_proxy = await pool.get_or_refresh_proxy(buffer_seconds=30)
            print(f"刷新后的代理: {refreshed_proxy.ip}:{refreshed_proxy.port}")

            # 6. 验证新代理未过期
            is_new_expired = pool.is_current_proxy_expired(buffer_seconds=30)
            print(f"新代理是否过期: {is_new_expired}")
            self.assertFalse(is_new_expired, msg="刷新后的新代理应该未过期")

            print("\n=== 代理池自动刷新测试完成 ===")
        else:
            print("当前代理未设置过期时间，跳过自动刷新测试")

    async def test_ip_expiration_standalone(self):
        """独立测试IP过期检测功能（不依赖真实代理提供商）"""
        print("\n=== 开始独立测试IP代理过期检测功能 ===")

        current_ts = int(time.time())

        # 1. 测试未设置过期时间的IP（永不过期）
        ip_no_expire = IpInfoModel(
            ip="192.168.1.1",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=None
        )
        print(f"\n测试1: IP未设置过期时间")
        is_expired = ip_no_expire.is_expired(buffer_seconds=30)
        print(f"  代理: {ip_no_expire.ip}:{ip_no_expire.port}")
        print(f"  过期时间: {ip_no_expire.expired_time_ts}")
        print(f"  是否过期: {is_expired}")
        self.assertFalse(is_expired, msg="未设置过期时间的IP应该永不过期")

        # 2. 测试5分钟后过期的IP（应该未过期）
        five_minutes_later = current_ts + 300
        ip_valid = IpInfoModel(
            ip="192.168.1.2",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=five_minutes_later
        )
        print(f"\n测试2: IP将在5分钟后过期")
        is_expired = ip_valid.is_expired(buffer_seconds=30)
        print(f"  代理: {ip_valid.ip}:{ip_valid.port}")
        print(f"  当前时间戳: {current_ts}")
        print(f"  过期时间戳: {ip_valid.expired_time_ts}")
        print(f"  剩余时间: {ip_valid.expired_time_ts - current_ts} 秒")
        print(f"  是否过期(缓冲30秒): {is_expired}")
        self.assertFalse(is_expired, msg="5分钟后过期的IP，缓冲30秒不应该过期")

        # 3. 测试已过期的IP
        already_expired = current_ts - 60
        ip_expired = IpInfoModel(
            ip="192.168.1.3",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=already_expired
        )
        print(f"\n测试3: IP已经过期（1分钟前）")
        is_expired = ip_expired.is_expired(buffer_seconds=30)
        print(f"  代理: {ip_expired.ip}:{ip_expired.port}")
        print(f"  当前时间戳: {current_ts}")
        print(f"  过期时间戳: {ip_expired.expired_time_ts}")
        print(f"  已过期: {current_ts - ip_expired.expired_time_ts} 秒")
        print(f"  是否过期(缓冲30秒): {is_expired}")
        self.assertTrue(is_expired, msg="已过期的IP应该被检测为过期")

        # 4. 测试临界过期（29秒后过期，缓冲30秒应该认为已过期）
        almost_expired = current_ts + 29
        ip_critical = IpInfoModel(
            ip="192.168.1.4",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=almost_expired
        )
        print(f"\n测试4: IP即将过期（29秒后）")
        is_expired = ip_critical.is_expired(buffer_seconds=30)
        print(f"  代理: {ip_critical.ip}:{ip_critical.port}")
        print(f"  当前时间戳: {current_ts}")
        print(f"  过期时间戳: {ip_critical.expired_time_ts}")
        print(f"  剩余时间: {ip_critical.expired_time_ts - current_ts} 秒")
        print(f"  是否过期(缓冲30秒): {is_expired}")
        self.assertTrue(is_expired, msg="29秒后过期的IP，缓冲30秒应该被认为已过期")

        # 5. 测试31秒后过期（缓冲30秒应该未过期）
        just_safe = current_ts + 31
        ip_just_safe = IpInfoModel(
            ip="192.168.1.5",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=just_safe
        )
        print(f"\n测试5: IP在安全范围内（31秒后过期）")
        is_expired = ip_just_safe.is_expired(buffer_seconds=30)
        print(f"  代理: {ip_just_safe.ip}:{ip_just_safe.port}")
        print(f"  当前时间戳: {current_ts}")
        print(f"  过期时间戳: {ip_just_safe.expired_time_ts}")
        print(f"  剩余时间: {ip_just_safe.expired_time_ts - current_ts} 秒")
        print(f"  是否过期(缓冲30秒): {is_expired}")
        self.assertFalse(is_expired, msg="31秒后过期的IP，缓冲30秒应该未过期")

        # 6. 测试ProxyIpPool的过期检测
        print(f"\n测试6: ProxyIpPool的过期检测功能")
        mock_provider = MagicMock()
        mock_provider.get_proxy = AsyncMock(return_value=[])

        pool = ProxyIpPool(
            ip_pool_count=1,
            enable_validate_ip=False,
            ip_provider=mock_provider
        )

        # 6.1 测试无当前代理时
        is_expired = pool.is_current_proxy_expired(buffer_seconds=30)
        print(f"  无当前代理时是否过期: {is_expired}")
        self.assertTrue(is_expired, msg="无当前代理时应该返回True")

        # 6.2 设置一个有效的代理
        valid_proxy = IpInfoModel(
            ip="192.168.1.6",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=current_ts + 300  # 5分钟后过期
        )
        pool.current_proxy = valid_proxy
        is_expired = pool.is_current_proxy_expired(buffer_seconds=30)
        print(f"  设置有效代理后是否过期: {is_expired}")
        self.assertFalse(is_expired, msg="有效的代理应该返回False")

        # 6.3 设置一个已过期的代理
        expired_proxy = IpInfoModel(
            ip="192.168.1.7",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=current_ts - 60  # 1分钟前已过期
        )
        pool.current_proxy = expired_proxy
        is_expired = pool.is_current_proxy_expired(buffer_seconds=30)
        print(f"  设置已过期代理后是否过期: {is_expired}")
        self.assertTrue(is_expired, msg="已过期的代理应该返回True")

        print("\n=== 独立IP代理过期检测测试完成 ===\n")
