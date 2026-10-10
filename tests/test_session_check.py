# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_session_check.py
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

"""
会话预检 (--check_session) 的单元测试。

全部离线：探测那一步 (_probe) 被 monkeypatch 掉，不会构造真实 client，也不会
发出任何请求。测试关注两件事：判定结果，以及失败原因的归类。
"""

import asyncio

import httpx
import pytest
from tenacity import AsyncRetrying, RetryError, stop_after_attempt

import config
from tools import session_check
from tools.session_check import (
    CAUSE_BLOCKED,
    CAUSE_BROWSER_REQUIRED,
    CAUSE_EXPIRED,
    CAUSE_MISSING_COOKIE_KEYS,
    CAUSE_NETWORK,
    CAUSE_NO_SESSION,
    CAUSE_PROXY,
    CAUSE_TIMEOUT,
    CAUSE_UNEXPECTED,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_UNKNOWN,
    check_platform_session,
    run_session_check,
)

# 满足各平台 REQUIRED_COOKIE_KEYS 的最小 cookie
COOKIES = {
    "xhs": "a1=abc;web_session=abc",
    "bili": "SESSDATA=abc",
    "wb": "SUB=abc",
    "zhihu": "d_c0=abc;z_c0=abc",
    "ks": "did=web_abc",
}


class PlatformAccessError(Exception):
    """名字与各平台 exception.py 中的一致，_classify_exception 按类名归类。"""


class DataFetchError(Exception):
    pass


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    """默认关闭代理，并让构造 client 这一步不做任何事。"""

    monkeypatch.setattr(config, "ENABLE_IP_PROXY", False)
    monkeypatch.setattr(
        session_check, "_build_client", lambda platform, cookie_str, httpx_proxy: object()
    )


def _probe_returns(value, delay=0.0):
    async def _inner(platform, client):
        if delay:
            await asyncio.sleep(delay)
        return value

    return _inner


def _probe_raises(exc, delay=0.0):
    async def _inner(platform, client):
        if delay:
            await asyncio.sleep(delay)
        raise exc

    return _inner


def _install_probe(monkeypatch, probe):
    calls = []

    async def _counting(platform, client):
        calls.append(platform)
        return await probe(platform, client)

    monkeypatch.setattr(session_check, "_probe", _counting)
    return calls


@pytest.mark.asyncio
async def test_missing_session_fails_without_touching_the_network(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("没有登录态时不应该构造 client")

    monkeypatch.setattr(session_check, "_build_client", _boom)
    monkeypatch.setattr(session_check, "_probe", _probe_raises(AssertionError("不应该发请求")))

    result = await check_platform_session("bili", cookie_str="   ")

    assert result.status == STATUS_FAILED
    assert result.cause == CAUSE_NO_SESSION


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "platform,cookie_str,missing",
    [
        ("zhihu", "z_c0=abc", "d_c0"),
        ("xhs", "web_session=abc", "a1"),
    ],
)
async def test_cookies_missing_a_required_field_fail_early(monkeypatch, platform, cookie_str, missing):
    """xhs 的签名缺 a1、zhihu 的 _pre_headers 缺 d_c0 都会在发请求前就抛异常。"""

    monkeypatch.setattr(session_check, "_probe", _probe_raises(AssertionError("不应该发请求")))

    result = await check_platform_session(platform, cookie_str=cookie_str)

    assert result.status == STATUS_FAILED
    assert result.cause == CAUSE_MISSING_COOKIE_KEYS
    assert missing in result.detail


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", sorted(COOKIES))
async def test_live_session_passes_with_exactly_one_request(monkeypatch, platform):
    calls = _install_probe(monkeypatch, _probe_returns(True))

    result = await check_platform_session(platform, cookie_str=COOKIES[platform])

    assert result.status == STATUS_OK
    assert result.cause == ""
    assert calls == [platform], "预检只能发一次请求"


@pytest.mark.asyncio
async def test_expired_session_is_reported_as_expired(monkeypatch):
    _install_probe(monkeypatch, _probe_returns(False))

    result = await check_platform_session("xhs", cookie_str=COOKIES["xhs"])

    assert result.status == STATUS_FAILED
    assert result.cause == CAUSE_EXPIRED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc,enable_proxy,expected_cause",
    [
        (httpx.ProxyError("proxy refused"), True, CAUSE_PROXY),
        (httpx.ConnectError("no route"), False, CAUSE_NETWORK),
        (httpx.ConnectError("no route"), True, CAUSE_PROXY),
        (PlatformAccessError("HTTP 403"), False, CAUSE_BLOCKED),
        (DataFetchError("bad json"), False, CAUSE_UNEXPECTED),
        (ValueError("something else"), False, CAUSE_UNEXPECTED),
    ],
)
async def test_failures_are_attributed_to_a_cause(monkeypatch, exc, enable_proxy, expected_cause):
    """这些异常只有绕开 pong() 直接探测才会冒出来——pong() 会把它们吞掉。"""

    monkeypatch.setattr(config, "ENABLE_IP_PROXY", enable_proxy)
    if enable_proxy:
        monkeypatch.setattr(session_check, "_resolve_proxy", _async_return("http://127.0.0.1:7890"))
    _install_probe(monkeypatch, _probe_raises(exc))

    result = await check_platform_session("bili", cookie_str=COOKIES["bili"])

    assert result.status == STATUS_FAILED
    assert result.cause == expected_cause


