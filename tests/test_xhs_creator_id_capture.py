import json

import pytest

import config
from tools.xhs_creator_id_capture import build_capture_record, capture_creator_id


VALID_ID = "5eb8e1d400000000010075ae"


def test_build_capture_record_contains_only_allowed_fields():
    record = build_capture_record({
        "note_id": "note-1",
        "user": {
            "user_id": VALID_ID,
            "nickname": "不得保存",
            "avatar": "https://private.invalid/avatar",
        },
        "xsec_token": "secret-token",
    }, captured_at="2026-07-31T10:00:00+08:00")

    assert record == {
        "note_id": "note-1",
        "creator_hash": "fb9185b3a79e6291",
        "public_user_id": VALID_ID,
        "profile_url": f"https://www.xiaohongshu.com/user/profile/{VALID_ID}",
        "captured_at": "2026-07-31T10:00:00+08:00",
    }


@pytest.mark.asyncio
async def test_capture_is_disabled_by_default_and_idempotent_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ENABLE_XHS_CREATOR_ID_CAPTURE", False)
    monkeypatch.setattr(config, "XHS_CREATOR_ID_CAPTURE_DIR", str(tmp_path))
    detail = {"note_id": "note-1", "user": {"user_id": VALID_ID}}

    await capture_creator_id(detail)
    assert list(tmp_path.iterdir()) == []

    monkeypatch.setattr(config, "ENABLE_XHS_CREATOR_ID_CAPTURE", True)
    await capture_creator_id(detail)
    await capture_creator_id(detail)
    records = json.loads(next(tmp_path.iterdir()).read_text(encoding="utf-8"))
    assert len(records) == 1
    assert records[0]["public_user_id"] == VALID_ID


def test_invalid_user_id_is_not_captured():
    assert build_capture_record({"note_id": "note-1", "user": {"user_id": "short"}}) is None
