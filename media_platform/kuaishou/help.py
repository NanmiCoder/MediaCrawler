# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/kuaishou/help.py
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


# -*- coding: utf-8 -*-

import re
from model.m_kuaishou import VideoUrlInfo, CreatorUrlInfo


def parse_video_info_from_url(url: str) -> VideoUrlInfo:
    """
    从快手视频URL中解析出视频ID
    支持以下格式:
    1. 完整视频URL: "https://www.kuaishou.com/short-video/3x3zxz4mjrsc8ke?authorId=3x84qugg4ch9zhs&streamSource=search"
    2. 纯视频ID: "3x3zxz4mjrsc8ke"

    Args:
        url: 快手视频链接或视频ID
    Returns:
        VideoUrlInfo: 包含视频ID的对象
    """
    # 如果不包含http且不包含kuaishou.com，认为是纯ID
    if not url.startswith("http") and "kuaishou.com" not in url:
        return VideoUrlInfo(video_id=url, url_type="normal")

    # 从标准视频URL中提取ID: /short-video/视频ID
    video_pattern = r'/short-video/([a-zA-Z0-9_-]+)'
    match = re.search(video_pattern, url)
    if match:
        video_id = match.group(1)
        return VideoUrlInfo(video_id=video_id, url_type="normal")

    raise ValueError(f"无法从URL中解析出视频ID: {url}")


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    """
    从快手创作者主页URL中解析出创作者ID
    支持以下格式:
    1. 创作者主页: "https://www.kuaishou.com/profile/3x84qugg4ch9zhs"
    2. 纯ID: "3x4sm73aye7jq7i"

    Args:
        url: 快手创作者主页链接或user_id
    Returns:
        CreatorUrlInfo: 包含创作者ID的对象
    """
    # 如果不包含http且不包含kuaishou.com，认为是纯ID
    if not url.startswith("http") and "kuaishou.com" not in url:
        return CreatorUrlInfo(user_id=url)

    # 从创作者主页URL中提取user_id: /profile/xxx
    user_pattern = r'/profile/([a-zA-Z0-9_-]+)'
    match = re.search(user_pattern, url)
    if match:
        user_id = match.group(1)
        return CreatorUrlInfo(user_id=user_id)

    raise ValueError(f"无法从URL中解析出创作者ID: {url}")


if __name__ == '__main__':
    # 测试视频URL解析
    print("=== 视频URL解析测试 ===")
    test_video_urls = [
        "https://www.kuaishou.com/short-video/3x3zxz4mjrsc8ke?authorId=3x84qugg4ch9zhs&streamSource=search&area=searchxxnull&searchKey=python",
        "3xf8enb8dbj6uig",
    ]
    for url in test_video_urls:
        try:
            result = parse_video_info_from_url(url)
            print(f"✓ URL: {url[:80]}...")
            print(f"  结果: {result}\n")
        except Exception as e:
            print(f"✗ URL: {url}")
            print(f"  错误: {e}\n")

    # 测试创作者URL解析
    print("=== 创作者URL解析测试 ===")
    test_creator_urls = [
        "https://www.kuaishou.com/profile/3x84qugg4ch9zhs",
        "3x4sm73aye7jq7i",
    ]
    for url in test_creator_urls:
        try:
            result = parse_creator_info_from_url(url)
            print(f"✓ URL: {url[:80]}...")
            print(f"  结果: {result}\n")
        except Exception as e:
            print(f"✗ URL: {url}")
            print(f"  错误: {e}\n")
