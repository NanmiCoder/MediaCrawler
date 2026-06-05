# -*- coding: utf-8 -*-
import subprocess
import sys

import insight.runner as runner


class _FakeCompleted:
    def __init__(self, returncode, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


def test_run_crawl_success_builds_command_and_env(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return _FakeCompleted(0, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    job = {"name": "kw", "type": "search", "keywords": "x", "hour": 2, "max_notes": 7}
    result = runner.run_crawl(job)

    assert result.exit_code == 0
    assert result.timed_out is False
    # 命令以当前解释器 + -m insight.crawl_entry 开头
    assert captured["cmd"][:3] == [sys.executable, "-m", "insight.crawl_entry"]
    assert "--keywords" in captured["cmd"]
    # max_notes 通过环境变量注入
    assert captured["kwargs"]["env"]["INSIGHT_MAX_NOTES"] == "7"


def test_run_crawl_nonzero_exit_returns_stderr_tail(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _FakeCompleted(1, stderr="boom"))
    job = {"name": "kw", "type": "search", "keywords": "x", "hour": 2}
    result = runner.run_crawl(job)
    assert result.exit_code == 1
    assert result.timed_out is False
    assert "boom" in result.stderr_tail


def test_run_crawl_timeout(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=1, stderr="late")

    monkeypatch.setattr(subprocess, "run", fake_run)
    job = {"name": "kw", "type": "search", "keywords": "x", "hour": 2}
    result = runner.run_crawl(job, timeout=1)
    assert result.timed_out is True
    assert result.exit_code == -1
