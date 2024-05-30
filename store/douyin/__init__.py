# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 18:46
# @Desc    :
from typing import List

import config

from .douyin_store_impl import *


class DouyinStoreFactory:
    STORES = {
        "csv": DouyinCsvStoreImplement,
        "db": DouyinDbStoreImplement,
        "json": DouyinJsonStoreImplement
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = DouyinStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[DouyinStoreFactory.create_store] Invalid save option only supported csv or db or json ...")
        return store_class()


async def update_douyin_aweme(aweme_item: Dict):
    aweme_id = aweme_item.get("aweme_id")
    user_info = aweme_item.get("author", {})
    interact_info = aweme_item.get("statistics", {})
    save_content_item = {
        "aweme_id": aweme_id,
        "aweme_type": str(aweme_item.get("aweme_type")),
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
        "liked_count": str(interact_info.get("digg_count")),
        "collected_count": str(interact_info.get("collect_count")),
        "comment_count": str(interact_info.get("comment_count")),
        "share_count": str(interact_info.get("share_count")),
        "ip_location": aweme_item.get("ip_label", ""),
        "last_modify_ts": utils.get_current_timestamp(),
        "aweme_url": f"https://www.douyin.com/video/{aweme_id}"
    }
    utils.logger.info(
        f"[store.douyin.update_douyin_aweme] douyin aweme id:{aweme_id}, title:{save_content_item.get('title')}")
    await DouyinStoreFactory.create_store().store_content(content_item=save_content_item)


async def batch_update_dy_aweme_comments(aweme_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_dy_aweme_comment(aweme_id, comment_item)


async def update_dy_aweme_comment(aweme_id: str, comment_item: Dict):
    comment_aweme_id = comment_item.get("aweme_id")
    if aweme_id != comment_aweme_id:
        utils.logger.error(
            f"[store.douyin.update_dy_aweme_comment] comment_aweme_id: {comment_aweme_id} != aweme_id: {aweme_id}")
        return
    user_info = comment_item.get("user", {})
    comment_id = comment_item.get("cid")
    avatar_info = user_info.get("avatar_medium", {}) or user_info.get("avatar_300x300", {}) or user_info.get(
        "avatar_168x168", {}) or user_info.get("avatar_thumb", {}) or {}
    save_comment_item = {
        "comment_id": comment_id,
        "create_time": comment_item.get("create_time"),
        "ip_location": comment_item.get("ip_label", ""),
        "aweme_id": aweme_id,
        "content": comment_item.get("text"),
        "user_id": user_info.get("uid"),
        "sec_uid": user_info.get("sec_uid"),
        "short_user_id": user_info.get("short_id"),
        "user_unique_id": user_info.get("unique_id"),
        "user_signature": user_info.get("signature"),
        "nickname": user_info.get("nickname"),
        "avatar": avatar_info.get("url_list", [""])[0],
        "sub_comment_count": str(comment_item.get("reply_comment_total", 0)),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(
        f"[store.douyin.update_dy_aweme_comment] douyin aweme comment: {comment_id}, content: {save_comment_item.get('content')}")

    await DouyinStoreFactory.create_store().store_comment(comment_item=save_comment_item)




async def save_creator(user_id: str, creator: Dict):
    user_info = creator.get('user', {})
    gender_map = {
        0: '未知',
        1: '男',
        2: '女'
    }
    avatar_uri = user_info.get('avatar_300x300', {}).get('uri')
    local_db_item = {
        'user_id': user_id,
        'nickname': user_info.get('nickname'),
        'gender': gender_map.get(user_info.get('gender'), '未知'),
        'avatar': f"https://p3-pc.douyinpic.com/img/{avatar_uri}" + r"~c5_300x300.jpeg?from=2956013662",
        'desc': user_info.get('signature'),
        'ip_location': user_info.get('ip_location'),
        'follows': user_info.get("following_count", 0),
        'fans': user_info.get("max_follower_count", 0),
        'interaction': user_info.get("total_favorited", 0),
        'videos_count': user_info.get("aweme_count", 0),
        "last_modify_ts": utils.get_current_timestamp(),

    }
    utils.logger.info(f"[store.douyin.save_creator] creator:{local_db_item}")
    await DouyinStoreFactory.create_store().store_creator(local_db_item)
