import json
from typing import Dict, List

from tools import utils


async def update_douyin_aweme(aweme_item: Dict):
    aweme_id = aweme_item.get("aweme_id")
    user_info = aweme_item.get("author", {})
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
        "ip_location": aweme_item.get("ip_label", ""),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    # do something ...
    print(f"douyin aweme id:{aweme_id}, title:{local_db_item.get('title')}")


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
    user_info = comment_item.get("user")
    comment_id = comment_item.get("cid")
    avatar_info = user_info.get("avatar_medium") or user_info.get("avatar_300x300") or user_info.get(
        "avatar_168x168") or user_info.get("avatar_thumb") or {}
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
    # do something ...
    print(f"douyin aweme comment: {comment_id}, content: {local_db_item.get('content')}")
