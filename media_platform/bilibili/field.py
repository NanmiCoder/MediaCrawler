# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/3 16:20
# @Desc    :

from enum import Enum


class OrderType(Enum):
    # 综合排序
    DEFAULT = ""

    # 最多点击
    MOST_CLICK = "click"

    # 最新发布
    LAST_PUBLISH = "pubdate"

    # 最多弹幕
    MOST_DANMU = "dm"

    # 最多收藏
    MOST_MARK = "stow"