@pytest.mark.asyncio
async def test_retry_error_is_attributed_to_the_wrapped_exception(monkeypatch):
    """weibo/zhihu 的 client 带 tenacity 重试，真实原因藏在 RetryError 里。"""

    retry_error = await _make_retry_error(httpx.ProxyError("proxy refused"))
    monkeypatch.setattr(config, "ENABLE_IP_PROXY", False)
    _install_probe(monkeypatch, _probe_raises(retry_error))

    result = await check_platform_session("wb", cookie_str=COOKIES["wb"])

    assert result.status == STATUS_FAILED
    assert result.cause == CAUSE_PROXY, "不应该退化成泛泛的网络错误"


@pytest.mark.asyncio
async def test_slow_platform_times_out_instead_of_hanging(monkeypatch):
    monkeypatch.setattr(session_check, "CHECK_TIMEOUT_SECONDS", 0.01)
    _install_probe(monkeypatch, _probe_returns(True, delay=0.2))

    result = await check_platform_session("wb", cookie_str=COOKIES["wb"])

    assert result.status == STATUS_FAILED
    assert result.cause == CAUSE_TIMEOUT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "platform,cookie_str,expected_hint",
    [
        ("dy", "LOGIN_STATUS=1", "LOGIN_STATUS=1 in cookies"),
        ("dy", "LOGIN_STATUS=0", "no LOGIN_STATUS=1 in cookies"),
        ("tieba", "BDUSS=abc", "BDUSS/STOKEN/PTOKEN present"),
        ("tieba", "BAIDUID=abc", "no BDUSS/STOKEN/PTOKEN in cookies"),
    ],
)
async def test_browser_only_platforms_are_unknown_not_a_verdict(
    monkeypatch, platform, cookie_str, expected_hint
):
    """dy 的 pong() 先看 localStorage，cookie 只是兜底，所以这里不能断言未登录。"""

    monkeypatch.setattr(session_check, "_probe", _probe_raises(AssertionError("dy/tieba 不该联网探测")))

    result = await check_platform_session(platform, cookie_str=cookie_str)

    assert result.status == STATUS_UNKNOWN
    assert result.cause == CAUSE_BROWSER_REQUIRED
    assert expected_hint in result.detail


@pytest.mark.asyncio
async def test_exit_code_is_zero_when_nothing_failed(monkeypatch, capsys):
    _install_probe(monkeypatch, _probe_returns(True))

    assert await run_session_check(["xhs"], cookie_str=COOKIES["xhs"]) == 0

    output = capsys.readouterr().out
    assert "Session preflight" in output
    assert "ok 1 / failed 0 / unknown 0" in output


@pytest.mark.asyncio
async def test_exit_code_is_one_when_any_platform_failed(monkeypatch):
    _install_probe(monkeypatch, _probe_returns(False))

    assert await run_session_check(["xhs"], cookie_str=COOKIES["xhs"]) == 1


@pytest.mark.asyncio
async def test_unknown_alone_does_not_fail_the_run(monkeypatch):
    """否则 dy / tieba 的定时任务会永远返回非零。"""

    assert await run_session_check(["dy"], cookie_str="LOGIN_STATUS=1") == 0


@pytest.mark.asyncio
async def test_a_failure_after_an_unknown_still_sets_the_exit_code(monkeypatch, capsys):
    _install_probe(monkeypatch, _probe_returns(False))

    exit_code = await run_session_check(["dy", "xhs"], cookie_str=COOKIES["xhs"])

    assert exit_code == 1
    assert "ok 0 / failed 1 / unknown 1" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_explicit_cookies_win_and_skip_the_browser_profile(monkeypatch, tmp_path):
    """传了 --cookies / 配了 config.COOKIES 时不该去开浏览器。"""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "COOKIES", COOKIES["bili"])

    async def _boom(platform):
        raise AssertionError("有 cookie 时不应该读浏览器 profile")

    monkeypatch.setattr(session_check, "_cookies_from_browser_profile", _boom)
    _install_probe(monkeypatch, _probe_returns(True))

    result = await check_platform_session("bili")

    assert result.status == STATUS_OK
    assert "config.COOKIES" in result.detail


