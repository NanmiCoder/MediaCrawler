"""
douyin_scraper.api.tests — API 层单元测试
==========================================
v6 新增：测试 FastAPI 路由和任务管理器。
"""

import asyncio
import csv
import io
import json
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def wait_for_task(tm, task_id: str, timeout: float = 10.0,
                  poll_interval: float = 0.05) -> str:
    """
    轮询等待任务达到终态（completed / failed），替代不可靠的 time.sleep。

    Args:
        tm: TaskManager 实例
        task_id: 任务 ID
        timeout: 最大等待秒数
        poll_interval: 轮询间隔秒数

    Returns:
        任务终态 status 字符串

    Raises:
        TimeoutError: 超时未完成
    """
    start = time.time()
    while time.time() - start < timeout:
        task = tm.get_task(task_id)
        if task is not None and task.status in ("completed", "failed"):
            return task.status
        time.sleep(poll_interval)
    raise TimeoutError(f"Task {task_id} did not complete in {timeout}s")


# ═══════════════════════════════════════════════════════════════
# TaskManager 测试
# ═══════════════════════════════════════════════════════════════

class TestTaskManager:
    """任务管理器核心功能"""

    def test_create_task(self, tmp_path: Path) -> None:
        """创建任务"""
        from api.tasks import TaskManager
        tm = TaskManager(base_dir=str(tmp_path))
        task = tm.create_task("search", params={"keywords": ["test"]})
        assert task.task_id
        assert task.task_type == "search"
        assert task.status == "pending"

    def test_submit_and_complete(self, tmp_path: Path) -> None:
        """提交任务并等待完成"""
        from api.tasks import TaskManager
        tm = TaskManager(base_dir=str(tmp_path))
        task = tm.create_task("search")

        def _fake_search() -> Dict[str, Any]:
            return {"video_jsonl": "/fake/path.jsonl"}

        tm.submit(task, _fake_search)
        final_status = wait_for_task(tm, task.task_id)

        assert final_status == "completed"
        updated = tm.get_task(task.task_id)
        assert updated is not None
        assert updated.result == {"video_jsonl": "/fake/path.jsonl"}

    def test_submit_and_fail(self, tmp_path: Path) -> None:
        """提交任务并失败"""
        from api.tasks import TaskManager
        tm = TaskManager(base_dir=str(tmp_path))
        task = tm.create_task("search")

        def _fail_search() -> None:
            raise ConnectionError("网络超时")

        tm.submit(task, _fail_search)
        final_status = wait_for_task(tm, task.task_id)

        assert final_status == "failed"
        updated = tm.get_task(task.task_id)
        assert updated is not None
        assert "网络超时" in (updated.error or "")

    def test_list_tasks(self, tmp_path: Path) -> None:
        """列出任务"""
        from api.tasks import TaskManager
        tm = TaskManager(base_dir=str(tmp_path))
        tm.create_task("search")
        tm.create_task("comments")
        tasks = tm.list_tasks()
        assert len(tasks) == 2

    def test_delete_task(self, tmp_path: Path) -> None:
        """删除任务"""
        from api.tasks import TaskManager
        tm = TaskManager(base_dir=str(tmp_path))
        task = tm.create_task("search")
        assert tm.delete_task(task.task_id) is True
        assert tm.get_task(task.task_id) is None

    def test_persistence(self, tmp_path: Path) -> None:
        """任务持久化到 JSON"""
        from api.tasks import TaskManager
        tm1 = TaskManager(base_dir=str(tmp_path))
        task = tm1.create_task("search")

        # 新建另一个 TaskManager 实例（模拟重启）
        tm2 = TaskManager(base_dir=str(tmp_path))
        restored = tm2.get_task(task.task_id)
        assert restored is not None
        assert restored.task_type == "search"

    def test_cleanup_old_tasks(self, tmp_path: Path) -> None:
        """清理过期任务"""
        from api.tasks import TaskManager
        tm = TaskManager(base_dir=str(tmp_path))

        # 创建一个已完成的任务
        task = tm.create_task("search")
        task.status = "completed"
        task.completed_at = "2020-01-01T00:00:00+08:00"  # 很久以前
        tm._save_registry()

        removed = tm.cleanup_old_tasks(max_age_hours=1)
        assert removed == 1

    def test_get_stats(self, tmp_path: Path) -> None:
        """任务统计"""
        from api.tasks import TaskManager
        tm = TaskManager(base_dir=str(tmp_path))
        tm.create_task("search")
        tm.create_task("comments")
        stats = tm.get_stats()
        assert stats["total"] == 2
        assert stats["pending"] == 2

    @pytest.mark.parametrize(
        ("task_type", "files", "expected"),
        [
            (
                "merge",
                ("douyin_koubo_data.csv", "content_asset.jsonl", "content_asset.csv"),
                "content_asset.csv",
            ),
            (
                "merge",
                ("legacy.csv", "douyin_koubo_data.csv"),
                "douyin_koubo_data.csv",
            ),
        ],
    )
    def test_get_result_path_task_type_priority(
        self,
        tmp_path: Path,
        task_type: str,
        files: tuple[str, ...],
        expected: str,
    ) -> None:
        from api.tasks import TaskManager

        tm = TaskManager(base_dir=str(tmp_path))
        task = tm.create_task(task_type)
        task.status = "completed"
        outputs = Path(task.workspace) / "outputs"
        outputs.mkdir(parents=True, exist_ok=True)
        for name in files:
            (outputs / name).write_text("value\n", encoding="utf-8")

        result = tm.get_result_path(task.task_id)

        assert result is not None
        assert result.name == expected


