import csv
import json
from pathlib import Path

from douyin_scraper import DouyinScraper


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_content_asset_from_search_and_title_only(tmp_path: Path) -> None:
    search_outputs = tmp_path / "workspaces" / "search-task" / "outputs"
    _write_csv(
        search_outputs / "search_result.csv",
        [
            "source_keyword",
            "platform",
            "video_id",
            "aweme_id",
            "title",
            "desc",
            "nickname",
            "liked_count",
            "collected_count",
            "comment_count",
            "share_count",
            "total_engagement",
            "aweme_url",
        ],
        [{
            "source_keyword": "parking",
            "platform": "douyin",
            "video_id": "a1",
            "aweme_id": "a1",
            "title": "\u4e2d\u6587\u6807\u9898",
            "desc": "raw desc",
            "nickname": "coach",
            "liked_count": "10",
            "collected_count": "2",
            "comment_count": "3",
            "share_count": "1",
            "total_engagement": "16",
            "aweme_url": "https://www.douyin.com/video/a1",
        }],
    )
    _write_csv(
        search_outputs / "search_title_clean.csv",
        [
            "source_keyword",
            "platform",
            "video_id",
            "aweme_id",
            "raw_title",
            "clean_title",
            "raw_desc",
            "clean_desc",
            "topic",
            "pain_point",
            "teaching_angle",
            "aweme_url",
        ],
        [{
            "source_keyword": "parking",
            "platform": "douyin",
            "video_id": "a1",
            "aweme_id": "a1",
            "raw_title": "\u4e2d\u6587\u6807\u9898",
            "clean_title": "\u4e2d\u6587",
            "raw_desc": "raw desc",
            "clean_desc": "clean desc",
            "topic": "parking",
            "pain_point": "line",
            "teaching_angle": "angle",
            "aweme_url": "https://www.douyin.com/video/a1",
        }],
    )

    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/merge-task/state",
    })
    jsonl_path, csv_path, stats = scraper.build_content_asset(search_outputs)

    assert stats["rows_in"] == 1
    assert stats["rows_out"] == 1
    assert stats["content_asset_csv_generated"] is True
    assert csv_path.read_bytes()[:3] == b"\xef\xbb\xbf"
    json_text = jsonl_path.read_text(encoding="utf-8")
    assert "\u4e2d\u6587" in json_text
    assert "\\u4e2d\\u6587" not in json_text

    row = _read_jsonl(jsonl_path)[0]
    assert row["clean_title"] == "\u4e2d\u6587"
    assert row["comment_data_status"] == "pending_cdp"
    assert row["asr_data_status"] == "missing"
    assert row["asset_quality"] == "low"
    paths = scraper.get_paths()
    assert paths["content_asset_jsonl"] == str(jsonl_path)
    assert paths["content_asset_csv"] == str(csv_path)
    assert paths["content_asset_stats"]["rows_out"] == 1


