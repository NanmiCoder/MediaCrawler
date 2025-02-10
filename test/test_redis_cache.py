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
# @Time    : 2024/6/2 19:54
# @Desc    :

import time
import unittest

from cache.redis_cache import RedisCache


class TestRedisCache(unittest.TestCase):

    def setUp(self):
        self.redis_cache = RedisCache()

    def test_set_and_get(self):
        self.redis_cache.set('key', 'value', 10)
        self.assertEqual(self.redis_cache.get('key'), 'value')

    def test_expired_key(self):
        self.redis_cache.set('key', 'value', 1)
        time.sleep(2)  # wait for the key to expire
        self.assertIsNone(self.redis_cache.get('key'))

    def test_keys(self):
        self.redis_cache.set('key1', 'value1', 10)
        self.redis_cache.set('key2', 'value2', 10)
        keys = self.redis_cache.keys('*')
        self.assertIn('key1', keys)
        self.assertIn('key2', keys)

    def tearDown(self):
        # self.redis_cache._redis_client.flushdb()  # 清空redis数据库
        pass


if __name__ == '__main__':
    unittest.main()
