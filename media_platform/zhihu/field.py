# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/zhihu/field.py
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
from typing import NamedTuple

from constant import zhihu as zhihu_constant


class SearchTime(Enum):
    """
    Search time range
    """
    DEFAULT = ""  # No time limit
    ONE_DAY = "a_day"  # Within one day
    ONE_WEEK = "a_week"  # Within one week
    ONE_MONTH = "a_month"  # Within one month
    THREE_MONTH = "three_months"  # Within three months
    HALF_YEAR = "half_a_year"  # Within half a year
    ONE_YEAR = "a_year"  # Within one year


class SearchType(Enum):
    """
    Search result type
    """
    DEFAULT = ""  # No type limit
    ANSWER = zhihu_constant.ANSWER_NAME  # Answers only
    ARTICLE = zhihu_constant.ARTICLE_NAME  # Articles only
    VIDEO = zhihu_constant.VIDEO_NAME  # Videos only


class SearchSort(Enum):
    """
    Search result sorting
    """
    DEFAULT = ""  # Default sorting
    UPVOTED_COUNT = "upvoted_count"  # Most upvoted
    CREATE_TIME = "created_time"  # Latest published
