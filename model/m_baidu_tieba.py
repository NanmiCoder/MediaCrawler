# -*- coding: utf-8 -*-
from typing import Optional

from pydantic import BaseModel, Field


class TiebaNote(BaseModel):
    """
    百度贴吧帖子
    """
    note_id: str = Field(..., description="帖子ID")
    title: str = Field(..., description="帖子标题")
    desc: str = Field(default="", description="帖子描述")
    note_url: str = Field(..., description="帖子链接")
    publish_time: str = Field(default="", description="发布时间")
    user_link: str = Field(default="", description="用户主页链接")
    user_nickname: str = Field(default="", description="用户昵称")
    user_avatar: str = Field(default="", description="用户头像地址")
    tieba_name: str = Field(..., description="贴吧名称")
    tieba_link: str = Field(..., description="贴吧链接")
    total_replay_num: int = Field(default=0, description="回复总数")
    total_replay_page: int = Field(default=0, description="回复总页数")
    ip_location: Optional[str] = Field(default="", description="IP地理位置")


class TiebaComment(BaseModel):
    """
    百度贴吧评论
    """

    comment_id: str = Field(..., description="评论ID")
    parent_comment_id: str = Field(default="", description="父评论ID")
    content: str = Field(..., description="评论内容")
    user_link: str = Field(default="", description="用户主页链接")
    user_nickname: str = Field(default="", description="用户昵称")
    user_avatar: str = Field(default="", description="用户头像地址")
    publish_time: str = Field(default="", description="发布时间")
    ip_location: Optional[str] = Field(default="", description="IP地理位置")
    sub_comment_count: int = Field(default=0, description="子评论数")
    note_id: str = Field(..., description="帖子ID")
    note_url: str = Field(..., description="帖子链接")
    tieba_id: str = Field(..., description="所属的贴吧ID")
    tieba_name: str = Field(..., description="所属的贴吧名称")
    tieba_link: str = Field(..., description="贴吧链接")