@pytest.mark.asyncio
async def test_saved_browser_profile_is_used_when_cookies_are_empty(monkeypatch, tmp_path):
    """默认的 qrcode 流程不写 config.COOKIES，登录态只在 browser_data/ 里。"""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "COOKIES", "")
    monkeypatch.setattr(config, "ENABLE_CDP_MODE", False)
    (tmp_path / "browser_data" / (config.USER_DATA_DIR % "bili")).mkdir(parents=True)

    read_from = []

    async def _fake_read(platform):
        read_from.append(platform)
        return COOKIES["bili"]

    monkeypatch.setattr(session_check, "_cookies_from_browser_profile", _fake_read)
    _install_probe(monkeypatch, _probe_returns(True))

    result = await check_platform_session("bili")

    assert result.status == STATUS_OK
    assert read_from == ["bili"]
    assert "browser_data/" in result.detail


@pytest.mark.asyncio
async def test_unreadable_browser_profile_is_reported_not_raised(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "COOKIES", "")
    monkeypatch.setattr(config, "ENABLE_CDP_MODE", False)
    (tmp_path / "browser_data" / (config.USER_DATA_DIR % "bili")).mkdir(parents=True)

    async def _fail(platform):
        raise RuntimeError("browser is not installed")

    monkeypatch.setattr(session_check, "_cookies_from_browser_profile", _fail)

    result = await check_platform_session("bili")

    assert result.status == STATUS_FAILED
    assert result.cause == CAUSE_NO_SESSION
    assert "browser is not installed" in result.detail


@pytest.mark.asyncio
async def test_main_turns_the_exit_code_into_systemexit(monkeypatch):
    """--check_session 的对外契约：通过 0，失败 1，且不建表、不启动爬虫。"""

    import main

    async def _fake_parse_cmd():
        from types import SimpleNamespace

        return SimpleNamespace(init_db=None, check_session=True)

    async def _fake_run_session_check(platforms, cookie_str=None):
        assert platforms == [config.PLATFORM]
        return 1

    def _no_crawler(*args, **kwargs):
        raise AssertionError("预检不应该创建爬虫")

    async def _no_init_db(*args, **kwargs):
        raise AssertionError("预检不应该建表")

    monkeypatch.setattr(main.cmd_arg, "parse_cmd", _fake_parse_cmd)
    monkeypatch.setattr(main, "run_session_check", _fake_run_session_check)
    monkeypatch.setattr(main.CrawlerFactory, "create_crawler", staticmethod(_no_crawler))
    monkeypatch.setattr(main.db, "init_db", _no_init_db)

    with pytest.raises(SystemExit) as excinfo:
        await main.main()

    assert excinfo.value.code == 1


@pytest.mark.asyncio
async def test_check_session_runs_even_when_init_db_is_requested(monkeypatch):
    """两个都传时预检要先跑，否则写在 cron 里的 --init_db --check_session 会静默跳过检查。"""

    import main

    ran = []

    async def _fake_parse_cmd():
        from types import SimpleNamespace

        return SimpleNamespace(init_db="sqlite", check_session=True)

    async def _fake_run_session_check(platforms, cookie_str=None):
        ran.append(platforms)
        return 0

    monkeypatch.setattr(main.cmd_arg, "parse_cmd", _fake_parse_cmd)
    monkeypatch.setattr(main, "run_session_check", _fake_run_session_check)

    with pytest.raises(SystemExit) as excinfo:
        await main.main()

    assert ran, "预检没有执行"
    assert excinfo.value.code == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("argv", [["--check_session"], ["--check_session", "--platform", "xhs"]])
async def test_cli_flag_sets_check_session(monkeypatch, argv):
    from cmd_arg import parse_cmd

    # parse_cmd 会就地改写 config 的全局变量，用 monkeypatch 兜住，避免污染其他测试
    for name in ("PLATFORM", "LOGIN_TYPE", "CRAWLER_TYPE", "COOKIES", "SAVE_DATA_OPTION"):
        monkeypatch.setattr(config, name, getattr(config, name))

    args = await parse_cmd(argv)

    assert args.check_session is True


@pytest.mark.asyncio
async def test_cli_flag_defaults_to_off(monkeypatch):
    from cmd_arg import parse_cmd

    for name in ("PLATFORM", "LOGIN_TYPE", "CRAWLER_TYPE", "COOKIES", "SAVE_DATA_OPTION"):
        monkeypatch.setattr(config, name, getattr(config, name))

    args = await parse_cmd(["--platform", "xhs"])

    assert args.check_session is False


async def _make_retry_error(exc: Exception) -> RetryError:
    """构造一个真实的 tenacity RetryError，内部包着 exc。"""

    try:
        async for attempt in AsyncRetrying(stop=stop_after_attempt(1), reraise=False):
            with attempt:
                raise exc
    except RetryError as retry_error:
        return retry_error
    raise AssertionError("expected a RetryError")


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner
