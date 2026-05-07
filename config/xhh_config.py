# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# Xiaoheihe (小黑盒) platform configuration

# 指定帖子 link_id 列表（detail 模式）
XHH_SPECIFIED_ID_LIST = [
    # "179403000",
]

# Cookie 文件路径（qrcode 模式登录后自动保存）
# 默认使用 ~/.xhh_cookies.json，与 tools/xhh/xhh_crawl.py 共享同一份 Cookie
XHH_COOKIE_FILE = "~/.xhh_cookies.json"
