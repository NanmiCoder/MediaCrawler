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
            self.assertIsNotNone(ip_proxy_info.ip, msg="Verify if IP is obtained successfully")

    async def test_ip_expiration(self):
        """Test IP proxy expiration detection functionality"""
        print("\n=== Starting IP proxy expiration detection test ===")

        # 1. Create IP pool and get a proxy
        pool = await create_ip_pool(ip_pool_count=2, enable_validate_ip=True)
        ip_proxy_info: IpInfoModel = await pool.get_proxy()
        print(f"Obtained proxy: {ip_proxy_info.ip}:{ip_proxy_info.port}")

        # 2. Test non-expired case
        if ip_proxy_info.expired_time_ts:
            print(f"Proxy expiration timestamp: {ip_proxy_info.expired_time_ts}")
            print(f"Current timestamp: {int(time.time())}")
            print(f"Remaining valid time: {ip_proxy_info.expired_time_ts - int(time.time())} seconds")

            is_expired = ip_proxy_info.is_expired(buffer_seconds=30)
            print(f"Is proxy expired (30s buffer): {is_expired}")
            self.assertFalse(is_expired, msg="Newly obtained IP should not be expired")
        else:
            print("Current proxy does not have expiration time set, skipping expiration detection")

        # 3. Test about to expire case (set to expire in 5 minutes)
        current_ts = int(time.time())
        five_minutes_later = current_ts + 300  # 5 minutes = 300 seconds
        ip_proxy_info.expired_time_ts = five_minutes_later
        print(f"\nSet proxy expiration time to 5 minutes later: {five_minutes_later}")

        # Should not be expired (30s buffer)
        is_expired_30s = ip_proxy_info.is_expired(buffer_seconds=30)
        print(f"Is proxy expired (30s buffer): {is_expired_30s}")
        self.assertFalse(is_expired_30s, msg="IP expiring in 5 minutes should not be expired with 30s buffer")

        # 4. Test already expired case (set to already expired)
        expired_ts = current_ts - 60  # Expired 1 minute ago
        ip_proxy_info.expired_time_ts = expired_ts
        print(f"\nSet proxy expiration time to 1 minute ago: {expired_ts}")

        is_expired = ip_proxy_info.is_expired(buffer_seconds=30)
        print(f"Is proxy expired (30s buffer): {is_expired}")
        self.assertTrue(is_expired, msg="Expired IP should be detected as expired")

        # 5. Test critical expiration case (expires in 29s, should be considered expired with 30s buffer)
        almost_expired_ts = current_ts + 29
        ip_proxy_info.expired_time_ts = almost_expired_ts
        print(f"\nSet proxy expiration time to 29 seconds later: {almost_expired_ts}")

        is_expired_critical = ip_proxy_info.is_expired(buffer_seconds=30)
        print(f"Is proxy expired (30s buffer): {is_expired_critical}")
        self.assertTrue(is_expired_critical, msg="IP expiring in 29s should be considered expired with 30s buffer")

        print("\n=== IP proxy expiration detection test completed ===")

    async def test_proxy_pool_auto_refresh(self):
        """Test proxy pool auto-refresh expired proxy functionality"""
        print("\n=== Starting proxy pool auto-refresh test ===")

        # 1. Create IP pool
        pool = await create_ip_pool(ip_pool_count=2, enable_validate_ip=True)

        # 2. Get a proxy
        first_proxy = await pool.get_proxy()
        print(f"First proxy obtained: {first_proxy.ip}:{first_proxy.port}")

        # Verify current proxy is not expired
        is_expired = pool.is_current_proxy_expired(buffer_seconds=30)
        print(f"Is current proxy expired: {is_expired}")

        if first_proxy.expired_time_ts:
            print(f"Current proxy expiration timestamp: {first_proxy.expired_time_ts}")

            # 3. Manually set current proxy as expired
            current_ts = int(time.time())
            pool.current_proxy.expired_time_ts = current_ts - 60
            print(f"\nManually set proxy as expired (1 minute ago)")

            # 4. Check if expired
            is_expired_after = pool.is_current_proxy_expired(buffer_seconds=30)
            print(f"Is proxy expired after setting: {is_expired_after}")
            self.assertTrue(is_expired_after, msg="Should be detected as expired after manual setting")

            # 5. Use get_or_refresh_proxy to auto-refresh
            print("\nCalling get_or_refresh_proxy to auto-refresh expired proxy...")
            refreshed_proxy = await pool.get_or_refresh_proxy(buffer_seconds=30)
            print(f"Refreshed proxy: {refreshed_proxy.ip}:{refreshed_proxy.port}")

            # 6. Verify new proxy is not expired
            is_new_expired = pool.is_current_proxy_expired(buffer_seconds=30)
            print(f"Is new proxy expired: {is_new_expired}")
            self.assertFalse(is_new_expired, msg="Refreshed new proxy should not be expired")

            print("\n=== Proxy pool auto-refresh test completed ===")
        else:
            print("Current proxy does not have expiration time set, skipping auto-refresh test")

    async def test_ip_expiration_standalone(self):
        """Standalone test for IP expiration detection (does not depend on real proxy provider)"""
        print("\n=== Starting standalone IP proxy expiration detection test ===")

        current_ts = int(time.time())

        # 1. Test IP without expiration time set (never expires)
        ip_no_expire = IpInfoModel(
            ip="192.168.1.1",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=None
        )
        print(f"\nTest 1: IP without expiration time set")
        is_expired = ip_no_expire.is_expired(buffer_seconds=30)
        print(f"  Proxy: {ip_no_expire.ip}:{ip_no_expire.port}")
        print(f"  Expiration time: {ip_no_expire.expired_time_ts}")
        print(f"  Is expired: {is_expired}")
        self.assertFalse(is_expired, msg="IP without expiration time should never expire")

        # 2. Test IP expiring in 5 minutes (should not be expired)
        five_minutes_later = current_ts + 300
        ip_valid = IpInfoModel(
            ip="192.168.1.2",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=five_minutes_later
        )
        print(f"\nTest 2: IP will expire in 5 minutes")
        is_expired = ip_valid.is_expired(buffer_seconds=30)
        print(f"  Proxy: {ip_valid.ip}:{ip_valid.port}")
        print(f"  Current timestamp: {current_ts}")
        print(f"  Expiration timestamp: {ip_valid.expired_time_ts}")
        print(f"  Remaining time: {ip_valid.expired_time_ts - current_ts} seconds")
        print(f"  Is expired (30s buffer): {is_expired}")
        self.assertFalse(is_expired, msg="IP expiring in 5 minutes should not be expired with 30s buffer")

        # 3. Test already expired IP
        already_expired = current_ts - 60
        ip_expired = IpInfoModel(
            ip="192.168.1.3",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=already_expired
        )
        print(f"\nTest 3: IP already expired (1 minute ago)")
        is_expired = ip_expired.is_expired(buffer_seconds=30)
        print(f"  Proxy: {ip_expired.ip}:{ip_expired.port}")
        print(f"  Current timestamp: {current_ts}")
        print(f"  Expiration timestamp: {ip_expired.expired_time_ts}")
        print(f"  Expired for: {current_ts - ip_expired.expired_time_ts} seconds")
        print(f"  Is expired (30s buffer): {is_expired}")
        self.assertTrue(is_expired, msg="Expired IP should be detected as expired")

        # 4. Test critical expiration (expires in 29s, should be considered expired with 30s buffer)
        almost_expired = current_ts + 29
        ip_critical = IpInfoModel(
            ip="192.168.1.4",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=almost_expired
        )
        print(f"\nTest 4: IP about to expire (in 29 seconds)")
        is_expired = ip_critical.is_expired(buffer_seconds=30)
        print(f"  Proxy: {ip_critical.ip}:{ip_critical.port}")
        print(f"  Current timestamp: {current_ts}")
        print(f"  Expiration timestamp: {ip_critical.expired_time_ts}")
        print(f"  Remaining time: {ip_critical.expired_time_ts - current_ts} seconds")
        print(f"  Is expired (30s buffer): {is_expired}")
        self.assertTrue(is_expired, msg="IP expiring in 29s should be considered expired with 30s buffer")

        # 5. Test expires in 31s (should not be expired with 30s buffer)
        just_safe = current_ts + 31
        ip_just_safe = IpInfoModel(
            ip="192.168.1.5",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=just_safe
        )
        print(f"\nTest 5: IP within safe range (expires in 31 seconds)")
        is_expired = ip_just_safe.is_expired(buffer_seconds=30)
        print(f"  Proxy: {ip_just_safe.ip}:{ip_just_safe.port}")
        print(f"  Current timestamp: {current_ts}")
        print(f"  Expiration timestamp: {ip_just_safe.expired_time_ts}")
        print(f"  Remaining time: {ip_just_safe.expired_time_ts - current_ts} seconds")
        print(f"  Is expired (30s buffer): {is_expired}")
        self.assertFalse(is_expired, msg="IP expiring in 31s should not be expired with 30s buffer")

        # 6. Test ProxyIpPool expiration detection
        print(f"\nTest 6: ProxyIpPool expiration detection functionality")
        mock_provider = MagicMock()
        mock_provider.get_proxy = AsyncMock(return_value=[])

        pool = ProxyIpPool(
            ip_pool_count=1,
            enable_validate_ip=False,
            ip_provider=mock_provider
        )

        # 6.1 Test when there is no current proxy
        is_expired = pool.is_current_proxy_expired(buffer_seconds=30)
        print(f"  Is expired when no current proxy: {is_expired}")
        self.assertTrue(is_expired, msg="Should return True when there is no current proxy")

        # 6.2 Set a valid proxy
        valid_proxy = IpInfoModel(
            ip="192.168.1.6",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=current_ts + 300  # Expires in 5 minutes
        )
        pool.current_proxy = valid_proxy
        is_expired = pool.is_current_proxy_expired(buffer_seconds=30)
        print(f"  Is expired after setting valid proxy: {is_expired}")
        self.assertFalse(is_expired, msg="Valid proxy should return False")

        # 6.3 Set an expired proxy
        expired_proxy = IpInfoModel(
            ip="192.168.1.7",
            port=8080,
            user="test_user",
            password="test_pwd",
            expired_time_ts=current_ts - 60  # Expired 1 minute ago
        )
        pool.current_proxy = expired_proxy
        is_expired = pool.is_current_proxy_expired(buffer_seconds=30)
        print(f"  Is expired after setting expired proxy: {is_expired}")
        self.assertTrue(is_expired, msg="Expired proxy should return True")

        print("\n=== Standalone IP proxy expiration detection test completed ===\n")
