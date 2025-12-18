# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/schemas/crawler.py
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

from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel


class PlatformEnum(str, Enum):
    """支持的媒体平台"""
    XHS = "xhs"
    DOUYIN = "dy"
    KUAISHOU = "ks"
    BILIBILI = "bili"
    WEIBO = "wb"
    TIEBA = "tieba"
    ZHIHU = "zhihu"


class LoginTypeEnum(str, Enum):
    """登录方式"""
    QRCODE = "qrcode"
    PHONE = "phone"
    COOKIE = "cookie"


class CrawlerTypeEnum(str, Enum):
    """爬虫类型"""
    SEARCH = "search"
    DETAIL = "detail"
    CREATOR = "creator"


class SaveDataOptionEnum(str, Enum):
    """数据保存方式"""
    CSV = "csv"
    DB = "db"
    JSON = "json"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    EXCEL = "excel"


class CrawlerStartRequest(BaseModel):
    """启动爬虫请求"""
    platform: PlatformEnum
    login_type: LoginTypeEnum = LoginTypeEnum.QRCODE
    crawler_type: CrawlerTypeEnum = CrawlerTypeEnum.SEARCH
    keywords: str = ""  # 搜索模式下的关键词
    specified_ids: str = ""  # 详情模式下的帖子/视频ID列表，逗号分隔
    creator_ids: str = ""  # 创作者模式下的创作者ID列表，逗号分隔
    start_page: int = 1
    enable_comments: bool = True
    enable_sub_comments: bool = False
    save_option: SaveDataOptionEnum = SaveDataOptionEnum.JSON
    cookies: str = ""
    headless: bool = False


class CrawlerStatusResponse(BaseModel):
    """爬虫状态响应"""
    status: Literal["idle", "running", "stopping", "error"]
    platform: Optional[str] = None
    crawler_type: Optional[str] = None
    started_at: Optional[str] = None
    error_message: Optional[str] = None


class LogEntry(BaseModel):
    """日志条目"""
    id: int
    timestamp: str
    level: Literal["info", "warning", "error", "success", "debug"]
    message: str


class DataFileInfo(BaseModel):
    """数据文件信息"""
    name: str
    path: str
    size: int
    modified_at: str
    record_count: Optional[int] = None
