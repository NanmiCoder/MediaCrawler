# -*- coding: utf-8 -*-
from typing import List, Dict
import json

import config
from base.base_crawler import AbstractStore
from tools import utils

from .niuke_store_impl import (
    NiukeCsvStoreImplement,
    NiukeDbStoreImplement,
    NiukeJsonStoreImplement,
)


class NiukeStoreFactory:
    STORES = {
        "csv": NiukeCsvStoreImplement,
        "db": NiukeDbStoreImplement,
        "json": NiukeJsonStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = NiukeStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[NiukeStoreFactory.create_store] Invalid save option only supported csv or db or json ..."
            )
        return store_class()


async def batch_update_niuke_notes(notes: List[Dict]):
    if not notes:
        return
    for note in notes:
        await update_niuke_note(note)


async def update_niuke_note(note_item: Dict):
    note_item = note_item.copy()
    note_item.update({
        "last_modify_ts": utils.get_current_timestamp(),
        "categories": json.dumps(config.CATEGORIES, ensure_ascii=False),
    })
    await NiukeStoreFactory.create_store().store_content(note_item)
