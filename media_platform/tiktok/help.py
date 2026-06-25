# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/tiktok/help.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习 and 研究目的使用。使用者应遵守以下原则：
# 1. 不得用于 any 商业用途。
# 2. 使用时应遵守目标平台的使用条款 and robots.txt规则。
# 3. 不得进行大规模爬取 or 对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于 any 非法 or 不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则 and LICENSE中的所有条款。

import re
from typing import Optional

from model.m_tiktok import VideoUrlInfo, CreatorUrlInfo


def extract_video_id_from_url(url: str) -> Optional[str]:
    """
    Extract video ID from a TikTok URL.
    """
    if url.isdigit():
        return url
    patterns = [
        r'tiktok\.com/@[^/]+/video/(\d+)',
        r'tiktok\.com/video/(\d+)',
        r'tiktok\.com/v/(\d+)',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def extract_creator_id_from_url(url: str) -> Optional[str]:
    """
    Extract creator unique ID from a TikTok profile URL.
    """
    if not url.startswith("http") and "tiktok.com" not in url:
        return url
    m = re.search(r'tiktok\.com/@([^/?]+)', url)
    return m.group(1) if m else None


def parse_video_info_from_url(url: str) -> VideoUrlInfo:
    """
    Parse video ID from TikTok video URL.
    """
    video_id = extract_video_id_from_url(url)
    if video_id:
        return VideoUrlInfo(video_id=video_id, url_type="normal")

    # If it is a short link (e.g. vt.tiktok.com)
    if "tiktok.com" in url:
        return VideoUrlInfo(video_id="", url_type="short")

    raise ValueError(f"Unable to parse video ID from URL: {url}")


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    """
    Parse creator unique ID from TikTok creator URL.
    """
    unique_id = extract_creator_id_from_url(url)
    if unique_id:
        return CreatorUrlInfo(unique_id=unique_id)

    raise ValueError(f"Unable to parse creator ID from URL: {url}")


if __name__ == '__main__':
    # Test video URL parsing
    print("=== Video URL Parsing Test ===")
    test_urls = [
        "https://www.tiktok.com/@user/video/7525082444551310602",
        "7525082444551310602",
    ]
    for url in test_urls:
        try:
            result = parse_video_info_from_url(url)
            print(f"✓ URL: {url} -> {result}")
        except Exception as e:
            print(f"✗ URL: {url} -> {e}")

    # Test creator URL parsing
    print("=== Creator URL Parsing Test ===")
    test_creator_urls = [
        "https://www.tiktok.com/@some_user_id?lang=en",
        "some_user_id",
    ]
    for url in test_creator_urls:
        try:
            result = parse_creator_info_from_url(url)
            print(f"✓ URL: {url} -> {result}")
        except Exception as e:
            print(f"✗ URL: {url} -> {e}")
