# -*- coding: utf-8 -*-
from typing import List

from . import tieba_store_impl
from .tieba_store_impl import *


class TieBaStoreFactory:
    STORES = {
        "csv": TieBaCsvStoreImplement,
        "db": TieBaDbStoreImplement,
        "json": TieBaJsonStoreImplement
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = TieBaStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[TieBaStoreFactory.create_store] Invalid save option only supported csv or db or json ...")
        return store_class()


async def update_tieba_note(note_item: Dict):
    tieba_url = "https://tieba.baidu.com"
    note_id = note_item.get("note_id")
    local_db_item = {
        "note_id": note_id,
        "title": note_item.get("title") or note_item.get("desc", "")[:255],
        "desc": note_item.get("desc", ""),
        "note_url": tieba_url + note_item.get("note_url"),
        "time": note_item.get("time"),
        "tieba_name": note_item.get("tieba_name"),
        "tieba_link": tieba_url + note_item.get("tieba_link", ""),
        "nickname": note_item.get("nickname"),
        "nickname_link": tieba_url + note_item.get("nickname_link", ""),
        "ip_location": note_item.get("ip_location", ""),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.tieba.update_tieba_note] tieba note: {local_db_item}")
    await TieBaStoreFactory.create_store().store_content(local_db_item)


async def batch_update_tieba_note_comments(note_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_tieba_note_comment(note_id, comment_item)


async def update_tieba_note_comment(note_id: str, comment_item: Dict):
    """
    Update tieba note comment
    Args:
        note_id:
        comment_item:

    Returns:

    """
    user_info = comment_item.get("user_info", {})
    comment_id = comment_item.get("id")
    comment_pictures = [item.get("url_default", "") for item in comment_item.get("pictures", [])]
    target_comment = comment_item.get("target_comment", {})
    local_db_item = {
        "comment_id": comment_id,
        "create_time": comment_item.get("create_time"),
        "ip_location": comment_item.get("ip_location"),
        "note_id": note_id,
        "content": comment_item.get("content"),
        "user_id": user_info.get("user_id"),
        "nickname": user_info.get("nickname"),
        "avatar": user_info.get("image"),
        "sub_comment_count": comment_item.get("sub_comment_count", 0),
        "pictures": ",".join(comment_pictures),
        "parent_comment_id": target_comment.get("id", 0),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.tieba.update_tieba_note_comment] tieba note comment:{local_db_item}")
    await TieBaStoreFactory.create_store().store_comment(local_db_item)
