# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tools/retry_decorator.py
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

import asyncio
from functools import wraps
from typing import Callable, Type, Tuple

import httpx

import config
from tools import utils


class RetryExhaustedError(Exception):
    pass


NETWORK_RELATED_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.TransportError,
    httpx.ProtocolError,
    ConnectionError,
    TimeoutError,
)


def is_network_exception(exception: Exception) -> bool:
    return isinstance(exception, NETWORK_RELATED_EXCEPTIONS)


def auto_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    enable_config: bool = True,
):
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if enable_config and not config.ENABLE_AUTO_RETRY:
                return await func(*args, **kwargs)

            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if not is_network_exception(e):
                        utils.logger.warning(
                            f"[auto_retry] Non-network exception occurred, not retrying: "
                            f"{e.__class__.__name__}: {str(e)}"
                        )
                        raise

                    if attempt >= max_retries:
                        utils.logger.error(
                            f"[auto_retry] All {max_retries} retry attempts failed. "
                            f"Last exception: {e.__class__.__name__}: {str(e)}"
                        )
                        raise RetryExhaustedError(
                            f"All {max_retries} retry attempts failed. "
                            f"Last exception: {e.__class__.__name__}: {str(e)}"
                        ) from e

                    delay = base_delay * (2 ** attempt)
                    utils.logger.warning(
                        f"[auto_retry] Network exception occurred: {e.__class__.__name__}: {str(e)}. "
                        f"Retry {attempt + 1}/{max_retries} in {delay}s..."
                    )
                    await asyncio.sleep(delay)

            if last_exception:
                raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if enable_config and not config.ENABLE_AUTO_RETRY:
                return func(*args, **kwargs)

            last_exception = None
            import time
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if not is_network_exception(e):
                        utils.logger.warning(
                            f"[auto_retry] Non-network exception occurred, not retrying: "
                            f"{e.__class__.__name__}: {str(e)}"
                        )
                        raise

                    if attempt >= max_retries:
                        utils.logger.error(
                            f"[auto_retry] All {max_retries} retry attempts failed. "
                            f"Last exception: {e.__class__.__name__}: {str(e)}"
                        )
                        raise RetryExhaustedError(
                            f"All {max_retries} retry attempts failed. "
                            f"Last exception: {e.__class__.__name__}: {str(e)}"
                        ) from e

                    delay = base_delay * (2 ** attempt)
                    utils.logger.warning(
                        f"[auto_retry] Network exception occurred: {e.__class__.__name__}: {str(e)}. "
                        f"Retry {attempt + 1}/{max_retries} in {delay}s..."
                    )
                    time.sleep(delay)

            if last_exception:
                raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
