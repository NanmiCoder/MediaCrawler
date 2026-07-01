"""Build first-version content_asset outputs from standardized task CSV files."""

import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


CONTENT_ASSET_FIELDNAMES = [
    "source_keyword",
    "platform",
    "video_id",
    "aweme_id",
    "aweme_url",
    "raw_title",
    "clean_title",
    "desc",
    "clean_desc",
    "topic",
    "pain_point",
    "teaching_angle",
    "nickname",
    "liked_count",
    "collected_count",
    "comment_count",
    "share_count",
    "total_engagement",
    "valid_comment_count",
    "top_valid_comments",
    "comment_pain_tags",
    "script_source_status",
    "script_source_quality",
    "script_clean_text",
    "script_clean_source",
    "script_clean_quality",
    "comment_data_status",
    "asr_data_status",
    "asset_quality",
    "created_at",
]


_MATCH_FIELDS = ("aweme_id", "video_id", "aweme_url")
_COMMENT_MATCH_FIELDS = ("aweme_id", "video_id")


def _empty_stats() -> Dict[str, Any]:
    return {
        "rows_in": 0,
        "rows_out": 0,
        "comments_available": 0,
        "scripts_available": 0,
        "valid_comments_total": 0,
        "asr_available": 0,
        "fallback_script_total": 0,
        "missing_script_total": 0,
        "content_asset_csv_generated": False,
        "errors": [],
    }


def _text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text == "None":
        return ""
    return text


def _safe_int(value: Any) -> int:
    try:
        if value is None or value == "":
            return 0
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).lower() in {"1", "true", "yes", "y", "on"}


