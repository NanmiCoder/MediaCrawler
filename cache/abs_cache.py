# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/6/2 11:06
# @Desc    : 抽象类

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class AbstractCache(ABC):

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        从缓存中获取键的值。
        这是一个抽象方法。子类必须实现这个方法。
        :param key: 键
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, expire_time: int) -> None:
        """
        将键的值设置到缓存中。
        这是一个抽象方法。子类必须实现这个方法。
        :param key: 键
        :param value: 值
        :param expire_time: 过期时间
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def keys(self, pattern: str) -> List[str]:
        """
        获取所有符合pattern的key
        :param pattern: 匹配模式
        :return:
        """
        raise NotImplementedError
