# XHS Insight Pipeline 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不修改任何 MediaCrawler 上游文件的前提下，新增一个独立的 `insight/` 包，实现「按 cron 定时调用爬虫子进程 → 把小红书笔记/评论原始数据写入既有 SQLite → 记录每次运行日志」。

**Architecture:** 所有自研代码隔离在顶层 `insight/` 包内。`insight` 通过 **子进程** 调用一个自研入口 `insight.crawl_entry`（它读取环境变量覆盖无 CLI 参数的配置后委托给上游 `main`），爬虫把数据写入上游既有表 `xhs_note` / `xhs_note_comment`；`insight` 自己只拥有一张 `insight_runs` 日志表（读取上游表只做计数）。调度用 APScheduler 3.x 的 `BlockingScheduler` + `CronTrigger`，通过 `uv run --with` 注入依赖以避免改动 `pyproject.toml`。

**Tech Stack:** Python 3.11、APScheduler 3.x、标准库 `sqlite3` / `subprocess` / `argparse`、pytest（项目既有）。

---

## 背景事实（实现者必须知道，已核实）

- **上游 CLI 参数**（`cmd_arg/arg.py`，由 `main.py` 解析）：`--platform`、`--type`（search/detail/creator）、`--keywords`、`--specified_id`（detail 模式，XHS 笔记 URL/ID，逗号分隔 → `config.XHS_SPECIFIED_NOTE_URL_LIST`）、`--creator_id`（creator 模式 → `config.XHS_CREATOR_ID_LIST`）、`--save_data_option`（取 `sqlite`）、`--get_comment`、`--get_sub_comment`、`--max_comments_count_singlenotes`、`--init_db sqlite`（初始化表结构）。
- **无 CLI 参数**的项：`CRAWLER_MAX_NOTES_COUNT`（每次最多爬多少篇）既无 CLI 参数也不读环境变量。因此每个 job 的 `max_notes` 通过 `insight.crawl_entry` 包装入口用环境变量 `INSIGHT_MAX_NOTES` 注入。
- **SQLite 路径**固定为 `database/sqlite_tables.db`（`config/db_config.py:50`，不读 env，不可由 CLI 改）。`insight/config.py` 的 `DB_PATH` 必须指向同一文件。
- **首次需初始化表结构**：`uv run python main.py --init_db sqlite` 会创建上游所有 SQLite 表。`insight` 的 `count_rows` 在表尚不存在时返回 0，不报错。
- **上游运行入口**：`main.main()` / `main.async_cleanup()` 搭配 `tools.app_runner.run(app_main, app_cleanup, *, cleanup_timeout_seconds=15.0)`（见 `main.py:141-157`）。`crawl_entry` 复用它们。
- **APScheduler 版本**：`pip install apscheduler` 默认装 3.x（4.x 仍为预发布）。本计划用 3.x API：`from apscheduler.schedulers.blocking import BlockingScheduler`、`from apscheduler.triggers.cron import CronTrigger`、`scheduler.add_job(func, trigger=..., args=[...], id=..., misfire_grace_time=..., replace_existing=True)`、`scheduler.start()`。
- **测试约定**：`tests/conftest.py` 已把项目根加入 `sys.path`。自研测试放 `tests/insight/`。运行测试需注入 apscheduler：`uv run --with "apscheduler>=3.10,<4" pytest tests/insight -v`。
- **包内 import 区分**：顶层 `import config` 指上游配置；`from insight import config` 指自研配置。两者都要用时按此区分，切勿混淆。

---

## 文件结构

```
insight/
├─ __init__.py            # 空，标记包
├─ config.py              # DB_PATH、超时、misfire、JOBS 列表（纯数据）
├─ schema.sql            # insight_runs 建表 DDL
├─ crawl_entry.py         # 子进程入口：env 覆盖 + 委托上游 main
├─ db.py                  # InsightDB：建表/记录运行/计数/查询
├─ runner.py              # build_crawl_args + run_crawl（子进程封装）
├─ orchestrator.py        # run_job：串起 db + runner（一次完整周期）
├─ requirements.txt       # apscheduler>=3.10,<4（依赖声明，避免改 pyproject）
├─ scheduler/
│  ├─ __init__.py
│  └─ daemon.py           # build_scheduler + main（BlockingScheduler）
├─ cli.py                 # crawl-once / run-daemon / status 子命令
└─ README.md              # 安装、使用、上游同步步骤

tests/insight/
├─ __init__.py
├─ test_db.py
├─ test_runner_args.py
├─ test_runner_subprocess.py
├─ test_crawl_entry.py
├─ test_orchestrator.py
├─ test_scheduler.py
└─ test_cli.py
```

