# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/23 15:41
# @Desc    :
from enum import Enum


class SearchType(Enum):
    # 综合
    DEFAULT = "1"

    # 实时
    REAL_TIME = "61"

    # 热门
    POPULAR = "60"

    # 视频
    VIDEO = "64"
