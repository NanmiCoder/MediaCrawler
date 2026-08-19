# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/routers/notes.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import os
import re
import json
import glob
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/notes", tags=["notes"])

# Data directories
DATA_DIR = Path(__file__).parent.parent.parent / "data"
XHS_DATA_DIR = DATA_DIR / "xhs"
JSONL_DIR = XHS_DATA_DIR / "jsonl"
IMAGES_DIR = XHS_DATA_DIR / "images"


def parse_interaction_count(count_str: str) -> int:
    """Parse Chinese interaction count format like '1.1万' to integer.

    Supports formats:
    - Plain numbers: "1234", "1,234"
    - Chinese units: "1.5万" (15,000), "2亿" (200,000,000)
    - English units: "1.5w" (15,000), "2k" (2,000)
    """
    if not count_str:
        return 0
    count_str = str(count_str).strip()
    try:
        # Handle Chinese units
        if "亿" in count_str:
            num = float(count_str.replace("亿", ""))
            return int(num * 100_000_000)
        if "万" in count_str:
            num = float(count_str.replace("万", ""))
            return int(num * 10000)
        # Handle English units
        lower_str = count_str.lower()
        if "w" in lower_str:
            num = float(lower_str.replace("w", ""))
            return int(num * 10000)
        if "k" in lower_str:
            num = float(lower_str.replace("k", ""))
            return int(num * 1000)
        # Plain number
        clean_str = count_str.replace("+", "").replace(",", "")
        return int(float(clean_str))
    except (ValueError, AttributeError, TypeError):
        return 0


# Valid note_id pattern: alphanumeric with underscores and hyphens
NOTE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


def validate_note_id(note_id: str) -> bool:
    """Validate note_id to prevent path traversal attacks."""
    if not note_id or len(note_id) > 64:
        return False
    return bool(NOTE_ID_PATTERN.match(note_id))


def get_local_image_count(note_id: str) -> int:
    """Get the count of local images for a note.

    Args:
        note_id: The note identifier (validated before use)

    Returns:
        Number of image files found, or 0 if directory doesn't exist
    """
    # Validate note_id to prevent path traversal
    if not validate_note_id(note_id):
        return 0

    note_image_dir = IMAGES_DIR / note_id

    # Ensure path is within IMAGES_DIR (additional safety check)
    try:
        note_image_dir.resolve().relative_to(IMAGES_DIR.resolve())
    except (ValueError, OSError):
        return 0

    if not note_image_dir.exists():
        return 0

    # Count image files using a single iteration
    count = 0
    try:
        for f in note_image_dir.iterdir():
            if f.suffix.lower() in ('.jpg', '.jpeg', '.webp', '.png'):
                count += 1
    except OSError:
        return 0
    return count


def read_jsonl_files() -> List[Dict[str, Any]]:
    """Read all JSONL files and return list of notes.

    Returns:
        List of note dictionaries sorted by time (newest first)
    """
    notes: List[Dict[str, Any]] = []

    if not JSONL_DIR.exists():
        return notes

    # Find all JSONL files
    try:
        jsonl_files = list(JSONL_DIR.glob("*.jsonl"))
    except OSError:
        return notes

    for jsonl_file in jsonl_files:
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        note = json.loads(line)
                        # Add local image count
                        note["local_image_count"] = get_local_image_count(note.get("note_id", ""))
                        notes.append(note)
                    except json.JSONDecodeError:
                        # Skip malformed JSON lines
                        continue
        except (OSError, IOError):
            # Skip files that cannot be read
            continue

    # Sort by time (newest first), handle None/0 values explicitly
    notes.sort(key=lambda x: x.get("time") or 0, reverse=True)

    return notes


