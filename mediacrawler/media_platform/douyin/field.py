from enum import Enum


class SearchChannelType(Enum):
    """search channel type"""
    GENERAL = "aweme_general"  # 综合
    VIDEO = "aweme_video_web"  # 视频
    USER = "aweme_user_web"  # 用户
    LIVE = "aweme_live"  # 直播


class SearchSortType(Enum):
    """search sort type"""
    GENERAL = 0  # 综合排序
    LATEST = 1  # 最新发布
    MOST_LIKE = 2  # 最多点赞


class PublishTimeType(Enum):
    """publish time type"""
    UNLIMITED = 0  # 不限
    ONE_DAY = 1  # 一天内
    ONE_WEEK = 2  # 一周内
    SIX_MONTH = 3  # 半年内
