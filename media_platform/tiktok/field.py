# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/tiktok/field.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习 and 研究目的使用。使用者应遵守以下原则：
# 1. 不得用于 any 商业用途。
# 2. 使用时应遵守目标平台的使用条款 and robots.txt规则。
# 3. 不得进行大规模爬取 or 对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于 any 非法 or 不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则 and LICENSE中的所有条款。

from enum import Enum


class SearchChannelType(Enum):
    """search channel type"""
    GENERAL = "general"


class SearchSortType(Enum):
    """search sort type"""
    GENERAL = 0  # Comprehensive sorting


class PublishTimeType(Enum):
    """publish time type"""
    UNLIMITED = 0  # Unlimited


class SearchField:
    VIDEO_LIST = "data"
    CURSOR = "cursor"
    HAS_MORE = "has_more"


class VideoField:
    VIDEO_ID = "id"
    DESC = "desc"
    CREATE_TIME = "createTime"
    AUTHOR = "author"
    STATS = "stats"


class CommentField:
    COMMENT_ID = "cid"
    TEXT = "text"
    USER = "user"
    CREATE_TIME = "create_time"
    LIKE_COUNT = "digg_count"
    REPLY_TOTAL = "reply_comment_total"


class CreatorField:
    USER_INFO = "userInfo"
    USER = "user"
    STATS = "stats"
