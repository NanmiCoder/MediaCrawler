# -*- coding: utf-8 -*-

import asyncio

import pytest

from api.scheduler import manager as scheduler_manager_module
from api.scheduler.manager import SchedulerManager
from api.scheduler.schemas import InstanceCreateRequest, JobCreateRequest
from api.scheduler.store import SchedulerStore


def test_scheduler_manager_builds_isolated_command(tmp_path):
    store = SchedulerStore(tmp_path / "scheduler.db")
    manager = SchedulerManager(store=store, project_root=tmp_path)
    instance = manager.create_instance(
        InstanceCreateRequest(
            name="抖音账号 A",
            platform="dy",
            browser_profile_dir=str(tmp_path / "profiles" / "dy-a"),
            default_params={"enable_comments": False, "max_notes_count": 8},
        )
    )
    task = store.create_task(
        {
            "instance_id": instance["id"],
            "crawler_type": "search",
            "target_text": "AI 工具",
            "params": {"enable_sub_comments": True, "content_filters": {"liked_count": {"min": 1000}}},
        },
        str(tmp_path / "artifacts" / "task-a"),
    )

    cmd = manager._build_command(instance, task)

    assert cmd[:4] == ["uv", "run", "python", "main.py"]
    assert cmd[cmd.index("--platform") + 1] == "dy"
    assert cmd[cmd.index("--type") + 1] == "search"
    assert cmd[cmd.index("--keywords") + 1] == "AI 工具"
    assert cmd[cmd.index("--browser_profile_dir") + 1] == str(tmp_path / "profiles" / "dy-a")
    assert cmd[cmd.index("--cdp_connect_existing") + 1] == "false"
    assert cmd[cmd.index("--get_comment") + 1] == "false"
    assert cmd[cmd.index("--get_sub_comment") + 1] == "true"
    assert cmd[cmd.index("--crawler_max_notes_count") + 1] == "8"
    assert cmd[cmd.index("--content_filters") + 1] == '{"liked_count": {"min": 1000}}'


def test_scheduler_manager_scans_artifacts(tmp_path):
    manager = SchedulerManager(store=SchedulerStore(tmp_path / "scheduler.db"), project_root=tmp_path)
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    artifact_file = artifact_dir / "data.jsonl"
    artifact_file.write_text('{"id": 1}\n{"id": 2}\n', encoding="utf-8")

    artifacts = manager._scan_artifacts(artifact_dir)

    assert artifacts[0]["type"] == "jsonl"
    assert artifacts[0]["record_count"] == 2


def test_scheduler_manager_builds_artifact_summary(tmp_path):
    store = SchedulerStore(tmp_path / "scheduler.db")
    manager = SchedulerManager(store=store, project_root=tmp_path)
    job = manager.create_job(JobCreateRequest(name="抖音作业", platform="dy"))
    artifact_dir = tmp_path / "artifacts" / "task-a"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "search_contents.jsonl").write_text(
        '{"aweme_id":"1","title":"郑州作品","nickname":"作者","liked_count":"10","aweme_url":"https://www.douyin.com/video/1"}\n',
        encoding="utf-8",
    )
    (artifact_dir / "search_comments.jsonl").write_text(
        '{"content":"郑州 城市 郑州"}\n{"content":"城市 交通"}\n',
        encoding="utf-8",
    )
    task = store.create_task(
        {"instance_id": job["id"], "crawler_type": "search", "target_text": "", "params": {}},
        str(artifact_dir),
    )
    store.update_instance(job["id"], last_task_id=task["id"])
    store.replace_artifacts(task["id"], manager._scan_artifacts(artifact_dir))

    summary = manager.list_job_artifact_summary(job["id"])

    assert summary["works"][0]["title"] == "郑州作品"
    assert summary["works"][0]["url"] == "https://www.douyin.com/video/1"
    assert {"text": "郑州", "weight": 2} in summary["word_cloud"]


