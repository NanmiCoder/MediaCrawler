# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_downloader/paths.py
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

"""媒体落盘路径规则：目录布局、文件名清洗、扩展名推断。

本模块全部为纯函数，不发起任何 IO（``ensure_within`` 会做路径解析）。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

# 允许落盘的扩展名白名单，白名单之外的推断结果一律丢弃
ALLOWED_EXTENSIONS = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".mp4",
        ".m4s",
        ".m4a",
        ".mp3",
        ".flv",
        ".mov",
    }
)

# Content-Type -> 扩展名（只取主类型，忽略 charset 等参数）
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/x-flv": ".flv",
    "video/x-m4v": ".mp4",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/aac": ".m4a",
}

_ILLEGAL_CHARS = re.compile(r"[^A-Za-z0-9._-]")
# 从 URL 路径里提取扩展名，兼容 "img.jpg!large" 这类 CDN 后缀写法
_URL_EXTENSION = re.compile(r"\.([A-Za-z0-9]{2,5})(?:!.*)?$")
_WINDOWS_RESERVED = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)
MAX_COMPONENT_LENGTH = 64
MEDIA_DIR_NAME = "media"


def url_fingerprint(url: str) -> str:
    """URL 的短指纹，用于命名下载中的临时文件，URL 变化时自动作废旧片段"""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]


def redact_url(url) -> str:
    """日志安全的 URL 表示：去掉 query（媒体直链常带签名参数）。

    对非字符串输入返回占位符——它常被用在异常处理路径里，自身抛异常会掩盖原始错误。
    """
    if not isinstance(url, str):
        return "<invalid-url>"
    try:
        parts = urlsplit(url)
    except ValueError:
        return "<invalid-url>"
    if not parts.scheme or not parts.netloc:
        return "<invalid-url>"
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


def sanitize_component(value: str, fallback: str = "unknown") -> str:
    """清洗单个路径片段，防止路径穿越与非法字符。

    - 只保留 ``[A-Za-z0-9._-]``，其余替换为 ``_``
    - 去掉开头的 ``.``，避免隐藏文件与 ``..``
    - 命中 Windows 保留设备名时加前缀
    - 超长截断
    """
    cleaned = _ILLEGAL_CHARS.sub("_", (value or "").strip())
    cleaned = cleaned.lstrip(".")
    cleaned = cleaned.replace("..", "_")
    cleaned = cleaned[:MAX_COMPONENT_LENGTH]
    if not cleaned:
        return fallback
    if cleaned.split(".")[0].upper() in _WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned


def guess_extension(
    url: str = "",
    content_type: Optional[str] = None,
    explicit: Optional[str] = None,
    default: str = ".bin",
) -> str:
    """推断文件扩展名，优先级：显式指定 > URL 后缀 > Content-Type > 默认值。

    只返回白名单内的扩展名（default 除外，由调用方保证合理）。
    """
    if explicit:
        normalized = explicit if explicit.startswith(".") else f".{explicit}"
        normalized = normalized.lower()
        if normalized in ALLOWED_EXTENSIONS:
            return normalized

    if url:
        path = urlsplit(url).path
        match = _URL_EXTENSION.search(path)
        if match:
            candidate = f".{match.group(1).lower()}"
            if candidate in ALLOWED_EXTENSIONS:
                return candidate

    if content_type:
        main_type = content_type.split(";")[0].strip().lower()
        candidate = CONTENT_TYPE_EXTENSIONS.get(main_type)
        if candidate:
            return candidate

    return default


def build_media_dir(base_dir: Path, platform: str, content_id) -> Path:
    """媒体目录：``{base}/{platform}/media/{content_id}``

    content_id 来自外部响应，可能是 int 或 None，先归一成字符串再清洗。
    """
    safe_platform = sanitize_component(platform, "unknown")
    raw_content_id = "" if content_id is None else str(content_id)
    safe_content_id = sanitize_component(
        raw_content_id, fallback=hashlib.sha1(raw_content_id.encode("utf-8")).hexdigest()[:16]
    )
    return Path(base_dir) / safe_platform / MEDIA_DIR_NAME / safe_content_id


def build_file_path(directory: Path, stem: str, extension: str) -> Path:
    """目录内的媒体文件路径：``{directory}/{stem}{ext}``"""
    safe_stem = sanitize_component(stem, "media")
    normalized_ext = extension if extension.startswith(".") else f".{extension}"
    return Path(directory) / f"{safe_stem}{normalized_ext.lower()}"


def build_media_path(
    base_dir: Path,
    platform: str,
    content_id: str,
    stem: str,
    extension: str,
) -> Path:
    """媒体文件最终路径：``{base}/{platform}/media/{content_id}/{stem}{ext}``"""
    return build_file_path(build_media_dir(base_dir, platform, content_id), stem, extension)


def ensure_within(base_dir: Path, target: Path) -> Path:
    """校验目标路径位于 base_dir 之内，返回解析后的绝对路径。

    防止外部响应里的 content_id 构造出越界路径。
    """
    base_resolved = Path(base_dir).resolve()
    target_resolved = Path(target).resolve()
    if not target_resolved.is_relative_to(base_resolved):
        raise ValueError(f"媒体落盘路径越界: {target_resolved} 不在 {base_resolved} 之内")
    return target_resolved