每个文件单一职责，可独立测试：`config` 只放数据；`db` 只管 SQLite；`runner` 只管「job→命令」与子进程；`orchestrator` 只做编排；`scheduler` 只做触发；`cli` 只做命令分发；`crawl_entry` 只做配置覆盖+委托。

---

## Task 1: 包骨架、配置、Schema、依赖声明

**Files:**
- Create: `insight/__init__.py`
- Create: `insight/scheduler/__init__.py`
- Create: `insight/config.py`
- Create: `insight/schema.sql`
- Create: `insight/requirements.txt`
- Create: `tests/insight/__init__.py`

- [ ] **Step 1: 创建空包标记文件**

`insight/__init__.py`：
```python
# -*- coding: utf-8 -*-
"""自研二次开发包：小红书评论定时采集与运行记录。不修改 MediaCrawler 上游文件。"""
```

`insight/scheduler/__init__.py`：
```python
# -*- coding: utf-8 -*-
```

`tests/insight/__init__.py`：
```python
# -*- coding: utf-8 -*-
```

- [ ] **Step 2: 写 `insight/config.py`（纯数据配置）**

```python
# -*- coding: utf-8 -*-
"""insight 包的配置。纯数据，不含逻辑。"""

import os

# 项目根目录（insight/ 的上一级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 爬虫写入的 SQLite 文件，必须与 config/db_config.py 的 SQLITE_DB_PATH 一致
DB_PATH = os.path.join(PROJECT_ROOT, "database", "sqlite_tables.db")

# 单次爬虫子进程的最大运行秒数，超时则杀死并记为 timeout
SUBPROCESS_TIMEOUT = 1800

# APScheduler 容忍的最大迟到秒数（睡眠/停机后仍补跑）
MISFIRE_GRACE_TIME = 3600

# 定时任务列表。每个 job 映射为一次爬虫调用。
# 必填键：name、type（"search"|"detail"|"creator"）、hour（0-23）
#   search  额外需要 "keywords"（英文逗号分隔的字符串）
#   detail  额外需要 "note_ids"（笔记 ID 或 URL 的列表）
#   creator 额外需要 "creator_ids"（创作者 ID 或 URL 的列表）
# 可选键：minute（默认 0）、max_notes（int）、max_comments（int）、get_sub_comment（bool）
JOBS = [
    {"name": "kw_daily", "type": "search", "keywords": "编程副业,编程兼职", "hour": 2, "minute": 0, "max_notes": 20},
    {"name": "watch_notes", "type": "detail", "note_ids": ["请替换为真实笔记ID"], "hour": 3, "minute": 0},
    {"name": "creator_daily", "type": "creator", "creator_ids": ["请替换为真实创作者ID"], "hour": 4, "minute": 0},
]
```

- [ ] **Step 3: 写 `insight/schema.sql`**

```sql
CREATE TABLE IF NOT EXISTS insight_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT NOT NULL,
    crawler_type TEXT NOT NULL,
    started_ts INTEGER NOT NULL,
    finished_ts INTEGER,
    exit_code INTEGER,
    notes_crawled INTEGER DEFAULT 0,
    comments_crawled INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    error_msg TEXT
);
CREATE INDEX IF NOT EXISTS idx_insight_runs_job ON insight_runs (job_name, started_ts);
```

- [ ] **Step 4: 写 `insight/requirements.txt`**

```
apscheduler>=3.10,<4
```

- [ ] **Step 5: 提交**

```bash
git add insight/__init__.py insight/scheduler/__init__.py insight/config.py insight/schema.sql insight/requirements.txt tests/insight/__init__.py
git commit -m "feat(insight): 包骨架、配置、insight_runs schema 与依赖声明"
```

---

## Task 2: `insight/db.py` — SQLite 运行记录与计数

**Files:**
- Create: `insight/db.py`
- Test: `tests/insight/test_db.py`

- [ ] **Step 1: 写失败测试**

