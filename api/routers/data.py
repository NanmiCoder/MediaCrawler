# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/routers/data.py
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
import glob
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

router = APIRouter(prefix="/data", tags=["data"])

# Data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"


def get_file_info(file_path: Path) -> dict:
    """Get file information"""
    stat = file_path.stat()
    record_count = None

    # Try to get record count
    try:
        if file_path.suffix.lower() == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    record_count = len(data)
        elif file_path.suffix.lower() == ".jsonl":
            # jsonl 每行一个 JSON 对象,统计非空行数
            with open(file_path, "r", encoding="utf-8") as f:
                record_count = sum(1 for line in f if line.strip())
        elif file_path.suffix.lower() == ".csv":
            with open(file_path, "r", encoding="utf-8") as f:
                record_count = sum(1 for _ in f) - 1  # Subtract header row
    except Exception:
        pass

    return {
        "name": file_path.name,
        "path": str(file_path.relative_to(DATA_DIR)),
        "size": stat.st_size,
        "modified_at": stat.st_mtime,
        "record_count": record_count,
        "type": file_path.suffix[1:] if file_path.suffix else "unknown"
    }


@router.get("/files")
async def list_data_files(platform: Optional[str] = None, file_type: Optional[str] = None):
    """Get data file list"""
    if not DATA_DIR.exists():
        return {"files": []}

    files = []
    supported_extensions = {".json", ".jsonl", ".csv", ".xlsx", ".xls"}

    for root, dirs, filenames in os.walk(DATA_DIR):
        root_path = Path(root)
        for filename in filenames:
            file_path = root_path / filename
            if file_path.suffix.lower() not in supported_extensions:
                continue

            # Platform filter
            if platform:
                rel_path = str(file_path.relative_to(DATA_DIR))
                if platform.lower() not in rel_path.lower():
                    continue

            # Type filter
            if file_type and file_path.suffix[1:].lower() != file_type.lower():
                continue

            try:
                files.append(get_file_info(file_path))
            except Exception:
                continue

    # Sort by modification time (newest first)
    files.sort(key=lambda x: x["modified_at"], reverse=True)

    return {"files": files}


