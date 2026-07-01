"""
douyin_scraper.models — 数据模型
=================================
v5 新增：使用 dataclass 定义数据结构，替代 v4 中的原始字典。
我实际执行时：字典字段名拼写错误（content vs text）导致评论丢失，
数据模型可以提前发现这类错误。
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Video:
    """视频元数据"""
    aweme_id: str
    title: str = ""
    author: str = ""
    video_download_url: str = ""
    liked_count: int = 0
    collected_count: int = 0
    share_count: int = 0
    comment_count: int = 0
    create_time: str = ""
    desc: str = ""

    def to_dict(self) -> dict:
        return {
            "aweme_id": self.aweme_id,
            "title": self.title,
            "author": self.author,
            "video_download_url": self.video_download_url,
            "liked_count": self.liked_count,
            "collected_count": self.collected_count,
            "share_count": self.share_count,
            "comment_count": self.comment_count,
            "create_time": self.create_time,
            "desc": self.desc,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Video":
        return cls(
            aweme_id=str(data.get("aweme_id", "")),
            title=str(data.get("title", "")),
            author=str(data.get("author", data.get("nickname", ""))),
            video_download_url=str(data.get("video_download_url", "")),
            liked_count=int(data.get("liked_count", 0) or 0),
            collected_count=int(data.get("collected_count", 0) or 0),
            share_count=int(data.get("share_count", 0) or 0),
            comment_count=int(data.get("comment_count", 0) or 0),
            create_time=str(data.get("create_time", "")),
            desc=str(data.get("desc", "")),
        )


@dataclass
class Comment:
    """
    评论数据。
    我实际执行时：评论字段名有时是 content 有时是 text，
    from_dict 兼容两种。
    """
    aweme_id: str = ""
    content: str = ""
    comment_id: str = ""
    nickname: str = ""
    create_time: str = ""

    def to_dict(self) -> dict:
        return {
            "aweme_id": self.aweme_id,
            "content": self.content,
            "comment_id": self.comment_id,
            "nickname": self.nickname,
            "create_time": self.create_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Comment":
        # ★ 兼容两种字段名 ★ 我实际执行时踩的坑
        text = data.get("content") or data.get("text") or ""
        return cls(
            aweme_id=str(data.get("aweme_id", "")),
            content=str(text),
            comment_id=str(data.get("comment_id", data.get("cid", ""))),
            nickname=str(data.get("nickname", "")),
            create_time=str(data.get("create_time", "")),
        )


@dataclass
class Script:
    """文案提取结果"""
    aweme_id: str
    script_text: str = ""
    script_status: str = ""  # success / download_failed / asr_failed
    model_name: str = ""

    def to_dict(self) -> dict:
        return {
            "aweme_id": self.aweme_id,
            "script_text": self.script_text,
            "script_status": self.script_status,
            "model_name": self.model_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Script":
        return cls(
            aweme_id=str(data.get("aweme_id", "")),
            script_text=str(data.get("script_text", "")),
            script_status=str(data.get("script_status", "")),
            model_name=str(data.get("model_name", "")),
        )
