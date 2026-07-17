# -*- coding: utf-8 -*-

from api.scheduler.store import SchedulerStore


def test_scheduler_store_crud(tmp_path):
    store = SchedulerStore(tmp_path / "scheduler.db")
    instance = store.create_instance(
        {
            "name": "小红书账号 A",
            "platform": "xhs",
            "login_type": "qrcode",
            "headless": False,
            "save_option": "jsonl",
            "default_params": {"enable_comments": True},
            "crawler_type": "search",
            "target_text": "编程副业",
            "params": {"max_notes_count": 5},
        },
        str(tmp_path / "profile"),
        9222,
        instance_id="inst-a",
    )

    assert instance["id"] == "inst-a"
    assert instance["default_params"] == {"enable_comments": True}
    assert instance["crawler_type"] == "search"
    assert instance["target_text"] == "编程副业"
    assert instance["params"] == {"max_notes_count": 5}

    task = store.create_task(
        {
            "instance_id": "inst-a",
            "crawler_type": "search",
            "target_text": "编程副业",
            "params": {"max_notes_count": 5},
        },
        str(tmp_path / "artifacts" / "task-a"),
    )
    store.append_log(task["id"], "started", "info")
    store.replace_artifacts(
        task["id"],
        [
            {
                "path": str(tmp_path / "artifacts" / "task-a" / "xhs.jsonl"),
                "type": "jsonl",
                "size": 12,
                "modified_at": 1.0,
                "record_count": 2,
            }
        ],
    )

    assert store.get_next_queued_task("inst-a")["id"] == task["id"]
    assert store.get_latest_task("inst-a")["id"] == task["id"]
    assert store.list_logs(task["id"])[0]["message"] == "started"
    assert store.list_artifacts(task["id"])[0]["record_count"] == 2
    assert store.scheduler_counts()["queued_tasks"] == 1