def test_scheduler_manager_builds_platform_work_urls(tmp_path):
    manager = SchedulerManager(store=SchedulerStore(tmp_path / "scheduler.db"), project_root=tmp_path)

    cases = [
        ("xhs", "abc", {"xsec_token": "token"}, "https://www.xiaohongshu.com/explore/abc?xsec_token=token&xsec_source=pc_search"),
        ("dy", "123", {}, "https://www.douyin.com/video/123"),
        ("ks", "123", {}, "https://www.kuaishou.com/short-video/123"),
        ("bili", "456", {}, "https://www.bilibili.com/video/av456"),
        ("bili", "BV1xx", {}, "https://www.bilibili.com/video/BV1xx"),
        ("wb", "123", {}, "https://m.weibo.cn/detail/123"),
        ("tieba", "123", {}, "https://tieba.baidu.com/p/123"),
        ("zhihu", "789", {"question_id": "456"}, "https://www.zhihu.com/question/456/answer/789"),
        ("zhihu", "789", {"content_type": "zvideo"}, "https://www.zhihu.com/zvideo/789"),
        ("zhihu", "789", {"content_type": "article"}, "https://zhuanlan.zhihu.com/p/789"),
    ]

    for platform, work_id, record, expected in cases:
        assert manager._default_work_url(platform, work_id, record) == expected


def test_scheduler_manager_deletes_job_artifact(tmp_path):
    store = SchedulerStore(tmp_path / "scheduler.db")
    manager = SchedulerManager(store=store, project_root=tmp_path)
    job = manager.create_job(JobCreateRequest(name="小红书作业", platform="xhs"))
    artifact_dir = tmp_path / "artifacts" / "task-a"
    artifact_dir.mkdir(parents=True)
    artifact_file = artifact_dir / "data.jsonl"
    artifact_file.write_text('{"id": 1}\n', encoding="utf-8")
    task = store.create_task(
        {"instance_id": job["id"], "crawler_type": "search", "target_text": "", "params": {}},
        str(artifact_dir),
    )
    store.update_instance(job["id"], last_task_id=task["id"])
    store.replace_artifacts(task["id"], manager._scan_artifacts(artifact_dir))
    artifact = store.list_artifacts(task["id"])[0]

    result = manager.delete_job_artifact(job["id"], artifact["id"])

    assert result["status"] == "ok"
    assert not artifact_file.exists()
    assert store.list_artifacts(task["id"]) == []


def test_scheduler_manager_opens_job_artifact(monkeypatch, tmp_path):
    store = SchedulerStore(tmp_path / "scheduler.db")
    manager = SchedulerManager(store=store, project_root=tmp_path)
    job = manager.create_job(JobCreateRequest(name="小红书作业", platform="xhs"))
    artifact_dir = tmp_path / "artifacts" / "task-a"
    artifact_dir.mkdir(parents=True)
    artifact_file = artifact_dir / "data.jsonl"
    artifact_file.write_text('{"id": 1}\n', encoding="utf-8")
    task = store.create_task(
        {"instance_id": job["id"], "crawler_type": "search", "target_text": "", "params": {}},
        str(artifact_dir),
    )
    store.update_instance(job["id"], last_task_id=task["id"])
    store.replace_artifacts(task["id"], manager._scan_artifacts(artifact_dir))
    artifact = store.list_artifacts(task["id"])[0]
    calls = []

    def fake_run(cmd, check, capture_output, text):
        calls.append((cmd, check, capture_output, text))

    monkeypatch.setattr(scheduler_manager_module.sys, "platform", "darwin")
    monkeypatch.setattr(scheduler_manager_module.subprocess, "run", fake_run)

    result = manager.open_job_artifact(job["id"], artifact["id"])

    assert result["status"] == "ok"
    assert result["path"] == str(artifact_file)
    assert calls == [(["open", "-t", str(artifact_file)], True, True, True)]


def test_scheduler_manager_runs_job_without_queue(monkeypatch, tmp_path):
    store = SchedulerStore(tmp_path / "scheduler.db")
    manager = SchedulerManager(store=store, project_root=tmp_path)
    job = manager.create_job(
        JobCreateRequest(
            name="小红书作业",
            platform="xhs",
            crawler_type="search",
            target_text="AI 工具",
            params={"max_notes_count": 3},
        )
    )

    async def fake_start(task):
        store.update_task(task["id"], status="running", pid=123)
        store.update_instance(
            task["instance_id"],
            status="running",
            current_task_id=task["id"],
            last_task_id=task["id"],
            pid=123,
        )

    monkeypatch.setattr(manager, "_start_task_locked", fake_start)

    task = asyncio.run(manager.run_job(job["id"]))

    assert task["crawler_type"] == "search"
    assert task["target_text"] == "AI 工具"
    assert task["params"] == {"max_notes_count": 3}
    assert store.get_instance(job["id"])["last_task_id"] == task["id"]
    with pytest.raises(RuntimeError, match="already running"):
        asyncio.run(manager.run_job(job["id"]))
