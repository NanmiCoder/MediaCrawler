# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/xhs/field.py
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


class FeedType(Enum):
    # Recommend
    RECOMMEND = "homefeed_recommend"
    # Fashion
    FASION = "homefeed.fashion_v3"
    # Food
    FOOD = "homefeed.food_v3"
    # Cosmetics
    COSMETICS = "homefeed.cosmetics_v3"
    # Movie and TV
    MOVIE = "homefeed.movie_and_tv_v3"
    # Career
    CAREER = "homefeed.career_v3"
    # Emotion
    EMOTION = "homefeed.love_v3"
    # Home
    HOURSE = "homefeed.household_product_v3"
    # Gaming
    GAME = "homefeed.gaming_v3"
    # Travel
    TRAVEL = "homefeed.travel_v3"
    # Fitness
    FITNESS = "homefeed.fitness_v3"


class NoteType(Enum):
    NORMAL = "normal"
    VIDEO = "video"


class SearchSortType(Enum):
    """Search sort type"""
    # Default
    GENERAL = "general"
    # Most popular
    MOST_POPULAR = "popularity_descending"
    # Latest
    LATEST = "time_descending"


class SearchNoteType(Enum):
    """Search note type"""
    # Default
    ALL = 0
    # Only video
    VIDEO = 1
    # Only image
    IMAGE = 2


class Note(NamedTuple):
    """Note tuple"""
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
