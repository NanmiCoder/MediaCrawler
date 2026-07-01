# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/model/m_zhihu.py
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


# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class ZhihuContent(BaseModel):
    """
    Zhihu content (answer, article, video)
    """
    content_id: str = Field(default="", description="Content ID")
    content_type: str = Field(default="", description="Content type (article | answer | zvideo)")
    content_text: str = Field(default="", description="Content text, empty for video type")
    content_url: str = Field(default="", description="Content landing page URL")
    question_id: str = Field(default="", description="Question ID, has value when type is answer")
    title: str = Field(default="", description="Content title")
    desc: str = Field(default="", description="Content description")
    created_time: int = Field(default=0, description="Create time")
    updated_time: int = Field(default=0, description="Update time")
    voteup_count: int = Field(default=0, description="Upvote count")
    comment_count: int = Field(default=0, description="Comment count")
    source_keyword: str = Field(default="", description="Source keyword")
    creator_hash: str = Field(default="", description="Creator anonymized hash")
    user_nickname: str = Field(default="", description="User nickname (masked)")


class ZhihuComment(BaseModel):
    """
    Zhihu comment
    """

    comment_id: str = Field(default="", description="Comment ID")
    parent_comment_id: str = Field(default="", description="Parent comment ID")
    content: str = Field(default="", description="Comment content")
    publish_time: int = Field(default=0, description="Publish time")
    sub_comment_count: int = Field(default=0, description="Sub-comment count")
    like_count: int = Field(default=0, description="Like count")
    dislike_count: int = Field(default=0, description="Dislike count")
    content_id: str = Field(default="", description="Content ID")
    content_type: str = Field(default="", description="Content type (article | answer | zvideo)")
    creator_hash: str = Field(default="", description="Creator anonymized hash")
    user_nickname: str = Field(default="", description="User nickname (masked)")


class ZhihuCreator(BaseModel):
    """
    Zhihu creator (in-memory only; personal profile is no longer persisted)
    """
    creator_hash: str = Field(default="", description="Creator anonymized hash")
    user_nickname: str = Field(default="", description="User nickname (masked)")
    follows: int = Field(default=0, description="Follows count")
    fans: int = Field(default=0, description="Fans count")
    anwser_count: int = Field(default=0, description="Answer count")
    video_count: int = Field(default=0, description="Video count")
    question_count: int = Field(default=0, description="Question count")
    article_count: int = Field(default=0, description="Article count")
    column_count: int = Field(default=0, description="Column count")
    get_voteup_count: int = Field(default=0, description="Total upvotes received")
