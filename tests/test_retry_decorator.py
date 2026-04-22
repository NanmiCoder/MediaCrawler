# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_retry_decorator.py
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
Tests for auto_retry decorator
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import config
from tools.retry_decorator import (
    RetryExhaustedError,
    auto_retry,
    is_network_exception,
    NETWORK_RELATED_EXCEPTIONS,
)
from media_platform.xhs.exception import DataFetchError


class TestNetworkExceptionDetection:
    """Tests for network exception detection"""

    @pytest.mark.parametrize(
        "exception_class,expected",
        [
            (httpx.ConnectError, True),
            (httpx.ReadTimeout, True),
            (httpx.ConnectTimeout, True),
            (httpx.WriteTimeout, True),
            (httpx.PoolTimeout, True),
            (httpx.TimeoutException, True),
            (httpx.NetworkError, True),
            (httpx.TransportError, True),
            (httpx.ProtocolError, True),
            (ConnectionError, True),
            (TimeoutError, True),
        ],
    )
    def test_network_exceptions_are_detected(self, exception_class, expected):
        exc = exception_class("test error")
        assert is_network_exception(exc) == expected

    def test_non_network_exception_not_detected(self):
        exc = DataFetchError("business logic error")
        assert not is_network_exception(exc)

    def test_general_exception_not_detected(self):
        exc = ValueError("some error")
        assert not is_network_exception(exc)


class TestRetryDecoratorAsync:
    """Tests for auto_retry decorator on async functions"""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        call_count = 0

        @auto_retry(max_retries=3, base_delay=1.0, enable_config=False)
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_network_exception(self):
        call_count = 0

        @auto_retry(max_retries=3, base_delay=0.1, enable_config=False)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.ReadTimeout("timeout")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_retry_exhausted_error(self):
        call_count = 0

        @auto_retry(max_retries=3, base_delay=0.1, enable_config=False)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise httpx.ReadTimeout("timeout")

        with pytest.raises(RetryExhaustedError) as exc_info:
            await test_func()

        assert call_count == 4
        assert "ReadTimeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_retry_on_business_exception(self):
        call_count = 0

        @auto_retry(max_retries=3, base_delay=0.1, enable_config=False)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise DataFetchError("business error")

        with pytest.raises(DataFetchError):
            await test_func()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        sleep_times = []

        @auto_retry(max_retries=3, base_delay=1.0, enable_config=False)
        async def test_func():
            raise httpx.ReadTimeout("timeout")

        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            sleep_times.append(delay)

        with patch.object(asyncio, 'sleep', side_effect=mock_sleep):
            with pytest.raises(RetryExhaustedError):
                await test_func()

        assert sleep_times == [1.0, 2.0, 4.0]

    @pytest.mark.asyncio
    async def test_config_switch_disabled_no_retry(self):
        call_count = 0

        @auto_retry(max_retries=3, base_delay=0.1, enable_config=True)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise httpx.ReadTimeout("timeout")

        with patch.object(config, 'ENABLE_AUTO_RETRY', False):
            with pytest.raises(httpx.ReadTimeout):
                await test_func()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_config_switch_enabled_retry(self):
        call_count = 0

        @auto_retry(max_retries=3, base_delay=0.1, enable_config=True)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.ReadTimeout("timeout")
            return "success"

        with patch.object(config, 'ENABLE_AUTO_RETRY', True):
            result = await test_func()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self):
        @auto_retry(max_retries=3, base_delay=0.1, enable_config=False)
        async def my_test_function(arg1, arg2="default"):
            """This is a test docstring"""
            return f"{arg1}-{arg2}"

        assert my_test_function.__name__ == "my_test_function"
        assert my_test_function.__doc__ == "This is a test docstring"

        result = await my_test_function("hello", arg2="world")
        assert result == "hello-world"


class TestRetryDecoratorSync:
    """Tests for auto_retry decorator on sync functions"""

    def test_success_on_first_attempt(self):
        call_count = 0

        @auto_retry(max_retries=3, base_delay=1.0, enable_config=False)
        def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_network_exception(self):
        call_count = 0

        @auto_retry(max_retries=3, base_delay=0.1, enable_config=False)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.ReadTimeout("timeout")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 3

    def test_no_retry_on_business_exception(self):
        call_count = 0

        @auto_retry(max_retries=3, base_delay=0.1, enable_config=False)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise DataFetchError("business error")

        with pytest.raises(DataFetchError):
            test_func()

        assert call_count == 1

    def test_exponential_backoff_timing(self):
        sleep_times = []
        import time

        @auto_retry(max_retries=3, base_delay=1.0, enable_config=False)
        def test_func():
            raise httpx.ReadTimeout("timeout")

        original_sleep = time.sleep

        def mock_sleep(delay):
            sleep_times.append(delay)

        with patch.object(time, 'sleep', side_effect=mock_sleep):
            with pytest.raises(RetryExhaustedError):
                test_func()

        assert sleep_times == [1.0, 2.0, 4.0]


class TestRetryLogging:
    """Tests for retry logging"""

    @pytest.mark.asyncio
    async def test_logs_retry_attempts(self):
        from tools import utils

        log_messages = []

        def mock_warning(msg):
            log_messages.append(msg)

        original_warning = utils.logger.warning

        @auto_retry(max_retries=2, base_delay=0.1, enable_config=False)
        async def test_func():
            raise httpx.ReadTimeout("test timeout error")

        with patch.object(utils.logger, 'warning', side_effect=mock_warning):
            with pytest.raises(RetryExhaustedError):
                await test_func()

        assert len(log_messages) == 2
        assert "Network exception occurred" in log_messages[0]
        assert "ReadTimeout" in log_messages[0]
        assert "Retry 1/2" in log_messages[0]
        assert "Retry 2/2" in log_messages[1]


class TestIntegrationScenarios:
    """Integration tests simulating real use cases"""

    @pytest.mark.asyncio
    async def test_mixed_exceptions(self):
        call_count = 0
        raised_exceptions = []

        @auto_retry(max_retries=3, base_delay=0.1, enable_config=False)
        async def test_func():
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                exc = httpx.ConnectError("connection failed")
                raised_exceptions.append(exc)
                raise exc
            elif call_count == 2:
                exc = httpx.ReadTimeout("timeout")
                raised_exceptions.append(exc)
                raise exc
            else:
                return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 3
        assert len(raised_exceptions) == 2

    @pytest.mark.asyncio
    async def test_retry_then_business_error(self):
        call_count = 0

        @auto_retry(max_retries=3, base_delay=0.1, enable_config=False)
        async def test_func():
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                raise httpx.ConnectError("connection failed")
            elif call_count == 2:
                raise DataFetchError("invalid data")
            else:
                return "success"

        with pytest.raises(DataFetchError):
            await test_func()

        assert call_count == 2