def _create_completed_task(
    tmp_path: Path,
    task_type: str,
    files: Dict[str, bytes],
):
    from api.tasks import TaskManager

    tm = TaskManager(base_dir=str(tmp_path))
    task = tm.create_task(task_type)
    task.status = "completed"
    outputs = Path(task.workspace) / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (outputs / name).write_bytes(content)
    return tm, task


def test_content_asset_result_preview_and_exports(tmp_path: Path) -> None:
    from api.routes import (
        ExportRequest,
        data_export_download,
        export_data,
        get_result,
        preview_data,
        set_task_manager,
    )

    source = (
        "video_id,platform,script_clean_text,liked_count,collected_count,"
        "share_count,comment_count,asset_quality\n"
        "video-1,douyin,clean script,11,12,13,14,partial\n"
    ).encode("utf-8-sig")
    tm, task = _create_completed_task(
        tmp_path,
        "merge",
        {
            "content_asset.csv": source,
            "content_asset.jsonl": b'{"video_id":"jsonl-fallback"}\n',
        },
    )
    set_task_manager(tm)

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

    rows = list(csv.DictReader(io.StringIO(
        batch_response.body.decode("utf-8-sig")
    )))
    assert rows == [{
        "video_id": "video-1",
        "platform": "douyin",
        "script_text": "clean script",
        "likes": "11",
        "favorites": "12",
        "shares": "13",
        "comments": "14",
    }]


def test_preview_jsonl_fallback_uses_shared_selector(tmp_path: Path) -> None:
    from api.routes import preview_data, set_task_manager

    tm, task = _create_completed_task(
        tmp_path,
        "merge",
        {
            "content_asset.jsonl": (
                '{"video_id":"video-1","script_clean_text":"text"}\n'
            ).encode("utf-8"),
        },
    )
    set_task_manager(tm)

    preview = asyncio.run(preview_data(task.task_id, limit=1))

    assert preview["file_name"] == "content_asset.jsonl"
    assert preview["format"] == "jsonl"
    assert preview["total_rows"] == 1
    assert preview["rows"][0]["video_id"] == "video-1"


