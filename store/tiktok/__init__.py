# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/tiktok/__init__.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习 and 研究目的使用。使用者应遵守以下原则：
# 1. 不得用于 any 商业用途。
# 2. 使用时应遵守目标平台的使用条款 and robots.txt规则。
# 3. 不得进行大规模爬取 or 对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于 any 非法 or 不当 the 用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE file。
# 使用本代码即表示您同意遵守上述原则 and LICENSE中的所有条款。

from typing import List, Dict

import config
from var import source_keyword_var
from base.base_crawler import AbstractStore
from tools import utils
from ._store_impl import *
from .tiktok_store_media import *


class TikTokStoreFactory:
    STORES = {
        "csv": TikTokCsvStoreImplement,
        "db": TikTokDbStoreImplement,
        "postgres": TikTokDbStoreImplement,
        "json": TikTokJsonStoreImplement,
        "jsonl": TikTokJsonlStoreImplement,
        "sqlite": TikTokSqliteStoreImplement,
        "mongodb": TikTokMongoStoreImplement,
        "excel": TikTokExcelStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = TikTokStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[TikTokStoreFactory.create_store] Invalid save option only supported csv or db or json or sqlite or mongodb or excel ...")
        return store_class()


def _extract_content_cover_url(item: Dict) -> str:
    return item.get("video", {}).get("cover", "")


def _extract_video_download_url(item: Dict) -> str:
    return item.get("video", {}).get("playAddr", "")


def _extract_music_download_url(item: Dict) -> str:
    return item.get("music", {}).get("playUrl", "")


async def update_tiktok_aweme(aweme_item: Dict):
    aweme_id = aweme_item.get("id") or aweme_item.get("aweme_id")
    author = aweme_item.get("author", {})
    stats = aweme_item.get("stats", {})

    save_content_item = {
        "aweme_id": str(aweme_id),
        "aweme_type": str(aweme_item.get("aweme_type", "video")),
        "title": aweme_item.get("desc", ""),
        "desc": aweme_item.get("desc", ""),
        "create_time": aweme_item.get("createTime") or aweme_item.get("create_time") or 0,
        "user_id": author.get("id") or author.get("uid") or "",
        "nickname": author.get("nickname", ""),
        "avatar": author.get("avatarLarger") or author.get("avatar_thumb", {}).get("url_list", [""])[0] or "",
        "user_signature": author.get("signature", ""),
        "liked_count": str(stats.get("diggCount") or stats.get("liked_count") or 0),
        "collected_count": str(stats.get("collectCount") or stats.get("collected_count") or 0),
        "comment_count": str(stats.get("commentCount") or stats.get("comment_count") or 0),
        "share_count": str(stats.get("shareCount") or stats.get("share_count") or 0),
        "ip_location": aweme_item.get("ip_label") or aweme_item.get("ipLocation") or "",
        "last_modify_ts": utils.get_current_timestamp(),
        "aweme_url": f"https://www.tiktok.com/@{author.get('uniqueId')}/video/{aweme_id}" if author.get("uniqueId") else f"https://www.tiktok.com/video/{aweme_id}",
        "cover_url": _extract_content_cover_url(aweme_item),
        "video_download_url": _extract_video_download_url(aweme_item),
        "music_download_url": _extract_music_download_url(aweme_item),
        "note_download_url": "",
        "source_keyword": source_keyword_var.get(),
    }
    utils.logger.info(f"[store.tiktok.update_tiktok_aweme] tiktok aweme id:{aweme_id}, desc:{save_content_item.get('desc')[:30]}")
    await TikTokStoreFactory.create_store().store_content(content_item=save_content_item)


async def batch_update_tiktok_comments(aweme_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_tiktok_comment(aweme_id, comment_item)


async def update_tiktok_comment(aweme_id: str, comment_item: Dict):
    comment_id = comment_item.get("cid") or comment_item.get("comment_id")
    user = comment_item.get("user", {})

    save_comment_item = {
        "comment_id": str(comment_id),
        "create_time": comment_item.get("create_time") or comment_item.get("createTime") or 0,
        "ip_location": comment_item.get("ip_label") or comment_item.get("ip_location") or "",
        "aweme_id": str(aweme_id),
        "content": comment_item.get("text") or comment_item.get("content") or "",
        "user_id": user.get("uid") or user.get("user_id") or "",
        "user_unique_id": user.get("unique_id") or user.get("user_unique_id") or "",
        "nickname": user.get("nickname", ""),
        "avatar": user.get("avatar_thumb", {}).get("url_list", [""])[0] if isinstance(user.get("avatar_thumb"), dict) else user.get("avatar", ""),
        "sub_comment_count": str(comment_item.get("reply_comment_total") or comment_item.get("sub_comment_count") or 0),
        "like_count": str(comment_item.get("digg_count") or comment_item.get("like_count") or 0),
        "last_modify_ts": utils.get_current_timestamp(),
        "parent_comment_id": str(comment_item.get("reply_id") or comment_item.get("parent_comment_id") or "0"),
        "pictures": "",
    }
    utils.logger.info(f"[store.tiktok.update_tiktok_comment] tiktok aweme comment: {comment_id}, content: {save_comment_item.get('content')[:30]}")
    await TikTokStoreFactory.create_store().store_comment(comment_item=save_comment_item)


async def save_creator(user_id: str, creator: Dict):
    user = creator.get("user", {})
    stats = creator.get("stats", {})
    gender_map = {0: "Unknown", 1: "Male", 2: "Female"}

    local_db_item = {
        "user_id": str(user_id),
        "nickname": user.get("nickname") or creator.get("nickname") or "",
        "gender": gender_map.get(user.get("gender"), "Unknown"),
        "avatar": user.get("avatarLarger") or user.get("avatar") or creator.get("avatar") or "",
        "desc": user.get("signature") or creator.get("bio") or "",
        "ip_location": user.get("ipLocation") or creator.get("region") or "",
        "follows": str(stats.get("followingCount") or stats.get("following_count") or 0),
        "fans": str(stats.get("followerCount") or stats.get("follower_count") or 0),
        "interaction": str(stats.get("heartCount") or stats.get("heart_count") or 0),
        "videos_count": str(stats.get("videoCount") or stats.get("video_count") or 0),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.tiktok.save_creator] creator:{local_db_item}")
    await TikTokStoreFactory.create_store().store_creator(local_db_item)


async def update_tiktok_image(aweme_id, pic_content, extension_file_name):
    await TikTokImage().store_image({"aweme_id": aweme_id, "pic_content": pic_content, "extension_file_name": extension_file_name})


async def update_tiktok_video(aweme_id, video_content, extension_file_name):
    await TikTokVideo().store_video({"aweme_id": aweme_id, "video_content": video_content, "extension_file_name": extension_file_name})
