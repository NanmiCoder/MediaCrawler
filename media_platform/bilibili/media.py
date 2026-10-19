# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/bilibili/media.py
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

"""B 站媒体地址提取与流选择。

B 站的播放地址需要先调 playurl 接口获取：
- ``fnval=DASH_FNVAL`` 返回音视频分轨的 DASH 流，画质最好，但需要 ffmpeg 合流
- ``fnval=MP4_FNVAL`` 返回音视频合一的 mp4 直链，无需外部依赖，但清晰度受限

本模块只做纯计算，接口调用与降级编排由 core 负责。
"""

from __future__ import annotations

from typing import Dict, List, Optional

import config
from media_downloader import MediaItem, MediaType

# fnval 位掩码：16(DASH) | 64(HDR) | 128(4K) | 256(Dolby Audio) | 512(Dolby Vision) | 1024(8K) | 2048(AV1)
DASH_FNVAL = 4048
# 请求音视频合一的 mp4 直链
MP4_FNVAL = 1

# B 站 codecid：7=AVC(H.264) 12=HEVC(H.265) 13=AV1 14=AV2
# 同一清晰度下优先 AVC：下载后的文件要进剪辑软件/播放器，H.264 的兼容性最好
_CODEC_PRIORITY = {7: 0, 13: 1, 12: 2}
_UNKNOWN_CODEC_PRIORITY = 3


def _as_dict(value) -> Dict:
    """接口响应里同名字段可能是字符串或 None，统一收敛为 dict"""
    return value if isinstance(value, dict) else {}


def _stream_url(stream) -> str:
    if not isinstance(stream, dict):
        return ""
    return stream.get("base_url") or stream.get("baseUrl") or ""


def _to_int(value, default: int = 0) -> int:
    """接口偶尔把 id/bandwidth 返回成字符串，排序与比较前统一转 int"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _stream_sort_key(stream: Dict) -> tuple:
    """同清晰度下把兼容性最好的编码排在后面（取 [-1] 即选中它）"""
    codec_rank = _CODEC_PRIORITY.get(_to_int(stream.get("codecid"), -1), _UNKNOWN_CODEC_PRIORITY)
    return (_to_int(stream.get("id")), -codec_rank, _to_int(stream.get("bandwidth")))


def _stream_backup_urls(stream) -> tuple:
    if not isinstance(stream, dict):
        return ()
    backups = stream.get("backup_url") or stream.get("backupUrl") or []
    return tuple(url for url in backups if isinstance(url, str) and url)


def build_cover_item(view: Dict, content_id: str) -> Optional[MediaItem]:
    """封面地址来自稿件详情里的 pic 字段"""
    cover_url = _as_dict(view).get("pic")
    if not isinstance(cover_url, str) or not cover_url:
        return None
    return MediaItem(
        url=cover_url,
        media_type=MediaType.IMAGE,
        content_id=content_id,
        stem="cover",
    )


def pick_video_stream(play_info: Dict, preferred_quality: Optional[int] = None) -> Optional[Dict]:
    """挑选视频流：优先不超过用户清晰度设置的最高档，都超出时取最低档。

    同一清晰度可能同时提供 AVC/HEVC/AV1 多种编码，按 ``_CODEC_PRIORITY``
    取兼容性最好的那一种（排序 key 让优先级高的排在末尾）。
    """
    if preferred_quality is None:
        preferred_quality = getattr(config, "BILI_QN", 80)

    dash = _as_dict(play_info).get("dash")
    if not isinstance(dash, dict):
        return None
    streams = [stream for stream in (dash.get("video") or []) if _stream_url(stream)]
    if not streams:
        return None

    streams.sort(key=_stream_sort_key)
    within_quality = [stream for stream in streams if _to_int(stream.get("id")) <= preferred_quality]
    if within_quality:
        return within_quality[-1]

    # 所有档位都超过用户设置时取最低清晰度，但编码优先级仍要生效：
    # 排序把每个 id 档内兼容性最好的编码放在该档最后，所以要在同 id 组里取最后一个
    lowest_id = _to_int(streams[0].get("id"))
    same_quality = [stream for stream in streams if _to_int(stream.get("id")) == lowest_id]
    return same_quality[-1]


def pick_audio_stream(play_info: Dict) -> Optional[Dict]:
    """音频流取码率最高的一档（id 越大码率越高）"""
    dash = _as_dict(play_info).get("dash")
    if not isinstance(dash, dict):
        return None
    streams = [stream for stream in (dash.get("audio") or []) if _stream_url(stream)]
    if not streams:
        return None
    return max(streams, key=lambda stream: (_to_int(stream.get("id")), _to_int(stream.get("bandwidth"))))


def build_dash_item(play_info: Dict, content_id: str, preferred_quality: Optional[int] = None) -> Optional[MediaItem]:
    """构建 DASH 下载任务（视频轨 + 音频轨，交由下载器用 ffmpeg 合流）"""
    video_stream = pick_video_stream(play_info, preferred_quality)
    audio_stream = pick_audio_stream(play_info)
    if video_stream is None or audio_stream is None:
        return None

    return MediaItem(
        url=_stream_url(video_stream),
        backup_urls=_stream_backup_urls(video_stream),
        audio_url=_stream_url(audio_stream),
        audio_backup_urls=_stream_backup_urls(audio_stream),
        media_type=MediaType.VIDEO,
        content_id=content_id,
        stem="video",
    )


def available_qualities(play_info: Dict) -> List[int]:
    """响应中实际可用的视频清晰度档位（从高到低）"""
    dash = _as_dict(play_info).get("dash")
    if not isinstance(dash, dict):
        return []
    qualities = {
        _to_int(stream.get("id"))
        for stream in (dash.get("video") or [])
        if _stream_url(stream)
    }
    return sorted(qualities, reverse=True)


def next_lower_quality(play_info: Dict, current_quality: int) -> Optional[int]:
    """比 ``current_quality`` 更低的下一个可用档位，没有则返回 None。

    用于"playurl 给了高清地址但 CDN 拒绝下载"时逐档降级
    （未登录或权限不足时 B 站会返回高清晰度 URL，但实际取流会被 403）。
    """
    lower = [quality for quality in available_qualities(play_info) if quality < current_quality]
    return lower[0] if lower else None


def count_durl_segments(play_info: Dict) -> int:
    """durl 的分段数量。大于 1 表示整片被切分，只下最大一段会得到不完整的文件。"""
    return len(
        [
            entry
            for entry in _as_dict(play_info).get("durl") or []
            if isinstance(entry, dict) and entry.get("url")
        ]
    )


def build_durl_item(play_info: Dict, content_id: str) -> Optional[MediaItem]:
    """构建 mp4 直链下载任务（取体积最大的一段）。

    stem 刻意与 DASH 产物（``video``）区分：直链画质受接口限制，是降级产物。
    两者同名会让先下到的低清文件被"已存在即跳过"永久信任，
    之后即使装好 ffmpeg 也再拿不到高清。
    """
    durl_list: List[Dict] = _as_dict(play_info).get("durl") or []
    candidates = [entry for entry in durl_list if isinstance(entry, dict) and entry.get("url")]
    if not candidates:
        return None

    best = max(candidates, key=lambda entry: _to_int(entry.get("size")))
    return MediaItem(
        url=best["url"],
        backup_urls=tuple(best.get("backup_url") or ()),
        media_type=MediaType.VIDEO,
        content_id=content_id,
        stem="video-durl",
    )