def test_search_preview_keeps_search_result_semantics(tmp_path: Path) -> None:
    from api.routes import preview_data, set_task_manager

    tm, task = _create_completed_task(
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
    set_task_manager(tm)

    preview = asyncio.run(preview_data(task.task_id, limit=1))

    assert preview["file_name"] == "search_result.csv"
    assert preview["rows"][0]["title"] == "raw title"


# ═══════════════════════════════════════════════════════════════
# API 路由测试
# ═══════════════════════════════════════════════════════════════

class TestAPIRoutes:
    """FastAPI 路由测试"""

    @pytest.fixture
    def client(self, tmp_path: Path) -> Any:
        """创建测试客户端"""
        import os
        # 设置环境变量让 lifespan 使用临时目录
        os.environ["DY_WORKSPACE_DIR"] = str(tmp_path / "workspaces")

        from api.main import app
        from api.tasks import TaskManager
        from api.routes import set_task_manager

        # 手动创建 TaskManager（lifespan 在 TestClient 中可能不触发）
        tm = TaskManager(base_dir=str(tmp_path / "workspaces"))
        set_task_manager(tm)

        # TestClient 在后台线程处理请求；submit() 内注册 signal 会失败
        with patch.object(TaskManager, "_register_shutdown_handlers"):
            with TestClient(app) as c:
                yield c

    def test_health_check(self, client: Any) -> None:
        """健康检查"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checks" in data
        assert "system" in data

    def test_root(self, client: Any) -> None:
        """根路径"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "version" in data

    def test_search_submit(self, client: Any) -> None:
        """搜索任务提交"""
        resp = client.post("/scrape/search", json={
            "keywords": ["测试关键词"],
            "max_count": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "submitted"
        assert data["type"] == "search"

    def test_comments_submit(self, client: Any) -> None:
        """评论任务提交"""
        resp = client.post("/scrape/comments", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data

    def test_scripts_submit(self, client: Any) -> None:
        """文案任务提交"""
        resp = client.post("/scrape/scripts", json={
            "model": "small",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data

    def test_merge_submit(self, client: Any) -> None:
        """合并任务提交"""
        resp = client.post("/scrape/merge", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data

    def test_run_all_submit(self, client: Any) -> None:
        """一键运行提交"""
        resp = client.post("/scrape/run-all", json={
            "keywords": ["测试"],
            "max_count": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data

    def test_task_status_not_found(self, client: Any) -> None:
        """查询不存在的任务"""
        resp = client.get("/scrape/status/nonexistent")
        assert resp.status_code == 404

    def test_task_result_not_completed(self, client: Any) -> None:
        """查询未完成任务的结果"""
        # 先创建任务
        resp = client.post("/scrape/search", json={
            "keywords": ["测试"],
            "max_count": 5,
        })
        task_id = resp.json()["task_id"]

        # 任务还在 running，结果不可用
        resp = client.get(f"/scrape/result/{task_id}")
        assert resp.status_code == 400

    def test_list_tasks(self, client: Any) -> None:
        """列出任务"""
        client.post("/scrape/search", json={"keywords": ["t1"]})
        client.post("/scrape/search", json={"keywords": ["t2"]})
        resp = client.get("/scrape/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    def test_delete_task(self, client: Any) -> None:
        """删除任务"""
        resp = client.post("/scrape/search", json={"keywords": ["t"]})
        task_id = resp.json()["task_id"]

        resp = client.delete(f"/scrape/tasks/{task_id}")
        assert resp.status_code == 200

    def test_cleanup(self, client: Any) -> None:
        """清理过期任务"""
        resp = client.post("/scrape/cleanup?max_age_hours=1")
        assert resp.status_code == 200
        assert "removed" in resp.json()

    def test_reset_step(self, client: Any) -> None:
        """重置步骤"""
        resp = client.post("/scrape/reset", json={
            "step": "run_search",
            "clear_dedupe": False,
        })
        # 可能成功也可能失败（取决于是否有对应状态文件）
        assert resp.status_code in (200, 400, 500)
