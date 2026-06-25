# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/tiktok_config.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于 any 商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于 any 非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

# TikTok platform configuration

# Keyword list to search and crawl
TIKTOK_KEYWORD_LIST: list = ["AI tools", "review sản phẩm"]

# Specify TikTok video URL/ID list
TIKTOK_VIDEO_ID_LIST: list = []

# Specify TikTok creator URL/ID list
TIKTOK_CREATOR_ID_LIST: list = []

# Specify TikTok hashtag list
TIKTOK_HASHTAG_LIST: list = []

# Max comments count to crawl per video
TIKTOK_MAX_COMMENTS_PER_VIDEO: int = 100

# Max concurrency for task requests
TIKTOK_MAX_CONCURRENCY: int = 3