def format_note_for_response(note: Dict[str, Any]) -> Dict[str, Any]:
    """Format a note for API response"""
    note_id = note.get("note_id", "")
    local_image_count = note.get("local_image_count", 0)

    return {
        "note_id": note_id,
        "type": note.get("type", "normal"),
        "title": note.get("title", ""),
        "desc": note.get("desc", ""),
        "nickname": note.get("nickname", ""),
        "avatar": note.get("avatar", ""),
        "liked_count": note.get("liked_count", "0"),
        "liked_count_num": parse_interaction_count(note.get("liked_count", "0")),
        "collected_count": note.get("collected_count", "0"),
        "collected_count_num": parse_interaction_count(note.get("collected_count", "0")),
        "comment_count": note.get("comment_count", "0"),
        "share_count": note.get("share_count", "0"),
        "tag_list": note.get("tag_list", "").split(",") if note.get("tag_list") else [],
        "source_keyword": note.get("source_keyword", ""),
        "note_url": note.get("note_url", ""),
        "time": note.get("time", 0),
        "image_count": local_image_count,
        "first_image_url": f"/images/{note_id}/0.jpg" if local_image_count > 0 else None,
        "video_url": note.get("video_url", ""),
    }


@router.get("")
async def list_notes(
    keyword: Optional[str] = Query(None, max_length=50, description="Filter by source keyword"),
    search: Optional[str] = Query(None, max_length=100, description="Search in title"),
    offset: int = Query(0, ge=0, le=10000, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Number of results")
) -> Dict[str, Any]:
    """Get list of notes with optional filtering"""
    notes = read_jsonl_files()

    # Filter by keyword (source_keyword)
    if keyword:
        keyword_lower = keyword.lower()
        notes = [n for n in notes if keyword_lower in (n.get("source_keyword", "") or "").lower()]

    # Filter by search text (title)
    if search:
        search_lower = search.lower()
        notes = [n for n in notes if search_lower in (n.get("title", "") or "").lower()]

    # Apply pagination
    total = len(notes)
    notes = notes[offset:offset + limit]

    # Format response
    formatted_notes = [format_note_for_response(n) for n in notes]

    return {
        "notes": formatted_notes,
        "total": total,
        "offset": offset,
        "limit": limit
    }


@router.get("/stats")
async def get_notes_stats() -> Dict[str, Any]:
    """Get notes statistics"""
    notes = read_jsonl_files()

    # Calculate statistics
    total_notes = len(notes)
    total_images = 0
    keywords_stats = {}

    for note in notes:
        # Count images
        total_images += note.get("local_image_count", 0)

        # Count by keyword
        keyword = note.get("source_keyword", "unknown")
        if keyword:
            keywords_stats[keyword] = keywords_stats.get(keyword, 0) + 1

    # Get recent notes (last 5)
    recent_notes = [format_note_for_response(n) for n in notes[:5]]

    return {
        "total_notes": total_notes,
        "total_images": total_images,
        "keywords_stats": keywords_stats,
        "recent_notes": recent_notes,
        "last_updated": datetime.now().isoformat()
    }


@router.get("/{note_id}")
async def get_note_detail(note_id: str) -> Dict[str, Any]:
    """Get single note detail by ID."""
    # Validate note_id to prevent path traversal
    if not validate_note_id(note_id):
        raise HTTPException(status_code=400, detail="Invalid note ID format")

    notes = read_jsonl_files()

    for note in notes:
        if note.get("note_id") == note_id:
            formatted = format_note_for_response(note)

            # Add all local image URLs
            local_image_count = note.get("local_image_count", 0)
            formatted["image_urls"] = [
                f"/images/{note_id}/{i}.jpg"
                for i in range(local_image_count)
            ]

            return formatted

    raise HTTPException(status_code=404, detail="Note not found")


@router.get("/keywords")
async def get_keywords() -> Dict[str, Any]:
    """Get list of unique keywords"""
    notes = read_jsonl_files()

    keywords = set()
    for note in notes:
        keyword = note.get("source_keyword")
        if keyword:
            keywords.add(keyword)

    return {
        "keywords": sorted(list(keywords))
    }
