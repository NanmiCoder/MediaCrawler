from enum import Enum
from typing import NamedTuple


class FeedType(Enum):
    # 推荐
    RECOMMEND = "homefeed_recommend"
    # 穿搭
    FASION = "homefeed.fashion_v3"
    # 美食
    FOOD = "homefeed.food_v3"
    # 彩妆
    COSMETICS = "homefeed.cosmetics_v3"
    # 影视
    MOVIE = "homefeed.movie_and_tv_v3"
    # 职场
    CAREER = "homefeed.career_v3"
    # 情感
    EMOTION = "homefeed.love_v3"
    # 家居
    HOURSE = "homefeed.household_product_v3"
    # 游戏
    GAME = "homefeed.gaming_v3"
    # 旅行
    TRAVEL = "homefeed.travel_v3"
    # 健身
    FITNESS = "homefeed.fitness_v3"


class NoteType(Enum):
    NORMAL = "normal"
    VIDEO = "video"


class SearchSortType(Enum):
    """search sort type"""
    # 搜索排序类型

    # default
    # 默认
    GENERAL = "general"
    # most popular
    # 最受欢迎
    MOST_POPULAR = "popularity_descending"
    # Latest
    # 最新
    LATEST = "time_descending"


class SearchNoteType(Enum):
    """search note type"""
    # 搜索笔记类型

    # default
    # 默认
    ALL = 0
    # only video
    # 只有视频
    VIDEO = 1
    # only image
    # 只有图片
    IMAGE = 2


class Note(NamedTuple):
    """note tuple"""
    # 注意元组
    note_id: str
    title: str
    desc: str
    type: str
    user: dict
    img_urls: list
    video_url: str
    tag_list: list
    at_user_list: list
    collected_count: str
    comment_count: str
    liked_count: str
    share_count: str
    time: int
    last_update_time: int
