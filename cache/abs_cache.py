# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/cache/abs_cache.py
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
# @Time    : 2024/6/2 11:06
# @Desc    : Abstract class

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class AbstractCache(ABC):

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Get the value of a key from the cache.
        This is an abstract method. Subclasses must implement this method.
        :param key: The key
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, expire_time: int) -> None:
        """
        Set the value of a key in the cache.
        This is an abstract method. Subclasses must implement this method.
        :param key: The key
        :param value: The value
        :param expire_time: Expiration time
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def keys(self, pattern: str) -> List[str]:
        """
        Get all keys matching the pattern
        :param pattern: Matching pattern
        :return:
        """
        raise NotImplementedError
