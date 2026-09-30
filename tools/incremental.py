# -*- coding: utf-8 -*-
"""Load the app's single newest-first rule. Do not reimplement it here.

The parent process points `CRAWL_INCREMENTAL_MODULE` at
`app/services/incremental.py`. Standalone runs fall back to the sibling
checkout of that same file.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Dict

_DEFAULT = (
    Path(__file__).resolve().parents[2]
    / "AI-Financial-Analysis"
    / "backend"
    / "app"
    / "services"
    / "incremental.py"
)


def _load():
    configured = os.environ.get("CRAWL_INCREMENTAL_MODULE", "").strip()
    path = Path(configured) if configured else _DEFAULT
    if not path.is_file():
        raise ImportError(f"找不到增量采集规则：{path}")
    spec = importlib.util.spec_from_file_location("app_crawl_incremental", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载增量采集规则：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_policy = _load()
collect_newest = _policy.collect_newest
load_known_content_ids = _policy.load_known_content_ids


def xhs_note_id(note: Dict) -> str:
    return str(note.get("note_id") or note.get("id") or "").strip()


def xhs_note_is_pinned(note: Dict) -> bool:
    sticky = note.get("sticky")
    if sticky in (True, 1, "1", "true", "True"):
        return True
    tags = note.get("corner_tag_info")
    texts = []
    if isinstance(tags, dict):
        texts.append(str(tags.get("text") or ""))
    elif isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict):
                texts.append(str(tag.get("text") or ""))
            else:
                texts.append(str(tag))
    return any("置顶" in text for text in texts)
