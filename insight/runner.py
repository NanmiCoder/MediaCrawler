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
