# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 11:18
# @Desc    : 爬虫 IP 获取实现
# @Url     : 现在实现了极速HTTP的接口，官网地址：https://www.jisuhttp.com/?pl=mAKphQ&plan=ZY&kd=Yang
import json
from abc import ABC, abstractmethod
from typing import Dict, List

import redis

import config
from tools import utils

from .types import IpInfoModel


class IpGetError(Exception):
    """ ip get error"""


class ProxyProvider(ABC):
    @abstractmethod
    async def get_proxies(self, num: int) -> List[IpInfoModel]:
        """
        获取 IP 的抽象方法，不同的 HTTP 代理商需要实现该方法
        :param num: 提取的 IP 数量
        :return:
        """
        pass


class RedisDbIpCache:
    def __init__(self):
        self.redis_client = redis.Redis(host=config.REDIS_DB_HOST, password=config.REDIS_DB_PWD)

    def set_ip(self, ip_key: str, ip_value_info: str, ex: int):
        """
        设置IP并带有过期时间，到期之后由 redis 负责删除
        :param ip_key:
        :param ip_value_info:
        :param ex:
        :return:
        """
        self.redis_client.set(name=ip_key, value=ip_value_info, ex=ex)

    def load_all_ip(self, proxy_brand_name: str) -> List[IpInfoModel]:
        """
        从 redis 中加载所有还未过期的 IP 信息
        :param proxy_brand_name: 代理商名称
        :return:
        """
        all_ip_list: List[IpInfoModel] = []
        all_ip_keys: List[bytes] = self.redis_client.keys(pattern=f"{proxy_brand_name}_*")
        try:
            for ip_key in all_ip_keys:
                ip_value = self.redis_client.get(ip_key)
                if not ip_value:
                    continue
                all_ip_list.append(IpInfoModel(**json.loads(ip_value)))
        except Exception as e:
            utils.logger.error("[RedisDbIpCache.load_all_ip] get ip err from redis db", e)
        return all_ip_list
