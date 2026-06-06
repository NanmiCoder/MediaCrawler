# -*- coding: utf-8 -*-
"""把 job 配置转成爬虫命令行参数，并以子进程方式运行爬虫。"""

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional

from insight import config as insight_config

# Windows 默认 console 是 cp1252，print 中文会触发 UnicodeEncodeError。
# 切到 utf-8 + errors='replace' 避免实时日志进程被这一行打挂。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

VALID_TYPES = {"search", "detail", "creator"}

# 注入子进程环境：绕开 Mihomo/Clash 等 fake-IP 代理对 localhost 的劫持
_BYPASS_HOSTS = "localhost,127.0.0.1,::1"


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
    """以子进程运行爬虫入口，实时把子进程 stdout 转发到父进程。

    - max_notes 通过环境变量 INSIGHT_MAX_NOTES 注入
    - 默认把 NO_PROXY/no_proxy 设为 localhost/127.0.0.1，绕开 Mihomo/Clash 的 fake-IP 劫持
    """
    timeout = timeout if timeout is not None else insight_config.SUBPROCESS_TIMEOUT
    args = build_crawl_args(job)
    cmd = [sys.executable, "-u", "-m", "insight.crawl_entry", *args]

    env = dict(os.environ)
    env.setdefault("NO_PROXY", _BYPASS_HOSTS)
    env.setdefault("no_proxy", _BYPASS_HOSTS)
    if job.get("max_notes"):
        env["INSIGHT_MAX_NOTES"] = str(job["max_notes"])

    proc = subprocess.Popen(
        cmd,
        cwd=insight_config.PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # 合并到 stdout，统一顺序
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    output_lines: List[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="", flush=True)  # 实时转发给父进程终端
            output_lines.append(line)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return CrawlResult(
            exit_code=-1,
            timed_out=True,
            stderr_tail="".join(output_lines)[-2000:],
        )

    return CrawlResult(
        exit_code=proc.returncode,
        timed_out=False,
        stderr_tail="".join(output_lines)[-2000:],
    )
