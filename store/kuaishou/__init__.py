# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/kuaishou/__init__.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 20:03
# @Desc    :
from typing import List

import config
from var import source_keyword_var

from ._store_impl import *


class KuaishouStoreFactory:
    STORES = {
        "csv": KuaishouCsvStoreImplement,
        "db": KuaishouDbStoreImplement,
        "json": KuaishouJsonStoreImplement,
        "sqlite": KuaishouSqliteStoreImplement,
        "mongodb": KuaishouMongoStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = KuaishouStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[KuaishouStoreFactory.create_store] Invalid save option only supported csv or db or json or sqlite or mongodb ...")
        return store_class()


async def update_kuaishou_video(video_item: Dict):
    photo_info: Dict = video_item.get("photo", {})
    video_id = photo_info.get("id")
    if not video_id:
        return
    user_info = video_item.get("author", {})
    save_content_item = {
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
        "source_keyword": source_keyword_var.get(),
    }
    utils.logger.info(
        f"[store.kuaishou.update_kuaishou_video] Kuaishou video id:{video_id}, title:{save_content_item.get('title')}")
    await KuaishouStoreFactory.create_store().store_content(content_item=save_content_item)


async def batch_update_ks_video_comments(video_id: str, comments: List[Dict]):
    utils.logger.info(f"[store.kuaishou.batch_update_ks_video_comments] video_id:{video_id}, comments:{comments}")
    if not comments:
        return
    for comment_item in comments:
        await update_ks_video_comment(video_id, comment_item)


async def update_ks_video_comment(video_id: str, comment_item: Dict):
    comment_id = comment_item.get("commentId")
    save_comment_item = {
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
    utils.logger.info(
        f"[store.kuaishou.update_ks_video_comment] Kuaishou video comment: {comment_id}, content: {save_comment_item.get('content')}")
    await KuaishouStoreFactory.create_store().store_comment(comment_item=save_comment_item)

async def save_creator(user_id: str, creator: Dict):
    ownerCount = creator.get('ownerCount', {})
    profile = creator.get('profile', {})

    local_db_item = {
        'user_id': user_id,
        'nickname': profile.get('user_name'),
        'gender': '女' if profile.get('gender') == "F" else '男',
        'avatar': profile.get('headurl'),
        'desc': profile.get('user_text'),
        'ip_location': "",
        'follows': ownerCount.get("follow"),
        'fans': ownerCount.get("fan"),
        'interaction': ownerCount.get("photo_public"),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.kuaishou.save_creator] creator:{local_db_item}")
    await KuaishouStoreFactory.create_store().store_creator(local_db_item)
