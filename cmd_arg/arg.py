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
from enum import Enum
from types import SimpleNamespace
from typing import Iterable, Optional, Sequence, Type, TypeVar

import typer
from typing_extensions import Annotated

import config
from tools.utils import str2bool


EnumT = TypeVar("EnumT", bound=Enum)


class PlatformEnum(str, Enum):
    """支持的媒体平台枚举"""

    XHS = "xhs"
    DOUYIN = "dy"
    KUAISHOU = "ks"
    BILIBILI = "bili"
    WEIBO = "wb"
    TIEBA = "tieba"
    ZHIHU = "zhihu"


class LoginTypeEnum(str, Enum):
    """登录方式枚举"""

    QRCODE = "qrcode"
    PHONE = "phone"
    COOKIE = "cookie"


class CrawlerTypeEnum(str, Enum):
    """爬虫类型枚举"""

    SEARCH = "search"
    DETAIL = "detail"
    CREATOR = "creator"


class SaveDataOptionEnum(str, Enum):
    """数据保存方式枚举"""

    CSV = "csv"
    DB = "db"
    JSON = "json"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    EXCEL = "excel"


class InitDbOptionEnum(str, Enum):
    """数据库初始化选项"""

    SQLITE = "sqlite"
    MYSQL = "mysql"


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
            f"⚠️ 配置值 '{value}' 不在 {enum_cls.__name__} 支持的范围内，已回退到默认值 '{default.value}'.",
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


async def parse_cmd(argv: Optional[Sequence[str]] = None):
    """使用 Typer 解析命令行参数。"""

    app = typer.Typer(add_completion=False)

    @app.callback(invoke_without_command=True)
    def main(
        platform: Annotated[
            PlatformEnum,
            typer.Option(
                "--platform",
                help="媒体平台选择 (xhs=小红书 | dy=抖音 | ks=快手 | bili=哔哩哔哩 | wb=微博 | tieba=百度贴吧 | zhihu=知乎)",
                rich_help_panel="基础配置",
            ),
        ] = _coerce_enum(PlatformEnum, config.PLATFORM, PlatformEnum.XHS),
        lt: Annotated[
            LoginTypeEnum,
            typer.Option(
                "--lt",
                help="登录方式 (qrcode=二维码 | phone=手机号 | cookie=Cookie)",
                rich_help_panel="账号配置",
            ),
        ] = _coerce_enum(LoginTypeEnum, config.LOGIN_TYPE, LoginTypeEnum.QRCODE),
        crawler_type: Annotated[
            CrawlerTypeEnum,
            typer.Option(
                "--type",
                help="爬取类型 (search=搜索 | detail=详情 | creator=创作者)",
                rich_help_panel="基础配置",
            ),
        ] = _coerce_enum(CrawlerTypeEnum, config.CRAWLER_TYPE, CrawlerTypeEnum.SEARCH),
        start: Annotated[
            int,
            typer.Option(
                "--start",
                help="起始页码",
                rich_help_panel="基础配置",
            ),
        ] = config.START_PAGE,
        keywords: Annotated[
            str,
            typer.Option(
                "--keywords",
                help="请输入关键词，多个关键词用逗号分隔",
                rich_help_panel="基础配置",
            ),
        ] = config.KEYWORDS,
        get_comment: Annotated[
            str,
            typer.Option(
                "--get_comment",
                help="是否爬取一级评论，支持 yes/true/t/y/1 或 no/false/f/n/0",
                rich_help_panel="评论配置",
                show_default=True,
            ),
        ] = str(config.ENABLE_GET_COMMENTS),
        get_sub_comment: Annotated[
            str,
            typer.Option(
                "--get_sub_comment",
                help="是否爬取二级评论，支持 yes/true/t/y/1 或 no/false/f/n/0",
                rich_help_panel="评论配置",
                show_default=True,
            ),
        ] = str(config.ENABLE_GET_SUB_COMMENTS),
        save_data_option: Annotated[
            SaveDataOptionEnum,
            typer.Option(
                "--save_data_option",
                help="数据保存方式 (csv=CSV文件 | db=MySQL数据库 | json=JSON文件 | sqlite=SQLite数据库 | mongodb=MongoDB数据库 | excel=Excel文件)",
                rich_help_panel="存储配置",
            ),
        ] = _coerce_enum(
            SaveDataOptionEnum, config.SAVE_DATA_OPTION, SaveDataOptionEnum.JSON
        ),
        init_db: Annotated[
            Optional[InitDbOptionEnum],
            typer.Option(
                "--init_db",
                help="初始化数据库表结构 (sqlite | mysql)",
                rich_help_panel="存储配置",
            ),
        ] = None,
        cookies: Annotated[
            str,
            typer.Option(
                "--cookies",
                help="Cookie 登录方式使用的 Cookie 值",
                rich_help_panel="账号配置",
            ),
        ] = config.COOKIES,
    ) -> SimpleNamespace:
        """MediaCrawler 命令行入口"""

        enable_comment = _to_bool(get_comment)
        enable_sub_comment = _to_bool(get_sub_comment)
        init_db_value = init_db.value if init_db else None

        # override global config
        config.PLATFORM = platform.value
        config.LOGIN_TYPE = lt.value
        config.CRAWLER_TYPE = crawler_type.value
        config.START_PAGE = start
        config.KEYWORDS = keywords
        config.ENABLE_GET_COMMENTS = enable_comment
        config.ENABLE_GET_SUB_COMMENTS = enable_sub_comment
        config.SAVE_DATA_OPTION = save_data_option.value
        config.COOKIES = cookies

        return SimpleNamespace(
            platform=config.PLATFORM,
            lt=config.LOGIN_TYPE,
            type=config.CRAWLER_TYPE,
            start=config.START_PAGE,
            keywords=config.KEYWORDS,
            get_comment=config.ENABLE_GET_COMMENTS,
            get_sub_comment=config.ENABLE_GET_SUB_COMMENTS,
            save_data_option=config.SAVE_DATA_OPTION,
            init_db=init_db_value,
            cookies=config.COOKIES,
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
