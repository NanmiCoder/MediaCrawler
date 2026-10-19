# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/weibo/media.py
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

"""微博媒体地址提取。

输入是微博 ``mblog``，输出是可下载的 ``MediaItem`` 列表。无 IO（少数平台会读取 config 决定策略）。

图片需要特殊处理：微博图床有防盗链，且缩略图路径里带尺寸段，
统一改写为 ``large`` 清晰度后经 i1.wp.com 代理访问。
"""

from __future__ import annotations

from typing import Dict, List
from urllib.parse import urlsplit

from media_downloader import MediaItem, MediaType

# 微博图床存在防盗链，统一走该图片代理访问
WEIBO_IMAGE_AGENT_HOST = "https://i1.wp.com/"

# 视频地址字段，按清晰度从高到低尝试
_VIDEO_KEYS = (
    "mp4_1080p_mp4",
    "mp4_hd_mp4",
    "mp4_720p_mp4",
    "hevc_mp4_hd",
    "mp4_ld_mp4",
    "stream_url",
)


def rewrite_image_url(raw_url: str) -> str:
    """把微博图床地址改写为 large 清晰度并加图片代理前缀。

    ``https://wx1.sinaimg.cn/orj360/abc.jpg``
    -> ``https://i1.wp.com/wx1.sinaimg.cn/large/abc.jpg``
    """
    parts = urlsplit(raw_url)
    if not parts.scheme or not parts.netloc:
        return raw_url

    segments = [segment for segment in parts.path.split("/") if segment]
    if segments:
        segments[0] = "large"  # 原始路径首段是尺寸标识（orj360 / thumbnail 等）

    path = "/" + "/".join(segments) if segments else parts.path
    return f"{WEIBO_IMAGE_AGENT_HOST}{parts.netloc}{path}"


def extract_image_urls(mblog: Dict) -> List[str]:
    """提取微博配图地址（已改写为可访问地址）"""
    urls: List[str] = []
    for pic in mblog.get("pics") or []:
        if isinstance(pic, str):
            raw_url = pic
        elif isinstance(pic, dict):
            raw_url = pic.get("url") or ""
        else:
            continue
        if isinstance(raw_url, str) and raw_url:
            urls.append(rewrite_image_url(raw_url))
    return urls


def extract_video_urls(mblog: Dict) -> List[str]:
    """提取微博视频地址候选列表（按清晰度从高到低）"""
    page_info = mblog.get("page_info") or {}
    if not isinstance(page_info, dict):
        return []
    if page_info.get("type") != "video" and not page_info.get("media_info"):
        return []

    urls: List[str] = []
    for container_key in ("media_info", "urls"):
        container = page_info.get(container_key) or {}
        if not isinstance(container, dict):
            continue
        for key in _VIDEO_KEYS:
            url = container.get(key)
            if isinstance(url, str) and url and url not in urls:
                urls.append(url)
    return urls


def extract_cover_url(mblog: Dict) -> str:
    """提取视频封面地址"""
    page_info = mblog.get("page_info") or {}
    if not isinstance(page_info, dict):
        return ""
    page_pic = page_info.get("page_pic") or {}
    if isinstance(page_pic, dict):
        url = page_pic.get("url")
        return url if isinstance(url, str) else ""
    return ""


def media_source_mblog(mblog: Dict) -> Dict:
    """返回真正承载媒体内容的那一层微博。

    纯转发的 ``pics`` / ``page_info`` 位于 ``retweeted_status`` 里，顶层两者皆无；
    不处理的话转发帖会静默地一条媒体都下载不到。
    若转发时自己带了图（顶层有媒体），则以顶层为准。
    """
    if mblog.get("pics") or mblog.get("page_info"):
        return mblog

    retweeted = mblog.get("retweeted_status")
    if isinstance(retweeted, dict):
        return retweeted
    return mblog


def build_media_items(mblog: Dict) -> List[MediaItem]:
    """把一条微博转换成待下载的媒体任务列表。

    - 视频微博：封面 + 视频（配图通常就是封面，不重复下载）
    - 普通微博：各张配图
    - 转发微博：取原博的媒体，目录仍按转发帖自身的 id 组织
    """
    if not isinstance(mblog, dict):
        return []

    content_id = mblog.get("id") or mblog.get("mid") or ""
    if not content_id:
        return []
    content_id = str(content_id)

    source = media_source_mblog(mblog)
    items: List[MediaItem] = []

    video_urls = extract_video_urls(source)
    if video_urls:
        cover_url = extract_cover_url(source)
        if cover_url:
            items.append(
                MediaItem(
                    url=cover_url,
                    media_type=MediaType.IMAGE,
                    content_id=content_id,
                    stem="cover",
                )
            )
        items.append(
            MediaItem(
                url=video_urls[0],
                backup_urls=tuple(video_urls[1:]),
                media_type=MediaType.VIDEO,
                content_id=content_id,
                stem="video",
            )
        )
        return items

    for index, image_url in enumerate(extract_image_urls(source), start=1):
        items.append(
            MediaItem(
                url=image_url,
                media_type=MediaType.IMAGE,
                content_id=content_id,
                stem=f"{index:03d}",
            )
        )

    return items
