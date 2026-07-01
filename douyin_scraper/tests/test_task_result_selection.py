import os
from pathlib import Path

import pytest

from api.tasks import TaskManager


def _selected_result(
    tmp_path: Path,
    task_type: str,
    files: tuple[str, ...],
):
    manager = TaskManager(base_dir=str(tmp_path))
    task = manager.create_task(task_type)
    task.status = "completed"
    outputs = Path(task.workspace) / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    base_mtime = 1_700_000_000
    for index, name in enumerate(files):
        output = outputs / name
        output.write_text("value\n", encoding="utf-8")
        timestamp = base_mtime + index
        os.utime(output, (timestamp, timestamp))
    return manager.get_result_path(task.task_id)


@pytest.mark.parametrize("task_type", ["search", "run_all"])
def test_search_selector_prefers_standard_csv(
    tmp_path: Path,
    task_type: str,
) -> None:
    result = _selected_result(
        tmp_path,
        task_type,
        ("search_result.jsonl", "search_result.csv"),
    )
    assert result is not None
    assert result.name == "search_result.csv"


def test_comments_selector_prefers_clean_output(tmp_path: Path) -> None:
    result = _selected_result(
        tmp_path,
        "comments",
        ("comments_raw.csv", "comments_clean.jsonl", "comments_clean.csv"),
    )
    assert result is not None
    assert result.name == "comments_clean.csv"


def test_scripts_selector_prefers_clean_output(tmp_path: Path) -> None:
    result = _selected_result(
        tmp_path,
        "scripts",
        ("script_sources.csv", "script_raw.csv", "script_clean.csv"),
    )
    assert result is not None
    assert result.name == "script_clean.csv"


def test_fallback_selector_uses_newest_supported_file(tmp_path: Path) -> None:
    result = _selected_result(
        tmp_path,
        "custom",
        ("older.csv", "newer.csv"),
    )
    assert result is not None
    assert result.name == "newer.csv"


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        (
            ("douyin_koubo_data.csv", "content_asset.jsonl", "content_asset.csv"),
            "content_asset.csv",
        ),
        (
            ("legacy.csv", "douyin_koubo_data.csv"),
            "douyin_koubo_data.csv",
        ),
    ],
)
def test_merge_selector_prefers_content_asset(
    tmp_path: Path,
    files: tuple[str, ...],
    expected: str,
) -> None:
    result = _selected_result(tmp_path, "merge", files)
    assert result is not None
    assert result.name == expected