`tests/insight/test_db.py`：
```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/insight/test_db.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'insight.db'`）

- [ ] **Step 3: 写最小实现 `insight/db.py`**

```python
# -*- coding: utf-8 -*-
"""insight 的 SQLite 访问层：运行记录与上游表计数。"""

import os
import sqlite3
import time
from typing import List, Dict, Optional

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

# 仅允许对这些上游表做计数，避免 SQL 注入
_COUNTABLE_TABLES = {"xhs_note", "xhs_note_comment"}


class InsightDB:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            ddl = f.read()
        with self._connect() as conn:
            conn.executescript(ddl)

    def start_run(self, job_name: str, crawler_type: str) -> int:
        now = int(time.time())
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO insight_runs (job_name, crawler_type, started_ts, status) "
                "VALUES (?, ?, ?, 'running')",
                (job_name, crawler_type, now),
            )
            return int(cur.lastrowid)

    def finish_run(
        self,
        run_id: int,
        *,
        exit_code: Optional[int],
        status: str,
        notes_crawled: int = 0,
        comments_crawled: int = 0,
        error_msg: Optional[str] = None,
    ) -> None:
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                "UPDATE insight_runs SET finished_ts=?, exit_code=?, status=?, "
                "notes_crawled=?, comments_crawled=?, error_msg=? WHERE id=?",
                (now, exit_code, status, notes_crawled, comments_crawled, error_msg, run_id),
            )

    def count_rows(self, table: str) -> int:
        if table not in _COUNTABLE_TABLES:
            raise ValueError(f"count_rows: table {table!r} not allowed")
        with self._connect() as conn:
            try:
                row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
            except sqlite3.OperationalError:
                return 0  # 表尚未由上游 --init_db 创建
            return int(row["c"])

    def recent_runs(self, limit: int = 20) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM insight_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/insight/test_db.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: 提交**

```bash
git add insight/db.py tests/insight/test_db.py
git commit -m "feat(insight): InsightDB 运行记录与上游表计数"
```

---

## Task 3: `insight/runner.py` — job 转命令行参数

**Files:**
- Create: `insight/runner.py`
- Test: `tests/insight/test_runner_args.py`

- [ ] **Step 1: 写失败测试**

`tests/insight/test_runner_args.py`：
```python
# -*- coding: utf-8 -*-
import pytest

from insight.runner import build_crawl_args


def test_search_job_args():
    job = {"name": "kw", "type": "search", "keywords": "a,b", "hour": 2}
    args = build_crawl_args(job)
    assert args[:6] == ["--platform", "xhs", "--type", "search", "--save_data_option", "sqlite"]
    assert "--keywords" in args and args[args.index("--keywords") + 1] == "a,b"
    assert args[args.index("--get_comment") + 1] == "true"


def test_detail_job_joins_note_ids():
    job = {"name": "w", "type": "detail", "note_ids": ["n1", "n2"], "hour": 3}
    args = build_crawl_args(job)
    assert "--type" in args and args[args.index("--type") + 1] == "detail"
    assert args[args.index("--specified_id") + 1] == "n1,n2"


def test_creator_job_joins_creator_ids():
    job = {"name": "c", "type": "creator", "creator_ids": ["c1"], "hour": 4}
    args = build_crawl_args(job)
    assert args[args.index("--creator_id") + 1] == "c1"


def test_optional_max_comments_and_sub_comment():
    job = {"name": "k", "type": "search", "keywords": "x", "hour": 2,
           "max_comments": 50, "get_sub_comment": True}
    args = build_crawl_args(job)
    assert args[args.index("--max_comments_count_singlenotes") + 1] == "50"
    assert args[args.index("--get_sub_comment") + 1] == "true"


def test_invalid_type_raises():
    with pytest.raises(ValueError):
        build_crawl_args({"name": "bad", "type": "homefeed", "hour": 1})


def test_search_missing_keywords_raises():
    with pytest.raises(ValueError):
        build_crawl_args({"name": "bad", "type": "search", "hour": 1})


def test_detail_missing_note_ids_raises():
    with pytest.raises(ValueError):
        build_crawl_args({"name": "bad", "type": "detail", "hour": 1})


