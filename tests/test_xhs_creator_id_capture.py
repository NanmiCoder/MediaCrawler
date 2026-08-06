import json
from unittest.mock import AsyncMock

import pytest

import config
from media_platform.xhs import core as xhs_core
from media_platform.xhs.core import XiaoHongShuCrawler
from tools import xhs_creator_id_capture as capture_module
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


@pytest.mark.asyncio
async def test_invalid_user_id_writes_only_allowlisted_error_and_returns_normally(
    tmp_path, monkeypatch
):
    invalid_id = "INVALID-RAW-ID-MUST-NOT-LEAK"
    monkeypatch.setattr(config, "ENABLE_XHS_CREATOR_ID_CAPTURE", True)
    monkeypatch.setattr(config, "XHS_CREATOR_ID_CAPTURE_DIR", str(tmp_path))
    monkeypatch.setattr(capture_module.utils, "get_current_date", lambda: "2026-07-31")

    await capture_creator_id({
        "note_id": "note-1",
        "user": {"user_id": invalid_id, "nickname": "must-not-leak"},
        "xsec_token": "must-not-leak",
    })

    error_path = tmp_path / "search_creator_id_errors_2026-07-31.json"
    records = json.loads(error_path.read_text(encoding="utf-8"))
    assert len(records) == 1
    assert records[0]["note_id"] == "note-1"
    assert records[0]["error"] == "missing_or_invalid_user_id"
    assert isinstance(records[0]["captured_at"], str)
    assert set(records[0]) == {"note_id", "error", "captured_at"}
    assert invalid_id not in error_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_invalid_user_id_sidecar_io_failure_is_raised(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ENABLE_XHS_CREATOR_ID_CAPTURE", True)
    monkeypatch.setattr(config, "XHS_CREATOR_ID_CAPTURE_DIR", str(tmp_path))

    async def fail_to_thread(*args, **kwargs):
        raise OSError("private sidecar unavailable")

    monkeypatch.setattr(capture_module.asyncio, "to_thread", fail_to_thread)

    with pytest.raises(OSError, match="private sidecar unavailable"):
        await capture_creator_id({
            "note_id": "note-1",
            "user": {"user_id": "INVALID-RAW-ID-MUST-NOT-LEAK"},
        })


@pytest.mark.asyncio
async def test_invalid_user_id_error_does_not_block_anonymous_note_storage(
    tmp_path, monkeypatch
):
    log_messages = []

    class Logger:
        def info(self, message):
            log_messages.append(str(message))

    detail = {
        "note_id": "note-1",
        "user": {"user_id": "INVALID-RAW-ID-MUST-NOT-LEAK"},
        "xsec_token": "token",
    }
    monkeypatch.setattr(config, "ENABLE_XHS_CREATOR_ID_CAPTURE", True)
    monkeypatch.setattr(config, "XHS_CREATOR_ID_CAPTURE_DIR", str(tmp_path))
    monkeypatch.setattr(config, "KEYWORDS", "keyword")
    monkeypatch.setattr(config, "CRAWLER_MAX_NOTES_COUNT", 20)
    monkeypatch.setattr(config, "START_PAGE", 1)
    monkeypatch.setattr(config, "SORT_TYPE", "")
    monkeypatch.setattr(config, "MAX_CONCURRENCY_NUM", 1)
    monkeypatch.setattr(config, "CRAWLER_MAX_SLEEP_SEC", 0)

    crawler = XiaoHongShuCrawler()
    crawler.xhs_client = type("Client", (), {
        "get_note_by_keyword": AsyncMock(return_value={
            "has_more": True,
            "items": [{"id": "note-1", "xsec_source": "search", "xsec_token": "token"}],
        })
    })()
    crawler.get_note_detail_async_task = AsyncMock(return_value=detail)
    crawler.get_notice_media = AsyncMock()
    crawler.batch_get_note_comments = AsyncMock()
    store_note = AsyncMock()
    monkeypatch.setattr(xhs_core.xhs_store, "update_xhs_note", store_note)
    monkeypatch.setattr(xhs_core.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(xhs_core.utils, "logger", Logger())

    await crawler.search()

    store_note.assert_awaited_once_with(detail)
    assert len(list(tmp_path.glob("search_creator_id_errors_*.json"))) == 1
    assert "INVALID-RAW-ID-MUST-NOT-LEAK" not in "\n".join(log_messages)
