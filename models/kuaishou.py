import csv
import pathlib
from typing import Dict, List

from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model

import config
from tools import utils
from var import crawler_type_var


class KuaishouBaseModel(Model):
    id = fields.IntField(pk=True, autoincrement=True, description="自增ID")
    user_id = fields.CharField(null=True, max_length=64, description="用户ID")
    nickname = fields.CharField(null=True, max_length=64, description="用户昵称")
    avatar = fields.CharField(null=True, max_length=255, description="用户头像地址")
    add_ts = fields.BigIntField(description="记录添加时间戳")
    last_modify_ts = fields.BigIntField(description="记录最后修改时间戳")

    class Meta:
        abstract = True


class KuaishouVideo(KuaishouBaseModel):
    video_id = fields.CharField(max_length=64, index=True, description="视频ID")
    video_type = fields.CharField(max_length=16, description="视频类型")
    title = fields.CharField(null=True, max_length=500, description="视频标题")
    desc = fields.TextField(null=True, description="视频描述")
    create_time = fields.BigIntField(description="视频发布时间戳", index=True)
    liked_count = fields.CharField(null=True, max_length=16, description="视频点赞数")
    viewd_count = fields.CharField(null=True, max_length=16, description="视频浏览数量")
    video_url = fields.CharField(null=True, max_length=512, description="视频详情URL")
    video_cover_url = fields.CharField(null=True, max_length=512, description="视频封面图 URL")
    video_play_url = fields.CharField(null=True, max_length=512, description="视频播放 URL")

    class Meta:
        table = "kuaishou_video"
        table_description = "快手视频"

    def __str__(self):
        return f"{self.video_id} - {self.title}"


class KuaishouVideoComment(KuaishouBaseModel):
    comment_id = fields.CharField(max_length=64, index=True, description="评论ID")
    video_id = fields.CharField(max_length=64, index=True, description="视频ID")
    content = fields.TextField(null=True, description="评论内容")
    create_time = fields.BigIntField(description="评论时间戳")
    sub_comment_count = fields.CharField(max_length=16, description="评论回复数")

    class Meta:
        table = "kuaishou_video_comment"
        table_description = "快手视频评论"

    def __str__(self):
        return f"{self.comment_id} - {self.content}"


async def update_kuaishou_video(video_item: Dict):
    photo_info: Dict = video_item.get("photo", {})
    video_id = photo_info.get("id")
    if not video_id:
        return
    user_info = video_item.get("author", {})
    local_db_item = {
        "video_id": video_id,
        "video_type": str(video_item.get("type")),
        "title": photo_info.get("caption", "")[:500],
        "desc": photo_info.get("caption", "")[:500],
        "create_time": photo_info.get("timestamp"),
        "user_id": user_info.get("id"),
        "nickname": user_info.get("name"),
        "avatar": user_info.get("headerUrl", ""),
        "liked_count": str(photo_info.get("realLikeCount")),
        "viewd_count": str(photo_info.get("viewCount")),
        "last_modify_ts": utils.get_current_timestamp(),
        "video_url": f"https://www.kuaishou.com/short-video/{video_id}",
        "video_cover_url": photo_info.get("coverUrl", ""),
        "video_play_url": photo_info.get("photoUrl", ""),
    }
    print(f"Kuaishou video id:{video_id}, title:{local_db_item.get('title')}")
    if config.IS_SAVED_DATABASED:
        if not await KuaishouVideo.filter(video_id=video_id).exists():
            local_db_item["add_ts"] = utils.get_current_timestamp()
            kuaishou_video_pydantic = pydantic_model_creator(KuaishouVideo, name='kuaishouVideoCreate', exclude=('id',))
            kuaishou_data = kuaishou_video_pydantic(**local_db_item)
            kuaishou_video_pydantic.model_validate(kuaishou_data)
            await KuaishouVideo.create(**kuaishou_data.model_dump())
        else:
            kuaishou_video_pydantic = pydantic_model_creator(KuaishouVideo, name='kuaishouVideoUpdate',
                                                             exclude=('id', 'add_ts'))
            kuaishou_data = kuaishou_video_pydantic(**local_db_item)
            kuaishou_video_pydantic.model_validate(kuaishou_data)
            await KuaishouVideo.filter(video_id=video_id).update(**kuaishou_data.model_dump())
    else:
        # Below is a simple way to save it in CSV format.
        pathlib.Path(f"data/kuaishou").mkdir(parents=True, exist_ok=True)
        save_file_name = f"data/kuaishou/{crawler_type_var.get()}_videos_{utils.get_current_date()}.csv"
        with open(save_file_name, mode='a+', encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(local_db_item.keys())
            writer.writerow(local_db_item.values())


async def batch_update_ks_video_comments(video_id: str, comments: List[Dict]):
    utils.logger.info(f"[batch_update_ks_video_comments] video_id:{video_id}, comments:{comments}")
    if not comments:
        return
    for comment_item in comments:
        await update_ks_video_comment(video_id, comment_item)


async def update_ks_video_comment(video_id: str, comment_item: Dict):
    comment_id = comment_item.get("commentId")
    local_db_item = {
        "comment_id": comment_id,
        "create_time": comment_item.get("timestamp"),
        "video_id": video_id,
        "content": comment_item.get("content"),
        "user_id": comment_item.get("authorId"),
        "nickname": comment_item.get("authorName"),
        "avatar": comment_item.get("headurl"),
        "sub_comment_count": str(comment_item.get("subCommentCount", 0)),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    print(f"Kuaishou video comment: {comment_id}, content: {local_db_item.get('content')}")
    if config.IS_SAVED_DATABASED:
        if not await KuaishouVideoComment.filter(comment_id=comment_id).exists():
            local_db_item["add_ts"] = utils.get_current_timestamp()
            comment_pydantic = pydantic_model_creator(KuaishouVideoComment, name='KuaishouVideoCommentCreate',
                                                      exclude=('id',))
            comment_data = comment_pydantic(**local_db_item)
            comment_pydantic.validate(comment_data)
            await KuaishouVideoComment.create(**comment_data.dict())
        else:
            comment_pydantic = pydantic_model_creator(KuaishouVideoComment, name='KuaishouVideoCommentUpdate',
                                                      exclude=('id', 'add_ts'))
            comment_data = comment_pydantic(**local_db_item)
            comment_pydantic.validate(comment_data)
            await KuaishouVideoComment.filter(comment_id=comment_id).update(**comment_data.dict())
    else:
        pathlib.Path(f"data/kuaishou").mkdir(parents=True, exist_ok=True)
        save_file_name = f"data/kuaishou/{crawler_type_var.get()}_comments_{utils.get_current_date()}.csv"
        with open(save_file_name, mode='a+', encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(local_db_item.keys())
            writer.writerow(local_db_item.values())
