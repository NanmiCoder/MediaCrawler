# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/douyin/field.py
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


from enum import Enum


class SearchChannelType(Enum):
    """search channel type"""
    GENERAL = "aweme_general"  # General
    VIDEO = "aweme_video_web"  # Video
    USER = "aweme_user_web"  # User
    LIVE = "aweme_live"  # Live


class SearchSortType(Enum):
    """search sort type"""
    GENERAL = 0  # Comprehensive sorting
    MOST_LIKE = 1  # Most likes
    LATEST = 2  # Latest published

class PublishTimeType(Enum):
    """publish time type"""
    UNLIMITED = 0  # Unlimited
    ONE_DAY = 1  # Within one day
    ONE_WEEK = 7  # Within one week
    SIX_MONTH = 180  # Within six months


# 通用 SortTypeEnum -> douyin SearchSortType 映射
GENERAL_SORT_TO_DY_SORT: dict = {
    "general": SearchSortType.GENERAL,
    "popularity_descending": SearchSortType.MOST_LIKE,
    "time_descending": SearchSortType.LATEST,
}

# 通用 PublishTimeTypeEnum -> douyin PublishTimeType 映射
# 注意：抖音原生未提供"一月内"，缺失项会在调用处回退为 UNLIMITED
GENERAL_PUBLISH_TIME_TO_DY: dict = {
    "不限": PublishTimeType.UNLIMITED,
    "一天内": PublishTimeType.ONE_DAY,
    "一周内": PublishTimeType.ONE_WEEK,
}