def _read_csv(path: Optional[Path], label: str, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not path or not path.exists():
        stats["errors"].append(f"{label}_missing: {path or ''}")
        return []
    try:
        with open(str(path), "r", encoding="utf-8-sig", newline="") as f:
            return [dict(row) for row in csv.DictReader(f)]
    except Exception as exc:
        stats["errors"].append(f"{label}_read_failed: {str(exc)[:200]}")
        return []


def _build_index(
    rows: Iterable[Dict[str, Any]],
    fields: Tuple[str, ...] = _MATCH_FIELDS,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    index: Dict[str, Dict[str, Dict[str, Any]]] = {field: {} for field in fields}
    for row in rows:
        for field in fields:
            value = _text(row.get(field))
            if value and value not in index[field]:
                index[field][value] = row
    return index


def _find_match(
    index: Dict[str, Dict[str, Dict[str, Any]]],
    row: Dict[str, Any],
    fields: Tuple[str, ...] = _MATCH_FIELDS,
) -> Dict[str, Any]:
    for field in fields:
        value = _text(row.get(field))
        if value and value in index.get(field, {}):
            return index[field][value]
    return {}


def _dedupe(items: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for item in items:
        value = _text(item)
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _split_tags(value: Any) -> List[str]:
    tags: List[str] = []
    for part in _text(value).split("|"):
        part = part.strip()
        if part:
            tags.append(part)
    return tags


def _aggregate_comments(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    aliases: Dict[str, str] = {}

    for row in rows:
        if not _truthy(row.get("is_valid")):
            continue
        primary = _text(row.get("aweme_id")) or _text(row.get("video_id"))
        if not primary:
            continue
        bucket = grouped.setdefault(primary, {"count": 0, "comments": [], "tags": []})
        bucket["count"] += 1
        clean_content = _text(row.get("clean_content"))
        if clean_content and len(bucket["comments"]) < 3:
            bucket["comments"].append(clean_content)
        bucket["tags"].extend(_split_tags(row.get("pain_tags")))

        for field in _COMMENT_MATCH_FIELDS:
            value = _text(row.get(field))
            if value:
                aliases.setdefault(value, primary)

    index = {field: {} for field in _COMMENT_MATCH_FIELDS}
    for alias, primary in aliases.items():
        bucket = grouped[primary]
        aggregate = {
            "valid_comment_count": bucket["count"],
            "top_valid_comments": "|".join(bucket["comments"]),
            "comment_pain_tags": "|".join(_dedupe(bucket["tags"])),
        }
        for field in _COMMENT_MATCH_FIELDS:
            index[field][alias] = aggregate
    return index


def _comment_status(
    comments_clean_exists: bool,
    comment_row: Dict[str, Any],
) -> str:
    if not comments_clean_exists:
        return "pending_cdp"
    if _safe_int(comment_row.get("valid_comment_count")) > 0:
        return "available"
    return "empty"


def _asr_status(
    script_clean_exists: bool,
    script_source: Dict[str, Any],
    script_raw: Dict[str, Any],
    script_clean: Dict[str, Any],
) -> str:
    raw_status = _text(script_raw.get("asr_status")) or _text(script_clean.get("asr_status"))
    clean_source = _text(script_clean.get("script_clean_source"))
    clean_text = _text(script_clean.get("script_clean_text"))

    if raw_status == "dependency_missing":
        return "dependency_missing"
    if not script_clean_exists:
        if _truthy(script_source.get("source_asr_planned")):
            return "pending_asr"
        return "missing"
    if clean_source == "asr_raw" and clean_text:
        return "available"
    if clean_source == "source_clean_title" and clean_text:
        return "fallback_title"
    if clean_source == "source_title_desc" and clean_text:
        return "fallback_desc"
    return "missing"


def _asset_quality(row: Dict[str, Any]) -> str:
    valid_comments = _safe_int(row.get("valid_comment_count"))
    script_source = _text(row.get("script_clean_source"))
    script_text = _text(row.get("script_clean_text"))
    has_clean_title = bool(_text(row.get("clean_title")) or _text(row.get("clean_desc")))
    has_any_title = bool(
        _text(row.get("raw_title"))
        or _text(row.get("clean_title"))
        or _text(row.get("desc"))
        or _text(row.get("clean_desc"))
    )

    if valid_comments > 0 and script_source == "asr_raw" and script_text:
        return "high"
    if not has_any_title and not script_text:
        return "missing"
    if has_clean_title and script_source in {"source_clean_title", "source_title_desc"} and script_text:
        return "medium"
    if script_text and (
        row.get("comment_data_status") != "available"
        or row.get("asr_data_status") != "available"
    ):
        return "partial"
    return "low"


def _build_asset_row(
    search_row: Dict[str, Any],
    title_row: Dict[str, Any],
    comment_row: Dict[str, Any],
    script_source_row: Dict[str, Any],
    script_raw_row: Dict[str, Any],
    script_clean_row: Dict[str, Any],
    comments_clean_exists: bool,
    script_clean_exists: bool,
    created_at: str,
) -> Dict[str, Any]:
    liked = _safe_int(search_row.get("liked_count"))
    collected = _safe_int(search_row.get("collected_count"))
    comment_count = _safe_int(search_row.get("comment_count"))
    share = _safe_int(search_row.get("share_count"))
    total = _safe_int(search_row.get("total_engagement")) or liked + collected + comment_count + share

    clean_title = _text(title_row.get("clean_title")) or _text(search_row.get("clean_title"))
    clean_desc = _text(title_row.get("clean_desc")) or _text(search_row.get("clean_desc"))
    script_clean_text = _text(script_clean_row.get("script_clean_text"))
    script_clean_source = _text(script_clean_row.get("script_clean_source"))

    row: Dict[str, Any] = {
        "source_keyword": _text(search_row.get("source_keyword")),
        "platform": _text(search_row.get("platform")) or "douyin",
        "video_id": _text(search_row.get("video_id")) or _text(search_row.get("aweme_id")),
        "aweme_id": _text(search_row.get("aweme_id")),
        "aweme_url": _text(search_row.get("aweme_url")),
        "raw_title": _text(search_row.get("title")) or _text(title_row.get("raw_title")),
        "clean_title": clean_title,
        "desc": _text(search_row.get("desc")) or _text(title_row.get("raw_desc")),
        "clean_desc": clean_desc,
        "topic": _text(title_row.get("topic")),
        "pain_point": _text(title_row.get("pain_point")),
        "teaching_angle": _text(title_row.get("teaching_angle")),
        "nickname": _text(search_row.get("nickname")),
        "liked_count": liked,
        "collected_count": collected,
        "comment_count": comment_count,
        "share_count": share,
        "total_engagement": total,
        "valid_comment_count": _safe_int(comment_row.get("valid_comment_count")),
        "top_valid_comments": _text(comment_row.get("top_valid_comments")),
        "comment_pain_tags": _text(comment_row.get("comment_pain_tags")),
        "script_source_status": _text(script_source_row.get("script_source_status")),
        "script_source_quality": _text(script_source_row.get("script_source_quality")),
        "script_clean_text": script_clean_text,
        "script_clean_source": script_clean_source,
        "script_clean_quality": _text(script_clean_row.get("script_clean_quality")),
        "comment_data_status": _comment_status(comments_clean_exists, comment_row),
        "asr_data_status": _asr_status(
            script_clean_exists,
            script_source_row,
            script_raw_row,
            script_clean_row,
        ),
        "asset_quality": "",
        "created_at": created_at,
    }
    row["asset_quality"] = _asset_quality(row)
    return row


def build_content_asset(
    *,
    search_result_csv: Path,
    output_dir: Path,
    search_title_clean_csv: Optional[Path] = None,
    comments_clean_csv: Optional[Path] = None,
    script_sources_csv: Optional[Path] = None,
    script_raw_csv: Optional[Path] = None,
    script_clean_csv: Optional[Path] = None,
) -> Tuple[Path, Path, Dict[str, Any]]:
    """Generate content_asset.jsonl/csv and return their paths plus stats."""
    stats = _empty_stats()
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "content_asset.jsonl"
    csv_path = output_dir / "content_asset.csv"

    search_rows = _read_csv(search_result_csv, "search_result", stats)
    title_rows = _read_csv(search_title_clean_csv, "search_title_clean", stats)
    comments_clean_exists = bool(comments_clean_csv and comments_clean_csv.exists())
    comment_rows = _read_csv(comments_clean_csv, "comments_clean", stats)
    script_source_rows = _read_csv(script_sources_csv, "script_sources", stats)
    script_raw_rows = _read_csv(script_raw_csv, "script_raw", stats)
    script_clean_exists = bool(script_clean_csv and script_clean_csv.exists())
    script_clean_rows = _read_csv(script_clean_csv, "script_clean", stats)

    title_index = _build_index(title_rows)
    comment_index = _aggregate_comments(comment_rows)
    script_source_index = _build_index(script_source_rows)
    script_raw_index = _build_index(script_raw_rows)
    script_clean_index = _build_index(script_clean_rows)

    stats["rows_in"] = len(search_rows)
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows: List[Dict[str, Any]] = []
    for search_row in search_rows:
        title_row = _find_match(title_index, search_row)
        comment_row = _find_match(comment_index, search_row, _COMMENT_MATCH_FIELDS)
        script_source_row = _find_match(script_source_index, search_row)
        script_raw_row = _find_match(script_raw_index, search_row)
        script_clean_row = _find_match(script_clean_index, search_row)
        row = _build_asset_row(
            search_row,
            title_row,
            comment_row,
            script_source_row,
            script_raw_row,
            script_clean_row,
            comments_clean_exists,
            script_clean_exists,
            created_at,
        )
        rows.append(row)

    stats["rows_out"] = len(rows)
    stats["comments_available"] = sum(1 for row in rows if row["comment_data_status"] == "available")
    stats["scripts_available"] = sum(1 for row in rows if _text(row.get("script_clean_text")))
    stats["valid_comments_total"] = sum(_safe_int(row.get("valid_comment_count")) for row in rows)
    stats["asr_available"] = sum(1 for row in rows if row["asr_data_status"] == "available")
    stats["fallback_script_total"] = sum(
        1 for row in rows if row["asr_data_status"] in {"fallback_title", "fallback_desc"}
    )
    stats["missing_script_total"] = sum(
        1 for row in rows if not _text(row.get("script_clean_text"))
    )

    with open(str(jsonl_path), "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with open(str(csv_path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CONTENT_ASSET_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    stats["content_asset_csv_generated"] = True
    return jsonl_path, csv_path, stats
