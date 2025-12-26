# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
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

import asyncio
import os
import signal
from collections.abc import Awaitable, Callable
from typing import Optional

AsyncFn = Callable[[], Awaitable[None]]


def run(
    app_main: AsyncFn,
    app_cleanup: AsyncFn,
    *,
    cleanup_timeout_seconds: float = 15.0,
    on_first_interrupt: Optional[Callable[[], None]] = None,
    force_exit_code: int = 130,
) -> None:
    async def _cleanup_with_timeout() -> None:
        try:
            await asyncio.wait_for(asyncio.shield(app_cleanup()), timeout=cleanup_timeout_seconds)
        except asyncio.TimeoutError:
            print(f"[Main] Cleanup timeout ({cleanup_timeout_seconds}s), skipping remaining cleanup.")

    async def _cancel_remaining_tasks(timeout_seconds: float = 2.0) -> None:
        current = asyncio.current_task()
        tasks = [t for t in asyncio.all_tasks() if t is not current and not t.done()]
        if not tasks:
            return
        for t in tasks:
            t.cancel()
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            pass

    async def _runner() -> None:
        loop = asyncio.get_running_loop()
        runner_task = asyncio.current_task()
        if runner_task is None:
            raise RuntimeError("Runner task not found")

        shutdown_requested = False

        def _on_signal(signum: int) -> None:
            nonlocal shutdown_requested

            if shutdown_requested:
                print("[Main] Received interrupt signal again, force exit.")
                os._exit(force_exit_code)

            shutdown_requested = True
            print(f"\n[Main] Received interrupt signal {signum}, exiting (cleanup max {cleanup_timeout_seconds}s)...")

            if on_first_interrupt is not None:
                try:
                    on_first_interrupt()
                except Exception:
                    pass

            runner_task.cancel()

        try:
            loop.add_signal_handler(signal.SIGINT, _on_signal, signal.SIGINT)
            loop.add_signal_handler(signal.SIGTERM, _on_signal, signal.SIGTERM)
        except NotImplementedError:
            signal.signal(signal.SIGINT, lambda signum, _frame: _on_signal(signum))
            signal.signal(signal.SIGTERM, lambda signum, _frame: _on_signal(signum))

        cancelled = False
        try:
            await app_main()
        except asyncio.CancelledError:
            cancelled = True
        finally:
            try:
                await _cleanup_with_timeout()
            except Exception as e:
                print(f"[Main] Error during cleanup: {e}")
            await _cancel_remaining_tasks()

        if cancelled:
            return

    asyncio.run(_runner())
