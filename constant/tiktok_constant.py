# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/constant/tiktok_constant.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于 any 商业用途。
# 2. 使用时应遵守目标平台的使用条款 and robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于 any 非法 or 不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则 and LICENSE中的所有条款。

TIKTOK_BASE_URL = "https://www.tiktok.com"

# API endpoints
SEARCH_VIDEO_URL = "/api/search/general/full/"
VIDEO_DETAIL_URL = "/api/item/detail/"
COMMENT_LIST_URL = "/api/comment/list/"
COMMENT_REPLY_URL = "/api/comment/reply/list/"
CREATOR_PROFILE_URL = "/api/user/detail/"
CREATOR_VIDEO_LIST_URL = "/api/post/item_list/"
HASHTAG_DETAIL_URL = "/api/challenge/detail/"
HASHTAG_VIDEO_URL = "/api/challenge/item_list/"

COMMON_PARAMS = {
    "aid": "1988",
    "app_language": "en",
    "app_name": "tiktok_web",
    "browser_language": "en-US",
    "browser_platform": "Win32",
    "channel": "tiktok_web",
    "device_platform": "web_pc",
    "os": "windows",
    "region": "VN",
    "tz_name": "Asia/Ho_Chi_Minh",
}
