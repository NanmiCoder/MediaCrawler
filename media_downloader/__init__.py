# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_downloader/__init__.py
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

"""统一媒体下载器：流式传输、断点续传、指数退避重试、大小校验、DASH 合流。

平台特有的"下载哪个 URL"由 ``media_platform/<platform>/media.py`` 负责，
本包只处理"怎么把字节落到磁盘"，因此不认识任何平台。
"""

from .downloader import MediaDownloader
from .ffmpeg import ffmpeg_path, is_available as is_ffmpeg_available, merge_audio_video
from .types import (
    MediaDownloadError,
    MediaFatalError,
    MediaItem,
    MediaRetryableError,
    MediaType,
)

__all__ = [
    "MediaDownloader",
    "MediaDownloadError",
    "MediaFatalError",
    "MediaItem",
    "MediaRetryableError",
    "MediaType",
    "ffmpeg_path",
    "is_ffmpeg_available",
    "merge_audio_video",
]
