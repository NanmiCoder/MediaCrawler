import csv
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from douyin_scraper import DouyinScraper


def _scraper(tmp_path: Path) -> DouyinScraper:
    return DouyinScraper(
        {
            "project_dir": str(tmp_path),
            "state_dir_name": "workspaces/comments-task/state",
        }
    )


def _comment(comment_id: str, content: str) -> dict:
    return {
        "source_keyword": "靠边停车",
        "platform": "douyin",
        "source_task_id": "search-task",
        "video_id": "video-1",
        "aweme_id": "video-1",
        "aweme_url": "https://www.douyin.com/video/video-1",
        "comment_id": comment_id,
        "content": content,
        "liked_count": "7",
        "reply_count": "2",
        "create_time": "1710000000",
        "crawl_time": "2026-06-16T00:00:00Z",
    }


def _source_csv(tmp_path: Path) -> Path:
    source = tmp_path / "search_result.csv"
    source.write_text(
        "\ufeffsource_keyword,platform,video_id,aweme_id,aweme_url\n"
        "停车,douyin,video-1,video-1,https://www.douyin.com/video/video-1\n",
        encoding="utf-8",
    )
    return source


def test_comments_raw_csv_export(tmp_path: Path) -> None:
    scraper = _scraper(tmp_path)
    jsonl_path = tmp_path / "comments_raw.jsonl"
    csv_path = tmp_path / "comments_raw.csv"
    jsonl_path.write_text(
        json.dumps(_comment("comment-1", "这个方法很实用"), ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    stats = scraper._convert_comments_jsonl_to_csv(
        jsonl_path,
        csv_path,
        videos_in=1,
    )

    assert stats["videos_in"] == 1
    assert stats["videos_success"] == 1
    assert stats["comments_out"] == 1
    assert stats["comments_csv_generated"] is True
    assert csv_path.read_bytes()[:3] == b"\xef\xbb\xbf"
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["content"] == "这个方法很实用"
    assert row["liked_count"] == "7"


def test_comments_clean_rule_export(tmp_path: Path) -> None:
    scraper = _scraper(tmp_path)
    raw_jsonl = tmp_path / "comments_raw.jsonl"
    records = [
        _comment("empty", ""),
        _comment("emoji", "😂😂"),
        _comment("pain", "30公分看不准，后视镜怎么看？"),
        _comment("duplicate", "30公分看不准，后视镜怎么看？"),
    ]
    raw_jsonl.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records),
        encoding="utf-8",
    )

    clean_jsonl, clean_csv, stats = scraper._do_clean_comments(raw_jsonl)

    assert stats["comments_in"] == 4
    assert stats["duplicates_removed"] == 1
    assert stats["clean_csv_generated"] is True
    assert clean_csv.read_bytes()[:3] == b"\xef\xbb\xbf"
    rows = [
        json.loads(line)
        for line in clean_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {row["comment_id"]: row for row in rows}
    assert by_id["empty"]["invalid_reason"] == "empty_comment"
    assert by_id["emoji"]["invalid_reason"] == "emoji_only"
    assert by_id["duplicate"]["invalid_reason"] == "duplicate"
    assert by_id["pain"]["is_valid"] is True
    assert by_id["pain"]["intent_type"] == "question"


def test_fetch_comments_writes_workspace_outputs(tmp_path: Path) -> None:
    scraper = _scraper(tmp_path)
    (tmp_path / "crawl_comments_v2.py").write_text("# stub\n", encoding="utf-8")
    source_csv = _source_csv(tmp_path)

    def fake_run(cmd, **kwargs):
        output_path = Path(cmd[cmd.index("--output") + 1])
        output_path.write_text(
            json.dumps(
                _comment("comment-1", "30公分看不准"),
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return MagicMock(returncode=0)

    with patch("douyin_scraper.core.subprocess.run", side_effect=fake_run):
        output = scraper.fetch_comments(
            video_jsonl=source_csv,
            source_task_id="search-task",
            max_comments_per_video=50,
        )

    outputs = tmp_path / "workspaces" / "comments-task" / "outputs"
    assert output == outputs / "comments_raw.jsonl"
    for name in (
        "comments_raw.jsonl",
        "comments_raw.csv",
        "comments_clean.jsonl",
        "comments_clean.csv",
    ):
        assert (outputs / name).exists()
    paths = scraper.get_paths()
    assert paths["comments_raw_jsonl"] == str(outputs / "comments_raw.jsonl")
    assert paths["comments_clean_csv"] == str(outputs / "comments_clean.csv")
    assert paths["comments_stats"]["comments_out"] == 1


def test_fetch_comments_subprocess_failure_keeps_outputs(tmp_path: Path) -> None:
    scraper = _scraper(tmp_path)
    (tmp_path / "crawl_comments_v2.py").write_text("# stub\n", encoding="utf-8")
    source_csv = _source_csv(tmp_path)

    with patch(
        "douyin_scraper.core.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, ["python", "crawl_comments_v2.py"]),
    ):
        output = scraper.fetch_comments(
            video_jsonl=source_csv,
            source_task_id="search-task",
            max_comments_per_video=5,
        )

    outputs = tmp_path / "workspaces" / "comments-task" / "outputs"
    assert output.exists()
    assert (outputs / "comments_raw.csv").read_bytes()[:3] == b"\xef\xbb\xbf"
    assert (outputs / "comments_clean.jsonl").exists()
    assert (outputs / "comments_clean.csv").exists()
    paths = scraper.get_paths()
    assert paths["comments_stats"]["comments_out"] == 0
    assert paths["comments_stats"]["errors"]
