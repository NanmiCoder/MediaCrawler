# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 21:35
# @Desc    : 微博存储到DB的模型类集合

from tortoise import fields
from tortoise.models import Model


class WeiboBaseModel(Model):
    id = fields.IntField(pk=True, autoincrement=True, description="自增ID")
    user_id = fields.CharField(null=True, max_length=64, description="用户ID")
    nickname = fields.CharField(null=True, max_length=64, description="用户昵称")
    avatar = fields.CharField(null=True, max_length=255, description="用户头像地址")
    gender = fields.CharField(null=True, max_length=12, description="用户性别")
    profile_url = fields.CharField(null=True, max_length=255, description="用户主页地址")
    ip_location = fields.CharField(null=True, max_length=32, default="发布微博的地理信息")
    add_ts = fields.BigIntField(description="记录添加时间戳")
    last_modify_ts = fields.BigIntField(description="记录最后修改时间戳")

    class Meta:
        abstract = True


class WeiboNote(WeiboBaseModel):
    note_id = fields.CharField(max_length=64, index=True, description="帖子ID")
    content = fields.TextField(null=True, description="帖子正文内容")
    create_time = fields.BigIntField(description="帖子发布时间戳", index=True)
    create_date_time = fields.CharField(description="帖子发布日期时间", max_length=32, index=True)
    liked_count = fields.CharField(null=True, max_length=16, description="帖子点赞数")
    comments_count = fields.CharField(null=True, max_length=16, description="帖子评论数量")
    shared_count = fields.CharField(null=True, max_length=16, description="帖子转发数量")
    note_url = fields.CharField(null=True, max_length=512, description="帖子详情URL")

    class Meta:
        table = "weibo_note"
        table_description = "微博帖子"

    def __str__(self):
        return f"{self.note_id}"


class WeiboComment(WeiboBaseModel):
    comment_id = fields.CharField(max_length=64, index=True, description="评论ID")
    note_id = fields.CharField(max_length=64, index=True, description="帖子ID")
    content = fields.TextField(null=True, description="评论内容")
    create_time = fields.BigIntField(description="评论时间戳")
    create_date_time = fields.CharField(description="评论日期时间", max_length=32, index=True)
    comment_like_count = fields.CharField(max_length=16, description="评论点赞数量")
    sub_comment_count = fields.CharField(max_length=16, description="评论回复数")

    class Meta:
        table = "weibo_note_comment"
        table_description = "微博帖子评论"

    def __str__(self):
        return f"{self.comment_id}"
