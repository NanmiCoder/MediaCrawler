import csv
import json
from pathlib import Path

from douyin_scraper import DouyinScraper


STANDARD_SEARCH_FIELDS = [
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
    "cover_url",
    "video_download_url",
    "music_download_url",
    "create_time",
    "last_modify_ts",
]


def _scraper(tmp_path: Path) -> DouyinScraper:
    return DouyinScraper(
        {
            "project_dir": str(tmp_path),
            "state_dir_name": "workspaces/search-task/state",
        }
    )


def test_search_writes_standard_workspace_outputs(tmp_path: Path) -> None:
    scraper = _scraper(tmp_path)
    source = tmp_path / "raw-search.jsonl"
    source.write_text(
        json.dumps(
            {
                "aweme_id": "search-1",
                "title": "停车技巧",
                "liked_count": 2,
                "collected_count": 3,
                "comment_count": 4,
                "share_count": 5,
                "aweme_url": "https://www.douyin.com/video/search-1",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    scraper.config.keywords = ["停车"]
    result_jsonl, result_csv = scraper._prepare_standard_search_outputs(source)

    outputs = tmp_path / "workspaces" / "search-task" / "outputs"
    assert result_jsonl == outputs / "search_result.jsonl"
    assert result_csv == outputs / "search_result.csv"
    assert result_jsonl.read_text(encoding="utf-8")
    assert result_csv.exists()
    paths = scraper.get_paths()
    assert paths["video_jsonl"] == str(outputs / "search_result.jsonl")
    assert paths["video_csv"] == str(outputs / "search_result.csv")
    assert paths["csv_stats"]["rows_out"] == 1


def test_standard_search_csv_has_18_fields_bom_dedupe_and_engagement(
    tmp_path: Path,
) -> None:
    scraper = _scraper(tmp_path)
    source = tmp_path / "search_result.jsonl"
    target = tmp_path / "search_result.csv"
    records = [
        {
            "aweme_id": "id-1",
            "title": "first",
            "liked_count": "10",
            "collected_count": "3",
            "comment_count": "2",
            "share_count": "1",
            "aweme_url": "https://www.douyin.com/video/id-1",
        },
        {
            "aweme_id": "id-1",
            "title": "duplicate id",
            "aweme_url": "https://www.douyin.com/video/other",
        },
        {
            "title": "url only",
            "liked_count": "bad",
            "collected_count": 1,
            "comment_count": 2,
            "share_count": 3,
            "aweme_url": "https://www.douyin.com/video/url-only",
        },
        {
            "title": "duplicate url",
            "aweme_url": "https://www.douyin.com/video/url-only",
        },
    ]
    source.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records),
        encoding="utf-8",
    )

    stats = scraper._convert_jsonl_to_standard_csv(
        str(source),
        str(target),
        source_keyword="停车",
    )

    assert stats == {
        "rows_in": 4,
        "rows_out": 2,
        "duplicates_removed": 2,
        "csv_generated": True,
        "csv_error": None,
    }
    assert target.read_bytes()[:3] == b"\xef\xbb\xbf"
    with open(target, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert reader.fieldnames == STANDARD_SEARCH_FIELDS
    assert len(rows) == 2
    assert rows[0]["source_keyword"] == "停车"
    assert rows[0]["total_engagement"] == "16"
    assert rows[1]["total_engagement"] == "6"
