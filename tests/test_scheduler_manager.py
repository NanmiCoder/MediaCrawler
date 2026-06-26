# -*- coding: utf-8 -*-

from api.scheduler.manager import SchedulerManager
from api.scheduler.schemas import InstanceCreateRequest
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
            "params": {"enable_sub_comments": True},
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


def test_scheduler_manager_scans_artifacts(tmp_path):
    manager = SchedulerManager(store=SchedulerStore(tmp_path / "scheduler.db"), project_root=tmp_path)
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    artifact_file = artifact_dir / "data.jsonl"
    artifact_file.write_text('{"id": 1}\n{"id": 2}\n', encoding="utf-8")

    artifacts = manager._scan_artifacts(artifact_dir)

    assert artifacts[0]["type"] == "jsonl"
    assert artifacts[0]["record_count"] == 2
