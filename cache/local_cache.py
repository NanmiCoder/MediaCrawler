# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/cache/local_cache.py
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
# @Name    : Programmer AJiang-Relakkes
# @Time    : 2024/6/2 11:05
# @Desc    : Local cache

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from cache.abs_cache import AbstractCache


class ExpiringLocalCache(AbstractCache):

    def __init__(self, cron_interval: int = 10):
        """
        Initialize local cache
        :param cron_interval: Time interval for scheduled cache cleanup
        :return:
        """
        self._cron_interval = cron_interval
        self._cache_container: Dict[str, Tuple[Any, float]] = {}
        self._cron_task: Optional[asyncio.Task] = None
        # Start scheduled cleanup task
        self._schedule_clear()

    def __del__(self):
        """
        Destructor function, cleanup scheduled task
        :return:
        """
        if self._cron_task is not None:
            self._cron_task.cancel()

    def get(self, key: str) -> Optional[Any]:
        """
        Get the value of a key from the cache
        :param key:
        :return:
        """
        value, expire_time = self._cache_container.get(key, (None, 0))
        if value is None:
            return None

        # If the key has expired, delete it and return None
        if expire_time < time.time():
            del self._cache_container[key]
            return None

        return value

    def set(self, key: str, value: Any, expire_time: int) -> None:
        """
        Set the value of a key in the cache
        :param key:
        :param value:
        :param expire_time:
        :return:
        """
        self._cache_container[key] = (value, time.time() + expire_time)

    def keys(self, pattern: str) -> List[str]:
        """
        Get all keys matching the pattern
        :param pattern: Matching pattern
        :return:
        """
        if pattern == '*':
            return list(self._cache_container.keys())

        # For local cache wildcard, temporarily replace * with empty string
        if '*' in pattern:
            pattern = pattern.replace('*', '')

        return [key for key in self._cache_container.keys() if pattern in key]

    def _schedule_clear(self):
        """
        Start scheduled cleanup task
        :return:
        """

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self._cron_task = loop.create_task(self._start_clear_cron())

    def _clear(self):
        """
        Clean up cache based on expiration time
        :return:
        """
        for key, (value, expire_time) in self._cache_container.items():
            if expire_time < time.time():
                del self._cache_container[key]

    async def _start_clear_cron(self):
        """
        Start scheduled cleanup task
        :return:
        """
        while True:
            self._clear()
            await asyncio.sleep(self._cron_interval)


if __name__ == '__main__':
    cache = ExpiringLocalCache(cron_interval=2)
    cache.set('name', 'Programmer AJiang-Relakkes', 3)
    print(cache.get('key'))
    print(cache.keys("*"))
    time.sleep(4)
    print(cache.get('key'))
    del cache
    time.sleep(1)
    print("done")
