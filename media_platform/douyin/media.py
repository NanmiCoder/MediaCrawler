# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/douyin/media.py
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

"""抖音媒体地址提取。

输入是抖音作品详情（``/aweme/v1/web/aweme/detail/`` 的响应），
输出是可下载的 ``MediaItem`` 列表。无 IO（少数平台会读取 config 决定策略）。
"""

from __future__ import annotations

from typing import Dict, List

from media_downloader import MediaItem, MediaType

# 视频清晰度字段，按优先级排列（h264 与 256 通常为无水印源）
_VIDEO_ADDR_KEYS = ("play_addr_h264", "play_addr_256", "play_addr")

# 封面字段，按优先级排列
_COVER_KEYS = ("raw_cover", "origin_cover", "cover", "dynamic_cover")


def _url_list_of(container) -> List[str]:
    """接口响应里同名字段可能是字符串或 None，统一收敛为 url 列表"""
    if not isinstance(container, dict):
        return []
    return [url for url in (container.get("url_list") or []) if url and isinstance(url, str)]


def extract_image_urls(aweme_detail: Dict) -> List[str]:
    """提取图集作品的图片地址（url_list 的最后一个通常是无水印原图）"""
    urls: List[str] = []
    for image in aweme_detail.get("images") or []:
        candidates = _url_list_of(image)
        if candidates:
            urls.append(candidates[-1])
    return urls


def extract_cover_url(aweme_detail: Dict) -> str:
    """提取视频封面地址"""
    video_item = aweme_detail.get("video")
    if not isinstance(video_item, dict):
        return ""
    for key in _COVER_KEYS:
        candidates = _url_list_of(video_item.get(key))
        if candidates:
            return candidates[-1]
    return ""


def extract_video_urls(aweme_detail: Dict) -> List[str]:
    """提取视频地址候选列表。

    同一档清晰度会返回多个 CDN 地址，优先取 url_list 最后一个（通常无水印），
    其余地址作为备用；主地址全部不可用时依次降级到更低清晰度档位。
    """
    video_item = aweme_detail.get("video")
    if not isinstance(video_item, dict):
        return []

    for key in _VIDEO_ADDR_KEYS:
        candidates = _url_list_of(video_item.get(key))
        if candidates:
            return list(reversed(candidates))

    # 兜底：bit_rate 列表里码率最高的那一档
    bit_rates = [entry for entry in (video_item.get("bit_rate") or []) if isinstance(entry, dict)]
    for entry in sorted(bit_rates, key=lambda item: item.get("bit_rate", 0), reverse=True):
        candidates = _url_list_of(entry.get("play_addr"))
        if candidates:
            return list(reversed(candidates))

    return []


def build_media_items(aweme_item: Dict) -> List[MediaItem]:
    """把一个抖音作品转换成待下载的媒体任务列表。

    - 图集作品：各张图片（第一张即封面，不再单独下载一份 cover）
    - 视频作品：封面 + 视频
    """
    if not isinstance(aweme_item, dict):
        return []

    content_id = aweme_item.get("aweme_id") or ""
    if not content_id:
        return []

    items: List[MediaItem] = []

    image_urls = extract_image_urls(aweme_item)
    if image_urls:
        for index, image_url in enumerate(image_urls, start=1):
            items.append(
                MediaItem(
                    url=image_url,
                    media_type=MediaType.IMAGE,
                    content_id=content_id,
                    stem=f"{index:03d}",
                )
            )
        return items

    cover_url = extract_cover_url(aweme_item)
    if cover_url:
        items.append(
            MediaItem(
                url=cover_url,
                media_type=MediaType.IMAGE,
                content_id=content_id,
                stem="cover",
            )
        )

    video_urls = extract_video_urls(aweme_item)
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
