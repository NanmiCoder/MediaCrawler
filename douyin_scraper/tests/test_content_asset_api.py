import asyncio
import csv
import io
from pathlib import Path
from typing import Dict

from api.routes import (
    ExportRequest,
    data_export_download,
    export_data,
    get_result,
    preview_data,
    set_task_manager,
)
from api.tasks import TaskManager


def _create_completed_task(
    tmp_path: Path,
    task_type: str,
    files: Dict[str, bytes],
):
    manager = TaskManager(base_dir=str(tmp_path))
    task = manager.create_task(task_type)
    task.status = "completed"
    outputs = Path(task.workspace) / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (outputs / name).write_bytes(content)
    return manager, task


def test_content_asset_result_preview_and_exports(tmp_path: Path) -> None:
    source = (
        "video_id,platform,script_clean_text,liked_count,collected_count,"
        "share_count,comment_count,asset_quality\n"
        "video-1,douyin,clean script,11,12,13,14,partial\n"
    ).encode("utf-8-sig")
    manager, task = _create_completed_task(
        tmp_path,
        "merge",
        {
            "content_asset.csv": source,
            "content_asset.jsonl": b'{"video_id":"jsonl-fallback"}\n',
        },
    )
    set_task_manager(manager)

    result_response = asyncio.run(get_result(task.task_id))
    preview = asyncio.run(preview_data(task.task_id, limit=1))
    export_response = asyncio.run(data_export_download(task.task_id))
    batch_response = asyncio.run(
        export_data(ExportRequest(task_ids=[task.task_id], format="csv", limit=10))
    )

    assert Path(result_response.path).name == "content_asset.csv"
    assert preview["file_name"] == "content_asset.csv"
    assert preview["format"] == "csv"
    assert preview["total_rows"] == 1
    assert preview["rows"][0]["script_clean_text"] == "clean script"
    assert Path(export_response.path).read_bytes() == source
    assert source.startswith(b"\xef\xbb\xbf")
    assert batch_response.body.startswith(b"\xef\xbb\xbf")

    rows = list(
        csv.DictReader(io.StringIO(batch_response.body.decode("utf-8-sig")))
    )
    assert rows == [
        {
            "video_id": "video-1",
            "platform": "douyin",
            "script_text": "clean script",
            "likes": "11",
            "favorites": "12",
            "shares": "13",
            "comments": "14",
        }
    ]


def test_preview_jsonl_fallback_uses_shared_selector(tmp_path: Path) -> None:
    manager, task = _create_completed_task(
        tmp_path,
        "merge",
        {
            "content_asset.jsonl": (
                '{"video_id":"video-1","script_clean_text":"text"}\n'
            ).encode("utf-8"),
        },
    )
    set_task_manager(manager)

    preview = asyncio.run(preview_data(task.task_id, limit=1))

    assert preview["file_name"] == "content_asset.jsonl"
    assert preview["format"] == "jsonl"
    assert preview["total_rows"] == 1
    assert preview["rows"][0]["video_id"] == "video-1"


def test_search_preview_keeps_search_result_semantics(tmp_path: Path) -> None:
    manager, task = _create_completed_task(
        tmp_path,
        "search",
        {
            "search_result.csv": (
                "video_id,title\nvideo-1,raw title\n"
            ).encode("utf-8-sig"),
            "search_title_clean.csv": (
                "video_id,clean_title\nvideo-1,clean title\n"
            ).encode("utf-8-sig"),
        },
    )
    set_task_manager(manager)

    preview = asyncio.run(preview_data(task.task_id, limit=1))

    assert preview["file_name"] == "search_result.csv"
    assert preview["rows"][0]["title"] == "raw title"
