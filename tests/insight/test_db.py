# -*- coding: utf-8 -*-
import os

from insight.db import InsightDB


def _db(tmp_path):
    db = InsightDB(os.path.join(str(tmp_path), "t.db"))
    db.init_schema()
    return db


def test_init_schema_creates_table_and_is_idempotent(tmp_path):
    db = _db(tmp_path)
    db.init_schema()  # 再次调用不应报错
    assert db.recent_runs() == []


def test_start_and_finish_run_roundtrip(tmp_path):
    db = _db(tmp_path)
    run_id = db.start_run("kw_daily", "search")
    assert isinstance(run_id, int)

    runs = db.recent_runs()
    assert len(runs) == 1
    assert runs[0]["status"] == "running"
    assert runs[0]["job_name"] == "kw_daily"
    assert runs[0]["finished_ts"] is None

    db.finish_run(run_id, exit_code=0, status="success", notes_crawled=3, comments_crawled=12)
    runs = db.recent_runs()
    assert runs[0]["status"] == "success"
    assert runs[0]["exit_code"] == 0
    assert runs[0]["notes_crawled"] == 3
    assert runs[0]["comments_crawled"] == 12
    assert runs[0]["finished_ts"] is not None


def test_count_rows_returns_zero_when_table_absent(tmp_path):
    db = _db(tmp_path)
    assert db.count_rows("xhs_note") == 0
    assert db.count_rows("xhs_note_comment") == 0


def test_count_rows_rejects_unknown_table(tmp_path):
    db = _db(tmp_path)
    try:
        db.count_rows("evil_table")
    except ValueError:
        return
    raise AssertionError("expected ValueError for disallowed table")


def test_recent_runs_orders_desc_and_limits(tmp_path):
    db = _db(tmp_path)
    for i in range(3):
        db.start_run(f"job{i}", "search")
    runs = db.recent_runs(limit=2)
    assert len(runs) == 2
    assert runs[0]["job_name"] == "job2"  # 最新在前
