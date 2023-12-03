# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/3 16:16
# @Desc    : B 站的模型类
import csv
import pathlib
from typing import Dict, List

from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model

import config
from tools import utils
from var import crawler_type_var


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


async def update_bilibili_video(video_item: Dict):
    video_id = video_item.get("id")
    if video_item.get("type") != "video":
        return
    local_db_item = {
        "video_id": video_id,
        "video_type": str(video_item.get("type")),
        "title": video_item.get("title", "")[:500],
        "desc": video_item.get("description", "")[:500],
        "create_time": video_item.get("pubdate"),
        "user_id": video_item.get("mid"),
        "nickname": video_item.get("author"),
        "avatar": video_item.get("upic", ""),
        "liked_count": str(video_item.get("like", "")),
        "video_play_count": str(video_item.get("play", "")),
        "video_danmaku": str(video_item.get("danmaku", "")),
        "video_comment": str(video_item.get("review", "")),
        "last_modify_ts": utils.get_current_timestamp(),
        "video_url": f"https://www.bilibili.com/video/av{video_id}",
        "video_cover_url": video_item.get("pic", ""),
    }
    print(f"bilibili video id:{video_id}, title:{local_db_item.get('title')}")
    if config.IS_SAVED_DATABASED:
        if not await BilibiliVideo.filter(video_id=video_id).exists():
            local_db_item["add_ts"] = utils.get_current_timestamp()
            bilibili_video_pydantic = pydantic_model_creator(BilibiliVideo, name='BilibiliVideoCreate', exclude=('id',))
            bilibili_data = bilibili_video_pydantic(**local_db_item)
            bilibili_video_pydantic.model_validate(bilibili_data)
            await BilibiliVideo.create(**bilibili_data.model_dump())
        else:
            bilibili_video_pydantic = pydantic_model_creator(BilibiliVideo, name='BilibiliVideoUpdate',
                                                             exclude=('id', 'add_ts'))
            bilibili_data = bilibili_video_pydantic(**local_db_item)
            bilibili_video_pydantic.model_validate(bilibili_data)
            await BilibiliVideo.filter(video_id=video_id).update(**bilibili_data.model_dump())
    else:
        # Below is a simple way to save it in CSV format.
        pathlib.Path(f"data/bilibili").mkdir(parents=True, exist_ok=True)
        save_file_name = f"data/bilibili/{crawler_type_var.get()}_videos_{utils.get_current_date()}.csv"
        with open(save_file_name, mode='a+', encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(local_db_item.keys())
            writer.writerow(local_db_item.values())