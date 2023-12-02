# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 11:18
# @Desc    : 爬虫 IP 获取实现
# @Url     : 现在实现了极速HTTP的接口，官网地址：https://www.jisuhttp.com/?pl=mAKphQ&plan=ZY&kd=Yang

import asyncio
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field

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


class JiSuHttpProxy(ProxyProvider):
    def __init__(self, exract_type: str, key: str, crypto: str, res_type: str, protocol: int, time: int):
        """
        极速HTTP 代理IP实现
        官网地址：https://www.jisuhttp.com/?pl=mAKphQ&plan=ZY&kd=Yang
        :param exract_type: 提取方式
        :param key: 提取key值 (到上面链接的官网去注册后获取)
        :param crypto: 加密签名 (到上面链接的官网去注册后获取)
        :param res_type: 返回的数据格式：TXT、JSON
        :param protocol: IP协议：1:HTTP、2:HTTPS、3:SOCKS5
        :param time: IP使用时长，支持3、5、10、15、30分钟时效
        """
        self.exract_type = exract_type
        self.api_path = "https://api.jisuhttp.com"
        self.params = {
            "key": key,
            "crypto": crypto,
            "type": res_type,
            "port": protocol,
            "time": time,
            "pw": "1",  # 是否使用账密验证， 1：是，0：否，否表示白名单验证；默认为0
            "se": "1",  # 返回JSON格式时是否显示IP过期时间， 1：显示，0：不显示；默认为0
        }

    async def get_proxies(self, num: int) -> List[IpInfoModel]:
        """
        :param num:
        :return:
        """
        if self.exract_type == "API":
            uri = "/fetchips"
            self.params.update({"num": num})
            ip_infos = []
            async with httpx.AsyncClient() as client:
                url = self.api_path + uri + '?' + urlencode(self.params)
                utils.logger.info(f"[JiSuHttpProxy] get ip proxy url:{url}")
                response = await client.get(url, headers={"User-Agent": "MediaCrawler"})
                res_dict: Dict = response.json()
                if res_dict.get("code") == 0:
                    data: List[Dict] = res_dict.get("data")
                    for ip_item in data:
                        ip_info_model = IpInfoModel(
                            ip=ip_item.get("ip"),
                            port=ip_item.get("port"),
                            user=ip_item.get("user"),
                            password=ip_item.get("pass"),
                            expired_time_ts=utils.get_unix_time_from_time_str(ip_item.get("expire"))
                        )
                        ip_infos.append(ip_info_model)
                else:
                    raise IpGetError(res_dict.get("msg", "unkown err"))
            return ip_infos
        else:
            pass



IpProxy = JiSuHttpProxy(
    key=os.getenv("jisu_key", ""),  # 通过环境变量的方式获取极速HTTPIP提取key值
    crypto=os.getenv("jisu_crypto", ""),  # 通过环境变量的方式获取极速HTTPIP提取加密签名
    res_type="json",
    protocol=2,
    time=30
)

if __name__ == '__main__':
    _ip_infos = asyncio.run(IpProxy.get_proxies(1))
    print(_ip_infos)
