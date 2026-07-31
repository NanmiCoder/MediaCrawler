import asyncio
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

import config
from tools import utils
from tools.user_hash import anonymize_user_id


_USER_ID = re.compile(r"^[0-9a-f]{24}$")
_LOCK = asyncio.Lock()


def build_capture_record(note_detail: dict, captured_at: str | None = None) -> dict | None:
    note_id = str(note_detail.get("note_id") or "").strip()
    user_id = str((note_detail.get("user") or {}).get("user_id") or "").strip()
    if not note_id or not _USER_ID.fullmatch(user_id):
        return None
    return {
        "note_id": note_id,
        "creator_hash": anonymize_user_id(user_id),
        "public_user_id": user_id,
        "profile_url": f"https://www.xiaohongshu.com/user/profile/{user_id}",
        "captured_at": captured_at or datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def _capture_path() -> Path:
    base = Path(config.XHS_CREATOR_ID_CAPTURE_DIR) if config.XHS_CREATOR_ID_CAPTURE_DIR else Path("data/xhs/private")
    return base / f"search_creator_ids_{utils.get_current_date()}.json"


def _write_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    keyed = {(item["note_id"], item["public_user_id"]): item for item in records}
    keyed[(record["note_id"], record["public_user_id"])] = record
    fd, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(list(keyed.values()), output, ensure_ascii=False, indent=2)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


async def capture_creator_id(note_detail: dict) -> None:
    if not config.ENABLE_XHS_CREATOR_ID_CAPTURE:
        return
    record = build_capture_record(note_detail)
    if record is None:
        return
    async with _LOCK:
        await asyncio.to_thread(_write_record, _capture_path(), record)
