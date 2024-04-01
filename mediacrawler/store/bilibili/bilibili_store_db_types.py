# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 19:34
# @Desc    : B站存储到DB的模型类集合

from tortoise import fields
from tortoise.models import Model


class BilibiliBaseModel(Model):
    id = fields.IntField(pk=True, autoincrement=True, description="自增ID")
    user_id = fields.CharField(null=True, max_length=64, description="用户ID")
    nickname = fields.CharField(null=True, max_length=64, description="用户昵称")
    avatar = fields.CharField(null=True, max_length=255, description="用户头像地址")
    add_ts = fields.BigIntField(description="记录添加时间戳")
    last_modify_ts = fields.BigIntField(description="记录最后修改时间戳")

    class Meta:
        abstract = True


class BilibiliVideo(BilibiliBaseModel):
    video_id = fields.CharField(max_length=64, index=True, description="视频ID")
    video_type = fields.CharField(max_length=16, description="视频类型")
    title = fields.CharField(null=True, max_length=500, description="视频标题")
    desc = fields.TextField(null=True, description="视频描述")
    create_time = fields.BigIntField(description="视频发布时间戳", index=True)
    liked_count = fields.CharField(null=True, max_length=16, description="视频点赞数")
    video_play_count = fields.CharField(null=True, max_length=16, description="视频播放数量")
    video_danmaku = fields.CharField(null=True, max_length=16, description="视频弹幕数量")
    video_comment = fields.CharField(null=True, max_length=16, description="视频评论数量")
    video_url = fields.CharField(null=True, max_length=512, description="视频详情URL")
    video_cover_url = fields.CharField(null=True, max_length=512, description="视频封面图 URL")

    class Meta:
        table = "bilibili_video"
        table_description = "B站视频"

    def __str__(self):
        return f"{self.video_id} - {self.title}"


class BilibiliComment(BilibiliBaseModel):
    comment_id = fields.CharField(max_length=64, index=True, description="评论ID")
    video_id = fields.CharField(max_length=64, index=True, description="视频ID")
    content = fields.TextField(null=True, description="评论内容")
    create_time = fields.BigIntField(description="评论时间戳")
    sub_comment_count = fields.CharField(max_length=16, description="评论回复数")

    class Meta:
        table = "bilibili_video_comment"
        table_description = "B 站视频评论"

    def __str__(self):
        return f"{self.comment_id} - {self.content}"
