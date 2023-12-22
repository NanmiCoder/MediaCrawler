# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 11:18
# @Desc    : 爬虫 IP 获取实现
# @Url     : 现在实现了极速HTTP的接口，官网地址：https://www.jisuhttp.com/?pl=mAKphQ&plan=ZY&kd=Yang

import asyncio
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from urllib.parse import urlencode

import httpx
import redis
from pydantic import BaseModel, Field

import config
from tools import utils


class IpGetError(Exception):
    """ ip get error"""


class IpInfoModel(BaseModel):
    """Unified IP model"""
    ip: str = Field(title="ip")
    port: int = Field(title="端口")
    user: str = Field(title="IP代理认证的用户名")
    protocol: str = Field(default="https://", title="代理IP的协议")
    password: str = Field(title="IP代理认证用户的密码")
    expired_time_ts: Optional[int] = Field(title="IP 过期时间")


class ProxyProvider(ABC):
    @abstractmethod
    async def get_proxies(self, num: int) -> List[Dict]:
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
        all_ip_keys: List[str] = self.redis_client.keys(pattern=f"{proxy_brand_name}_*")
        try:
            for ip_key in all_ip_keys:
                ip_value = self.redis_client.get(ip_key)
                if not ip_value:
                    continue
                all_ip_list.append(IpInfoModel(**json.loads(ip_value)))
        except Exception as e:
            utils.logger.error("[RedisDbIpCache.load_all_ip] get ip err from redis db", e)
        return all_ip_list


class JiSuHttpProxy(ProxyProvider):
    def __init__(self, key: str, crypto: str, time_validity_period: int):
        """
        极速HTTP 代理IP实现
        官网地址：https://www.jisuhttp.com/?pl=mAKphQ&plan=ZY&kd=Yang
        :param key: 提取key值 (去官网注册后获取)
        :param crypto: 加密签名 (去官网注册后获取)
        """
        self.proxy_brand_name = "JISUHTTP"
        self.api_path = "https://api.jisuhttp.com"
        self.params = {
            "key": key,
            "crypto": crypto,
            "time": time_validity_period,  # IP使用时长，支持3、5、10、15、30分钟时效
            "type": "json",  # 数据结果为json
            "port": "2",  # IP协议：1:HTTP、2:HTTPS、3:SOCKS5
            "pw": "1",  # 是否使用账密验证， 1：是，0：否，否表示白名单验证；默认为0
            "se": "1",  # 返回JSON格式时是否显示IP过期时间， 1：显示，0：不显示；默认为0
        }
        self.ip_cache = RedisDbIpCache()

    async def get_proxies(self, num: int) -> List[IpInfoModel]:
        """
        :param num:
        :return:
        """

        # 优先从缓存中拿 IP
        ip_cache_list = self.ip_cache.load_all_ip(proxy_brand_name=self.proxy_brand_name)
        if len(ip_cache_list) >= num:
            return ip_cache_list[:num]

        # 如果缓存中的数量不够，从IP代理商获取补上，再存入缓存中
        need_get_count = num - len(ip_cache_list)
        self.params.update({"num": need_get_count})
        ip_infos = []
        async with httpx.AsyncClient() as client:
            url = self.api_path + "/fetchips" + '?' + urlencode(self.params)
            utils.logger.info(f"[JiSuHttpProxy.get_proxies] get ip proxy url:{url}")
            response = await client.get(url, headers={
                "User-Agent": "MediaCrawler https://github.com/NanmiCoder/MediaCrawler"})
            res_dict: Dict = response.json()
            if res_dict.get("code") == 0:
                data: List[Dict] = res_dict.get("data")
                current_ts = utils.get_unix_timestamp()
                for ip_item in data:
                    ip_info_model = IpInfoModel(
                        ip=ip_item.get("ip"),
                        port=ip_item.get("port"),
                        user=ip_item.get("user"),
                        password=ip_item.get("pass"),
                        expired_time_ts=utils.get_unix_time_from_time_str(ip_item.get("expire"))
                    )
                    ip_key = f"JISUHTTP_{ip_info_model.ip}_{ip_info_model.port}_{ip_info_model.user}_{ip_info_model.password}"
                    ip_value = ip_info_model.model_dump_json()
                    ip_infos.append(ip_info_model)
                    self.ip_cache.set_ip(ip_key, ip_value, ex=ip_info_model.expired_time_ts - current_ts)
            else:
                raise IpGetError(res_dict.get("msg", "unkown err"))
        return ip_cache_list + ip_infos


IpProxy = JiSuHttpProxy(
    key=os.getenv("jisu_key", ""),  # 通过环境变量的方式获取极速HTTPIP提取key值
    crypto=os.getenv("jisu_crypto", ""),  # 通过环境变量的方式获取极速HTTPIP提取加密签名
    time_validity_period=30  # 30分钟（最长时效）
)

if __name__ == '__main__':
    # 每一次提取都要消耗 IP 数量，谨慎使用
    _ip_infos = asyncio.run(IpProxy.get_proxies(1))
    print(_ip_infos)
