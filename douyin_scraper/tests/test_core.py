"""
douyin_scraper.tests.test_core — DouyinScraper 核心测试
=======================================================

覆盖：
  1. 配置初始化和验证
  2. 状态管理（三态转换、reset、去重）
  3. 错误分类
  4. 安全文件写入
  5. 重试装饰器（指数退避 + 随机抖动）
  6. 幂等键缺失伪 ID 生成
  7. ensure_dir_writable
  8. check_disk_space_enforced
  9. 日志轮转
  10. setup_ffmpeg RuntimeError 降级

★ 不依赖外部网络（mock 网络请求）★
★ 不依赖全局变量（通过实例属性注入临时目录）★
"""

import asyncio
import csv
import json
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from douyin_scraper import DouyinScraper
from douyin_scraper.config import ScraperConfig
from douyin_scraper.exceptions import (
    ConfigError,
    FatalError,
    NonRetryableError,
    RetryableError,
)
from douyin_scraper.state import StateManager
from douyin_scraper.utils import (
    EXIT_FATAL,
    EXIT_NON_RETRYABLE,
    EXIT_RETRYABLE,
    append_record,
    check_disk_space_enforced,
    classify_error,
    ensure_dir_writable,
    retry,
    safe_write_line,
    setup_log_rotation,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def state_mgr(tmp_path: Path) -> StateManager:
    """创建临时目录下的 StateManager"""
    return StateManager(tmp_path / "state")


@pytest.fixture
def fallback_dir(tmp_path: Path) -> Path:
    return tmp_path / "fallback"


# ═══════════════════════════════════════════════════════════════
# 1. 配置测试
# ═══════════════════════════════════════════════════════════════

def test_config_from_dict() -> None:
    config = ScraperConfig({
        "project_dir": "/tmp/test",
        "keywords": ["test"],
        "log_level": "DEBUG",
    })
    assert config.project_dir == Path("/tmp/test")
    assert config.keywords == ["test"]
    assert config.log_level == "DEBUG"


def test_config_validate_ok() -> None:
    config = ScraperConfig({"project_dir": "/tmp/test"})
    config.validate()  # 不应抛异常


def test_config_validate_bad_ffmpeg_backend() -> None:
    config = ScraperConfig({
        "project_dir": "/tmp/test",
        "ffmpeg_backend": "invalid",
    })
    with pytest.raises(ConfigError, match="ffmpeg_backend"):
        config.validate()


def test_config_env_vars(tmp_path: Path) -> None:
    """环境变量 DOUYIN_SCRAPER_ 前缀可覆盖配置"""
    # Windows 环境变量有长度限制，用 os.environ 直接设置更安全
    import os
    original = os.environ.get("DOUYIN_SCRAPER_LOG_LEVEL")
    try:
        os.environ["DOUYIN_SCRAPER_LOG_LEVEL"] = "DEBUG"
        config = ScraperConfig({"project_dir": str(tmp_path)})
        assert config.log_level == "DEBUG"
    finally:
        if original is not None:
            os.environ["DOUYIN_SCRAPER_LOG_LEVEL"] = original
        else:
            os.environ.pop("DOUYIN_SCRAPER_LOG_LEVEL", None)


# ═══════════════════════════════════════════════════════════════
# 2. 状态管理测试
# ═══════════════════════════════════════════════════════════════

def test_state_transitions(state_mgr: StateManager) -> None:
    """三态转换: pending → in_progress → completed/failed"""
    step = "test_step"
    assert state_mgr.get_step_status(step) == "pending"

    state_mgr.mark_step_started(step)
    assert state_mgr.get_step_status(step) == "in_progress"

    state_mgr.mark_step_completed(step, detail="done")
    assert state_mgr.get_step_status(step) == "completed"

    state_mgr.reset_step(step)
    assert state_mgr.get_step_status(step) == "pending"

    state_mgr.mark_step_started(step)
    state_mgr.mark_step_failed(step, error_summary="broke", exit_code=1)
    assert state_mgr.get_step_status(step) == "failed"

    info = state_mgr.get_step_info(step)
    assert info["error_summary"] == "broke"
    assert info["exit_code"] == 1


def test_check_step_ready(state_mgr: StateManager) -> None:
    """completed 和 failed 不应继续执行"""
    step = "test_ready"
    assert state_mgr.check_step_ready(step) is True  # pending

    state_mgr.mark_step_completed(step)
    assert state_mgr.check_step_ready(step) is False  # completed

    state_mgr.reset_step(step)
    state_mgr.mark_step_failed(step, error_summary="err")
    assert state_mgr.check_step_ready(step) is False  # failed


def test_reset_with_clear_dedupe(state_mgr: StateManager) -> None:
    """重置步骤时清除去重索引"""
    step = "test_reset_dedupe"
    state_mgr.mark_step_started(step)
    state_mgr.mark_step_failed(step, error_summary="err")

    state_mgr.mark_written("idx1", "id1")
    state_mgr.mark_written(step, "id2")

    state_mgr.reset_step(step, clear_dedupe=True)
    assert state_mgr.get_step_status(step) == "pending"
    assert not state_mgr.is_duplicate(step, "id2")
    assert state_mgr.is_duplicate("idx1", "id1")  # 其他索引不受影响


def test_load_completed_ids(state_mgr: StateManager, tmp_path: Path) -> None:
    """从 JSONL 加载已完成 ID"""
    filepath = tmp_path / "test.jsonl"
    filepath.write_text(
        '{"aweme_id": "111"}\n'
        '{"aweme_id": "222"}\n'
        'bad line\n'
        '{"aweme_id": "333"}\n',
        encoding="utf-8",
    )
    ids = state_mgr.load_completed_ids_from_jsonl(filepath, "aweme_id")
    assert ids == {"111", "222", "333"}


def test_load_ids_empty_file(state_mgr: StateManager, tmp_path: Path) -> None:
    filepath = tmp_path / "empty.jsonl"
    filepath.write_text("", encoding="utf-8")
    assert state_mgr.load_completed_ids_from_jsonl(filepath, "aweme_id") == set()


def test_load_ids_nonexistent(state_mgr: StateManager, tmp_path: Path) -> None:
    filepath = tmp_path / "nope.jsonl"
    assert state_mgr.load_completed_ids_from_jsonl(filepath, "aweme_id") == set()


def test_generate_pseudo_id() -> None:
    """确定性伪 ID：相同输入必须生成相同结果"""
    record = {"title": "测试视频", "author": "user1"}
    id1 = StateManager.generate_pseudo_id(5, record)
    id2 = StateManager.generate_pseudo_id(5, record)
    assert id1 == id2
    assert id1.startswith("unknown_5_")

    # 不同记录 → 不同 ID
    record2 = {"title": "另一个视频"}
    id3 = StateManager.generate_pseudo_id(5, record2)
    assert id3 != id1


# ═══════════════════════════════════════════════════════════════
# 3. 评论 workspace 输出测试
# ═══════════════════════════════════════════════════════════════

def _legacy_search_title_clean_rule_export(tmp_path: Path) -> None:
    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/search-task/state",
    })
    outputs_dir = tmp_path / "workspaces" / "search-task" / "outputs"
    outputs_dir.mkdir(parents=True)
    source_csv = outputs_dir / "search_result.csv"
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
    rows = [
        {
            "source_keyword": "靠边停车",
            "platform": "douyin",
            "video_id": "v-topic",
            "aweme_id": "v-topic",
            "title": "科三靠边停车保姆级教学 #科目三技巧 #靠边停车技巧 #靠边停车技巧 #学车 #驾考",
            "desc": "30公分看不准，找点总压线，建议收藏 点赞关注",
            "liked_count": "10",
            "collected_count": "3",
            "comment_count": "2",
            "share_count": "1",
            "total_engagement": "16",
            "aweme_url": "https://www.douyin.com/video/v-topic",
        },
        {
            "source_keyword": "压线",
            "platform": "douyin",
            "video_id": "v-line",
            "aweme_id": "v-line",
            "title": "靠边停车老压线怎么办 #压线 #压线 #热门",
            "desc": "防压线技巧",
            "liked_count": "4",
            "collected_count": "1",
            "comment_count": "1",
            "share_count": "0",
            "total_engagement": "6",
            "aweme_url": "https://www.douyin.com/video/v-line",
        },
        {
            "source_keyword": "30公分",
            "platform": "douyin",
            "video_id": "v-30",
            "aweme_id": "v-30",
            "title": "30公分看不准怎么找点 #科目三技巧",
            "desc": "后视镜找点方法",
            "liked_count": "8",
            "collected_count": "2",
            "comment_count": "1",
            "share_count": "1",
            "total_engagement": "12",
            "aweme_url": "https://www.douyin.com/video/v-30",
        },
    ]
    with open(source_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    clean_jsonl, clean_csv, stats = scraper._do_clean_search_titles(source_csv)

    assert stats["rows_in"] == 3
    assert stats["rows_out"] == 3
    assert stats["clean_csv_generated"] is True
    assert clean_csv.read_bytes()[:3] == b"\xef\xbb\xbf"

    jsonl_text = clean_jsonl.read_text(encoding="utf-8")
    assert "科三靠边停车" in jsonl_text
    assert "\\u" not in jsonl_text
    json_rows = [json.loads(line) for line in jsonl_text.splitlines() if line.strip()]
    by_id = {row["aweme_id"]: row for row in json_rows}

    topic_row = by_id["v-topic"]
    assert topic_row["raw_title"] == rows[0]["title"]
    assert topic_row["clean_title"]
    assert "#" not in topic_row["clean_title"]
    assert "科三" in topic_row["clean_title"]
    assert "靠边停车" in topic_row["clean_title"]
    assert topic_row["hashtags"] == ["科目三技巧", "靠边停车技巧"]
    assert topic_row["topic"] == "靠边停车"
    assert topic_row["pain_point"] == "30公分看不准"
    assert topic_row["teaching_angle"] == "找点方法"
    assert "#学车" in topic_row["title_noise_removed"]
    assert "#驾考" in topic_row["title_noise_removed"]

    line_row = by_id["v-line"]
    assert line_row["pain_point"] == "压线"
    assert line_row["teaching_angle"] == "防压线技巧"

    point_row = by_id["v-30"]
    assert point_row["pain_point"] == "30公分看不准"
    assert point_row["teaching_angle"] == "找点方法"

    with open(clean_csv, "r", encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    csv_by_id = {row["aweme_id"]: row for row in csv_rows}
    assert csv_by_id["v-topic"]["hashtags"] == "科目三技巧|靠边停车技巧"
    assert "title_noise_removed" in csv_by_id["v-topic"]


def _legacy_search_generates_title_clean_when_jsonl_already_standard_path(tmp_path: Path) -> None:
    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/search-task/state",
    })
    outputs_dir = tmp_path / "workspaces" / "search-task" / "outputs"
    outputs_dir.mkdir(parents=True)
    result_jsonl = outputs_dir / "search_result.jsonl"
    result_jsonl.write_text(
        json.dumps({
            "aweme_id": "v-same",
            "title": "科三靠边停车30公分看不准 #靠边停车技巧",
            "desc": "找点方法",
            "liked_count": "5",
            "collected_count": "2",
            "comment_count": "1",
            "share_count": "1",
            "aweme_url": "https://www.douyin.com/video/v-same",
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with patch.object(scraper, "_do_search", return_value=result_jsonl):
        output = scraper.search(keywords=["靠边停车"], max_count=1)

    assert output == result_jsonl
    assert (outputs_dir / "search_result.csv").exists()
    assert (outputs_dir / "search_title_clean.jsonl").exists()
    assert (outputs_dir / "search_title_clean.csv").exists()
    paths = scraper.get_paths()
    assert paths["title_clean_jsonl"] == str(outputs_dir / "search_title_clean.jsonl")
    assert paths["title_clean_csv"] == str(outputs_dir / "search_title_clean.csv")
    assert paths["title_clean_stats"]["rows_in"] == 1
    assert paths["title_clean_stats"]["clean_csv_generated"] is True
    assert (outputs_dir / "script_sources.jsonl").exists()
    assert (outputs_dir / "script_sources.csv").exists()
    assert paths["script_sources_jsonl"] == str(outputs_dir / "script_sources.jsonl")
    assert paths["script_sources_csv"] == str(outputs_dir / "script_sources.csv")
    assert paths["script_sources_stats"]["rows_in"] == 1
    assert paths["script_sources_stats"]["script_sources_csv_generated"] is True


def _legacy_script_sources_export_from_search_csv(tmp_path: Path) -> None:
    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/search-task/state",
    })
    outputs_dir = tmp_path / "workspaces" / "search-task" / "outputs"
    outputs_dir.mkdir(parents=True)
    search_csv = outputs_dir / "search_result.csv"
    title_clean_csv = outputs_dir / "search_title_clean.csv"
    search_fields = [
        "source_keyword",
        "platform",
        "video_id",
        "aweme_id",
        "title",
        "desc",
        "aweme_url",
        "video_download_url",
    ]
    with open(search_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=search_fields)
        writer.writeheader()
        writer.writerows([
            {
                "source_keyword": "靠边停车",
                "platform": "douyin",
                "video_id": "v-source-1",
                "aweme_id": "v-source-1",
                "title": "科三靠边停车",
                "desc": "30公分找点防压线",
                "aweme_url": "https://www.douyin.com/video/v-source-1",
                "video_download_url": "https://example.com/video.mp4",
            },
            {
                "source_keyword": "直线行驶",
                "platform": "douyin",
                "video_id": "v-source-2",
                "aweme_id": "v-source-2",
                "title": "直线行驶老跑偏",
                "desc": "",
                "aweme_url": "https://www.douyin.com/video/v-source-2",
                "video_download_url": "",
            },
        ])
    with open(title_clean_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "source_keyword",
            "platform",
            "video_id",
            "aweme_id",
            "clean_title",
            "clean_desc",
            "aweme_url",
        ])
        writer.writeheader()
        writer.writerow({
            "source_keyword": "靠边停车",
            "platform": "douyin",
            "video_id": "v-source-1",
            "aweme_id": "v-source-1",
            "clean_title": "科三靠边停车",
            "clean_desc": "30公分找点与防压线技巧",
            "aweme_url": "https://www.douyin.com/video/v-source-1",
        })

    with patch.object(scraper, "_download_video") as download_mock, \
            patch.object(scraper, "_transcribe_video") as transcribe_mock:
        sources_jsonl, sources_csv, stats = scraper._do_build_script_sources(
            search_csv, search_csv.with_suffix(".jsonl"), title_clean_csv
        )

    download_mock.assert_not_called()
    transcribe_mock.assert_not_called()
    assert stats["rows_in"] == 2
    assert stats["rows_out"] == 2
    assert stats["title_desc_available"] == 2
    assert stats["clean_title_available"] == 1
    assert stats["video_download_available"] == 1
    assert stats["asr_planned"] == 1
    assert stats["script_sources_csv_generated"] is True
    assert sources_csv.read_bytes()[:3] == b"\xef\xbb\xbf"

    jsonl_text = sources_jsonl.read_text(encoding="utf-8")
    assert "科三靠边停车" in jsonl_text
    assert "\\u" not in jsonl_text
    rows = [json.loads(line) for line in jsonl_text.splitlines() if line.strip()]
    by_id = {row["aweme_id"]: row for row in rows}

    first = by_id["v-source-1"]
    assert first["source_title_desc_available"] is True
    assert first["source_title_desc_text"] == "科三靠边停车 30公分找点防压线"
    assert first["source_clean_title_available"] is True
    assert first["source_clean_title_text"] == "科三靠边停车 30公分找点与防压线技巧"
    assert first["source_video_download_available"] is True
    assert first["source_asr_planned"] is True
    assert first["source_ocr_planned"] is False
    assert first["source_subtitle_planned"] is False
    assert first["script_source_quality"] == "medium"

    second = by_id["v-source-2"]
    assert second["source_clean_title_available"] is False
    assert second["source_video_download_available"] is False
    assert second["source_asr_planned"] is False
    assert second["script_source_quality"] == "weak"

    with open(sources_csv, "r", encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    assert csv_rows[0]["source_video_download_available"] == "True"
    assert csv_rows[0]["script_source_quality"] == "medium"


def _legacy_script_sources_fallback_to_search_jsonl(tmp_path: Path) -> None:
    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/search-task/state",
    })
    outputs_dir = tmp_path / "workspaces" / "search-task" / "outputs"
    outputs_dir.mkdir(parents=True)
    missing_csv = outputs_dir / "search_result.csv"
    search_jsonl = outputs_dir / "search_result.jsonl"
    search_jsonl.write_text(
        json.dumps({
            "source_keyword": "视频文案",
            "platform": "douyin",
            "video_id": "v-jsonl",
            "aweme_id": "v-jsonl",
            "title": "",
            "desc": "",
            "aweme_url": "https://www.douyin.com/video/v-jsonl",
            "video_download_url": "https://example.com/v-jsonl.mp4",
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with patch.object(scraper, "_download_video") as download_mock, \
            patch.object(scraper, "_transcribe_video") as transcribe_mock:
        sources_jsonl, sources_csv, stats = scraper._do_build_script_sources(
            missing_csv, search_jsonl, None
        )

    download_mock.assert_not_called()
    transcribe_mock.assert_not_called()
    assert stats["rows_in"] == 1
    assert stats["rows_out"] == 1
    assert stats["title_desc_available"] == 0
    assert stats["clean_title_available"] == 0
    assert stats["video_download_available"] == 1
    assert stats["asr_planned"] == 1
    assert sources_csv.read_bytes()[:3] == b"\xef\xbb\xbf"

    rows = [json.loads(line) for line in sources_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows[0]["source_title_desc_available"] is False
    assert rows[0]["source_video_download_available"] is True
    assert rows[0]["source_asr_planned"] is True
    assert rows[0]["script_source_quality"] == "low"


def _legacy_script_raw_from_script_sources_jsonl_success_and_skips(tmp_path: Path) -> None:
    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/scripts-task/state",
    })
    source_outputs = tmp_path / "workspaces" / "search-task" / "outputs"
    source_outputs.mkdir(parents=True)
    sources_jsonl = source_outputs / "script_sources.jsonl"
    source_rows = [
        {
            "source_keyword": "靠边停车",
            "platform": "douyin",
            "video_id": "raw-1",
            "aweme_id": "raw-1",
            "aweme_url": "https://www.douyin.com/video/raw-1",
            "video_download_url": "https://example.com/raw-1.mp4",
            "source_video_download_available": True,
            "source_asr_planned": True,
        },
        {
            "source_keyword": "靠边停车",
            "platform": "douyin",
            "video_id": "raw-2",
            "aweme_id": "raw-2",
            "aweme_url": "https://www.douyin.com/video/raw-2",
            "video_download_url": "https://example.com/raw-2.mp4",
            "source_video_download_available": True,
            "source_asr_planned": False,
        },
        {
            "source_keyword": "靠边停车",
            "platform": "douyin",
            "video_id": "raw-3",
            "aweme_id": "raw-3",
            "aweme_url": "https://www.douyin.com/video/raw-3",
            "video_download_url": "",
            "source_video_download_available": False,
            "source_asr_planned": True,
        },
    ]
    sources_jsonl.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in source_rows),
        encoding="utf-8",
    )

    with patch("douyin_scraper.core.check_disk_space_enforced"), \
            patch.object(scraper, "_load_script_raw_whisper_model", return_value=(MagicMock(), "", "")), \
            patch.object(scraper, "_download_video", return_value=True) as download_mock, \
            patch.object(scraper, "_transcribe_video", return_value="这是转写文案") as transcribe_mock:
        output = scraper.extract_script_raw(sources_jsonl, None, model="tiny")

    outputs_dir = tmp_path / "workspaces" / "scripts-task" / "outputs"
    raw_jsonl = outputs_dir / "script_raw.jsonl"
    raw_csv = outputs_dir / "script_raw.csv"
    clean_jsonl = outputs_dir / "script_clean.jsonl"
    clean_csv = outputs_dir / "script_clean.csv"
    assert output == raw_jsonl
    assert raw_jsonl.exists()
    assert raw_csv.exists()
    assert clean_jsonl.exists()
    assert clean_csv.exists()
    assert raw_csv.read_bytes()[:3] == b"\xef\xbb\xbf"
    assert clean_csv.read_bytes()[:3] == b"\xef\xbb\xbf"
    download_mock.assert_called_once()
    transcribe_mock.assert_called_once()

    paths = scraper.get_paths()
    assert paths["script_raw_jsonl"] == str(raw_jsonl)
    assert paths["script_raw_csv"] == str(raw_csv)
    assert paths["script_raw_stats"]["rows_in"] == 3
    assert paths["script_raw_stats"]["rows_targeted"] == 1
    assert paths["script_raw_stats"]["download_success"] == 1
    assert paths["script_raw_stats"]["asr_success"] == 1
    assert paths["script_clean_jsonl"] == str(clean_jsonl)
    assert paths["script_clean_csv"] == str(clean_csv)
    assert paths["script_clean_stats"]["rows_in"] == 3
    assert paths["script_clean_stats"]["asr_text_used"] == 1

    jsonl_text = raw_jsonl.read_text(encoding="utf-8")
    assert "这是转写文案" in jsonl_text
    assert "\\u" not in jsonl_text
    rows = [json.loads(line) for line in jsonl_text.splitlines() if line.strip()]
    by_id = {row["aweme_id"]: row for row in rows}

    assert by_id["raw-1"]["download_status"] == "success"
    assert by_id["raw-1"]["asr_status"] == "success"
    assert by_id["raw-1"]["asr_raw_text"] == "这是转写文案"
    assert by_id["raw-1"]["script_raw_quality"] == "high"
    assert "workspaces" in by_id["raw-1"]["local_video_path"]
    assert "tmp" in by_id["raw-1"]["local_video_path"]
    assert by_id["raw-2"]["download_status"] == "skipped"
    assert by_id["raw-2"]["asr_status"] == "skipped"
    assert by_id["raw-3"]["download_status"] == "skipped"
    assert by_id["raw-3"]["asr_status"] == "skipped"

    clean_rows = [
        json.loads(line)
        for line in clean_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    clean_by_id = {row["aweme_id"]: row for row in clean_rows}
    assert clean_by_id["raw-1"]["script_clean_source"] == "asr_raw"
    assert clean_by_id["raw-1"]["script_clean_text"] == "这是转写文案"
    assert clean_by_id["raw-2"]["script_clean_source"] == "missing"


def _legacy_script_raw_fallback_to_csv_download_failed_and_empty_asr(tmp_path: Path) -> None:
    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/scripts-task/state",
    })
    source_outputs = tmp_path / "workspaces" / "search-task" / "outputs"
    source_outputs.mkdir(parents=True)
    sources_csv = source_outputs / "script_sources.csv"
    fieldnames = [
        "source_keyword",
        "platform",
        "video_id",
        "aweme_id",
        "aweme_url",
        "video_download_url",
        "source_video_download_available",
        "source_asr_planned",
    ]
    with open(sources_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([
            {
                "source_keyword": "科三",
                "platform": "douyin",
                "video_id": "csv-1",
                "aweme_id": "csv-1",
                "aweme_url": "https://www.douyin.com/video/csv-1",
                "video_download_url": "https://example.com/csv-1.mp4",
                "source_video_download_available": "True",
                "source_asr_planned": "True",
            },
            {
                "source_keyword": "科三",
                "platform": "douyin",
                "video_id": "csv-2",
                "aweme_id": "csv-2",
                "aweme_url": "https://www.douyin.com/video/csv-2",
                "video_download_url": "https://example.com/csv-2.mp4",
                "source_video_download_available": "True",
                "source_asr_planned": "True",
            },
        ])

    with patch("douyin_scraper.core.check_disk_space_enforced"), \
            patch.object(scraper, "_load_script_raw_whisper_model", return_value=(MagicMock(), "", "")), \
            patch.object(scraper, "_download_video", side_effect=[False, True]) as download_mock, \
            patch.object(scraper, "_transcribe_video", return_value="") as transcribe_mock:
        raw_jsonl, raw_csv, stats = scraper._do_build_script_raw(
            script_sources_jsonl=None,
            script_sources_csv=sources_csv,
            model_name="tiny",
        )

    assert download_mock.call_count == 2
    transcribe_mock.assert_called_once()
    assert stats["rows_in"] == 2
    assert stats["rows_targeted"] == 2
    assert stats["download_failed"] == 1
    assert stats["download_success"] == 1
    assert stats["asr_empty_text"] == 1
    assert stats["rows_out"] == 2
    assert stats["script_raw_csv_generated"] is True
    assert raw_csv.read_bytes()[:3] == b"\xef\xbb\xbf"

    rows = [json.loads(line) for line in raw_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {row["aweme_id"]: row for row in rows}
    assert by_id["csv-1"]["download_status"] == "failed"
    assert by_id["csv-1"]["download_error"] == "download_failed"
    assert by_id["csv-1"]["asr_status"] == "skipped"
    assert by_id["csv-2"]["download_status"] == "success"
    assert by_id["csv-2"]["asr_status"] == "empty_text"
    assert by_id["csv-2"]["script_raw_quality"] == "low"


def _legacy_script_raw_dependency_missing_does_not_download(tmp_path: Path) -> None:
    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/scripts-task/state",
    })
    source_outputs = tmp_path / "workspaces" / "search-task" / "outputs"
    source_outputs.mkdir(parents=True)
    sources_jsonl = source_outputs / "script_sources.jsonl"
    sources_jsonl.write_text(
        json.dumps({
            "source_keyword": "依赖缺失",
            "platform": "douyin",
            "video_id": "dep-1",
            "aweme_id": "dep-1",
            "aweme_url": "https://www.douyin.com/video/dep-1",
            "video_download_url": "https://example.com/dep-1.mp4",
            "source_video_download_available": True,
            "source_asr_planned": True,
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with patch("douyin_scraper.core.check_disk_space_enforced"), \
            patch.object(
                scraper,
                "_load_script_raw_whisper_model",
                return_value=(None, "dependency_missing", "faster-whisper 未安装"),
            ), \
            patch.object(scraper, "_download_video") as download_mock, \
            patch.object(scraper, "_transcribe_video") as transcribe_mock:
        raw_jsonl, raw_csv, stats = scraper._do_build_script_raw(sources_jsonl, None, "tiny")

    download_mock.assert_not_called()
    transcribe_mock.assert_not_called()
    assert stats["rows_in"] == 1
    assert stats["rows_targeted"] == 1
    assert stats["asr_dependency_missing"] == 1
    assert stats["download_success"] == 0
    assert raw_csv.read_bytes()[:3] == b"\xef\xbb\xbf"
    row = json.loads(raw_jsonl.read_text(encoding="utf-8").strip())
    assert row["download_status"] == "skipped"
    assert row["asr_status"] == "dependency_missing"
    assert row["asr_error"] == "faster-whisper 未安装"
    assert row["script_raw_quality"] == "missing"


def _legacy_script_clean_priority_from_raw_sources_and_title_clean(tmp_path: Path) -> None:
    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/scripts-task/state",
    })
    source_outputs = tmp_path / "workspaces" / "search-task" / "outputs"
    current_outputs = tmp_path / "workspaces" / "scripts-task" / "outputs"
    source_outputs.mkdir(parents=True)
    current_outputs.mkdir(parents=True)

    sources_jsonl = source_outputs / "script_sources.jsonl"
    raw_jsonl = current_outputs / "script_raw.jsonl"
    title_clean_csv = source_outputs / "search_title_clean.csv"

    source_rows = [
        {
            "source_keyword": "parking",
            "platform": "douyin",
            "video_id": "asr-1",
            "aweme_id": "asr-1",
            "aweme_url": "https://www.douyin.com/video/asr-1",
            "source_clean_title_text": "clean title should lose",
            "source_title_desc_text": "raw title should lose",
        },
        {
            "source_keyword": "parking",
            "platform": "douyin",
            "video_id": "source-clean-1",
            "aweme_id": "source-clean-1",
            "aweme_url": "https://www.douyin.com/video/source-clean-1",
            "source_clean_title_text": "source clean title text",
            "source_title_desc_text": "source raw title text",
        },
        {
            "source_keyword": "parking",
            "platform": "douyin",
            "video_id": "title-clean-1",
            "aweme_id": "title-clean-1",
            "aweme_url": "https://www.douyin.com/video/title-clean-1",
            "source_clean_title_text": "",
            "source_title_desc_text": "title clean fallback should win over raw",
        },
        {
            "source_keyword": "parking",
            "platform": "douyin",
            "video_id": "title-desc-1",
            "aweme_id": "title-desc-1",
            "aweme_url": "https://www.douyin.com/video/title-desc-1",
            "source_clean_title_text": "",
            "source_title_desc_text": "source title desc text",
        },
        {
            "source_keyword": "parking",
            "platform": "douyin",
            "video_id": "missing-1",
            "aweme_id": "missing-1",
            "aweme_url": "https://www.douyin.com/video/missing-1",
            "source_clean_title_text": "",
            "source_title_desc_text": "",
        },
    ]
    sources_jsonl.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in source_rows),
        encoding="utf-8",
    )

    raw_rows = [
        {
            "source_keyword": "parking",
            "platform": "douyin",
            "video_id": "asr-1",
            "aweme_id": "asr-1",
            "aweme_url": "https://www.douyin.com/video/asr-1",
            "asr_status": "success",
            "asr_raw_text": "asr text wins",
            "script_raw_quality": "high",
        },
        {
            "source_keyword": "parking",
            "platform": "douyin",
            "video_id": "source-clean-1",
            "aweme_id": "source-clean-1",
            "aweme_url": "https://www.douyin.com/video/source-clean-1",
            "asr_status": "dependency_missing",
            "asr_raw_text": "",
            "script_raw_quality": "missing",
        },
        {
            "source_keyword": "parking",
            "platform": "douyin",
            "video_id": "title-clean-1",
            "aweme_id": "title-clean-1",
            "aweme_url": "https://www.douyin.com/video/title-clean-1",
            "asr_status": "skipped",
            "asr_raw_text": "",
            "script_raw_quality": "missing",
        },
    ]
    raw_jsonl.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in raw_rows),
        encoding="utf-8",
    )

    with open(title_clean_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "source_keyword",
            "platform",
            "video_id",
            "aweme_id",
            "clean_title",
            "clean_desc",
            "aweme_url",
        ])
        writer.writeheader()
        writer.writerow({
            "source_keyword": "parking",
            "platform": "douyin",
            "video_id": "title-clean-1",
            "aweme_id": "title-clean-1",
            "clean_title": "title clean csv title",
            "clean_desc": "title clean csv desc",
            "aweme_url": "https://www.douyin.com/video/title-clean-1",
        })

    clean_jsonl, clean_csv, stats = scraper._do_build_script_clean(
        script_sources_jsonl=sources_jsonl,
        script_sources_csv=None,
        script_raw_jsonl=raw_jsonl,
        script_raw_csv=None,
        title_clean_csv=title_clean_csv,
    )

    assert stats["rows_in"] == 5
    assert stats["script_raw_rows"] == 3
    assert stats["rows_out"] == 5
    assert stats["asr_text_used"] == 1
    assert stats["clean_title_used"] == 2
    assert stats["title_desc_used"] == 1
    assert stats["missing"] == 1
    assert stats["script_clean_csv_generated"] is True
    assert clean_csv.read_bytes()[:3] == b"\xef\xbb\xbf"

    rows = [
        json.loads(line)
        for line in clean_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {row["aweme_id"]: row for row in rows}
    assert by_id["asr-1"]["script_clean_source"] == "asr_raw"
    assert by_id["asr-1"]["script_clean_text"] == "asr text wins"
    assert by_id["source-clean-1"]["script_clean_source"] == "source_clean_title"
    assert by_id["source-clean-1"]["script_clean_text"] == "source clean title text"
    assert by_id["title-clean-1"]["script_clean_source"] == "source_clean_title"
    assert by_id["title-clean-1"]["script_clean_text"] == "title clean csv title title clean csv desc"
    assert by_id["title-desc-1"]["script_clean_source"] == "source_title_desc"
    assert by_id["title-desc-1"]["script_clean_text"] == "source title desc text"
    assert by_id["missing-1"]["script_clean_source"] == "missing"
    assert by_id["missing-1"]["script_clean_status"] == "missing"


def _legacy_comments_raw_csv_export(tmp_path: Path) -> None:
    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/comments-task/state",
    })
    outputs_dir = tmp_path / "workspaces" / "comments-task" / "outputs"
    outputs_dir.mkdir(parents=True)
    jsonl_path = outputs_dir / "comments_raw.jsonl"
    csv_path = outputs_dir / "comments_raw.csv"
    jsonl_path.write_text(
        json.dumps({
            "source_keyword": "测试",
            "platform": "douyin",
            "source_task_id": "search-task",
            "video_id": "7604453470036918193",
            "aweme_id": "7604453470036918193",
            "aweme_url": "https://www.douyin.com/video/7604453470036918193",
            "comment_id": "cid-1",
            "parent_comment_id": "0",
            "user_id": "uid-1",
            "nickname": "昵称",
            "content": "不错",
            "liked_count": "7",
            "reply_count": "2",
            "create_time": "1710000000",
            "ip_location": "北京",
            "raw_comment": {"cid": "cid-1"},
            "crawl_time": "2026-06-16T00:00:00Z",
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    stats = scraper._convert_comments_jsonl_to_csv(jsonl_path, csv_path, videos_in=1)

    assert stats["videos_in"] == 1
    assert stats["videos_success"] == 1
    assert stats["comments_out"] == 1
    assert stats["comments_csv_generated"] is True
    assert stats["errors"] == []
    assert csv_path.read_bytes()[:3] == b"\xef\xbb\xbf"
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["liked_count"] == "7"
    assert rows[0]["reply_count"] == "2"
    assert rows[0]["content"] == "不错"


def _legacy_comments_clean_rule_export(tmp_path: Path) -> None:
    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/comments-task/state",
    })
    outputs_dir = tmp_path / "workspaces" / "comments-task" / "outputs"
    outputs_dir.mkdir(parents=True)
    raw_jsonl = outputs_dir / "comments_raw.jsonl"

    def raw(content: str, comment_id: str) -> dict:
        return {
            "source_keyword": "靠边停车",
            "platform": "douyin",
            "source_task_id": "search-task",
            "video_id": "7604453470036918193",
            "aweme_id": "7604453470036918193",
            "aweme_url": "https://www.douyin.com/video/7604453470036918193",
            "comment_id": comment_id,
            "content": content,
            "liked_count": "1",
            "reply_count": "0",
            "create_time": "1710000000",
            "crawl_time": "2026-06-16T00:00:00Z",
        }

    records = [
        raw("", "empty"),
        raw("😂😂", "emoji"),
        raw("666", "six"),
        raw("哈哈", "haha"),
        raw("加V 领取资料", "contact"),
        raw("30公分看不准", "pain-30"),
        raw("靠边停车老压线", "pain-line"),
        raw("靠边停车老压线", "dup-line"),
        raw("后视镜怎么看", "mirror-question"),
    ]
    raw_jsonl.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records),
        encoding="utf-8",
    )

    clean_jsonl, clean_csv, stats = scraper._do_clean_comments(raw_jsonl)

    assert stats["comments_in"] == len(records)
    assert stats["comments_valid"] == 3
    assert stats["comments_invalid"] == 6
    assert stats["duplicates_removed"] == 1
    assert stats["clean_csv_generated"] is True
    assert clean_csv.read_bytes()[:3] == b"\xef\xbb\xbf"
    clean_text = clean_jsonl.read_text(encoding="utf-8")
    assert "30公分看不准" in clean_text
    assert "\\u" not in clean_text

    clean_rows = [json.loads(line) for line in clean_text.splitlines() if line.strip()]
    by_id = {row["comment_id"]: row for row in clean_rows}
    assert by_id["empty"]["invalid_reason"] == "empty_comment"
    assert by_id["emoji"]["invalid_reason"] == "emoji_only"
    assert by_id["six"]["invalid_reason"] == "meaningless"
    assert by_id["haha"]["invalid_reason"] == "meaningless"
    assert by_id["contact"]["invalid_reason"] == "contact_spam"
    assert by_id["dup-line"]["invalid_reason"] == "duplicate"
    assert by_id["pain-30"]["is_valid"] is True
    assert "30公分" in by_id["pain-30"]["pain_tags"]
    assert "看点不准" in by_id["pain-30"]["pain_tags"]
    assert by_id["pain-line"]["is_valid"] is True
    assert "压线" in by_id["pain-line"]["pain_tags"]
    assert by_id["mirror-question"]["is_valid"] is True
    assert by_id["mirror-question"]["intent_type"] == "question"

    with open(clean_csv, "r", encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    csv_by_id = {row["comment_id"]: row for row in csv_rows}
    assert "30公分" in csv_by_id["pain-30"]["pain_tags"]
    assert "看点不准" in csv_by_id["pain-30"]["pain_tags"]


def _legacy_fetch_comments_writes_workspace_outputs(tmp_path: Path) -> None:
    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/comments-task/state",
    })
    (tmp_path / "crawl_comments_v2.py").write_text("# test stub\n", encoding="utf-8")
    source_outputs = tmp_path / "workspaces" / "search-task" / "outputs"
    source_outputs.mkdir(parents=True)
    source_csv = source_outputs / "search_result.csv"
    source_csv.write_text(
        "\ufeffsource_keyword,platform,video_id,aweme_id,aweme_url\n"
        "测试,douyin,7604453470036918193,7604453470036918193,https://www.douyin.com/video/7604453470036918193\n",
        encoding="utf-8",
    )

    def fake_run(cmd, **kwargs):
        output_path = Path(cmd[cmd.index("--output") + 1])
        output_path.write_text(
            json.dumps({
                "source_keyword": "测试",
                "platform": "douyin",
                "source_task_id": "search-task",
                "video_id": "7604453470036918193",
                "aweme_id": "7604453470036918193",
                "aweme_url": "https://www.douyin.com/video/7604453470036918193",
                "comment_id": "cid-1",
                "parent_comment_id": "0",
                "user_id": "uid-1",
                "sec_uid": "sec-1",
                "nickname": "昵称",
                "content": "原始评论",
                "liked_count": 3,
                "reply_count": 1,
                "create_time": "1710000000",
                "ip_location": "上海",
                "raw_comment": {"cid": "cid-1"},
                "crawl_time": "2026-06-16T00:00:00Z",
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return MagicMock(returncode=0)

    with patch("douyin_scraper.core.subprocess.run", side_effect=fake_run) as run_mock:
        output = scraper.fetch_comments(
            video_jsonl=source_csv,
            source_task_id="search-task",
            max_comments_per_video=50,
        )

    outputs_dir = tmp_path / "workspaces" / "comments-task" / "outputs"
    assert output == outputs_dir / "comments_raw.jsonl"
    assert (outputs_dir / "comments_raw.csv").exists()
    assert (outputs_dir / "comments_raw.csv").read_bytes()[:3] == b"\xef\xbb\xbf"
    cmd = run_mock.call_args.args[0]
    assert "--input" in cmd
    assert str(source_csv) in cmd
    assert "--output" in cmd
    assert str(outputs_dir / "comments_raw.jsonl") in cmd
    paths = scraper.get_paths()
    assert paths["comments_raw_jsonl"] == str(outputs_dir / "comments_raw.jsonl")
    assert paths["comments_raw_csv"] == str(outputs_dir / "comments_raw.csv")
    assert paths["comments_clean_jsonl"] == str(outputs_dir / "comments_clean.jsonl")
    assert paths["comments_clean_csv"] == str(outputs_dir / "comments_clean.csv")
    assert paths["comments_stats"]["comments_out"] == 1
    assert paths["clean_stats"]["comments_in"] == 1
    assert paths["clean_stats"]["clean_csv_generated"] is True


def _legacy_fetch_comments_subprocess_failure_keeps_outputs(tmp_path: Path) -> None:
    scraper = DouyinScraper({
        "project_dir": str(tmp_path),
        "state_dir_name": "workspaces/comments-task/state",
    })
    (tmp_path / "crawl_comments_v2.py").write_text("# test stub\n", encoding="utf-8")
    source_csv = tmp_path / "search_result.csv"
    source_csv.write_text(
        "\ufeffsource_keyword,platform,video_id,aweme_id,aweme_url\n"
        "测试,douyin,7604453470036918193,7604453470036918193,https://www.douyin.com/video/7604453470036918193\n",
        encoding="utf-8",
    )

    with patch(
        "douyin_scraper.core.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, ["python", "crawl_comments_v2.py"]),
    ):
        output = scraper.fetch_comments(
            video_jsonl=source_csv,
            source_task_id="search-task",
            max_comments_per_video=5,
        )

    outputs_dir = tmp_path / "workspaces" / "comments-task" / "outputs"
    csv_path = outputs_dir / "comments_raw.csv"
    assert output == outputs_dir / "comments_raw.jsonl"
    assert output.exists()
    assert csv_path.exists()
    assert csv_path.read_bytes()[:3] == b"\xef\xbb\xbf"
    assert (outputs_dir / "comments_clean.jsonl").exists()
    assert (outputs_dir / "comments_clean.csv").exists()
    paths = scraper.get_paths()
    stats = paths["comments_stats"]
    assert stats["videos_in"] == 1
    assert stats["comments_out"] == 0
    assert stats["comments_csv_generated"] is True
    assert stats["errors"]
    assert paths["clean_stats"]["comments_in"] == 0
    assert paths["clean_stats"]["clean_csv_generated"] is True


# ═══════════════════════════════════════════════════════════════
# 4. 错误分类测试
# ═══════════════════════════════════════════════════════════════

def test_classify_by_type() -> None:
    assert classify_error(RetryableError("t")) == EXIT_RETRYABLE
    assert classify_error(NonRetryableError("c")) == EXIT_NON_RETRYABLE
    assert classify_error(FatalError("o")) == EXIT_FATAL
    assert classify_error(ConnectionError("r")) == EXIT_RETRYABLE
    assert classify_error(PermissionError("d")) == EXIT_NON_RETRYABLE
    assert classify_error(MemoryError()) == EXIT_FATAL


def test_classify_by_message() -> None:
    assert classify_error(OSError("No space left")) == EXIT_FATAL
    assert classify_error(OSError("connection timeout")) == EXIT_RETRYABLE
    assert classify_error(OSError("HTTP 429")) == EXIT_RETRYABLE
    assert classify_error(ValueError("module not found")) == EXIT_NON_RETRYABLE


# ═══════════════════════════════════════════════════════════════
# 4. 安全文件写入测试
# ═══════════════════════════════════════════════════════════════

def test_append_record_basic(tmp_path: Path, fallback_dir: Path) -> None:
    filepath = tmp_path / "test.jsonl"
    append_record(filepath, {"id": 1}, fallback_dir)
    append_record(filepath, {"id": 2}, fallback_dir)
    lines = filepath.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2


def test_append_record_in_async(tmp_path: Path, fallback_dir: Path) -> None:
    """os.open 在 asyncio 环境中正常工作"""
    filepath = tmp_path / "async.jsonl"

    async def write():
        append_record(filepath, {"id": "async"}, fallback_dir)

    asyncio.run(write())
    lines = filepath.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1


def test_append_record_fallback(tmp_path: Path, fallback_dir: Path) -> None:
    """目标路径不可写时 fallback"""
    impossible = tmp_path / "no" / "such" / "dir" / "test.jsonl"
    result = append_record(impossible, {"id": "fb"}, fallback_dir)
    assert result != impossible
    assert result.exists()


def test_append_record_permission_denied(tmp_path: Path, fallback_dir: Path) -> None:
    """模拟第一次 os.open 失败，第二次成功"""
    fallback_dir.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "readonly" / "test.jsonl"
    target.parent.mkdir()

    real_os_open = os.open
    call_count = {"n": 0}

    def side_effect(*args: object, **kwargs: object) -> int:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise PermissionError("denied")
        return real_os_open(*args, **kwargs)  # type: ignore[arg-type]

    with patch("douyin_scraper.utils.os.open", side_effect=side_effect):
        result = append_record(target, {"id": "perm"}, fallback_dir)

    assert result != target
    assert result.exists()


# ═══════════════════════════════════════════════════════════════
# 5. 重试装饰器测试
# ═══════════════════════════════════════════════════════════════

def test_retry_delay_with_jitter() -> None:
    """指数退避 + 随机抖动"""
    call_times: list = []

    @retry(max_retries=3, base_delay=0.1, backoff_factor=2,
           retryable_exceptions=(ValueError,))
    def flaky() -> str:
        call_times.append(time.time())
        if len(call_times) < 3:
            raise ValueError("not yet")
        return "ok"

    result = flaky()
    assert result == "ok"
    assert len(call_times) == 3


def test_retry_max_exceeded() -> None:
    @retry(max_retries=2, base_delay=0.01,
           retryable_exceptions=(ConnectionError,))
    def always_fail() -> None:
        raise ConnectionError("timeout")

    with pytest.raises(ConnectionError):
        always_fail()


def test_retry_non_retryable_not_retried() -> None:
    attempts: list = []

    @retry(max_retries=3, base_delay=0.01,
           retryable_exceptions=(ConnectionError,))
    def config_err() -> None:
        attempts.append(1)
        raise NonRetryableError("config")

    with pytest.raises(NonRetryableError):
        config_err()
    assert len(attempts) == 1


# ═══════════════════════════════════════════════════════════════
# 6. ensure_dir_writable 测试
# ═══════════════════════════════════════════════════════════════

def test_ensure_dir_writable_normal(tmp_path: Path, fallback_dir: Path) -> None:
    target = tmp_path / "writable"
    result = ensure_dir_writable(target, fallback_dir)
    assert result == target
    assert target.exists()


def test_ensure_dir_writable_fallback(tmp_path: Path, fallback_dir: Path) -> None:
    target = tmp_path / "nowhere" / "deep"
    real_mkdir = Path.mkdir

    def side_effect(self: Path, *args: object, **kwargs: object) -> None:
        if "nowhere" in str(self):
            raise PermissionError("denied")
        return real_mkdir(self, *args, **kwargs)  # type: ignore[arg-type]

    with patch.object(Path, "mkdir", side_effect):
        result = ensure_dir_writable(target, fallback_dir)
    assert result == fallback_dir


# ═══════════════════════════════════════════════════════════════
# 7. check_disk_space_enforced 测试
# ═══════════════════════════════════════════════════════════════

def test_disk_space_normal(tmp_path: Path) -> None:
    check_disk_space_enforced(tmp_path, min_gb=0.001)


def test_disk_space_insufficient(tmp_path: Path) -> None:
    from collections import namedtuple
    Usage = namedtuple("Usage", ["total", "used", "free"])

    with patch("douyin_scraper.utils.shutil.disk_usage",
               return_value=Usage(total=100, used=99, free=1)):
        with pytest.raises(FatalError, match="磁盘空间不足"):
            check_disk_space_enforced(tmp_path, min_gb=1.0)


# ═══════════════════════════════════════════════════════════════
# 8. 日志轮转测试
# ═══════════════════════════════════════════════════════════════

def test_log_rotation(tmp_path: Path) -> None:
    log_path = tmp_path / "rotation.jsonl"
    handler = setup_log_rotation(log_path, max_bytes=1024, backup_count=3)
    assert handler.maxBytes == 1024

    import logging
    logger = logging.getLogger("douyin_scraper")
    logger.removeHandler(handler)
    handler.close()


# ═══════════════════════════════════════════════════════════════
# 9. setup_ffmpeg 降级测试
# ═══════════════════════════════════════════════════════════════

def test_setup_ffmpeg_runtime_error() -> None:
    """imageio_ffmpeg.get_ffmpeg_exe() 抛 RuntimeError 时降级"""
    from douyin_scraper.utils import setup_ffmpeg

    mock_mod = MagicMock()
    mock_mod.get_ffmpeg_exe = MagicMock(side_effect=RuntimeError("not found"))

    with patch.dict("sys.modules", {"imageio_ffmpeg": mock_mod}):
        with patch("douyin_scraper.utils.check_command_exists", return_value=False):
            assert setup_ffmpeg() is False


# ═══════════════════════════════════════════════════════════════
# 10. 异常属性测试
# ═══════════════════════════════════════════════════════════════

def test_exception_attributes() -> None:
    e = RetryableError("timeout", step="download", details={"url": "http://x"})
    assert e.step == "download"
    assert e.exit_code == 1
    assert e.details == {"url": "http://x"}

    e2 = ConfigError("missing key", step="config")
    assert e2.exit_code == 2

    e3 = FatalError("disk full", step="extract")
    assert e3.exit_code == 3
