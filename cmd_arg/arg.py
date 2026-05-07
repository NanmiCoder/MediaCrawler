# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/cmd_arg/arg.py
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


from __future__ import annotations


import sys
import re
from enum import Enum
from types import SimpleNamespace
from typing import Iterable, Optional, Sequence, Type, TypeVar

import typer
from bool_detector import str2bool
from typer import Option

import config

app = typer.Typer()

EnumT = TypeVar("EnumT", bound=Enum)


class PlatformEnum(str, Enum):
    """Supported media platform enumeration"""

    XHS = "xhs"
    DOUYIN = "dy"
    KUAISHOU = "ks"
    BILIBILI = "bili"
    WEIBO = "wb"
    TIEBA = "tieba"
    ZHIHU = "zhihu"
    XIAOHEIHE = "xhh"


class LoginTypeEnum(str, Enum):
    """Login type enumeration"""

    QRCODE = "qrcode"
    PHONE = "phone"
    COOKIE = "cookie"


class CrawlerTypeEnum(str, Enum):
    """Crawler type enumeration"""

    SEARCH = "search"
    DETAIL = "detail"
    CREATOR = "creator"


class SaveDataOptionEnum(str, Enum):
    """Data save option enumeration"""

    CSV = "csv"
    DB = "db"
    JSON = "json"
    JSONL = "jsonl"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    EXCEL = "excel"
    POSTGRES = "postgres"


class InitDbOptionEnum(str, Enum):
    """Database initialization option"""

    SQLITE = "sqlite"
    MYSQL = "mysql"
    POSTGRES = "postgres"


def _to_bool(value: bool | str) -> bool:
    if isinstance(value, bool):
        return value
    return str2bool(value)


def _coerce_enum(
    enum_cls: Type[EnumT],
    value: EnumT | str,
    default: EnumT,
) -> EnumT:
    """Safely convert a raw config value to an enum member."""

    if isinstance(value, enum_cls):
        return value

    try:
        return enum_cls(value)
    except ValueError:
        typer.secho(
            f"⚠️ Config value '{value}' is not within the supported range of {enum_cls.__name__}, falling back to default value '{default.value}'.",
            fg=typer.colors.YELLOW,
        )
        return default


def _normalize_init_db_args(
    args: Sequence[str],
    enum_cls: Type[InitDbOptionEnum],
    default: InitDbOptionEnum,
) -> list[str]:
    """Ensure bare --init_db defaults to sqlite for backward compatibility."""

    normalized = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--init_db", "--init-db"):
            # Peek at the next token
            next_token = args[i + 1] if i + 1 < len(args) else None
            if next_token is None or next_token.startswith("-"):
                # No value follows → inject default
                normalized.append(arg)
                normalized.append(default.value)
            else:
                # Value follows → keep as-is
                normalized.append(arg)
                normalized.append(next_token)
                i += 1
        else:
            normalized.append(arg)
        i += 1
    return normalized


