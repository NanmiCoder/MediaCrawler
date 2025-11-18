# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/test/test_expiring_local_cache.py
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
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/6/2 10:35
# @Desc    :

import time
import unittest

from cache.local_cache import ExpiringLocalCache


class TestExpiringLocalCache(unittest.TestCase):

    def setUp(self):
        self.cache = ExpiringLocalCache(cron_interval=10)

    def test_set_and_get(self):
        self.cache.set('key', 'value', 10)
        self.assertEqual(self.cache.get('key'), 'value')

    def test_expired_key(self):
        self.cache.set('key', 'value', 1)
        time.sleep(2)  # wait for the key to expire
        self.assertIsNone(self.cache.get('key'))

    def test_clear(self):
        # 设置两个键值对，过期时间为11秒
        self.cache.set('key', 'value', 11)
        # 睡眠12秒，让cache类的定时任务执行一次
        time.sleep(12)
        self.assertIsNone(self.cache.get('key'))

    def tearDown(self):
        del self.cache


if __name__ == '__main__':
    unittest.main()
