# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/6/2 11:23
# @Desc    :


class CacheFactory:
    """
    缓存工厂类
    """

    @staticmethod
    def create_cache(cache_type: str, *args, **kwargs):
        """
        创建缓存对象
        :param cache_type: 缓存类型
        :param args: 参数
        :param kwargs: 关键字参数
        :return:
        """
        if cache_type == 'memory':
            from .local_cache import ExpiringLocalCache
            return ExpiringLocalCache(*args, **kwargs)
        elif cache_type == 'redis':
            from .redis_cache import RedisCache
            return RedisCache()
        else:
            raise ValueError(f'Unknown cache type: {cache_type}')
