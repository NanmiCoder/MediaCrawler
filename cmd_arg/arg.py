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
from typing_extensions import Annotated

import config
from tools.content_filter import ContentFilterError, normalize_content_filters
from tools.utils import str2bool


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
    LOGIN = "login"


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


def _normalize_argv(argv: Optional[Sequence[str]]) -> Iterable[str]:
    if argv is None:
        return list(sys.argv[1:])
    return list(argv)


def _inject_init_db_default(args: Sequence[str]) -> list[str]:
    """Ensure bare --init_db defaults to sqlite for backward compatibility."""

    normalized: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        normalized.append(arg)

        if arg == "--init_db":
            next_arg = args[i + 1] if i + 1 < len(args) else None
            if not next_arg or next_arg.startswith("-"):
                normalized.append(InitDbOptionEnum.SQLITE.value)
        i += 1

    return normalized


def _normalize_tieba_note_id(value: str) -> str:
    """Accept a raw Tieba thread id or a /p/<id> URL."""
    value = value.strip()
    match = re.search(r"/p/(\d+)", value)
    return match.group(1) if match else value


def _normalize_tieba_creator_url(value: str) -> str:
    """Accept a Tieba creator homepage URL or a portrait id."""
    value = value.strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return f"https://tieba.baidu.com/home/main?id={value}"


