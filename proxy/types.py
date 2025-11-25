# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/proxy/types.py
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
# @Time    : 2024/4/5 10:18
# @Desc    : 基础类型
import time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProviderNameEnum(Enum):
    KUAI_DAILI_PROVIDER: str = "kuaidaili"
    WANDOU_HTTP_PROVIDER: str = "wandouhttp"


class IpInfoModel(BaseModel):
    """Unified IP model"""

    ip: str = Field(title="ip")
    port: int = Field(title="端口")
    user: str = Field(title="IP代理认证的用户名")
    protocol: str = Field(default="https://", title="代理IP的协议")
    password: str = Field(title="IP代理认证用户的密码")
    expired_time_ts: Optional[int] = Field(default=None, title="IP 过期时间")

    def is_expired(self, buffer_seconds: int = 30) -> bool:
        """
        检测代理IP是否已过期
        Args:
            buffer_seconds: 缓冲时间（秒），提前多少秒认为已过期，避免临界时间请求失败
        Returns:
            bool: True表示已过期或即将过期，False表示仍然有效
        """
        if self.expired_time_ts is None:
            return False
        current_ts = int(time.time())
        return current_ts >= (self.expired_time_ts - buffer_seconds)
