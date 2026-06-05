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
