# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/xhs/media.py
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

"""小红书媒体地址提取。

输入是 ``/api/sns/web/v1/feed`` 返回的原始 ``note_card``（snake_case 字段），
输出是下载器可直接消费的 ``MediaItem`` 列表。无 IO（会读取 config 决定国际版策略）。
"""

from __future__ import annotations

from typing import Dict, List

import config
from media_downloader import MediaItem, MediaType

# 小红书视频 CDN：origin_video_key 拼在此域名后可拿到无水印源片
XHS_VIDEO_CDN_HOST = "https://sns-video-bd.xhscdn.com"


def _as_dict(value) -> Dict:
    """接口响应里同名字段可能是字符串或 None，统一收敛为 dict"""
    return value if isinstance(value, dict) else {}


def _extract_origin_video_key(video_dict: Dict) -> str:
    """从 video.consumer 中取无水印源片 key（兼容 snake_case 与 camelCase）"""
    consumer = _as_dict(video_dict.get("consumer"))
    return consumer.get("origin_video_key") or consumer.get("originVideoKey") or ""


def _to_int(value, default: int = 0) -> int:
    """接口偶尔把 height/bitrate 返回成字符串，排序前统一转 int"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _stream_quality_key(item: Dict) -> tuple:
    """分档排序 key：分辨率优先，其次平均码率"""
    return (_to_int(item.get("height")), _to_int(item.get("avg_bitrate")))


def _iter_stream_items(stream: Dict) -> List[Dict]:
    """摊平 stream 下的全部分档条目。

    分档名上游换过两代：早期按编码命名（h264/h265/av1），现在按内部档位命名
    （EF4/EF5/EF6/EF7）。这里刻意不写死任何分档名——凡是列表都当候选，
    以后再改名也不会像 ``stream["h264"]`` 那样静默取空。
    """
    return [
        item
        for bucket in stream.values()
        if isinstance(bucket, list)
        for item in bucket
        if isinstance(item, dict) and item.get("master_url")
    ]


def extract_video_urls(note_item: Dict) -> List[str]:
    """提取视频地址候选列表，按可用性排序。

    优先无水印源片（origin_video_key），其余按清晰度从高到低排。
    同一分档内含多个分辨率（720P→4K），取最高的作主地址，其余交给下载器回退。
    国际版（rednote）的 CDN 域名与国内不同，不能拼接 xhscdn 域名。
    """
    if note_item.get("type") != "video":
        return []

    video_dict = _as_dict(note_item.get("video"))
    if not video_dict:
        return []

    urls: List[str] = []
    origin_video_key = _extract_origin_video_key(video_dict)
    if origin_video_key and not getattr(config, "XHS_INTERNATIONAL", False):
        urls.append(f"{XHS_VIDEO_CDN_HOST}/{origin_video_key}")

    stream = _as_dict(_as_dict(video_dict.get("media")).get("stream"))
    ranked = sorted(_iter_stream_items(stream), key=_stream_quality_key, reverse=True)
    for item in ranked:
        master_url = item["master_url"]
        if master_url not in urls:
            urls.append(master_url)

    return urls


def extract_image_urls(note_item: Dict) -> List[str]:
    """提取图文笔记的图片地址（按原始顺序）"""
    urls: List[str] = []
    for image_item in note_item.get("image_list") or []:
        if not isinstance(image_item, dict):
            continue
        url = image_item.get("url_default") or image_item.get("url") or ""
        if isinstance(url, str) and url:
            urls.append(url)
    return urls


def extract_cover_url(note_item: Dict) -> str:
    """提取封面地址。

    小红书不同接口返回的封面字段位置不一致，这里按可靠性依次兜底；
    视频笔记的 image_list 通常就是封面图，作为最后兜底。
    """
    video_dict = _as_dict(note_item.get("video"))
    cover_dict = _as_dict(note_item.get("cover"))
    video_cover = _as_dict(video_dict.get("cover"))

    candidates = [
        video_cover.get("url_default"),
        video_cover.get("url"),
        cover_dict.get("url_default"),
        cover_dict.get("url"),
    ]
    for candidate in candidates:
        if candidate:
            return candidate

    images = extract_image_urls(note_item)
    return images[0] if images else ""


def build_media_items(note_item: Dict) -> List[MediaItem]:
    """把一个笔记转换成待下载的媒体任务列表。

    - 视频笔记：封面 + 视频。其 image_list 通常只有封面一张，不再按图集重复下载
    - 图文笔记：各张图片（第一张即封面，因此不再单独下载一份 cover）
    """
    if not isinstance(note_item, dict):
        return []

    content_id = note_item.get("note_id") or note_item.get("id") or ""
    if not content_id:
        return []

    items: List[MediaItem] = []

    if note_item.get("type") == "video":
        cover_url = extract_cover_url(note_item)
        if cover_url:
            items.append(
                MediaItem(
                    url=cover_url,
                    media_type=MediaType.IMAGE,
                    content_id=content_id,
                    stem="cover",
                )
            )

        video_urls = extract_video_urls(note_item)
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
    else:
        for index, image_url in enumerate(extract_image_urls(note_item), start=1):
            items.append(
                MediaItem(
                    url=image_url,
                    media_type=MediaType.IMAGE,
                    content_id=content_id,
                    stem=f"{index:03d}",
                )
            )

    return items