@app.command()
def main(
    platform: Annotated[
        PlatformEnum,
        Option(
            "--platform",
            help="Media platform selection (xhs=XiaoHongShu | dy=Douyin | ks=Kuaishou | bili=Bilibili | wb=Weibo | tieba=Baidu Tieba | zhihu=Zhihu | xhh=XiaoHeiHe)",
        ),
    ] = _coerce_enum(PlatformEnum, config.PLATFORM, PlatformEnum.XHS),
    lt: Annotated[
        LoginTypeEnum,
        Option(
            "--lt",
            help="Login type (qrcode | phone | cookie)",
        ),
    ] = _coerce_enum(LoginTypeEnum, config.LOGIN_TYPE, LoginTypeEnum.QRCODE),
    type: Annotated[
        CrawlerTypeEnum,
        Option(
            "--type",
            help="Crawler type (search | detail | creator)",
        ),
    ] = _coerce_enum(CrawlerTypeEnum, config.CRAWLER_TYPE, CrawlerTypeEnum.SEARCH),
    keywords: Annotated[
        Optional[str],
        Option("--keywords", help="Search keywords (comma-separated)"),
    ] = None,
    get_comment: Annotated[
        Optional[str],
        Option("--get_comment", help="Whether to get comments (true/false)"),
    ] = None,
    save_data_option: Annotated[
        Optional[SaveDataOptionEnum],
        Option("--save_data_option", help="Data save format (csv|db|json|jsonl|sqlite|mongodb|excel|postgres)"),
    ] = None,
    max_notes_count: Annotated[
        Optional[int],
        Option("--max_notes_count", help="Maximum number of notes to crawl"),
    ] = None,
    max_comments_count_singlenotes: Annotated[
        Optional[int],
        Option("--max_comments_count_singlenotes", help="Maximum number of comments per note"),
    ] = None,
    start_page: Annotated[
        Optional[int],
        Option("--start_page", help="Start page number"),
    ] = None,
    headless: Annotated[
        Optional[str],
        Option("--headless", help="Run in headless mode (true/false)"),
    ] = None,
    enable_ip_proxy: Annotated[
        Optional[str],
        Option("--enable_ip_proxy", help="Enable IP proxy (true/false)"),
    ] = None,
    specified_id_list: Annotated[
        Optional[str],
        Option("--specified_id", help="Specified ID or URL to crawl"),
    ] = None,
    creator_id: Annotated[
        Optional[str],
        Option("--creator_id", help="Creator ID or URL"),
    ] = None,
    cookies: Annotated[
        Optional[str],
        Option("--cookies", help="Cookie string for cookie-based login"),
    ] = None,
    get_sub_comments: Annotated[
        Optional[str],
        Option("--get_sub_comments", help="Whether to get sub-comments (true/false)"),
    ] = None,
    enable_get_media: Annotated[
        Optional[str],
        Option("--enable_get_media", help="Enable downloading media files (true/false)"),
    ] = None,
    init_db: Annotated[
        Optional[InitDbOptionEnum],
        Option("--init_db", help="Initialize database (sqlite|mysql|postgres)"),
    ] = None,
    save_data_path: Annotated[
        Optional[str],
        Option("--save_data_path", help="Path to save data files"),
    ] = None,
    enable_cdp_mode: Annotated[
        Optional[str],
        Option("--enable_cdp_mode", help="Enable CDP mode (true/false)"),
    ] = None,
    cdp_debug_port: Annotated[
        Optional[int],
        Option("--cdp_debug_port", help="CDP debug port"),
    ] = None,
    custom_browser_path: Annotated[
        Optional[str],
        Option("--custom_browser_path", help="Custom browser executable path"),
    ] = None,
) -> SimpleNamespace:
    """MediaCrawler - Social media data crawler"""
    config.PLATFORM = platform.value
    config.LOGIN_TYPE = lt.value
    config.CRAWLER_TYPE = type.value

    if keywords is not None:
        config.KEYWORDS = keywords
    if get_comment is not None:
        config.ENABLE_GET_COMMENTS = _to_bool(get_comment)
    if save_data_option is not None:
        config.SAVE_DATA_OPTION = save_data_option.value
    if max_notes_count is not None:
        config.CRAWLER_MAX_NOTES_COUNT = max_notes_count
    if max_comments_count_singlenotes is not None:
        config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = max_comments_count_singlenotes
    if start_page is not None:
        config.START_PAGE = start_page
    if headless is not None:
        config.HEADLESS = _to_bool(headless)
    if enable_ip_proxy is not None:
        config.ENABLE_IP_PROXY = _to_bool(enable_ip_proxy)
    if cookies is not None:
        config.COOKIES = cookies
    if get_sub_comments is not None:
        config.ENABLE_GET_SUB_COMMENTS = _to_bool(get_sub_comments)
    if enable_get_media is not None:
        config.ENABLE_GET_MEIDAS = _to_bool(enable_get_media)
    if save_data_path is not None:
        config.SAVE_DATA_PATH = save_data_path
    if enable_cdp_mode is not None:
        config.ENABLE_CDP_MODE = _to_bool(enable_cdp_mode)
    if cdp_debug_port is not None:
        config.CDP_DEBUG_PORT = cdp_debug_port
    if custom_browser_path is not None:
        config.CUSTOM_BROWSER_PATH = custom_browser_path

    # Handle specified_id_list based on platform
    if specified_id_list is not None:
        _set_specified_id_list(platform.value, specified_id_list)
    if creator_id is not None:
        _set_creator_id(platform.value, creator_id)

    return SimpleNamespace(
        platform=platform,
        lt=lt,
        type=type,
        keywords=keywords,
        get_comment=get_comment,
        save_data_option=save_data_option,
        max_notes_count=max_notes_count,
        max_comments_count_singlenotes=max_comments_count_singlenotes,
        start_page=start_page,
        headless=headless,
        enable_ip_proxy=enable_ip_proxy,
        specified_id_list=specified_id_list,
        creator_id=creator_id,
        cookies=cookies,
        get_sub_comments=get_sub_comments,
        enable_get_media=enable_get_media,
        init_db=init_db,
        save_data_path=save_data_path,
        enable_cdp_mode=enable_cdp_mode,
        cdp_debug_port=cdp_debug_port,
        custom_browser_path=custom_browser_path,
    )


def _set_specified_id_list(platform: str, specified_id: str) -> None:
    """Set the specified ID list for the given platform."""
    ids = [s.strip() for s in specified_id.split(",") if s.strip()]
    if platform == "xhs":
        config.XHS_SPECIFIED_NOTE_URL_LIST = ids
    elif platform == "dy":
        config.DY_SPECIFIED_ID_LIST = ids
    elif platform == "bili":
        config.BILI_SPECIFIED_ID_LIST = ids
    elif platform == "wb":
        config.WEIBO_SPECIFIED_ID_LIST = ids
    elif platform == "tieba":
        config.TIEBA_SPECIFIED_ID_LIST = ids
    elif platform == "zhihu":
        config.ZHIHU_SPECIFIED_ID_LIST = ids
    elif platform == "xhh":
        config.XHH_SPECIFIED_ID_LIST = ids


def _set_creator_id(platform: str, creator_id: str) -> None:
    """Set the creator ID for the given platform."""
    if platform == "xhs":
        config.XHS_CREATOR_ID_LIST = [creator_id]
    elif platform == "dy":
        config.DY_CREATOR_ID_LIST = [creator_id]
    elif platform == "bili":
        config.BILI_CREATOR_ID_LIST = [creator_id]
    elif platform == "wb":
        config.WEIBO_CREATOR_ID_LIST = [creator_id]
    elif platform == "tieba":
        config.TIEBA_CREATOR_URL_LIST = [creator_id]
    elif platform == "zhihu":
        config.ZHIHU_CREATOR_URL_LIST = [creator_id]


async def parse_cmd() -> SimpleNamespace:
    """Parse command line arguments."""
    cli_args = sys.argv[1:]
    cli_args = _normalize_init_db_args(cli_args, InitDbOptionEnum, InitDbOptionEnum.SQLITE)
    result = app(args=cli_args, standalone_mode=False)
    if isinstance(result, SimpleNamespace):
        return result
    return SimpleNamespace(init_db=None)


from typing import Annotated
