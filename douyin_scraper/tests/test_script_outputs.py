import csv
import json
from pathlib import Path
from unittest.mock import patch

from douyin_scraper import DouyinScraper


def _scraper(tmp_path: Path) -> DouyinScraper:
    return DouyinScraper(
        {
            "project_dir": str(tmp_path),
            "state_dir_name": "workspaces/scripts-task/state",
            "keep_videos": True,
        }
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _source(
    aweme_id: str,
    *,
    video_url: str = "",
    clean_text: str = "",
    raw_text: str = "",
) -> dict:
    return {
        "source_keyword": "停车",
        "platform": "douyin",
        "video_id": aweme_id,
        "aweme_id": aweme_id,
        "aweme_url": f"https://www.douyin.com/video/{aweme_id}",
        "video_download_url": video_url,
        "source_video_download_url": video_url,
        "source_video_download_available": bool(video_url),
        "source_asr_planned": bool(video_url),
        "source_clean_title_text": clean_text,
        "source_title_desc_text": raw_text,
    }


def test_script_sources_export_from_search_csv(tmp_path: Path) -> None:
    scraper = _scraper(tmp_path)
    search_csv = tmp_path / "search_result.csv"
    title_csv = tmp_path / "search_title_clean.csv"
    with open(search_csv, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_keyword",
                "platform",
                "video_id",
                "aweme_id",
                "title",
                "desc",
                "aweme_url",
                "video_download_url",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "source_keyword": "停车",
                "platform": "douyin",
                "video_id": "source-1",
                "aweme_id": "source-1",
                "title": "raw title",
                "desc": "raw desc",
                "aweme_url": "https://www.douyin.com/video/source-1",
                "video_download_url": "https://example.com/source-1.mp4",
            }
        )
    with open(title_csv, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "video_id",
                "aweme_id",
                "aweme_url",
                "clean_title",
                "clean_desc",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "video_id": "source-1",
                "aweme_id": "source-1",
                "aweme_url": "https://www.douyin.com/video/source-1",
                "clean_title": "clean title",
                "clean_desc": "clean desc",
            }
        )

    sources_jsonl, sources_csv, stats = scraper._do_build_script_sources(
        search_csv,
        title_clean_csv_path=title_csv,
    )

    assert stats["rows_in"] == 1
    assert stats["rows_out"] == 1
    assert stats["clean_title_available"] == 1
    assert stats["asr_planned"] == 1
    assert sources_csv.read_bytes()[:3] == b"\xef\xbb\xbf"
    row = json.loads(sources_jsonl.read_text(encoding="utf-8").strip())
    assert row["source_clean_title_text"] == "clean title clean desc"
    assert row["script_source_quality"] == "medium"


def test_script_sources_fallback_to_search_jsonl(tmp_path: Path) -> None:
    scraper = _scraper(tmp_path)
    missing_csv = tmp_path / "search_result.csv"
    search_jsonl = tmp_path / "search_result.jsonl"
    _write_jsonl(
        search_jsonl,
        [
            {
                "aweme_id": "fallback-1",
                "video_id": "fallback-1",
                "title": "fallback title",
                "desc": "fallback desc",
                "aweme_url": "https://www.douyin.com/video/fallback-1",
            }
        ],
    )

    sources_jsonl, sources_csv, stats = scraper._do_build_script_sources(
        missing_csv,
        search_jsonl,
    )

    assert stats["rows_in"] == 1
    assert stats["rows_out"] == 1
    assert sources_jsonl.exists()
    assert sources_csv.exists()
    row = json.loads(sources_jsonl.read_text(encoding="utf-8").strip())
    assert row["source_title_desc_text"] == "fallback title fallback desc"


