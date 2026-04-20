# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/routers/zhihu.py
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

router = APIRouter(prefix="/zhihu", tags=["zhihu"])

# Data directories
DATA_DIR = Path(__file__).parent.parent.parent / "data"
ZHIHU_DATA_DIR = DATA_DIR / "zhihu"
JSONL_DIR = ZHIHU_DATA_DIR / "jsonl"


def read_zhihu_jsonl_files() -> List[Dict[str, Any]]:
    """Read all Zhihu JSONL files and return list of answers.

    Returns:
        List of answer dictionaries sorted by created_time (newest first)
    """
    answers: List[Dict[str, Any]] = []

    if not JSONL_DIR.exists():
        return answers

    # Find all JSONL files
    try:
        jsonl_files = list(JSONL_DIR.glob("*.jsonl"))
    except OSError:
        return answers

    for jsonl_file in jsonl_files:
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        answer = json.loads(line)
                        # Only include answer type content
                        if answer.get("content_type") == "answer":
                            answers.append(answer)
                    except json.JSONDecodeError:
                        # Skip malformed JSON lines
                        continue
        except (OSError, IOError):
            # Skip files that cannot be read
            continue

    # Sort by created_time (newest first), handle None/0 values explicitly
    answers.sort(key=lambda x: x.get("created_time") or 0, reverse=True)

    return answers


def format_answer_for_response(answer: Dict[str, Any]) -> Dict[str, Any]:
    """Format an answer for API response"""
    return {
        "content_id": answer.get("content_id", ""),
        "content_type": answer.get("content_type", "answer"),
        "content_text": answer.get("content_text", ""),
        "content_url": answer.get("content_url", ""),
        "question_id": answer.get("question_id", ""),
        "desc": answer.get("desc", ""),
        "created_time": answer.get("created_time", 0),
        "updated_time": answer.get("updated_time", 0),
        "voteup_count": answer.get("voteup_count", 0),
        "comment_count": answer.get("comment_count", 0),
        "user_id": answer.get("user_id", ""),
        "user_link": answer.get("user_link", ""),
        "user_nickname": answer.get("user_nickname", "匿名用户"),
        "user_avatar": answer.get("user_avatar", ""),
        "user_url_token": answer.get("user_url_token", ""),
        "source_keyword": answer.get("source_keyword", ""),
    }


@router.get("")
async def list_answers(
    creator: Optional[str] = Query(None, max_length=100, description="Filter by creator (user_url_token)"),
    search: Optional[str] = Query(None, max_length=100, description="Search in content text"),
    offset: int = Query(0, ge=0, le=10000, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Number of results")
) -> Dict[str, Any]:
    """Get list of Zhihu answers with optional filtering"""
    answers = read_zhihu_jsonl_files()

    # Filter by creator (user_url_token)
    if creator:
        creator_lower = creator.lower()
        answers = [a for a in answers if creator_lower in (a.get("user_url_token", "") or "").lower()]

    # Filter by search text (content_text)
    if search:
        search_lower = search.lower()
        answers = [a for a in answers if search_lower in (a.get("content_text", "") or "").lower()]

    # Apply pagination
    total = len(answers)
    answers = answers[offset:offset + limit]

    # Format response
    formatted_answers = [format_answer_for_response(a) for a in answers]

    return {
        "answers": formatted_answers,
        "total": total,
        "offset": offset,
        "limit": limit
    }


@router.get("/stats")
async def get_zhihu_stats() -> Dict[str, Any]:
    """Get Zhihu answers statistics"""
    answers = read_zhihu_jsonl_files()

    # Calculate statistics
    total_answers = len(answers)
    total_voteup = 0
    total_comments = 0
    creators_stats = {}

    for answer in answers:
        # Count interactions
        total_voteup += answer.get("voteup_count", 0) or 0
        total_comments += answer.get("comment_count", 0) or 0

        # Count by creator
        creator_token = answer.get("user_url_token", "unknown")
        if creator_token:
            creators_stats[creator_token] = creators_stats.get(creator_token, 0) + 1

    # Get recent answers (last 5)
    recent_answers = [format_answer_for_response(a) for a in answers[:5]]

    return {
        "total_answers": total_answers,
        "total_voteup": total_voteup,
        "total_comments": total_comments,
        "creators_stats": creators_stats,
        "recent_answers": recent_answers,
        "last_updated": datetime.now().isoformat()
    }


@router.get("/creators")
async def get_creators() -> Dict[str, Any]:
    """Get list of unique creators (user_url_token)"""
    answers = read_zhihu_jsonl_files()

    creators = set()
    creator_info = {}
    for answer in answers:
        token = answer.get("user_url_token")
        if token:
            creators.add(token)
            # Store creator info for display
            if token not in creator_info:
                creator_info[token] = {
                    "nickname": answer.get("user_nickname", "匿名用户"),
                    "avatar": answer.get("user_avatar", ""),
                }

    return {
        "creators": sorted(list(creators)),
        "creator_info": creator_info
    }


# Valid content_id pattern: numeric
CONTENT_ID_PATTERN = re.compile(r'^[0-9]+$')


def validate_content_id(content_id: str) -> bool:
    """Validate content_id to prevent path traversal attacks."""
    if not content_id or len(content_id) > 32:
        return False
    return bool(CONTENT_ID_PATTERN.match(content_id))


@router.get("/{content_id}")
async def get_answer_detail(content_id: str) -> Dict[str, Any]:
    """Get single answer detail by ID."""
    # Validate content_id to prevent path traversal
    if not validate_content_id(content_id):
        raise HTTPException(status_code=400, detail="Invalid content ID format")

    answers = read_zhihu_jsonl_files()

    for answer in answers:
        if answer.get("content_id") == content_id:
            return format_answer_for_response(answer)

    raise HTTPException(status_code=404, detail="Answer not found")
