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
