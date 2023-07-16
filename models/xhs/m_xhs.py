from typing import Dict, List

from tools import utils


async def update_xhs_note(note_item: Dict):
    note_id = note_item.get("note_id")
    user_info = note_item.get("user", {})
    interact_info = note_item.get("interact_info")
    image_list: List[Dict]= note_item.get("image_list", [])

    local_db_item = {
        "note_id": note_item.get("note_id"),
        "type": note_item.get("type"),
        "title": note_item.get("title"),
        "desc": note_item.get("desc", ""),
        "time": note_item.get("time"),
        "last_update_time": note_item.get("last_update_time", 0),
        "user_id": user_info.get("user_id"),
        "nickname": user_info.get("nickname"),
        "avatar": user_info.get("avatar"),
        "ip_location": note_item.get("ip_location", ""),
        "image_list": ','.join([img.get('url','') for img in image_list]),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    # do something ...
    print("xhs note:", local_db_item)


async def update_xhs_note_comment(note_id: str, comment_item: Dict):
    user_info = comment_item.get("user_info", {})
    comment_id = comment_item.get("id")
    local_db_item = {
        "comment_id": comment_id,
        "create_time": comment_item.get("create_time"),
        "ip_location": comment_item.get("ip_location"),
        "note_id": note_id,
        "content": comment_item.get("content"),
        "user_id": user_info.get("user_id"),
        "nickname": user_info.get("nickname"),
        "avatar": user_info.get("image"),
        "sub_comment_count": comment_item.get("sub_comment_count"),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    # do something ...
    print("xhs note comment:", local_db_item)
