# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/bilibili_config.py
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
# bilili platform configuration

# Control the number of videos/posts crawled per day
MAX_NOTES_PER_DAY = 1

# Specify Bilibili video URL list (supports complete URL or BV number)
# Example:
# - Full URL: "https://www.bilibili.com/video/BV1dwuKzmE26/?spm_id_from=333.1387.homepage.video_card.click"
# - BV number: "BV1d54y1g7db"
BILI_SPECIFIED_ID_LIST = [
    "https://www.bilibili.com/video/BV1dwuKzmE26/?spm_id_from=333.1387.homepage.video_card.click",
    "BV1Sz4y1U77N",
    "BV14Q4y1n7jz",
    # ........................
]

# Specify the URL list of Bilibili creators (supports full URL or UID)
# Example:
# - Full URL: "https://space.bilibili.com/434377496?spm_id_from=333.1007.0.0"
# - UID: "20813884"
BILI_CREATOR_ID_LIST = [
    "https://space.bilibili.com/434377496?spm_id_from=333.1007.0.0",
    "20813884",
    # ........................
]

# Specify time range
START_DAY = "2024-01-01"
END_DAY = "2024-01-01"

# Search mode
BILI_SEARCH_MODE = "normal"

# Video definition (qn) configuration, common values:
# 16=360p, 32=480p, 64=720p, 80=1080p, 112=1080p high bit rate, 116=1080p60, 120=4K
# Note: Higher definition requires account/video support
BILI_QN = 80

# Whether to crawl user information
CREATOR_MODE = True

# Start crawling user information page number
START_CONTACTS_PAGE = 1

# Maximum number of crawled comments for a single video/post
CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES = 100

# Maximum number of crawled dynamics for a single video/post
CRAWLER_MAX_DYNAMICS_COUNT_SINGLENOTES = 50
