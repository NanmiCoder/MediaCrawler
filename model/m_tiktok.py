# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/model/m_tiktok.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于 any 商业用途。
# 2. 使用时应遵守目标平台的使用条款 and robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于 any 非法 or 不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则 and LICENSE中的所有条款。

from dataclasses import dataclass, field
from typing import List, Optional
from pydantic import BaseModel, Field as PydanticField


class VideoUrlInfo(BaseModel):
    """TikTok video URL information"""
    video_id: str = PydanticField(title="video id")
    url_type: str = PydanticField(default="normal", title="url type: normal, short")


class CreatorUrlInfo(BaseModel):
    """TikTok creator URL information"""
    unique_id: str = PydanticField(title="unique_id (creator id)")


@dataclass
class TikTokVideo:
    video_id: str
    desc: str
    create_time: int
    author_id: str
    author_unique_id: str
    author_nickname: str
    video_play_url: str
    video_cover_url: str
    liked_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    play_count: int = 0
    collect_count: int = 0
    duration: int = 0
    hashtags: List[str] = field(default_factory=list)
    source_keyword: str = ""


@dataclass
class TikTokComment:
    comment_id: str
    video_id: str
    content: str
    user_id: str
    user_unique_id: str
    nickname: str
    create_time: int
    like_count: int = 0
    reply_count: int = 0
    parent_comment_id: Optional[str] = None


@dataclass
class TikTokCreator:
    user_id: str
    unique_id: str
    nickname: str
    bio: str
    avatar_url: str
    follower_count: int = 0
    following_count: int = 0
    video_count: int = 0
    heart_count: int = 0
    verified: bool = False
    region: str = ""
