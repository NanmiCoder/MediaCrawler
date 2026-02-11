# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/weibo_config.py
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


# Weibo platform configuration

# Search type, the specific enumeration value is in media_platform/weibo/field.py
WEIBO_SEARCH_TYPE = "default"

# Specify Weibo ID list
WEIBO_SPECIFIED_ID_LIST = [
    "4982041758140155",
    # ........................
]

# Specify Weibo user ID list
WEIBO_CREATOR_ID_LIST = [
    "5756404150",
    # ........................
]

# Whether to enable the function of crawling the full text of Weibo. It is enabled by default.
# If turned on, it will increase the probability of being risk controlled, which is equivalent to a keyword search request that will traverse all posts and request the post details again.
ENABLE_WEIBO_FULL_TEXT = True
