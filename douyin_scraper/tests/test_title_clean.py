import csv
import json
from pathlib import Path
from unittest.mock import patch

from douyin_scraper import DouyinScraper


def _scraper(tmp_path: Path) -> DouyinScraper:
    return DouyinScraper(
        {
            "project_dir": str(tmp_path),
            "state_dir_name": "workspaces/search-task/state",
        }
    )


def test_title_clean_extracts_hashtags_topic_pain_and_angle(
    tmp_path: Path,
) -> None:
    scraper = _scraper(tmp_path)
    search_csv = tmp_path / "search_result.csv"
    fieldnames = [
        "source_keyword",
        "platform",
        "video_id",
        "aweme_id",
        "title",
        "desc",
        "liked_count",
        "collected_count",
        "comment_count",
        "share_count",
        "total_engagement",
        "aweme_url",
    ]
    with open(search_csv, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "source_keyword": "靠边停车",
                "platform": "douyin",
                "video_id": "title-1",
                "aweme_id": "title-1",
                "title": "科三靠边停车30公分看不准 #科目三技巧 #靠边停车技巧 #学车",
                "desc": "后视镜找点方法，建议收藏",
                "liked_count": "10",
                "collected_count": "3",
                "comment_count": "2",
                "share_count": "1",
                "total_engagement": "16",
                "aweme_url": "https://www.douyin.com/video/title-1",
            }
        )

    clean_jsonl, clean_csv, stats = scraper._do_clean_search_titles(search_csv)

    assert stats["rows_in"] == 1
    assert stats["rows_out"] == 1
    assert stats["clean_csv_generated"] is True
    assert clean_csv.read_bytes()[:3] == b"\xef\xbb\xbf"
    row = json.loads(clean_jsonl.read_text(encoding="utf-8").strip())
    assert row["raw_title"]
    assert "#" not in row["clean_title"]
    assert "科目三技巧" in row["hashtags"]
    assert "靠边停车技巧" in row["hashtags"]
    assert row["topic"] == "靠边停车"
    assert row["pain_point"] == "30公分看不准"
    assert row["teaching_angle"] == "找点方法"


def test_search_registers_title_clean_outputs_separately(tmp_path: Path) -> None:
    scraper = _scraper(tmp_path)
    outputs = tmp_path / "workspaces" / "search-task" / "outputs"
    outputs.mkdir(parents=True)
    result_jsonl = outputs / "search_result.jsonl"
    result_jsonl.write_text(
        json.dumps(
            {
                "aweme_id": "title-search-1",
                "title": "科三靠边停车 #靠边停车技巧",
                "desc": "30公分看不准，找点方法",
                "aweme_url": "https://www.douyin.com/video/title-search-1",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with (
        patch.object(scraper, "_do_search", return_value=result_jsonl),
        patch.object(scraper, "_prepare_script_source_outputs"),
    ):
        scraper.search(keywords=["靠边停车"], max_count=1)

    paths = scraper.get_paths()
    assert paths["title_clean_jsonl"] == str(outputs / "search_title_clean.jsonl")
    assert paths["title_clean_csv"] == str(outputs / "search_title_clean.csv")
    assert paths["title_clean_stats"]["rows_out"] == 1
