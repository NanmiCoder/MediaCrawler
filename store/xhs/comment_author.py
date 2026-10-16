# -*- coding: utf-8 -*-
"""Helpers for detecting and persisting Xiaohongshu author reply comment threads."""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Set

import config

# note_id -> post author user_id (from note detail, in-memory only)
_note_author_user_ids: Dict[str, str] = {}
# note_id -> top-level comment_id -> raw API comment (waiting for author reply)
_pending_top_comments: Dict[str, Dict[str, Dict]] = {}
_saved_comment_ids: Set[str] = set()


def reset_note_comment_session(note_id: str) -> None:
    """Clear per-note pending tops. Do not touch the global saved-id set:
    comment fetches for different notes may run concurrently."""
    _pending_top_comments.pop(note_id, None)


def clear_saved_comment_ids() -> None:
    _saved_comment_ids.clear()


def register_note_author(note_id: str, user_id: Optional[str]) -> None:
    if note_id and user_id:
        _note_author_user_ids[str(note_id)] = str(user_id)


def get_note_author_user_id(note_id: str) -> str:
    return _note_author_user_ids.get(str(note_id), "")


def show_tags_list(comment_item: Dict) -> List[str]:
    tags = comment_item.get("show_tags") or []
    if not isinstance(tags, list):
        return []
    result: List[str] = []
    for tag in tags:
        if isinstance(tag, str) and tag.strip():
            result.append(tag.strip())
        elif isinstance(tag, dict):
            for key in ("type", "name", "tag"):
                value = tag.get(key)
                if isinstance(value, str) and value.strip():
                    result.append(value.strip())
    return result


def comment_user_info(comment_item: Dict) -> Dict:
    user = comment_item.get("user_info") or comment_item.get("user") or {}
    return user if isinstance(user, dict) else {}


def comment_user_id(comment_item: Dict) -> str:
    user = comment_user_info(comment_item)
    return str(user.get("user_id") or user.get("userid") or user.get("id") or "")


_AUTHOR_TAG_ALIASES = {"is_author", "author", "作者", "帖主", "贴主"}


def is_author_comment(comment_item: Dict, note_author_user_id: str) -> bool:
    for tag in show_tags_list(comment_item):
        lowered = tag.lower()
        if tag in _AUTHOR_TAG_ALIASES or lowered in _AUTHOR_TAG_ALIASES or "author" in lowered:
            return True
    user_id = comment_user_id(comment_item)
    return bool(note_author_user_id and user_id and str(user_id) == str(note_author_user_id))


def is_top_level_comment(comment_item: Dict) -> bool:
    # Sub-comment pages often omit target_comment; the crawler stamps _root_comment_id.
    if comment_item.get("_root_comment_id"):
        return False
    target = comment_item.get("target_comment") or {}
    return not target.get("id")


def top_level_has_author_reply_inline(comment_item: Dict, note_author_user_id: str) -> bool:
    for sub in comment_item.get("sub_comments") or []:
        if isinstance(sub, dict) and is_author_comment(sub, note_author_user_id):
            return True
    return False


def resolve_root_comment_id(comment_item: Dict) -> str:
    root_id = comment_item.get("_root_comment_id")
    if root_id:
        return str(root_id)
    target = comment_item.get("target_comment") or {}
    return str(target.get("id") or "")


def remember_pending_top_comment(note_id: str, comment_item: Dict) -> None:
    comment_id = comment_item.get("id")
    if not comment_id:
        return
    _pending_top_comments.setdefault(note_id, {})[str(comment_id)] = comment_item


def pop_pending_top_comment(note_id: str, root_comment_id: str) -> Optional[Dict]:
    if not root_comment_id:
        return None
    pending = _pending_top_comments.get(note_id, {})
    return pending.pop(str(root_comment_id), None)


def flush_pending_top_comments(note_id: str) -> int:
    """Drop unsaved pending tops (no author reply discovered). Returns count dropped."""
    pending = _pending_top_comments.pop(note_id, {})
    return len(pending)


def mark_comment_saved(comment_id: str) -> bool:
    """Return False if this comment_id was already saved in the current run."""
    if not comment_id:
        return False
    cid = str(comment_id)
    if cid in _saved_comment_ids:
        return False
    _saved_comment_ids.add(cid)
    return True


def only_author_reply_threads_enabled() -> bool:
    override = os.getenv("XHS_SAVE_ONLY_AUTHOR_REPLY_THREADS")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes", "on"}
    return bool(getattr(config, "XHS_SAVE_ONLY_AUTHOR_REPLY_THREADS", False))