def test_creator_missing_ids_raises():
    with pytest.raises(ValueError):
        build_crawl_args({"name": "bad", "type": "creator", "hour": 1})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/insight/test_runner_args.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'insight.runner'`）

- [ ] **Step 3: 写最小实现（仅 `build_crawl_args` 部分）`insight/runner.py`**

```python
# -*- coding: utf-8 -*-
"""把 job 配置转成爬虫命令行参数，并以子进程方式运行爬虫。"""

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional

from insight import config as insight_config

VALID_TYPES = {"search", "detail", "creator"}


def build_crawl_args(job: dict) -> List[str]:
    """把一个 job dict 翻译成 `python -m insight.crawl_entry` 的参数列表。"""
    name = job.get("name")
    jtype = job.get("type")
    if jtype not in VALID_TYPES:
        raise ValueError(f"job {name!r}: invalid type {jtype!r}")

    args: List[str] = ["--platform", "xhs", "--type", jtype, "--save_data_option", "sqlite"]

    if jtype == "search":
        keywords = job.get("keywords")
        if not keywords:
            raise ValueError(f"job {name!r}: search type requires 'keywords'")
        args += ["--keywords", keywords]
    elif jtype == "detail":
        note_ids = job.get("note_ids")
        if not note_ids:
            raise ValueError(f"job {name!r}: detail type requires 'note_ids'")
        args += ["--specified_id", ",".join(note_ids)]
    elif jtype == "creator":
        creator_ids = job.get("creator_ids")
        if not creator_ids:
            raise ValueError(f"job {name!r}: creator type requires 'creator_ids'")
        args += ["--creator_id", ",".join(creator_ids)]

    args += ["--get_comment", "true"]
    if job.get("get_sub_comment"):
        args += ["--get_sub_comment", "true"]
    if job.get("max_comments"):
        args += ["--max_comments_count_singlenotes", str(job["max_comments"])]

    return args
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/insight/test_runner_args.py -v`
Expected: PASS（8 passed）

- [ ] **Step 5: 提交**

```bash
git add insight/runner.py tests/insight/test_runner_args.py
git commit -m "feat(insight): build_crawl_args 把 job 翻译为爬虫参数"
```

---

## Task 4: `insight/runner.py` — 子进程运行 `run_crawl`

**Files:**
- Modify: `insight/runner.py`（追加 `CrawlResult` 与 `run_crawl`）
- Test: `tests/insight/test_runner_subprocess.py`

- [ ] **Step 1: 写失败测试**

`tests/insight/test_runner_subprocess.py`：
```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/insight/test_runner_subprocess.py -v`
Expected: FAIL（`AttributeError: module 'insight.runner' has no attribute 'run_crawl'`）

- [ ] **Step 3: 在 `insight/runner.py` 末尾追加实现**

```python
@dataclass
class CrawlResult:
    exit_code: int
    timed_out: bool
    stderr_tail: str


