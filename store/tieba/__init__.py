# -*- coding: utf-8 -*-
from typing import List

from model.m_baidu_tieba import TiebaComment, TiebaNote

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


async def update_tieba_note(note_item: TiebaNote):
    """
    Add or Update tieba note
    Args:
        note_item:

    Returns:

    """
    save_note_item = note_item.model_dump()
    save_note_item.update({"last_modify_ts": utils.get_current_timestamp()})
    utils.logger.info(f"[store.tieba.update_tieba_note] tieba note: {save_note_item}")

    await TieBaStoreFactory.create_store().store_content(save_note_item)


async def batch_update_tieba_note_comments(note_id:str, comments: List[TiebaComment]):
    """
    Batch update tieba note comments
    Args:
        note_id:
        comments:

    Returns:

    """
    if not comments:
        return
    for comment_item in comments:
        await update_tieba_note_comment(note_id, comment_item)


async def update_tieba_note_comment(note_id: str, comment_item: TiebaComment):
    """
    Update tieba note comment
    Args:
        note_id:
        comment_item:

    Returns:

    """
    save_comment_item = comment_item.model_dump()
    save_comment_item.update({"last_modify_ts": utils.get_current_timestamp()})
    utils.logger.info(f"[store.tieba.update_tieba_note_comment] tieba note id: {note_id} comment:{save_comment_item}")
    await TieBaStoreFactory.create_store().store_comment(save_comment_item)
