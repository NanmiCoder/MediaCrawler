# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 18:50
# @Desc    : 抖音存储到DB的模型类集合


from tortoise import fields
from tortoise.models import Model


class DouyinBaseModel(Model):
    id = fields.IntField(pk=True, autoincrement=True, description="自增ID")
    user_id = fields.CharField(null=True, max_length=64, description="用户ID")
    sec_uid = fields.CharField(null=True, max_length=128, description="用户sec_uid")
    short_user_id = fields.CharField(null=True, max_length=64, description="用户短ID")
    user_unique_id = fields.CharField(null=True, max_length=64, description="用户唯一ID")
    nickname = fields.CharField(null=True, max_length=64, description="用户昵称")
    avatar = fields.CharField(null=True, max_length=255, description="用户头像地址")
    user_signature = fields.CharField(null=True, max_length=500, description="用户签名")
    ip_location = fields.CharField(null=True, max_length=255, description="评论时的IP地址")
    add_ts = fields.BigIntField(description="记录添加时间戳")
    last_modify_ts = fields.BigIntField(description="记录最后修改时间戳")

    class Meta:
        abstract = True


class DouyinAweme(DouyinBaseModel):
    aweme_id = fields.CharField(max_length=64, index=True, description="视频ID")
    aweme_type = fields.CharField(max_length=16, description="视频类型")
    title = fields.CharField(null=True, max_length=500, description="视频标题")
    desc = fields.TextField(null=True, description="视频描述")
    create_time = fields.BigIntField(description="视频发布时间戳", index=True)
    liked_count = fields.CharField(null=True, max_length=16, description="视频点赞数")
    comment_count = fields.CharField(null=True, max_length=16, description="视频评论数")
    share_count = fields.CharField(null=True, max_length=16, description="视频分享数")
    collected_count = fields.CharField(null=True, max_length=16, description="视频收藏数")
    aweme_url = fields.CharField(null=True, max_length=255, description="视频详情页URL")

    class Meta:
        table = "douyin_aweme"
        table_description = "抖音视频"

    def __str__(self):
        return f"{self.aweme_id} - {self.title}"


class DouyinAwemeComment(DouyinBaseModel):
    comment_id = fields.CharField(max_length=64, index=True, description="评论ID")
    aweme_id = fields.CharField(max_length=64, index=True, description="视频ID")
    content = fields.TextField(null=True, description="评论内容")
    create_time = fields.BigIntField(description="评论时间戳")
    sub_comment_count = fields.CharField(max_length=16, description="评论回复数")

    class Meta:
        table = "douyin_aweme_comment"
        table_description = "抖音视频评论"

    def __str__(self):
        return f"{self.comment_id} - {self.content}"
