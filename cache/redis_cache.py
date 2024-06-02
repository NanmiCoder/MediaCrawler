# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/5/29 22:57
# @Desc    : RedisCache实现
import pickle
import time
from typing import Any, List

from redis import Redis

from cache.abs_cache import AbstractCache
from config import db_config


class RedisCache(AbstractCache):

    def __init__(self) -> None:
        # 连接redis, 返回redis客户端
        self._redis_client = self._connet_redis()

    @staticmethod
    def _connet_redis() -> Redis:
        """
        连接redis, 返回redis客户端, 这里按需配置redis连接信息
        :return:
        """
        return Redis(
            host=db_config.REDIS_DB_HOST,
            port=db_config.REDIS_DB_PORT,
            db=db_config.REDIS_DB_NUM,
            password=db_config.REDIS_DB_PWD,
        )

    def get(self, key: str) -> Any:
        """
        从缓存中获取键的值, 并且反序列化
        :param key:
        :return:
        """
        value = self._redis_client.get(key)
        if value is None:
            return None
        return pickle.loads(value)

    def set(self, key: str, value: Any, expire_time: int) -> None:
        """
        将键的值设置到缓存中, 并且序列化
        :param key:
        :param value:
        :param expire_time:
        :return:
        """
        self._redis_client.set(key, pickle.dumps(value), ex=expire_time)

    def keys(self, pattern: str) -> List[str]:
        """
        获取所有符合pattern的key
        """
        return [key.decode() for key in self._redis_client.keys(pattern)]


if __name__ == '__main__':
    redis_cache = RedisCache()
    # basic usage
    redis_cache.set("name", "程序员阿江-Relakkes", 1)
    print(redis_cache.get("name"))  # Relakkes
    print(redis_cache.keys("*"))  # ['name']
    time.sleep(2)
    print(redis_cache.get("name"))  # None

    # special python type usage
    # list
    redis_cache.set("list", [1, 2, 3], 10)
    _value = redis_cache.get("list")
    print(_value, f"value type:{type(_value)}")  # [1, 2, 3]
