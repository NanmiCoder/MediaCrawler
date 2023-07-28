import json
from typing import Dict, List

from tortoise.models import Model
from tortoise import fields

import config
from tools import utils


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


async def update_douyin_aweme(aweme_item: Dict):
    aweme_id = aweme_item.get("aweme_id")
    user_info = aweme_item.get("author", {})
    interact_info = aweme_item.get("statistics", {})
    local_db_item = {
        "aweme_id": aweme_id,
        "aweme_type": aweme_item.get("aweme_type"),
        "title": aweme_item.get("desc", ""),
        "desc": aweme_item.get("desc", ""),
        "create_time": aweme_item.get("create_time"),
        "user_id": user_info.get("uid"),
        "sec_uid": user_info.get("sec_uid"),
        "short_user_id": user_info.get("short_id"),
        "user_unique_id": user_info.get("unique_id"),
        "user_signature": user_info.get("signature"),
        "nickname": user_info.get("nickname"),
        "avatar": user_info.get("avatar_thumb", {}).get("url_list", [""])[0],
        "liked_count": interact_info.get("digg_count"),
        "collected_count": interact_info.get("collect_count"),
        "comment_count": interact_info.get("comment_count"),
        "share_count": interact_info.get("share_count"),
        "ip_location": aweme_item.get("ip_label", ""),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    print(f"douyin aweme id:{aweme_id}, title:{local_db_item.get('title')}")
    if config.IS_SAVED_DATABASED:
        if not await DouyinAweme.filter(aweme_id=aweme_id).exists():
            local_db_item["add_ts"] = utils.get_current_timestamp()
            await DouyinAweme.create(**local_db_item)
        else:
            await DouyinAweme.filter(aweme_id=aweme_id).update(**local_db_item)


async def batch_update_dy_aweme_comments(aweme_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_dy_aweme_comment(aweme_id, comment_item)


async def update_dy_aweme_comment(aweme_id: str, comment_item: Dict):
    comment_aweme_id = comment_item.get("aweme_id")
    if aweme_id != comment_aweme_id:
        print(f"comment_aweme_id: {comment_aweme_id} != aweme_id: {aweme_id}")
        return
    user_info = comment_item.get("user", {})
    comment_id = comment_item.get("cid")
    avatar_info = user_info.get("avatar_medium", {}) or user_info.get("avatar_300x300", {}) or user_info.get(
        "avatar_168x168", {}) or user_info.get("avatar_thumb", {}) or {}
    local_db_item = {
        "comment_id": comment_id,
        "create_time": comment_item.get("create_time"),
        "ip_location": comment_item.get("ip_label", ""),
        "aweme_id": aweme_id,
        "content": comment_item.get("text"),
        "content_extra": json.dumps(comment_item.get("text_extra", [])),
        "user_id": user_info.get("uid"),
        "sec_uid": user_info.get("sec_uid"),
        "short_user_id": user_info.get("short_id"),
        "user_unique_id": user_info.get("unique_id"),
        "user_signature": user_info.get("signature"),
        "nickname": user_info.get("nickname"),
        "avatar": avatar_info.get("url_list", [""])[0],
        "sub_comment_count": comment_item.get("reply_comment_total", 0),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    print(f"douyin aweme comment: {comment_id}, content: {local_db_item.get('content')}")
    if config.IS_SAVED_DATABASED:
        if not await DouyinAwemeComment.filter(comment_id=comment_id).exists():
            local_db_item["add_ts"] = utils.get_current_timestamp()
            await DouyinAwemeComment.create(**local_db_item)
        else:
            await DouyinAwemeComment.filter(comment_id=comment_id).update(**local_db_item)
