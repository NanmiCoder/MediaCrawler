# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 21:34
# @Desc    :

import re
from typing import List

from .weibo_store_image import *
from .weibo_store_impl import *


class WeibostoreFactory:
    STORES = {
        "csv": WeiboCsvStoreImplement,
        "db": WeiboDbStoreImplement,
        "json": WeiboJsonStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = WeibostoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[WeibotoreFactory.create_store] Invalid save option only supported csv or db or json ...")
        return store_class()


async def update_weibo_note(note_item: Dict):
    mblog: Dict = note_item.get("mblog")
    user_info: Dict = mblog.get("user")
    note_id = mblog.get("id")
    content_text = mblog.get("text")
    clean_text = re.sub(r"<.*?>", "", content_text)
    save_content_item = {
        # 微博信息
        "note_id": note_id,
        "content": clean_text,
        "create_time": utils.rfc2822_to_timestamp(mblog.get("created_at")),
        "create_date_time": str(utils.rfc2822_to_china_datetime(mblog.get("created_at"))),
        "liked_count": str(mblog.get("attitudes_count", 0)),
        "comments_count": str(mblog.get("comments_count", 0)),
        "shared_count": str(mblog.get("reposts_count", 0)),
        "last_modify_ts": utils.get_current_timestamp(),
        "note_url": f"https://m.weibo.cn/detail/{note_id}",
        "ip_location": mblog.get("region_name", "").replace("发布于 ", ""),

        # 用户信息
        "user_id": str(user_info.get("id")),
        "nickname": user_info.get("screen_name", ""),
        "gender": user_info.get("gender", ""),
        "profile_url": user_info.get("profile_url", ""),
        "avatar": user_info.get("profile_image_url", ""),
    }
    utils.logger.info(
        f"[store.weibo.update_weibo_note] weibo note id:{note_id}, title:{save_content_item.get('content')[:24]} ...")
    await WeibostoreFactory.create_store().store_content(content_item=save_content_item)


async def batch_update_weibo_note_comments(note_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_weibo_note_comment(note_id, comment_item)


async def update_weibo_note_comment(note_id: str, comment_item: Dict):
    comment_id = str(comment_item.get("id"))
    user_info: Dict = comment_item.get("user")
    content_text = comment_item.get("text")
    clean_text = re.sub(r"<.*?>", "", content_text)
    save_comment_item = {
        "comment_id": comment_id,
        "create_time": utils.rfc2822_to_timestamp(comment_item.get("created_at")),
        "create_date_time": str(utils.rfc2822_to_china_datetime(comment_item.get("created_at"))),
        "note_id": note_id,
        "content": clean_text,
        "sub_comment_count": str(comment_item.get("total_number", 0)),
        "comment_like_count": str(comment_item.get("like_count", 0)),
        "last_modify_ts": utils.get_current_timestamp(),
        "ip_location": comment_item.get("source", "").replace("来自", ""),
        "parent_comment_id": comment_item.get("rootid", ""),

        # 用户信息
        "user_id": str(user_info.get("id")),
        "nickname": user_info.get("screen_name", ""),
        "gender": user_info.get("gender", ""),
        "profile_url": user_info.get("profile_url", ""),
        "avatar": user_info.get("profile_image_url", ""),
    }
    utils.logger.info(
        f"[store.weibo.update_weibo_note_comment] Weibo note comment: {comment_id}, content: {save_comment_item.get('content', '')[:24]} ...")
    await WeibostoreFactory.create_store().store_comment(comment_item=save_comment_item)

async def update_weibo_note_image(picid: str, pic_content, extension_file_name):
    await WeiboStoreImage().store_image({"pic_id": picid, "pic_content": pic_content, "extension_file_name": extension_file_name})