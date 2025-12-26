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
# @Desc    : Basic types
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
    port: int = Field(title="port")
    user: str = Field(title="Username for IP proxy authentication")
    protocol: str = Field(default="https://", title="Protocol for proxy IP")
    password: str = Field(title="Password for IP proxy authentication user")
    expired_time_ts: Optional[int] = Field(default=None, title="IP expiration time")

    def is_expired(self, buffer_seconds: int = 30) -> bool:
        """
        Check if proxy IP has expired
        Args:
            buffer_seconds: Buffer time (seconds), how many seconds ahead to consider expired to avoid critical time request failures
        Returns:
            bool: True means expired or about to expire, False means still valid
        """
        if self.expired_time_ts is None:
            return False
        current_ts = int(time.time())
        return current_ts >= (self.expired_time_ts - buffer_seconds)