def test_content_asset_aggregates_comments_and_scripts(tmp_path: Path) -> None:
    search_outputs = tmp_path / "workspaces" / "search-task" / "outputs"
    comments_outputs = tmp_path / "workspaces" / "comments-task" / "outputs"
    scripts_outputs = tmp_path / "workspaces" / "scripts-task" / "outputs"
    search_fields = [
        "source_keyword",
        "platform",
        "video_id",
        "aweme_id",
        "title",
        "desc",
        "nickname",
        "liked_count",
        "collected_count",
        "comment_count",
        "share_count",
        "total_engagement",
        "aweme_url",
    ]
    _write_csv(
        search_outputs / "search_result.csv",
        search_fields,
        [
            {
                "source_keyword": "parking",
                "platform": "douyin",
                "video_id": "video-1",
                "aweme_id": "a1",
                "title": "raw one",
                "desc": "desc one",
                "nickname": "coach1",
                "liked_count": "5",
                "collected_count": "1",
                "comment_count": "9",
                "share_count": "2",
                "total_engagement": "",
                "aweme_url": "https://www.douyin.com/video/a1",
            },
            {
                "source_keyword": "parking",
                "platform": "douyin",
                "video_id": "video-2",
                "aweme_id": "",
                "title": "raw two",
                "desc": "desc two",
                "nickname": "coach2",
                "liked_count": "1",
                "collected_count": "1",
                "comment_count": "0",
                "share_count": "1",
                "total_engagement": "3",
                "aweme_url": "https://www.douyin.com/video/v2",
            },
            {
                "source_keyword": "parking",
                "platform": "douyin",
                "video_id": "video-3",
                "aweme_id": "a3",
                "title": "raw three",
                "desc": "desc three",
                "nickname": "coach3",
                "liked_count": "1",
                "collected_count": "0",
                "comment_count": "1",
                "share_count": "0",
                "total_engagement": "2",
                "aweme_url": "https://www.douyin.com/video/a3",
            },
        ],
    )
    _write_csv(
        search_outputs / "search_title_clean.csv",
        [
            "source_keyword",
            "platform",
            "video_id",
            "aweme_id",
            "raw_title",
            "clean_title",
            "raw_desc",
            "clean_desc",
            "topic",
            "pain_point",
            "teaching_angle",
            "aweme_url",
        ],
        [
            {
                "source_keyword": "parking",
                "platform": "douyin",
                "video_id": "video-1",
                "aweme_id": "a1",
                "raw_title": "raw one",
                "clean_title": "clean one",
                "raw_desc": "desc one",
                "clean_desc": "clean desc one",
                "topic": "topic one",
                "pain_point": "pain one",
                "teaching_angle": "angle one",
                "aweme_url": "https://www.douyin.com/video/a1",
            },
            {
                "source_keyword": "parking",
                "platform": "douyin",
                "video_id": "video-2",
                "aweme_id": "",
                "raw_title": "raw two",
                "clean_title": "clean two",
                "raw_desc": "desc two",
                "clean_desc": "clean desc two",
                "topic": "topic two",
                "pain_point": "pain two",
                "teaching_angle": "angle two",
                "aweme_url": "https://www.douyin.com/video/v2",
            },
        ],
    )
    _write_csv(
        comments_outputs / "comments_clean.csv",
        [
            "video_id",
            "aweme_id",
            "comment_id",
            "clean_content",
            "is_valid",
            "invalid_reason",
            "pain_tags",
        ],
        [
            {
                "video_id": "video-1",
                "aweme_id": "a1",
                "comment_id": "c1",
                "clean_content": "valid one",
                "is_valid": "true",
                "invalid_reason": "",
                "pain_tags": "line|mirror",
            },
            {
                "video_id": "video-1",
                "aweme_id": "a1",
                "comment_id": "c2",
                "clean_content": "valid two",
                "is_valid": "1",
                "invalid_reason": "",
                "pain_tags": "line|nervous",
            },
            {
                "video_id": "video-1",
                "aweme_id": "a1",
                "comment_id": "c3",
                "clean_content": "invalid",
                "is_valid": "false",
                "invalid_reason": "duplicate",
                "pain_tags": "ignore",
            },
            {
                "video_id": "video-3",
                "aweme_id": "a3",
                "comment_id": "c4",
                "clean_content": "valid three",
                "is_valid": "true",
                "invalid_reason": "",
                "pain_tags": "line",
            },
        ],
    )
    _write_csv(
        scripts_outputs / "script_sources.csv",
        [
            "video_id",
            "aweme_id",
            "aweme_url",
            "source_asr_planned",
            "script_source_status",
            "script_source_quality",
        ],
        [
            {
                "video_id": "video-1",
                "aweme_id": "a1",
                "aweme_url": "https://www.douyin.com/video/a1",
                "source_asr_planned": "true",
                "script_source_status": "available",
                "script_source_quality": "medium",
            },
            {
                "video_id": "video-2",
                "aweme_id": "",
                "aweme_url": "https://www.douyin.com/video/v2",
                "source_asr_planned": "false",
                "script_source_status": "available",
                "script_source_quality": "weak",
            },
            {
                "video_id": "video-3",
                "aweme_id": "a3",
                "aweme_url": "https://www.douyin.com/video/a3",
                "source_asr_planned": "true",
                "script_source_status": "available",
                "script_source_quality": "high",
            },
        ],
    )
    _write_csv(
        scripts_outputs / "script_raw.csv",
        [
            "video_id",
            "aweme_id",
            "aweme_url",
            "asr_status",
            "asr_raw_text",
            "script_raw_quality",
        ],
        [
            {
                "video_id": "video-1",
                "aweme_id": "a1",
                "aweme_url": "https://www.douyin.com/video/a1",
                "asr_status": "dependency_missing",
                "asr_raw_text": "",
                "script_raw_quality": "missing",
            },
            {
                "video_id": "video-3",
                "aweme_id": "a3",
                "aweme_url": "https://www.douyin.com/video/a3",
                "asr_status": "success",
                "asr_raw_text": "asr text",
                "script_raw_quality": "high",
            },
        ],
    )
    _write_csv(
        scripts_outputs / "script_clean.csv",
        [
            "video_id",
            "aweme_id",
            "aweme_url",
            "script_clean_text",
            "script_clean_source",
            "script_clean_status",
            "script_clean_quality",
            "asr_status",
        ],
        [
            {
                "video_id": "video-1",
                "aweme_id": "a1",
                "aweme_url": "https://www.douyin.com/video/a1",
                "script_clean_text": "fallback title text",
                "script_clean_source": "source_clean_title",
                "script_clean_status": "available",
                "script_clean_quality": "medium",
                "asr_status": "dependency_missing",
            },
            {
                "video_id": "video-2",
                "aweme_id": "",
                "aweme_url": "https://www.douyin.com/video/v2",
                "script_clean_text": "fallback desc text",
                "script_clean_source": "source_title_desc",
                "script_clean_status": "available",
                "script_clean_quality": "weak",
                "asr_status": "skipped",
            },
            {
                "video_id": "video-3",
                "aweme_id": "a3",
                "aweme_url": "https://www.douyin.com/video/a3",
                "script_clean_text": "asr text",
                "script_clean_source": "asr_raw",
                "script_clean_status": "available",
                "script_clean_quality": "high",
                "asr_status": "success",
            },
        ],
    )

    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/merge-task/state",
    })
    jsonl_path, csv_path, stats = scraper.build_content_asset(
        search_outputs,
        comments_outputs,
        scripts_outputs,
    )

    assert csv_path.read_bytes()[:3] == b"\xef\xbb\xbf"
    rows = _read_jsonl(jsonl_path)
    by_video = {row["video_id"]: row for row in rows}
    row1 = by_video["video-1"]
    assert row1["valid_comment_count"] == 2
    assert row1["top_valid_comments"] == "valid one|valid two"
    assert row1["comment_pain_tags"] == "line|mirror|nervous"
    assert row1["comment_data_status"] == "available"
    assert row1["script_source_status"] == "available"
    assert row1["script_source_quality"] == "medium"
    assert row1["script_clean_text"] == "fallback title text"
    assert row1["script_clean_source"] == "source_clean_title"
    assert row1["script_clean_quality"] == "medium"
    assert row1["asr_data_status"] == "dependency_missing"
    assert row1["asset_quality"] != "high"

    row2 = by_video["video-2"]
    assert row2["aweme_id"] == ""
    assert row2["clean_title"] == "clean two"
    assert row2["script_clean_text"] == "fallback desc text"
    assert row2["script_clean_source"] == "source_title_desc"
    assert row2["asr_data_status"] == "fallback_desc"
    assert row2["comment_data_status"] == "empty"

    row3 = by_video["video-3"]
    assert row3["valid_comment_count"] == 1
    assert row3["script_clean_source"] == "asr_raw"
    assert row3["asr_data_status"] == "available"
    assert row3["asset_quality"] == "high"

    assert stats["rows_in"] == 3
    assert stats["rows_out"] == 3
    assert stats["comments_available"] == 2
    assert stats["valid_comments_total"] == 3
    assert stats["asr_available"] == 1
    assert stats["fallback_script_total"] == 1
    assert stats["missing_script_total"] == 0
    assert stats["content_asset_csv_generated"] is True
