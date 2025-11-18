# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/ks_config.py
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

# 快手平台配置

# 指定快手视频URL列表 (支持完整URL或纯ID)
# 支持格式:
# 1. 完整视频URL: "https://www.kuaishou.com/short-video/3x3zxz4mjrsc8ke?authorId=3x84qugg4ch9zhs&streamSource=search"
# 2. 纯视频ID: "3xf8enb8dbj6uig"
KS_SPECIFIED_ID_LIST = [
    "https://www.kuaishou.com/short-video/3x3zxz4mjrsc8ke?authorId=3x84qugg4ch9zhs&streamSource=search&area=searchxxnull&searchKey=python",
    "3xf8enb8dbj6uig",
    # ........................
]

# 指定快手创作者URL列表 (支持完整URL或纯ID)
# 支持格式:
# 1. 创作者主页URL: "https://www.kuaishou.com/profile/3x84qugg4ch9zhs"
# 2. 纯user_id: "3x4sm73aye7jq7i"
KS_CREATOR_ID_LIST = [
    "https://www.kuaishou.com/profile/3x84qugg4ch9zhs",
    "3x4sm73aye7jq7i",
    # ........................
]
