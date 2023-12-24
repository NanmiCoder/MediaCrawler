# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/23 21:53
# @Desc    : 微博的模型类

import csv
import pathlib
from typing import Dict, List

from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model

import config
from tools import utils
from var import crawler_type_var


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
    create_date_time = fields.BigIntField(description="帖子发布日期时间", index=True)
    liked_count = fields.CharField(null=True, max_length=16, description="帖子点赞数")
    comments_count = fields.CharField(null=True, max_length=16, description="帖子评论数量")
    shared_count = fields.CharField(null=True, max_length=16, description="帖子转发数量")
    note_url = fields.CharField(null=True, max_length=512, description="帖子详情URL")

    class Meta:
        table = "weibo_video"
        table_description = "微博帖子"

    def __str__(self):
        return f"{self.note_id}"


class WeiboComment(WeiboBaseModel):
    comment_id = fields.CharField(max_length=64, index=True, description="评论ID")
    note_id = fields.CharField(max_length=64, index=True, description="帖子ID")
    content = fields.TextField(null=True, description="评论内容")
    create_time = fields.BigIntField(description="评论时间戳")
    create_date_time = fields.BigIntField(description="评论日期时间", index=True)
    comment_like_count = fields.CharField(max_length=16, description="评论点赞数量")
    sub_comment_count = fields.CharField(max_length=16, description="评论回复数")

    class Meta:
        table = "weibo_note_comment"
        table_description = "微博帖子评论"

    def __str__(self):
        return f"{self.comment_id}"


async def update_weibo_note(note_item: Dict):
    mblog: Dict = note_item.get("mblog")
    user_info: Dict = mblog.get("user")
    note_id = mblog.get("id")
    local_db_item = {
        # 微博信息
        "note_id": note_id,
        "content": mblog.get("text"),
        "create_time": utils.rfc2822_to_timestamp(mblog.get("created_at")),
        "create_date_time": utils.rfc2822_to_china_datetime(mblog.get("created_at")),
        "liked_count": mblog.get("attitudes_count", 0),
        "comments_count": mblog.get("comments_count", 0),
        "shared_count": mblog.get("reposts_count", 0),
        "last_modify_ts": utils.get_current_timestamp(),
        "note_url": f"https://m.weibo.cn/detail/{note_id}",
        "ip_location": mblog.get("region_name", "").replace("发布于 ", ""),

        # 用户信息
        "user_id": user_info.get("id"),
        "nickname": user_info.get("screen_name", ""),
        "gender": user_info.get("gender", ""),
        "profile_url": user_info.get("profile_url", ""),
        "avatar": user_info.get("profile_image_url", ""),
    }
    utils.logger.info(
        f"[models.weibo.update_weibo_video] weibo note id:{note_id}, title:{local_db_item.get('content')[:24]} ...")
    if config.IS_SAVED_DATABASED:
        if not await WeiboNote.filter(note_id=note_id).exists():
            local_db_item["add_ts"] = utils.get_current_timestamp()
            weibo_video_pydantic = pydantic_model_creator(WeiboNote, name='WeiboNoteCreate', exclude=('id',))
            weibo_data = weibo_video_pydantic(**local_db_item)
            weibo_video_pydantic.model_validate(weibo_data)
            await WeiboNote.create(**weibo_data.model_dump())
        else:
            weibo_video_pydantic = pydantic_model_creator(WeiboNote, name='WeiboNoteUpdate',
                                                          exclude=('id', 'add_ts'))
            weibo_data = weibo_video_pydantic(**local_db_item)
            weibo_video_pydantic.model_validate(weibo_data)
            await WeiboNote.filter(note_id=note_id).update(**weibo_data.model_dump())
    else:
        # Below is a simple way to save it in CSV format.
        pathlib.Path(f"data/weibo").mkdir(parents=True, exist_ok=True)
        save_file_name = f"data/weibo/{crawler_type_var.get()}_notes_{utils.get_current_date()}.csv"
        with open(save_file_name, mode='a+', encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(local_db_item.keys())
            writer.writerow(local_db_item.values())


async def batch_update_weibo_video_comments(video_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_weibo_video_comment(video_id, comment_item)


async def update_weibo_video_comment(note_id: str, comment_item: Dict):
    comment_id = str(comment_item.get("id"))
    content: Dict = comment_item.get("text")
    user_info: Dict = comment_item.get("member")
    local_db_item = {
        "comment_id": comment_id,
        "create_time": utils.rfc2822_to_timestamp(comment_item.get("created_at")),
        "create_date_time": utils.rfc2822_to_china_datetime(comment_item.get("created_at")),
        "note_id": note_id,
        "content": content.get("message"),
        "sub_comment_count": str(comment_item.get("total_number", 0)),
        "comment_like_count": str(comment_item.get("like_count", 0)),
        "last_modify_ts": utils.get_current_timestamp(),
        "ip_location": comment_item.get("source", "").replace("来自", ""),

        # 用户信息
        "user_id": user_info.get("id"),
        "nickname": user_info.get("screen_name", ""),
        "gender": user_info.get("gender", ""),
        "profile_url": user_info.get("profile_url", ""),
        "avatar": user_info.get("profile_image_url", ""),
    }
    utils.logger.info(
        f"[models.weibo.update_weibo_video_comment] Weibo note comment: {comment_id}, content: {local_db_item.get('content','')[:24]} ...")
    if config.IS_SAVED_DATABASED:
        if not await WeiboComment.filter(comment_id=comment_id).exists():
            local_db_item["add_ts"] = utils.get_current_timestamp()
            comment_pydantic = pydantic_model_creator(WeiboComment, name='WeiboNoteCommentCreate',
                                                      exclude=('id',))
            comment_data = comment_pydantic(**local_db_item)
            comment_pydantic.validate(comment_data)
            await WeiboComment.create(**comment_data.dict())
        else:
            comment_pydantic = pydantic_model_creator(WeiboComment, name='WeiboNoteCommentUpdate',
                                                      exclude=('id', 'add_ts'))
            comment_data = comment_pydantic(**local_db_item)
            comment_pydantic.validate(comment_data)
            await WeiboComment.filter(comment_id=comment_id).update(**comment_data.dict())
    else:
        pathlib.Path(f"data/weibo").mkdir(parents=True, exist_ok=True)
        save_file_name = f"data/weibo/{crawler_type_var.get()}_comments_{utils.get_current_date()}.csv"
        with open(save_file_name, mode='a+', encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(local_db_item.keys())
            writer.writerow(local_db_item.values())
