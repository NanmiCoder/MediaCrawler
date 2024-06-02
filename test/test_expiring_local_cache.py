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
