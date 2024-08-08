from enum import Enum


class SearchSortType(Enum):
    """search sort type"""
    # 按时间倒序
    TIME_DESC = "1"
    # 按时间顺序
    TIME_ASC = "0"
    # 按相关性顺序
    RELEVANCE_ORDER = "2"


class SearchNoteType(Enum):
    # 只看主题贴
    MAIN_THREAD = "1"
    # 混合模式（帖子+回复）
    FIXED_THREAD = "0"
