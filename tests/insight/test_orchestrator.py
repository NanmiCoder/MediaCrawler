# -*- coding: utf-8 -*-
import os

import insight.orchestrator as orchestrator
import insight.runner as runner
from insight.db import InsightDB


def _db(tmp_path):
    db = InsightDB(os.path.join(str(tmp_path), "t.db"))
    db.init_schema()
    return db


def test_run_job_success_records_success(tmp_path, monkeypatch):
    db = _db(tmp_path)
    monkeypatch.setattr(
        runner, "run_crawl",
        lambda job, timeout=None: runner.CrawlResult(exit_code=0, timed_out=False, stderr_tail=""),
    )
    job = {"name": "kw", "type": "search", "keywords": "x", "hour": 2}
    result = orchestrator.run_job(job, db=db)

    assert result["status"] == "success"
    runs = db.recent_runs()
    assert runs[0]["status"] == "success"
    assert runs[0]["error_msg"] is None


def test_run_job_nonzero_records_error_with_stderr(tmp_path, monkeypatch):
    db = _db(tmp_path)
    monkeypatch.setattr(
        runner, "run_crawl",
        lambda job, timeout=None: runner.CrawlResult(exit_code=2, timed_out=False, stderr_tail="kaboom"),
    )
    job = {"name": "kw", "type": "search", "keywords": "x", "hour": 2}
    result = orchestrator.run_job(job, db=db)

    assert result["status"] == "error"
    runs = db.recent_runs()
    assert runs[0]["status"] == "error"
    assert "kaboom" in runs[0]["error_msg"]


def test_run_job_timeout_records_timeout(tmp_path, monkeypatch):
    db = _db(tmp_path)
    monkeypatch.setattr(
        runner, "run_crawl",
        lambda job, timeout=None: runner.CrawlResult(exit_code=-1, timed_out=True, stderr_tail=""),
    )
    job = {"name": "kw", "type": "search", "keywords": "x", "hour": 2}
    result = orchestrator.run_job(job, db=db)
    assert result["status"] == "timeout"
    assert db.recent_runs()[0]["status"] == "timeout"
