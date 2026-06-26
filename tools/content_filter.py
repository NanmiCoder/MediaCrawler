# -*- coding: utf-8 -*-
import json
import re
from collections.abc import Callable
from typing import Any, Iterable, TypeVar


T = TypeVar("T")


class ContentFilterError(ValueError):
    pass


MetricGetter = Callable[[Any], Any]


def _dig(item: Any, *path: str) -> Any:
    value = item
    for key in path:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            value = getattr(value, key, None)
        if value is None:
            return None
    return value


def _first_value(*getters: MetricGetter) -> MetricGetter:
    def getter(item: Any) -> Any:
        for get_value in getters:
            value = get_value(item)
            if value not in (None, ""):
                return value
        return None

    return getter


METRIC_GETTERS: dict[str, dict[str, MetricGetter]] = {
    "xhs": {
        "liked_count": _first_value(lambda item: _dig(item, "interact_info", "liked_count"), lambda item: _dig(item, "liked_count")),
        "collected_count": _first_value(lambda item: _dig(item, "interact_info", "collected_count"), lambda item: _dig(item, "collected_count")),
        "comment_count": _first_value(lambda item: _dig(item, "interact_info", "comment_count"), lambda item: _dig(item, "comment_count")),
        "share_count": _first_value(lambda item: _dig(item, "interact_info", "share_count"), lambda item: _dig(item, "share_count")),
    },
    "dy": {
        "liked_count": _first_value(lambda item: _dig(item, "statistics", "digg_count"), lambda item: _dig(item, "liked_count")),
        "collected_count": _first_value(lambda item: _dig(item, "statistics", "collect_count"), lambda item: _dig(item, "collected_count")),
        "comment_count": _first_value(lambda item: _dig(item, "statistics", "comment_count"), lambda item: _dig(item, "comment_count")),
        "share_count": _first_value(lambda item: _dig(item, "statistics", "share_count"), lambda item: _dig(item, "share_count")),
    },
    "ks": {
        "liked_count": _first_value(lambda item: _dig(item, "photo", "realLikeCount"), lambda item: _dig(item, "liked_count")),
        "view_count": _first_value(lambda item: _dig(item, "photo", "viewCount"), lambda item: _dig(item, "view_count"), lambda item: _dig(item, "viewd_count")),
    },
    "bili": {
        "liked_count": _first_value(lambda item: _dig(item, "View", "stat", "like"), lambda item: _dig(item, "liked_count")),
        "disliked_count": _first_value(lambda item: _dig(item, "View", "stat", "dislike"), lambda item: _dig(item, "disliked_count")),
        "play_count": _first_value(lambda item: _dig(item, "View", "stat", "view"), lambda item: _dig(item, "video_play_count"), lambda item: _dig(item, "play_count")),
        "favorite_count": _first_value(lambda item: _dig(item, "View", "stat", "favorite"), lambda item: _dig(item, "video_favorite_count"), lambda item: _dig(item, "favorite_count")),
        "share_count": _first_value(lambda item: _dig(item, "View", "stat", "share"), lambda item: _dig(item, "video_share_count"), lambda item: _dig(item, "share_count")),
        "coin_count": _first_value(lambda item: _dig(item, "View", "stat", "coin"), lambda item: _dig(item, "video_coin_count"), lambda item: _dig(item, "coin_count")),
        "danmaku_count": _first_value(lambda item: _dig(item, "View", "stat", "danmaku"), lambda item: _dig(item, "video_danmaku"), lambda item: _dig(item, "danmaku_count")),
        "comment_count": _first_value(lambda item: _dig(item, "View", "stat", "reply"), lambda item: _dig(item, "video_comment"), lambda item: _dig(item, "comment_count")),
    },
    "wb": {
        "liked_count": _first_value(lambda item: _dig(item, "mblog", "attitudes_count"), lambda item: _dig(item, "liked_count")),
        "comment_count": _first_value(lambda item: _dig(item, "mblog", "comments_count"), lambda item: _dig(item, "comments_count"), lambda item: _dig(item, "comment_count")),
        "share_count": _first_value(lambda item: _dig(item, "mblog", "reposts_count"), lambda item: _dig(item, "shared_count"), lambda item: _dig(item, "share_count")),
    },
    "tieba": {
        "reply_count": _first_value(lambda item: _dig(item, "total_replay_num"), lambda item: _dig(item, "total_reply_num"), lambda item: _dig(item, "reply_count")),
        "reply_page_count": _first_value(lambda item: _dig(item, "total_replay_page"), lambda item: _dig(item, "total_reply_page"), lambda item: _dig(item, "reply_page_count")),
    },
    "zhihu": {
        "voteup_count": _first_value(lambda item: _dig(item, "voteup_count")),
        "comment_count": _first_value(lambda item: _dig(item, "comment_count")),
    },
}


