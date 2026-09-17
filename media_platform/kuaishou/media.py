# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/kuaishou/media.py
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

"""快手媒体地址提取。

输入是快手作品详情（``{"photo": {...}, "author": {...}}``），
输出是可下载的 ``MediaItem`` 列表。无 IO（少数平台会读取 config 决定策略）。
"""

from __future__ import annotations

from typing import Dict, List

from media_downloader import MediaItem, MediaType


def _first_url(urls) -> str:
    """从 url 列表里取第一个非空字符串"""
    if isinstance(urls, str):
        return urls
    for url in urls or []:
        if isinstance(url, str) and url:
            return url
    return ""


def _photo_of(video_item: Dict) -> Dict:
    """接口响应里 photo 字段可能是字符串或 None，统一收敛为 dict"""
    photo = video_item.get("photo")
    return photo if isinstance(photo, dict) else {}


def _extract_representation_url(codec_resource) -> str:
    """从 videoResource.{hevc,h264} 的 adaptationSet 里取第一个播放地址"""
    if not isinstance(codec_resource, dict):
        return ""
    for adaptation in codec_resource.get("adaptationSet") or []:
        if not isinstance(adaptation, dict):
            continue
        for representation in adaptation.get("representation") or []:
            if isinstance(representation, dict) and representation.get("url"):
                return representation["url"]
    return ""


def extract_video_urls(video_item: Dict) -> List[str]:
    """提取视频地址候选列表（H265 优先，画质与体积更优）"""
    photo = _photo_of(video_item)
    if not photo:
        return []

    video_resource = photo.get("videoResource") if isinstance(photo.get("videoResource"), dict) else {}
    candidates = [
        photo.get("photoH265Url"),
        photo.get("photoUrl"),
        _extract_representation_url(video_resource.get("hevc")),
        _extract_representation_url(video_resource.get("h264")),
        # 详情接口另有 manifest.adaptationSet[].representation[].url 一份等价描述，
        # search 接口的 photo 对象字段更少时靠它兜底
        _extract_representation_url(photo.get("manifest")),
    ]

    urls: List[str] = []
    for candidate in candidates:
        if candidate and isinstance(candidate, str) and candidate not in urls:
            urls.append(candidate)
    return urls


def extract_cover_url(video_item: Dict) -> str:
    """提取视频封面地址"""
    photo = _photo_of(video_item)
    if not photo:
        return ""

    for candidate in (
        photo.get("coverUrl"),
        _first_url([entry.get("url") for entry in photo.get("coverUrls") or [] if isinstance(entry, dict)]),
        photo.get("animatedCoverUrl"),
    ):
        if isinstance(candidate, str) and candidate:
            return candidate
    return ""


def build_media_items(video_item: Dict) -> List[MediaItem]:
    """把一个快手作品转换成待下载的媒体任务列表：封面 + 视频"""
    if not isinstance(video_item, dict):
        return []

    content_id = _photo_of(video_item).get("id")
    if not content_id:
        return []

    content_id = str(content_id)
    items: List[MediaItem] = []

    cover_url = extract_cover_url(video_item)
    if cover_url:
        items.append(
            MediaItem(
                url=cover_url,
                media_type=MediaType.IMAGE,
                content_id=content_id,
                stem="cover",
            )
        )

    video_urls = extract_video_urls(video_item)
    if video_urls:
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
