# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 17:31
# @Desc    : 小红书存储到DB的模型类集合

from tortoise import fields
from tortoise.models import Model


class XhsBaseModel(Model):
    id = fields.IntField(pk=True, autoincrement=True, description="自增ID")
    user_id = fields.CharField(max_length=64, description="用户ID")
    nickname = fields.CharField(null=True, max_length=64, description="用户昵称")
    avatar = fields.CharField(null=True, max_length=255, description="用户头像地址")
    ip_location = fields.CharField(null=True, max_length=255, description="评论时的IP地址")
    add_ts = fields.BigIntField(description="记录添加时间戳")
    last_modify_ts = fields.BigIntField(description="记录最后修改时间戳")

    class Meta:
        abstract = True


class XHSNote(XhsBaseModel):
    note_id = fields.CharField(max_length=64, index=True, description="笔记ID")
    type = fields.CharField(null=True, max_length=16, description="笔记类型(normal | video)")
    title = fields.CharField(null=True, max_length=255, description="笔记标题")
    desc = fields.TextField(null=True, description="笔记描述")
    time = fields.BigIntField(description="笔记发布时间戳", index=True)
    last_update_time = fields.BigIntField(description="笔记最后更新时间戳")
    liked_count = fields.CharField(null=True, max_length=16, description="笔记点赞数")
    collected_count = fields.CharField(null=True, max_length=16, description="笔记收藏数")
    comment_count = fields.CharField(null=True, max_length=16, description="笔记评论数")
    share_count = fields.CharField(null=True, max_length=16, description="笔记分享数")
    image_list = fields.TextField(null=True, description="笔记封面图片列表")
    note_url = fields.CharField(null=True, max_length=255, description="笔记详情页的URL")

    class Meta:
        table = "xhs_note"
        table_description = "小红书笔记"

    def __str__(self):
        return f"{self.note_id} - {self.title}"


class XHSNoteComment(XhsBaseModel):
    comment_id = fields.CharField(max_length=64, index=True, description="评论ID")
    create_time = fields.BigIntField(index=True, description="评论时间戳")
    note_id = fields.CharField(max_length=64, description="笔记ID")
    content = fields.TextField(description="评论内容")
    sub_comment_count = fields.IntField(description="子评论数量")

    class Meta:
        table = "xhs_note_comment"
        table_description = "小红书笔记评论"

    def __str__(self):
        return f"{self.comment_id} - {self.content}"
