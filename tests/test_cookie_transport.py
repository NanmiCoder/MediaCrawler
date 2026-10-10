# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_cookie_transport.py
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

from unittest.mock import AsyncMock, Mock

import pytest

from api.schemas import CrawlerStartRequest
from api.services.crawler_manager import CrawlerManager


@pytest.mark.asyncio
async def test_cookie_is_not_in_command_or_logs_and_reaches_child(monkeypatch):
    manager = CrawlerManager()
    secret = "sessionid=example-secret; token=another-secret"
    request = CrawlerStartRequest(platform="xhs", cookies=secret)
    process = Mock()
    process.poll.return_value = None
    spawn = Mock(return_value=process)
    monkeypatch.setattr("subprocess.Popen", spawn)
    monkeypatch.setattr(manager, "_read_output", AsyncMock())
    assert await manager.start(request)
    await manager._read_task
    assert secret not in " ".join(spawn.call_args.args[0])
    assert "--cookies" not in spawn.call_args.args[0]
    assert spawn.call_args.kwargs["env"]["MEDIACRAWLER_COOKIES"] == secret
    assert all("example-secret" not in entry.message for entry in manager.logs)
    assert all("another-secret" not in entry.message for entry in manager.logs)
    entry = manager._create_log_entry("server echoed sessionid=example-secret; token=another-secret")
    assert entry.message == "server echoed sessionid=[REDACTED]; token=[REDACTED]"
    assert "example-secret" not in repr(request)


@pytest.mark.asyncio
async def test_cli_reads_cookie_from_environment_without_exposing_help(monkeypatch, capsys):
    import config
    from cmd_arg import parse_cmd
    original = {name: value for name, value in vars(config).items() if name.isupper()}
    monkeypatch.setenv("MEDIACRAWLER_COOKIES", "sessionid=env-only-secret")
    try:
        await parse_cmd(["--platform", "xhs", "--lt", "cookie"])
        assert config.COOKIES == "sessionid=env-only-secret"
        with pytest.raises(SystemExit) as exit_info:
            await parse_cmd(["--help"])
        assert exit_info.value.code == 0
        assert "env-only-secret" not in capsys.readouterr().out
        await parse_cmd(["--platform", "xhs", "--cookies", "explicit=value"])
        assert config.COOKIES == "explicit=value"
    finally:
        for name, value in original.items():
            setattr(config, name, value)


@pytest.mark.parametrize("value", ["1", "0", "true"])
def test_common_cookie_values_do_not_corrupt_unrelated_logs(value):
    manager = CrawlerManager()
    manager.current_config = CrawlerStartRequest(platform="xhs", cookies=f"flag={value}")
    message = "page 10, count 101, enabled true, errors 0"
    assert manager._create_log_entry(message).message == message
    entry = manager._create_log_entry(f"flag={value}; page 10")
    assert entry.message == "flag=[REDACTED]; page 10"


def test_cookie_dictionary_values_are_redacted_in_context():
    manager = CrawlerManager()
    manager.current_config = CrawlerStartRequest(platform="xhs", cookies="sessionid=example-secret; flag=1")
    entry = manager._create_log_entry('{"sessionid": "example-secret", "flag": "1", "count": 101}')
    assert entry.message == '{"sessionid": "[REDACTED]", "flag": "[REDACTED]", "count": 101}'


def test_common_long_cookie_values_do_not_corrupt_identifiers():
    manager = CrawlerManager()
    manager.current_config = CrawlerStartRequest(platform="xhs", cookies="timezone=Asia/Shanghai")
    message = "timezone display Asia/Shanghai; record Asia/Shanghai-123"
    assert manager._create_log_entry(message).message == message


def test_cookie_headers_are_redacted_without_a_current_request():
    manager = CrawlerManager()
    entry = manager._create_log_entry("Cookies: sessionid=unknown-secret")
    assert entry.message == "Cookies: [REDACTED]"