async def parse_cmd(argv: Optional[Sequence[str]] = None):
    """Parse command line arguments using Typer."""

    app = typer.Typer(add_completion=False)

    @app.callback(invoke_without_command=True)
    def main(
        platform: Annotated[
            PlatformEnum,
            typer.Option(
                "--platform",
                help="Media platform selection (xhs=XiaoHongShu | dy=Douyin | ks=Kuaishou | bili=Bilibili | wb=Weibo | tieba=Baidu Tieba | zhihu=Zhihu)",
                rich_help_panel="Basic Configuration",
            ),
        ] = _coerce_enum(PlatformEnum, config.PLATFORM, PlatformEnum.XHS),
        lt: Annotated[
            LoginTypeEnum,
            typer.Option(
                "--lt",
                help="Login type (qrcode=QR Code | phone=Phone | cookie=Cookie)",
                rich_help_panel="Account Configuration",
            ),
        ] = _coerce_enum(LoginTypeEnum, config.LOGIN_TYPE, LoginTypeEnum.QRCODE),
        crawler_type: Annotated[
            CrawlerTypeEnum,
            typer.Option(
                "--type",
                help="Crawler type (search=Search | detail=Detail | creator=Creator | login=Login only)",
                rich_help_panel="Basic Configuration",
            ),
        ] = _coerce_enum(CrawlerTypeEnum, config.CRAWLER_TYPE, CrawlerTypeEnum.SEARCH),
        start: Annotated[
            int,
            typer.Option(
                "--start",
                help="Starting page number",
                rich_help_panel="Basic Configuration",
            ),
        ] = config.START_PAGE,
        keywords: Annotated[
            str,
            typer.Option(
                "--keywords",
                help="Enter keywords, multiple keywords separated by commas",
                rich_help_panel="Basic Configuration",
            ),
        ] = config.KEYWORDS,
        get_comment: Annotated[
            str,
            typer.Option(
                "--get_comment",
                help="Whether to crawl first-level comments, supports yes/true/t/y/1 or no/false/f/n/0",
                rich_help_panel="Comment Configuration",
                show_default=True,
            ),
        ] = str(config.ENABLE_GET_COMMENTS),
        get_sub_comment: Annotated[
            str,
            typer.Option(
                "--get_sub_comment",
                help="Whether to crawl second-level comments, supports yes/true/t/y/1 or no/false/f/n/0",
                rich_help_panel="Comment Configuration",
                show_default=True,
            ),
        ] = str(config.ENABLE_GET_SUB_COMMENTS),
        headless: Annotated[
            str,
            typer.Option(
                "--headless",
                help="Whether to enable headless mode (applies to both Playwright and CDP), supports yes/true/t/y/1 or no/false/f/n/0",
                rich_help_panel="Runtime Configuration",
                show_default=True,
            ),
        ] = str(config.HEADLESS),
        save_data_option: Annotated[
            SaveDataOptionEnum,
            typer.Option(
                "--save_data_option",
                help="Data save option (csv=CSV file | db=MySQL database | json=JSON file | jsonl=JSONL file | sqlite=SQLite database | mongodb=MongoDB database | excel=Excel file | postgres=PostgreSQL database)",
                rich_help_panel="Storage Configuration",
            ),
        ] = _coerce_enum(
            SaveDataOptionEnum, config.SAVE_DATA_OPTION, SaveDataOptionEnum.JSONL
        ),
        init_db: Annotated[
            Optional[InitDbOptionEnum],
            typer.Option(
                "--init_db",
                help="Initialize database table structure (sqlite | mysql | postgres)",
                rich_help_panel="Storage Configuration",
            ),
        ] = None,
        cookies: Annotated[
            str,
            typer.Option(
                "--cookies",
                help="Cookie value used for Cookie login method",
                rich_help_panel="Account Configuration",
            ),
        ] = config.COOKIES,
        specified_id: Annotated[
            str,
            typer.Option(
                "--specified_id",
                help="Post/video ID list in detail mode, multiple IDs separated by commas (supports full URL or ID)",
                rich_help_panel="Basic Configuration",
            ),
        ] = "",
        creator_id: Annotated[
            str,
            typer.Option(
                "--creator_id",
                help="Creator ID list in creator mode, multiple IDs separated by commas (supports full URL or ID)",
                rich_help_panel="Basic Configuration",
            ),
        ] = "",
        max_comments_count_singlenotes: Annotated[
            int,
            typer.Option(
                "--max_comments_count_singlenotes",
                help="Maximum number of first-level comments to crawl per post/video",
                rich_help_panel="Comment Configuration",
            ),
        ] = config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
        crawler_max_notes_count: Annotated[
            int,
            typer.Option(
                "--crawler_max_notes_count",
                help="Maximum number of videos/posts to crawl",
                rich_help_panel="Basic Configuration",
            ),
        ] = config.CRAWLER_MAX_NOTES_COUNT,
        content_filters: Annotated[
            str,
            typer.Option(
                "--content_filters",
                help='Content metric filters JSON, for example {"liked_count":{"min":1000}}',
                rich_help_panel="Basic Configuration",
            ),
        ] = "",
        max_concurrency_num: Annotated[
            int,
            typer.Option(
                "--max_concurrency_num",
                help="Maximum number of concurrent crawlers",
                rich_help_panel="Performance Configuration",
            ),
        ] = config.MAX_CONCURRENCY_NUM,
        save_data_path: Annotated[
            str,
            typer.Option(
                "--save_data_path",
                help="Data save path, default is empty and will save to data folder",
                rich_help_panel="Storage Configuration",
            ),
        ] = config.SAVE_DATA_PATH,
        enable_ip_proxy: Annotated[
            str,
            typer.Option(
                "--enable_ip_proxy",
                help="Whether to enable IP proxy, supports yes/true/t/y/1 or no/false/f/n/0",
                rich_help_panel="Proxy Configuration",
                show_default=True,
            ),
        ] = str(config.ENABLE_IP_PROXY),
        ip_proxy_pool_count: Annotated[
            int,
            typer.Option(
                "--ip_proxy_pool_count",
                help="IP proxy pool count",
                rich_help_panel="Proxy Configuration",
            ),
        ] = config.IP_PROXY_POOL_COUNT,
        ip_proxy_provider_name: Annotated[
            str,
            typer.Option(
                "--ip_proxy_provider_name",
                help="IP proxy provider name (kuaidaili | wandouhttp | static)",
                rich_help_panel="Proxy Configuration",
            ),
        ] = config.IP_PROXY_PROVIDER_NAME,
        static_proxy_url: Annotated[
            str,
            typer.Option(
                "--static_proxy_url",
                help="Static proxy URL, for example http://user:password@host:port",
                rich_help_panel="Proxy Configuration",
            ),
        ] = config.STATIC_PROXY_URL,
        instance_id: Annotated[
            str,
            typer.Option(
                "--instance_id",
                help="Scheduler instance ID for multi-instance runs",
                rich_help_panel="Scheduler Configuration",
            ),
        ] = config.INSTANCE_ID,
        browser_profile_dir: Annotated[
            str,
            typer.Option(
                "--browser_profile_dir",
                help="Browser profile directory for this crawler instance",
                rich_help_panel="Scheduler Configuration",
            ),
        ] = config.BROWSER_PROFILE_DIR,
        cdp_debug_port: Annotated[
            int,
            typer.Option(
                "--cdp_debug_port",
                help="CDP debug port for this crawler instance",
                rich_help_panel="Scheduler Configuration",
            ),
        ] = config.CDP_DEBUG_PORT,
        cdp_connect_existing: Annotated[
            str,
            typer.Option(
                "--cdp_connect_existing",
                help="Whether CDP mode connects to an existing browser",
                rich_help_panel="Scheduler Configuration",
                show_default=True,
            ),
        ] = str(config.CDP_CONNECT_EXISTING),
    ) -> SimpleNamespace:
        """MediaCrawler 命令行入口"""

        enable_comment = _to_bool(get_comment)
        enable_sub_comment = _to_bool(get_sub_comment)
        enable_headless = _to_bool(headless)
        enable_ip_proxy_value = _to_bool(enable_ip_proxy)
        cdp_connect_existing_value = _to_bool(cdp_connect_existing)
        init_db_value = init_db.value if init_db else None
        try:
            content_filters_value = normalize_content_filters(platform.value, content_filters or config.CONTENT_FILTERS)
        except ContentFilterError as exc:
            raise typer.BadParameter(str(exc)) from exc

        # Parse specified_id and creator_id into lists
        specified_id_list = [id.strip() for id in specified_id.split(",") if id.strip()] if specified_id else []
        creator_id_list = [id.strip() for id in creator_id.split(",") if id.strip()] if creator_id else []

        # override global config
        config.PLATFORM = platform.value
        config.LOGIN_TYPE = lt.value
        config.CRAWLER_TYPE = crawler_type.value
        config.START_PAGE = start
        config.KEYWORDS = keywords
        config.ENABLE_GET_COMMENTS = enable_comment
        config.ENABLE_GET_SUB_COMMENTS = enable_sub_comment
        config.HEADLESS = enable_headless
        config.CDP_HEADLESS = enable_headless
        config.SAVE_DATA_OPTION = save_data_option.value
        config.COOKIES = cookies
        config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = max_comments_count_singlenotes
        config.CRAWLER_MAX_NOTES_COUNT = crawler_max_notes_count
        config.CONTENT_FILTERS = content_filters_value
        config.MAX_CONCURRENCY_NUM = max_concurrency_num
        config.SAVE_DATA_PATH = save_data_path
        config.ENABLE_IP_PROXY = enable_ip_proxy_value
        config.IP_PROXY_POOL_COUNT = ip_proxy_pool_count
        config.IP_PROXY_PROVIDER_NAME = ip_proxy_provider_name
        config.STATIC_PROXY_URL = static_proxy_url
        config.INSTANCE_ID = instance_id
        config.BROWSER_PROFILE_DIR = browser_profile_dir
        config.CDP_DEBUG_PORT = cdp_debug_port
        config.CDP_CONNECT_EXISTING = cdp_connect_existing_value

        # Set platform-specific ID lists for detail/creator mode
        if specified_id_list:
            if platform == PlatformEnum.XHS:
                config.XHS_SPECIFIED_NOTE_URL_LIST = specified_id_list
            elif platform == PlatformEnum.BILIBILI:
                config.BILI_SPECIFIED_ID_LIST = specified_id_list
            elif platform == PlatformEnum.DOUYIN:
                config.DY_SPECIFIED_ID_LIST = specified_id_list
            elif platform == PlatformEnum.WEIBO:
                config.WEIBO_SPECIFIED_ID_LIST = specified_id_list
            elif platform == PlatformEnum.KUAISHOU:
                config.KS_SPECIFIED_ID_LIST = specified_id_list
            elif platform == PlatformEnum.TIEBA:
                config.TIEBA_SPECIFIED_ID_LIST = [
                    _normalize_tieba_note_id(item) for item in specified_id_list
                ]
            elif platform == PlatformEnum.ZHIHU:
                config.ZHIHU_SPECIFIED_ID_LIST = specified_id_list

        if creator_id_list:
            if platform == PlatformEnum.XHS:
                config.XHS_CREATOR_ID_LIST = creator_id_list
            elif platform == PlatformEnum.BILIBILI:
                config.BILI_CREATOR_ID_LIST = creator_id_list
            elif platform == PlatformEnum.DOUYIN:
                config.DY_CREATOR_ID_LIST = creator_id_list
            elif platform == PlatformEnum.WEIBO:
                config.WEIBO_CREATOR_ID_LIST = creator_id_list
            elif platform == PlatformEnum.KUAISHOU:
                config.KS_CREATOR_ID_LIST = creator_id_list
            elif platform == PlatformEnum.TIEBA:
                config.TIEBA_CREATOR_URL_LIST = [
                    _normalize_tieba_creator_url(item) for item in creator_id_list
                ]

        return SimpleNamespace(
            platform=config.PLATFORM,
            lt=config.LOGIN_TYPE,
            type=config.CRAWLER_TYPE,
            start=config.START_PAGE,
            keywords=config.KEYWORDS,
            get_comment=config.ENABLE_GET_COMMENTS,
            get_sub_comment=config.ENABLE_GET_SUB_COMMENTS,
            headless=config.HEADLESS,
            save_data_option=config.SAVE_DATA_OPTION,
            init_db=init_db_value,
            cookies=config.COOKIES,
            specified_id=specified_id,
            creator_id=creator_id,
            content_filters=config.CONTENT_FILTERS,
            instance_id=config.INSTANCE_ID,
            browser_profile_dir=config.BROWSER_PROFILE_DIR,
            cdp_debug_port=config.CDP_DEBUG_PORT,
            cdp_connect_existing=config.CDP_CONNECT_EXISTING,
        )

    command = typer.main.get_command(app)

    cli_args = _normalize_argv(argv)
    cli_args = _inject_init_db_default(cli_args)

    try:
        result = command.main(args=cli_args, standalone_mode=False)
        if isinstance(result, int):  # help/options handled by Typer; propagate exit code
            raise SystemExit(result)
        return result
    except typer.Exit as exc:  # pragma: no cover - CLI exit paths
        raise SystemExit(exc.exit_code) from exc
