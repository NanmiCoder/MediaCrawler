from enum import Enum
from typing import NamedTuple

from constant import zhihu as zhihu_constant


class SearchTime(Enum):
    """
    搜索时间范围
    """
    DEFAULT = ""  # 不限时间
    ONE_DAY = "a_day"  # 一天内
    ONE_WEEK = "a_week"  # 一周内
    ONE_MONTH = "a_month"  # 一个月内
    THREE_MONTH = "three_months"  # 三个月内
    HALF_YEAR = "half_a_year"  # 半年内
    ONE_YEAR = "a_year"  # 一年内


class SearchType(Enum):
    """
    搜索结果类型
    """
    DEFAULT = ""  # 不限类型
    ANSWER = zhihu_constant.ANSWER_NAME  # 只看回答
    ARTICLE = zhihu_constant.ARTICLE_NAME  # 只看文章
    VIDEO = zhihu_constant.VIDEO_NAME  # 只看视频


class SearchSort(Enum):
    """
    搜索结果排序
    """
    DEFAULT = ""  # 综合排序
    UPVOTED_COUNT = "upvoted_count"  # 最多赞同
    CREATE_TIME = "created_time"  # 最新发布