def run_crawl(job: dict, timeout: Optional[int] = None) -> CrawlResult:
    """以子进程运行爬虫入口。max_notes 通过环境变量 INSIGHT_MAX_NOTES 注入。"""
    timeout = timeout if timeout is not None else insight_config.SUBPROCESS_TIMEOUT
    args = build_crawl_args(job)
    cmd = [sys.executable, "-m", "insight.crawl_entry", *args]

    env = dict(os.environ)
    if job.get("max_notes"):
        env["INSIGHT_MAX_NOTES"] = str(job["max_notes"])

    try:
        proc = subprocess.run(
            cmd,
            cwd=insight_config.PROJECT_ROOT,
            env=env,
            timeout=timeout,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return CrawlResult(exit_code=-1, timed_out=True, stderr_tail=stderr[-2000:])

    stderr = proc.stderr or ""
    return CrawlResult(exit_code=proc.returncode, timed_out=False, stderr_tail=stderr[-2000:])
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/insight/test_runner_subprocess.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add insight/runner.py tests/insight/test_runner_subprocess.py
git commit -m "feat(insight): run_crawl 子进程封装（超时/退出码/stderr）"
```

---

## Task 5: `insight/crawl_entry.py` — 子进程入口（env 覆盖 + 委托上游）

**Files:**
- Create: `insight/crawl_entry.py`
- Test: `tests/insight/test_crawl_entry.py`

- [ ] **Step 1: 写失败测试**

`tests/insight/test_crawl_entry.py`：
```python
# -*- coding: utf-8 -*-
import config  # 上游配置
from insight.crawl_entry import apply_overrides


def test_apply_overrides_sets_max_notes(monkeypatch):
    original = config.CRAWLER_MAX_NOTES_COUNT
    try:
        monkeypatch.setenv("INSIGHT_MAX_NOTES", "33")
        apply_overrides()
        assert config.CRAWLER_MAX_NOTES_COUNT == 33
    finally:
        config.CRAWLER_MAX_NOTES_COUNT = original


def test_apply_overrides_noop_without_env(monkeypatch):
    original = config.CRAWLER_MAX_NOTES_COUNT
    try:
        monkeypatch.delenv("INSIGHT_MAX_NOTES", raising=False)
        apply_overrides()
        assert config.CRAWLER_MAX_NOTES_COUNT == original
    finally:
        config.CRAWLER_MAX_NOTES_COUNT = original
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/insight/test_crawl_entry.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'insight.crawl_entry'`）

- [ ] **Step 3: 写实现 `insight/crawl_entry.py`**

```python
# -*- coding: utf-8 -*-
"""爬虫子进程入口。

读取 INSIGHT_MAX_NOTES 等无 CLI 参数的覆盖项写入上游 config，
然后把其余 CLI 参数交给上游 main 处理。本文件位于 insight 包内，
不修改任何上游文件。

用法（由 insight.runner 以子进程调用）：
    python -m insight.crawl_entry --platform xhs --type search --keywords ... --save_data_option sqlite
"""

import os


def apply_overrides() -> None:
    """把没有 CLI 参数的配置项从环境变量写入上游 config。"""
    import config  # 上游配置模块

    max_notes = os.environ.get("INSIGHT_MAX_NOTES")
    if max_notes:
        config.CRAWLER_MAX_NOTES_COUNT = int(max_notes)


def main_entry() -> None:
    apply_overrides()
    # 复用上游的协程入口与清理逻辑（sys.argv 由上游 cmd_arg 解析）
    from main import main as crawler_main, async_cleanup
    from tools.app_runner import run

    run(crawler_main, async_cleanup, cleanup_timeout_seconds=15.0)


if __name__ == "__main__":
    main_entry()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/insight/test_crawl_entry.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: 提交**

```bash
git add insight/crawl_entry.py tests/insight/test_crawl_entry.py
git commit -m "feat(insight): crawl_entry 子进程入口（env 覆盖 max_notes 后委托上游）"
```

---

## Task 6: `insight/orchestrator.py` — 一次完整周期编排

**Files:**
- Create: `insight/orchestrator.py`
- Test: `tests/insight/test_orchestrator.py`

- [ ] **Step 1: 写失败测试**

`tests/insight/test_orchestrator.py`：
```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/insight/test_orchestrator.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'insight.orchestrator'`）

- [ ] **Step 3: 写实现 `insight/orchestrator.py`**

```python
# -*- coding: utf-8 -*-
"""一次完整调度周期：开始记录 → 计数前 → 跑爬虫 → 计数后 → 结束记录。"""

from typing import Optional

from insight import config, runner
from insight.db import InsightDB


def run_job(job: dict, db: Optional[InsightDB] = None) -> dict:
    db = db or InsightDB(config.DB_PATH)
    db.init_schema()

    run_id = db.start_run(job["name"], job["type"])
    notes_before = db.count_rows("xhs_note")
    comments_before = db.count_rows("xhs_note_comment")

    result = runner.run_crawl(job)

    notes_after = db.count_rows("xhs_note")
    comments_after = db.count_rows("xhs_note_comment")
    notes_delta = max(0, notes_after - notes_before)
    comments_delta = max(0, comments_after - comments_before)

    if result.timed_out:
        status = "timeout"
    elif result.exit_code == 0:
        status = "success"
    else:
        status = "error"

    db.finish_run(
        run_id,
        exit_code=result.exit_code,
        status=status,
        notes_crawled=notes_delta,
        comments_crawled=comments_delta,
        error_msg=None if status == "success" else (result.stderr_tail or status),
    )

    return {"run_id": run_id, "status": status, "notes": notes_delta, "comments": comments_delta}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/insight/test_orchestrator.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add insight/orchestrator.py tests/insight/test_orchestrator.py
git commit -m "feat(insight): orchestrator.run_job 编排一次完整采集周期"
```

---

## Task 7: `insight/scheduler/daemon.py` — APScheduler 守护进程

**Files:**
- Create: `insight/scheduler/daemon.py`
- Test: `tests/insight/test_scheduler.py`

> 本任务起的测试需要 apscheduler，运行命令统一加 `--with`。

- [ ] **Step 1: 写失败测试**

`tests/insight/test_scheduler.py`：
```python
# -*- coding: utf-8 -*-
from apscheduler.schedulers.blocking import BlockingScheduler

from insight.scheduler.daemon import build_scheduler


def test_build_scheduler_registers_one_job_per_config():
    jobs = [
        {"name": "kw_daily", "type": "search", "keywords": "x", "hour": 2, "minute": 0},
        {"name": "watch", "type": "detail", "note_ids": ["n1"], "hour": 3, "minute": 30},
    ]
    sched = build_scheduler(jobs=jobs, scheduler=BlockingScheduler())
    ids = {j.id for j in sched.get_jobs()}
    assert ids == {"kw_daily", "watch"}


def test_build_scheduler_sets_cron_hour_and_minute():
    jobs = [{"name": "watch", "type": "detail", "note_ids": ["n1"], "hour": 3, "minute": 30}]
    sched = build_scheduler(jobs=jobs, scheduler=BlockingScheduler())
    job = sched.get_job("watch")
    fields = {f.name: str(f) for f in job.trigger.fields}
    assert fields["hour"] == "3"
    assert fields["minute"] == "30"


def test_build_scheduler_defaults_minute_to_zero():
    jobs = [{"name": "kw", "type": "search", "keywords": "x", "hour": 5}]
    sched = build_scheduler(jobs=jobs, scheduler=BlockingScheduler())
    job = sched.get_job("kw")
    fields = {f.name: str(f) for f in job.trigger.fields}
    assert fields["minute"] == "0"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run --with "apscheduler>=3.10,<4" pytest tests/insight/test_scheduler.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'insight.scheduler.daemon'`）

- [ ] **Step 3: 写实现 `insight/scheduler/daemon.py`**

```python
# -*- coding: utf-8 -*-
"""APScheduler 守护进程：按 cron 触发每个 job。"""

from typing import List, Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from insight import config
from insight.orchestrator import run_job


def build_scheduler(jobs: Optional[List[dict]] = None, scheduler: Optional[BlockingScheduler] = None) -> BlockingScheduler:
    jobs = jobs if jobs is not None else config.JOBS
    scheduler = scheduler if scheduler is not None else BlockingScheduler()
    for job in jobs:
        trigger = CronTrigger(hour=job["hour"], minute=job.get("minute", 0))
        scheduler.add_job(
            run_job,
            trigger=trigger,
            args=[job],
            id=job["name"],
            misfire_grace_time=config.MISFIRE_GRACE_TIME,
            replace_existing=True,
        )
    return scheduler


def main() -> None:
    scheduler = build_scheduler()
    print(f"[insight] scheduler started with {len(scheduler.get_jobs())} job(s). Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[insight] scheduler stopped.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run --with "apscheduler>=3.10,<4" pytest tests/insight/test_scheduler.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add insight/scheduler/daemon.py tests/insight/test_scheduler.py
git commit -m "feat(insight): APScheduler 守护进程，按 cron 触发各 job"
```

---

## Task 8: `insight/cli.py` — 命令行入口

**Files:**
- Create: `insight/cli.py`
- Test: `tests/insight/test_cli.py`

> `run-daemon` 子命令对 apscheduler 的依赖采用**惰性导入**（在处理函数内 import），使 `crawl-once` / `status` 无需安装 apscheduler 即可使用。

- [ ] **Step 1: 写失败测试**

`tests/insight/test_cli.py`：
```python
# -*- coding: utf-8 -*-
import pytest

from insight.cli import build_parser, cmd_crawl_once, cmd_status


def test_parser_crawl_once():
    args = build_parser().parse_args(["crawl-once", "kw_daily"])
    assert args.name == "kw_daily"
    assert args.func is cmd_crawl_once


def test_parser_status_default_limit():
    args = build_parser().parse_args(["status"])
    assert args.limit == 20
    assert args.func is cmd_status


def test_parser_status_custom_limit():
    args = build_parser().parse_args(["status", "--limit", "5"])
    assert args.limit == 5


def test_parser_requires_subcommand():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/insight/test_cli.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'insight.cli'`）

- [ ] **Step 3: 写实现 `insight/cli.py`**

```python
# -*- coding: utf-8 -*-
"""insight 命令行入口：crawl-once / run-daemon / status。"""

import argparse
from typing import Optional, Sequence

from insight import config
from insight.db import InsightDB
from insight.orchestrator import run_job


def _find_job(name: str) -> dict:
    for job in config.JOBS:
        if job["name"] == name:
            return job
    raise SystemExit(f"job not found: {name!r}. Known jobs: {[j['name'] for j in config.JOBS]}")


def cmd_crawl_once(args: argparse.Namespace) -> None:
    job = _find_job(args.name)
    result = run_job(job)
    print(result)


def cmd_run_daemon(args: argparse.Namespace) -> None:
    # 惰性导入：只有 run-daemon 需要 apscheduler
    from insight.scheduler.daemon import main as run_daemon
    run_daemon()


def cmd_status(args: argparse.Namespace) -> None:
    db = InsightDB(config.DB_PATH)
    db.init_schema()
    runs = db.recent_runs(args.limit)
    if not runs:
        print("(no runs yet)")
        return
    for run in runs:
        print(
            f"#{run['id']} {run['job_name']} [{run['crawler_type']}] "
            f"status={run['status']} exit={run['exit_code']} "
            f"notes={run['notes_crawled']} comments={run['comments_crawled']}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="insight")
    sub = parser.add_subparsers(dest="command", required=True)

    p_once = sub.add_parser("crawl-once", help="立即运行某个 job")
    p_once.add_argument("name", help="config.JOBS 中的 job 名")
    p_once.set_defaults(func=cmd_crawl_once)

    p_daemon = sub.add_parser("run-daemon", help="启动定时守护进程")
    p_daemon.set_defaults(func=cmd_run_daemon)

    p_status = sub.add_parser("status", help="查看最近的运行记录")
    p_status.add_argument("--limit", type=int, default=20)
    p_status.set_defaults(func=cmd_status)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/insight/test_cli.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: 全量回归 + 提交**

Run: `uv run --with "apscheduler>=3.10,<4" pytest tests/insight -v`
Expected: 全部 PASS（约 28 个用例）

```bash
git add insight/cli.py tests/insight/test_cli.py
git commit -m "feat(insight): cli 入口 crawl-once / run-daemon / status"
```

---

## Task 9: `insight/README.md` 与手动集成验证

**Files:**
- Create: `insight/README.md`

- [ ] **Step 1: 写 `insight/README.md`**

````markdown
# insight — 小红书评论定时采集（MediaCrawler 二次开发）

本包是对 MediaCrawler 的二次开发，**不修改任何上游文件**，全部代码在 `insight/` 内。
本期范围：定时爬取 + 原始数据入库（复用上游 SQLite）+ 运行日志。**不含文本分析**（后续迭代）。

## 一次性准备

```bash
# 1. 初始化上游 SQLite 表结构（创建 xhs_note / xhs_note_comment 等）
uv run python main.py --init_db sqlite

# 2. 确保已登录小红书（CDP 模式，复用本机 Chrome 登录态）
#    参见项目根 README 的 Chrome 远程调试配置
```

## 配置

编辑 `insight/config.py` 的 `JOBS` 列表（job 类型 search/detail/creator、关键词/笔记ID/创作者ID、触发时刻 hour/minute、max_notes 等）。

## 使用

```bash
# 立即跑一次某个 job（不依赖 apscheduler）
uv run python -m insight.cli crawl-once kw_daily

# 查看最近运行记录（不依赖 apscheduler）
uv run python -m insight.cli status --limit 20

# 启动定时守护进程（前台运行，Ctrl+C 退出；需 apscheduler）
uv run --with "apscheduler>=3.10,<4" python -m insight.cli run-daemon
```

> 守护进程为前台常驻进程；本机重启后需手动重新启动。

## 运行测试

```bash
uv run --with "apscheduler>=3.10,<4" pytest tests/insight -v
```

## 与上游 MediaCrawler 同步更新

```bash
# 一次性：添加上游远程
git remote add upstream https://github.com/NanmiCoder/MediaCrawler.git

# 定期同步
git fetch upstream
git merge upstream/main        # 或 git rebase upstream/main
```

因为本包全部是 `insight/` 下的新增文件、未改动任何上游文件，合并几乎不会冲突。
唯一与上游耦合的假设：
- 上游 CLI 参数（`--platform/--type/--keywords/--specified_id/--creator_id/--save_data_option` 等）保持不变；
- SQLite 路径仍为 `database/sqlite_tables.db`（见 `config/db_config.py`）；
- `main.main` / `main.async_cleanup` / `tools.app_runner.run` 接口保持不变。
同步后若上述任一处变化，只需相应调整 `insight/runner.py`、`insight/config.py`、`insight/crawl_entry.py`。
````

- [ ] **Step 2: 手动集成验证（需真实登录态，按需执行）**

> 这些是人工验证步骤，不是自动化测试。若当前环境无法登录小红书，记录为「待人工验证」并跳过。

1. 初始化表：`uv run python main.py --init_db sqlite` → 预期打印 `Database sqlite initialized successfully.`
2. 跑一次小批量 job（先把 `kw_daily` 的 `max_notes` 临时设为 2）：
   `uv run python -m insight.cli crawl-once kw_daily`
   预期：浏览器弹出/复用登录态完成爬取，命令结束打印形如 `{'run_id': 1, 'status': 'success', 'notes': N, 'comments': M}`。
3. 查看运行记录：`uv run python -m insight.cli status`
   预期：看到一条 `status=success` 记录，`notes`/`comments` 与上一步一致。
4. 验证守护进程可启动（把某 job 的 `hour/minute` 临时设为 1~2 分钟后的时刻）：
   `uv run --with "apscheduler>=3.10,<4" python -m insight.cli run-daemon`
   预期：打印 `scheduler started with N job(s)`，到点自动触发并在 `status` 中新增记录；`Ctrl+C` 可优雅退出。

- [ ] **Step 3: 提交**

```bash
git add insight/README.md
git commit -m "docs(insight): 使用说明与上游同步指南"
```

---

## Self-Review（计划编写者已执行）

**1. Spec 覆盖核对（对照设计文档各节）：**
- §2 隔离策略 → 全部代码在 `insight/`，零改上游文件（Task 1-9）；同步工作流写入 README（Task 9）。✅
- §3 目录结构 → Task 1 建包骨架，后续任务逐一落地各模块。✅
- §4 数据流（调度→子进程→入库→记录）→ orchestrator（Task 6）+ scheduler（Task 7）+ crawl_entry（Task 5）。✅
- §5.2 `insight_runs` 表 → schema.sql（Task 1）+ db.py（Task 2）。✅
- §6 Job 配置形态 → config.JOBS（Task 1）+ build_crawl_args（Task 3）。✅
- §7 运行环境（CDP 登录、常驻、依赖注入）→ README（Task 9）+ `--with` 注入策略（Task 7/8）。✅
- §8 错误处理（超时/退出码/幂等）→ run_crawl（Task 4）+ orchestrator 状态判定（Task 6）。✅
- §9 测试策略（runner/db/scheduler 隔离）→ Task 2-8 均含单测。✅
- §11 待定项已在「背景事实」中定稿：max_notes 用 env 注入（crawl_entry）、依赖用 `uv run --with` 注入、计数用前后差值。✅

**2. 占位符扫描：** 无 TODO/TBD/「类似上文」。`config.JOBS` 中的 `"请替换为真实笔记ID"` 是面向用户的配置占位说明，非计划缺口。✅

**3. 类型/签名一致性核对：**
- `CrawlResult(exit_code, timed_out, stderr_tail)` 在 runner 定义（Task 4），orchestrator 与测试一致引用（Task 6）。✅
- `InsightDB` 方法名 `init_schema/start_run/finish_run/count_rows/recent_runs` 在 db（Task 2）、orchestrator（Task 6）、cli（Task 8）一致。✅
- `build_crawl_args` / `run_crawl(job, timeout=None)` 在 runner（Task 3/4）定义，runner 测试与 orchestrator monkeypatch 签名一致。✅
- `build_scheduler(jobs=None, scheduler=None)` 在 daemon（Task 7）定义，测试一致。✅
- `run_job(job, db=None)` 在 orchestrator（Task 6）定义，cli（Task 8）按 `run_job(job)` 调用（db 默认从 config.DB_PATH 构造），一致。✅