def test_script_raw_from_script_sources_jsonl_success_and_skips(
    tmp_path: Path,
) -> None:
    scraper = _scraper(tmp_path)
    sources = tmp_path / "script_sources.jsonl"
    _write_jsonl(
        sources,
        [
            _source("raw-1", video_url="https://example.com/raw-1.mp4"),
            _source("skip-1"),
        ],
    )

    with (
        patch("douyin_scraper.core.check_disk_space_enforced"),
        patch.object(
            scraper,
            "_load_script_raw_whisper_model",
            return_value=(object(), "", ""),
        ),
        patch.object(scraper, "_download_video", return_value=True),
        patch.object(scraper, "_transcribe_video", return_value="ASR text"),
    ):
        raw_jsonl, raw_csv, stats = scraper._do_build_script_raw(
            script_sources_jsonl=sources,
            max_items=1,
        )

    assert stats["rows_in"] == 2
    assert stats["rows_targeted"] == 1
    assert stats["asr_success"] == 1
    assert raw_csv.read_bytes()[:3] == b"\xef\xbb\xbf"
    rows = [
        json.loads(line)
        for line in raw_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {row["aweme_id"]: row for row in rows}
    assert by_id["raw-1"]["download_status"] == "success"
    assert by_id["raw-1"]["asr_status"] == "success"
    assert by_id["skip-1"]["download_status"] == "skipped"


def test_script_raw_fallback_to_csv_download_failed_and_empty_asr(
    tmp_path: Path,
) -> None:
    scraper = _scraper(tmp_path)
    sources_csv = tmp_path / "script_sources.csv"
    rows = [
        _source("download-failed", video_url="https://example.com/failed.mp4"),
        _source("empty-asr", video_url="https://example.com/empty.mp4"),
    ]
    with open(sources_csv, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    with (
        patch("douyin_scraper.core.check_disk_space_enforced"),
        patch.object(
            scraper,
            "_load_script_raw_whisper_model",
            return_value=(object(), "", ""),
        ),
        patch.object(scraper, "_download_video", side_effect=[False, True]),
        patch.object(scraper, "_transcribe_video", return_value=""),
    ):
        raw_jsonl, _, stats = scraper._do_build_script_raw(
            script_sources_csv=sources_csv,
            max_items=2,
        )

    assert stats["download_failed"] == 1
    assert stats["asr_empty_text"] == 1
    rows = [
        json.loads(line)
        for line in raw_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {row["aweme_id"]: row for row in rows}
    assert by_id["download-failed"]["download_status"] == "failed"
    assert by_id["empty-asr"]["asr_status"] == "empty_text"


def test_script_raw_dependency_missing_does_not_download(tmp_path: Path) -> None:
    scraper = _scraper(tmp_path)
    sources = tmp_path / "script_sources.jsonl"
    _write_jsonl(
        sources,
        [_source("dependency-1", video_url="https://example.com/video.mp4")],
    )

    with (
        patch("douyin_scraper.core.check_disk_space_enforced"),
        patch.object(
            scraper,
            "_load_script_raw_whisper_model",
            return_value=(None, "dependency_missing", "missing"),
        ),
        patch.object(scraper, "_download_video") as download,
    ):
        raw_jsonl, _, stats = scraper._do_build_script_raw(
            script_sources_jsonl=sources,
            max_items=1,
        )

    download.assert_not_called()
    assert stats["asr_dependency_missing"] == 1
    row = json.loads(raw_jsonl.read_text(encoding="utf-8").strip())
    assert row["asr_status"] == "dependency_missing"
    assert row["download_status"] == "skipped"


def test_script_clean_priority_from_raw_sources_and_title_clean(
    tmp_path: Path,
) -> None:
    scraper = _scraper(tmp_path)
    sources = tmp_path / "script_sources.jsonl"
    raw = tmp_path / "script_raw.jsonl"
    title_csv = tmp_path / "search_title_clean.csv"
    _write_jsonl(
        sources,
        [
            _source("asr-1", clean_text="clean fallback", raw_text="raw fallback"),
            _source("source-clean-1", clean_text="source clean text"),
            _source("title-clean-1"),
            _source("title-desc-1", raw_text="source title desc"),
            _source("missing-1"),
        ],
    )
    _write_jsonl(
        raw,
        [
            {
                "aweme_id": "asr-1",
                "video_id": "asr-1",
                "asr_status": "success",
                "asr_raw_text": "ASR wins",
                "script_raw_quality": "high",
            }
        ],
    )
    with open(title_csv, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "video_id",
                "aweme_id",
                "aweme_url",
                "clean_title",
                "clean_desc",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "video_id": "title-clean-1",
                "aweme_id": "title-clean-1",
                "aweme_url": "https://www.douyin.com/video/title-clean-1",
                "clean_title": "title clean",
                "clean_desc": "title desc",
            }
        )

    clean_jsonl, clean_csv, stats = scraper._do_build_script_clean(
        script_sources_jsonl=sources,
        script_raw_jsonl=raw,
        title_clean_csv=title_csv,
    )

    assert stats["rows_out"] == 5
    assert stats["asr_text_used"] == 1
    assert stats["clean_title_used"] == 2
    assert stats["title_desc_used"] == 1
    assert stats["missing"] == 1
    assert clean_csv.read_bytes()[:3] == b"\xef\xbb\xbf"
    rows = [
        json.loads(line)
        for line in clean_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {row["aweme_id"]: row for row in rows}
    assert by_id["asr-1"]["script_clean_source"] == "asr_raw"
    assert by_id["source-clean-1"]["script_clean_source"] == "source_clean_title"
    assert by_id["title-clean-1"]["script_clean_text"] == "title clean title desc"
    assert by_id["title-desc-1"]["script_clean_source"] == "source_title_desc"
    assert by_id["missing-1"]["script_clean_status"] == "missing"