ALIASES: dict[str, dict[str, str]] = {
    "xhs": {"like_count": "liked_count", "collect_count": "collected_count"},
    "dy": {"like_count": "liked_count", "collect_count": "collected_count"},
    "ks": {"viewd_count": "view_count", "like_count": "liked_count"},
    "bili": {
        "like_count": "liked_count",
        "view_count": "play_count",
        "video_play_count": "play_count",
        "video_favorite_count": "favorite_count",
        "video_share_count": "share_count",
        "video_coin_count": "coin_count",
        "video_danmaku": "danmaku_count",
        "video_comment": "comment_count",
        "reply_count": "comment_count",
    },
    "wb": {"like_count": "liked_count", "comments_count": "comment_count", "shared_count": "share_count", "reposts_count": "share_count"},
    "tieba": {"total_replay_num": "reply_count", "total_reply_num": "reply_count", "total_replay_page": "reply_page_count", "total_reply_page": "reply_page_count"},
    "zhihu": {"like_count": "voteup_count"},
}


def parse_content_filters(value: Any) -> dict[str, Any]:
    if value in (None, "", {}):
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ContentFilterError(f"content_filters must be valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ContentFilterError("content_filters must be a JSON object")
    return value


def normalize_content_filters(platform: str, filters: Any) -> dict[str, dict[str, float]]:
    raw_filters = parse_content_filters(filters)
    if not raw_filters:
        return {}

    platform_getters = METRIC_GETTERS.get(platform)
    if not platform_getters:
        raise ContentFilterError(f"unsupported platform for content filters: {platform}")

    aliases = ALIASES.get(platform, {})
    normalized: dict[str, dict[str, float]] = {}
    for raw_name, raw_rule in raw_filters.items():
        metric = aliases.get(raw_name, raw_name)
        if metric not in platform_getters:
            supported = ", ".join(sorted(platform_getters))
            raise ContentFilterError(f"unsupported content filter field for {platform}: {raw_name}. Supported: {supported}")
        normalized[metric] = _normalize_rule(raw_rule, raw_name)
    return normalized


def filter_content_items(platform: str, items: Iterable[T], filters: Any = None) -> list[T]:
    rules = normalize_content_filters(platform, _current_filters() if filters is None else filters)
    if not rules:
        return list(items)
    return [item for item in items if match_content_filter(platform, item, rules)]


def match_content_filter(platform: str, item: Any, filters: Any = None) -> bool:
    rules = normalize_content_filters(platform, _current_filters() if filters is None else filters)
    if not rules:
        return True

    getters = METRIC_GETTERS[platform]
    for metric, rule in rules.items():
        value = _parse_number(getters[metric](item))
        if value is None:
            return False
        if "min" in rule and value < rule["min"]:
            return False
        if "max" in rule and value > rule["max"]:
            return False
    return True


def log_filter_result(platform: str, source: str, total: int, kept: int, logger: Any) -> None:
    if total == kept:
        return
    logger.info(f"[content_filter] platform={platform}, source={source}, kept={kept}, skipped={total - kept}, total={total}")


def supported_filter_fields(platform: str) -> list[str]:
    return sorted(METRIC_GETTERS.get(platform, {}))


def _current_filters() -> Any:
    import config

    return getattr(config, "CONTENT_FILTERS", {})


def _normalize_rule(rule: Any, field_name: str) -> dict[str, float]:
    if isinstance(rule, (int, float, str)) and not isinstance(rule, bool):
        value = _parse_number(rule)
        if value is None:
            raise ContentFilterError(f"content filter field {field_name} has invalid value: {rule}")
        return {"min": value}
    if not isinstance(rule, dict):
        raise ContentFilterError(f"content filter field {field_name} must use min/max object")

    normalized: dict[str, float] = {}
    for bound in ("min", "max"):
        if bound not in rule or rule[bound] in (None, ""):
            continue
        value = _parse_number(rule[bound])
        if value is None:
            raise ContentFilterError(f"content filter field {field_name}.{bound} has invalid value: {rule[bound]}")
        normalized[bound] = value
    if not normalized:
        raise ContentFilterError(f"content filter field {field_name} must include min or max")
    if "min" in normalized and "max" in normalized and normalized["min"] > normalized["max"]:
        raise ContentFilterError(f"content filter field {field_name} min cannot exceed max")
    return normalized


def _parse_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(",", "")
    if not text:
        return None
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*([万亿wWkK]?)", text)
    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2).lower()
    multiplier = {"万": 10_000, "亿": 100_000_000, "w": 10_000, "k": 1_000}.get(unit, 1)
    return number * multiplier