@router.get("/files/{file_path:path}")
async def get_file_content(file_path: str, preview: bool = True, limit: int = 100):
    """Get file content or preview"""
    full_path = DATA_DIR / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    # Security check: ensure within DATA_DIR
    try:
        full_path.resolve().relative_to(DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if preview:
        # Return preview data
        try:
            if full_path.suffix.lower() == ".json":
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return {"data": data[:limit], "total": len(data)}
                    return {"data": data, "total": 1}
            elif full_path.suffix.lower() == ".jsonl":
                # jsonl: 每行一个 JSON 对象,逐行解析,返回前 limit 条
                rows = []
                total = 0
                with open(full_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        total += 1
                        if len(rows) < limit:
                            try:
                                rows.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
                return {"data": rows, "total": total}
            elif full_path.suffix == ".csv":
                import csv
                with open(full_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    rows = []
                    for i, row in enumerate(reader):
                        if i >= limit:
                            break
                        rows.append(row)
                    # Re-read to get total count
                    f.seek(0)
                    total = sum(1 for _ in f) - 1
                    return {"data": rows, "total": total}
            elif full_path.suffix.lower() in (".xlsx", ".xls"):
                import pandas as pd
                # Read first limit rows
                df = pd.read_excel(full_path, nrows=limit)
                # Get total row count (only read first column to save memory)
                df_count = pd.read_excel(full_path, usecols=[0])
                total = len(df_count)
                # Convert to list of dictionaries, handle NaN values
                rows = df.where(pd.notnull(df), None).to_dict(orient='records')
                return {
                    "data": rows,
                    "total": total,
                    "columns": list(df.columns)
                }
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type for preview")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Return file download
        return FileResponse(
            path=full_path,
            filename=full_path.name,
            media_type="application/octet-stream"
        )


@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """Download file"""
    full_path = DATA_DIR / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    # Security check
    try:
        full_path.resolve().relative_to(DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        path=full_path,
        filename=full_path.name,
        media_type="application/octet-stream"
    )


@router.get("/stats")
async def get_data_stats():
    """Get data statistics"""
    if not DATA_DIR.exists():
        return {"total_files": 0, "total_size": 0, "by_platform": {}, "by_type": {}}

    stats = {
        "total_files": 0,
        "total_size": 0,
        "by_platform": {},
        "by_type": {}
    }

    supported_extensions = {".json", ".jsonl", ".csv", ".xlsx", ".xls"}

    for root, dirs, filenames in os.walk(DATA_DIR):
        root_path = Path(root)
        for filename in filenames:
            file_path = root_path / filename
            if file_path.suffix.lower() not in supported_extensions:
                continue

            try:
                stat = file_path.stat()
                stats["total_files"] += 1
                stats["total_size"] += stat.st_size

                # Statistics by type
                file_type = file_path.suffix[1:].lower()
                stats["by_type"][file_type] = stats["by_type"].get(file_type, 0) + 1

                # Statistics by platform (inferred from path)
                rel_path = str(file_path.relative_to(DATA_DIR))
                for platform in ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"]:
                    if platform in rel_path.lower():
                        stats["by_platform"][platform] = stats["by_platform"].get(platform, 0) + 1
                        break
            except Exception:
                continue

    return stats


# ==================== BGM 播放相关 ====================

# aweme_id 合法字符（防路径穿越）
_AWEME_ID_RE = re.compile(r"^[A-Za-z0-9]+$")

# BGM 文件扩展名优先级（glob bgm.* 后按此排序取第一个）
_BGM_EXT_PRIORITY = [".m4a", ".mp3", ".mp4", ".m4v"]

# 扩展名 → MIME 映射
_BGM_MIME = {
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".mp4": "audio/mp4",
    ".m4v": "audio/mp4",
}


@router.get("/bgm/playlist")
async def get_bgm_playlist(run_id: Optional[str] = None):
    """
    读取 BGM 播放清单，按 run 分组返回。

    扫描所有 data/douyin/jsonl/search_bgm_playlist_*.jsonl（不只最新），按 aweme_id
    去重（保留最大 add_ts）。每条 track 带 run_id/keyword/add_ts/has_local。
    groups 按 run_id 分组并合并 run_history 元信息（关键词/开始时间/状态）。
    可用 ?run_id= 过滤单个运行。历史数据无 run_id 归 "unattributed" 组。
    """
    playlist_dir = DATA_DIR / "douyin" / "jsonl"
    if not playlist_dir.exists():
        return {"tracks": [], "groups": []}

    # 收集所有 bgm_playlist jsonl，按 mtime 倒序（新文件优先，去重时保留新记录）
    candidates = sorted(
        playlist_dir.glob("search_bgm_playlist_*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    tracks_by_id: dict[str, dict] = {}
    for fpath in candidates:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    aweme_id = item.get("aweme_id", "")
                    if not aweme_id:
                        continue
                    existing = tracks_by_id.get(aweme_id)
                    if existing and existing.get("add_ts", 0) >= item.get("add_ts", 0):
                        continue
                    tracks_by_id[aweme_id] = item
        except Exception:
            continue

    # 组装扁平 tracks（带 run_id）+ 按 run 分组
    tracks = []
    groups_map: dict[str, dict] = {}
    for aweme_id, item in tracks_by_id.items():
        rid = item.get("run_id") or "unattributed"
        if run_id and rid != run_id:
            continue
        track = {
            "aweme_id": aweme_id,
            "music_title": item.get("music_title", ""),
            "music_author": item.get("music_author", ""),
            "music_duration": item.get("music_duration", 0),
            "aweme_url": item.get("aweme_url", ""),
            "has_local": _resolve_bgm_file(aweme_id) is not None,
            "run_id": rid,
            "keyword": item.get("keyword", ""),
            "add_ts": item.get("add_ts", 0),
        }
        tracks.append(track)
        g = groups_map.setdefault(rid, {"run_id": rid, "keyword": track["keyword"], "tracks": []})
        g["tracks"].append(track)

    groups = _enrich_run_groups(groups_map)
    return {"tracks": tracks, "groups": groups}


def _resolve_bgm_file(aweme_id: str) -> Optional[Path]:
    """
    按 aweme_id 解析磁盘上的 BGM 音频文件。

    不信任 jsonl 里的 local_path（实测可能为空或扩展名不一致），
    直接 glob data/douyin/bgm/<aweme_id>/bgm.*，按优先级取第一个。
    返回 None 表示找不到。
    """
    if not _AWEME_ID_RE.match(aweme_id):
        return None
    bgm_dir = DATA_DIR / "douyin" / "bgm" / aweme_id
    if not bgm_dir.exists():
        return None
    # glob bgm.*
    candidates = list(bgm_dir.glob("bgm.*"))
    if not candidates:
        return None
    # 按优先级排序
    candidates.sort(key=lambda p: _BGM_EXT_PRIORITY.index(p.suffix.lower()) if p.suffix.lower() in _BGM_EXT_PRIORITY else 99)
    return candidates[0]


# BGM 场景标签标注文件（aweme_id -> 场景名）
_BGM_TAGS_PATH = DATA_DIR / ".bgm_tags.json"


def _load_bgm_tags() -> dict:
    """读取 BGM 场景标签映射。文件不存在或损坏返回空 dict。"""
    if not _BGM_TAGS_PATH.exists():
        return {}
    try:
        with open(_BGM_TAGS_PATH, "r", encoding="utf-8") as f:
            tags = json.load(f)
            return tags if isinstance(tags, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_bgm_tags(tags: dict) -> None:
    """原子写 BGM 场景标签（tmp + os.replace）。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _BGM_TAGS_PATH.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(tags, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _BGM_TAGS_PATH)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


@router.get("/bgm/tags")
async def get_bgm_tags():
    """读取全部 BGM 场景标签（{aweme_id: scene}）。必须在 /bgm/{aweme_id} 之前声明。"""
    return {"tags": _load_bgm_tags()}


@router.put("/bgm/scene/{aweme_id}")
async def update_bgm_scene(aweme_id: str, body: Optional[dict] = None):
    """
    设置/更新某 BGM 的场景标签。body: {"scene": "婚礼"}；空字符串=清除标签。
    路径用 /bgm/scene/{aweme_id} 避免被 GET /bgm/{aweme_id} 吞掉。
    """
    if not _AWEME_ID_RE.match(aweme_id):
        raise HTTPException(status_code=400, detail="Invalid aweme_id")
    scene = ""
    if body and isinstance(body, dict):
        scene = str(body.get("scene", "")).strip()
    tags = _load_bgm_tags()
    if scene:
        tags[aweme_id] = scene
    else:
        tags.pop(aweme_id, None)
    _save_bgm_tags(tags)
    return {"aweme_id": aweme_id, "scene": scene}


@router.get("/bgm/{aweme_id}")
async def stream_bgm(aweme_id: str, request: Request):
    """
    流式播放指定 aweme_id 的 BGM 音频。

    手动实现 HTTP Range 支持（Starlette 0.37 FileResponse 不处理 Range），
    让 <audio> 标签可拖动进度条。aweme_id 正则校验防路径穿越，扩展名服务端解析。
    """
    if not _AWEME_ID_RE.match(aweme_id):
        raise HTTPException(status_code=400, detail="Invalid aweme_id")

    bgm_file = _resolve_bgm_file(aweme_id)
    if bgm_file is None or not bgm_file.is_file():
        raise HTTPException(status_code=404, detail="BGM file not found")

    # 路径逃逸防护
    try:
        bgm_file.resolve().relative_to(DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    mime = _BGM_MIME.get(bgm_file.suffix.lower(), "application/octet-stream")
    file_size = bgm_file.stat().st_size

    # 解析 Range header（支持 bytes=start-end / bytes=start- / bytes=-suffix）
    range_header = request.headers.get("range")
    if range_header and range_header.startswith("bytes="):
        range_spec = range_header[6:].strip()
        try:
            start_str, end_str = range_spec.split("-", 1)
            start = int(start_str) if start_str else None
            end = int(end_str) if end_str else None
            if start is None and end is not None:
                # bytes=-N → 最后 N 字节
                start = max(0, file_size - end)
                end = file_size - 1
            elif start is not None and end is None:
                # bytes=N- → 从 N 到末尾
                end = file_size - 1
            elif start is not None and end is not None:
                end = min(end, file_size - 1)
            else:
                raise ValueError
            if start < 0 or start >= file_size or start > end:
                raise ValueError
        except (ValueError, IndexError):
            raise HTTPException(status_code=416, detail="Invalid range")

        content_length = end - start + 1

        def _range_iter():
            with open(bgm_file, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk = f.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Disposition": "inline",
        }
        return StreamingResponse(_range_iter(), status_code=206, media_type=mime, headers=headers)

    # 无 Range header：返回全量
    return FileResponse(path=str(bgm_file), media_type=mime, content_disposition_type="inline")


# ==================== Run 分组 / BGM 删除 / 场景标签 / 评论 ====================

_UNATTRIBUTED = "unattributed"


def _enrich_run_groups(groups_map: dict) -> list:
    """
    合并 run_history 元信息（关键词/开始时间/爬取类型/状态）到每个分组。
    无 run_id 的分组标 status="historical"。按 started_at 倒序，unattributed 沉底。
    """
    from ..services import run_history  # 函数内 import，避免顶层循环依赖

    try:
        runs = {r.get("run_id"): r for r in run_history.load_runs()}
    except Exception:
        runs = {}

    result = []
    for rid, g in groups_map.items():
        r = runs.get(rid, {})
        g["keyword"] = r.get("keywords") or g.get("keyword", "")
        g["started_at"] = r.get("started_at")
        g["crawler_type"] = r.get("crawler_type")
        g["status"] = "historical" if rid == _UNATTRIBUTED else r.get("status")
        g["track_count"] = len(g.get("tracks", []))
        g["comment_count"] = len(g.get("comments", []))
        result.append(g)

    # 有 started_at 按时间倒序；unattributed 沉底
    result.sort(key=lambda x: x.get("started_at") or "", reverse=True)
    result.sort(key=lambda x: x["run_id"] == _UNATTRIBUTED)
    return result


@router.delete("/bgm/{aweme_id}")
async def delete_bgm_track(aweme_id: str, delete_audio: bool = False):
    """
    从所有 BGM playlist jsonl 中移除指定 aweme_id 的记录。
    delete_audio=True 时同时删除磁盘上的音频文件。
    原子重写（tmp + os.replace）保证并发安全。
    """
    if not _AWEME_ID_RE.match(aweme_id):
        raise HTTPException(status_code=400, detail="Invalid aweme_id")

    playlist_dir = DATA_DIR / "douyin" / "jsonl"
    removed_rows = 0
    if playlist_dir.exists():
        for fpath in playlist_dir.glob("search_bgm_playlist_*.jsonl"):
            removed_rows += _remove_aweme_from_jsonl(fpath, aweme_id)

    audio_deleted = False
    if delete_audio:
        bgm_dir = DATA_DIR / "douyin" / "bgm" / aweme_id
        if bgm_dir.exists():
            for f in bgm_dir.glob("bgm.*"):
                try:
                    f.unlink(missing_ok=True)
                    audio_deleted = True
                except Exception:
                    continue

    return {"removed_rows": removed_rows, "audio_deleted": audio_deleted}


def _remove_aweme_from_jsonl(fpath: Path, aweme_id: str) -> int:
    """
    从 jsonl 文件移除所有 aweme_id 匹配行，原子重写。返回移除行数。
    保留其余行原样（含 run_id 字段）。
    """
    if not fpath.exists():
        return 0
    kept_lines: list[str] = []
    removed = 0
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    kept_lines.append(line)
                    continue
                try:
                    item = json.loads(stripped)
                except json.JSONDecodeError:
                    kept_lines.append(line)
                    continue
                if str(item.get("aweme_id", "")) == aweme_id:
                    removed += 1
                    continue
                kept_lines.append(line)
    except Exception:
        return 0

    if removed == 0:
        return 0

    # 原子写：tmp → os.replace
    tmp = fpath.with_suffix(fpath.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            for line in kept_lines:
                f.write(line if line.endswith("\n") else line + "\n")
        os.replace(tmp, fpath)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        return 0
    return removed


# ---------- 评论按 run 分组 ----------

@router.get("/comments/playlist")
async def get_comments_playlist(run_id: Optional[str] = None, limit_per_run: int = 200):
    """
    读取评论清单，按 run 分组返回。

    扫描所有 data/douyin/jsonl/search_comments_*.jsonl，每条评论取
    comment_id/aweme_id/nickname/content/like_count/create_time/sub_comment_count/run_id。
    按 run_id 分组，每组最多 limit_per_run 条展示，count 记总数。
    可用 ?run_id= 过滤。历史无 run_id 评论归 "unattributed" 组。
    """
    comments_dir = DATA_DIR / "douyin" / "jsonl"
    if not comments_dir.exists():
        return {"groups": []}

    candidates = sorted(
        comments_dir.glob("search_comments_*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    groups_map: dict[str, dict] = {}
    for fpath in candidates:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    rid = item.get("run_id") or _UNATTRIBUTED
                    if run_id and rid != run_id:
                        continue
                    comment = {
                        "comment_id": item.get("comment_id", ""),
                        "aweme_id": item.get("aweme_id", ""),
                        "nickname": item.get("nickname", ""),
                        "content": item.get("content", ""),
                        "like_count": item.get("like_count", 0),
                        "create_time": item.get("create_time"),
                        "sub_comment_count": item.get("sub_comment_count", 0),
                        "run_id": rid,
                    }
                    g = groups_map.setdefault(rid, {"run_id": rid, "comments": [], "count": 0})
                    if len(g["comments"]) < limit_per_run:
                        g["comments"].append(comment)
                    g["count"] += 1
        except Exception:
            continue

    groups = _enrich_run_groups(groups_map)
    return {"groups": groups}

