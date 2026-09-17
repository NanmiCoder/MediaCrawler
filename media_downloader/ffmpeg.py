# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_downloader/ffmpeg.py
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

"""ffmpeg 检测与音视频合流。

DASH 资源（如 B 站）的视频轨与音频轨是分开的，需要 ffmpeg 无损封装成 mp4。
本机没有 ffmpeg 时调用方应降级为单流直链，不做任何隐式安装。
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import logging
import shutil
from pathlib import Path

from .types import MediaDownloadError

logger = logging.getLogger("MediaCrawler.media_downloader.ffmpeg")

DEFAULT_MERGE_TIMEOUT = 300.0


@functools.lru_cache(maxsize=1)
def ffmpeg_path() -> str | None:
    """返回本机 ffmpeg 可执行文件路径，不存在则返回 None（进程内缓存一次）"""
    return shutil.which("ffmpeg")


def is_available() -> bool:
    """本机是否具备 ffmpeg"""
    return ffmpeg_path() is not None


async def merge_audio_video(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    timeout: float = DEFAULT_MERGE_TIMEOUT,
) -> None:
    """把独立的视频轨与音频轨无损封装成 mp4。

    必须使用 ``asyncio.create_subprocess_exec``：爬虫的采集与评论任务跑在同一个
    事件循环上，同步的 ``subprocess.run`` 会阻塞整个循环数十秒。

    :raises MediaDownloadError: ffmpeg 不存在、超时或返回非 0
    """
    executable = ffmpeg_path()
    if not executable:
        raise MediaDownloadError("未检测到 ffmpeg，无法合流 DASH 音视频")

    process = await asyncio.create_subprocess_exec(
        executable,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c",
        "copy",
        str(output_path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.wait()
        raise MediaDownloadError(f"ffmpeg 合流超时（{timeout}s）") from exc
    except BaseException:
        # 外部取消（Ctrl-C / 任务被 abort）不会走上面的超时分支，
        # 这里必须显式回收子进程，否则 ffmpeg 会变成孤儿继续跑满整个编解码任务
        if process.returncode is None:
            process.kill()
            # 等待子进程真正退出：否则 transport 会留到事件循环关闭后才被 GC 并报错。
            # 取消状态下这个 await 可能再次被取消，吞掉即可，原始异常照常抛出
            with contextlib.suppress(BaseException):
                await process.wait()
        raise

    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace")[-500:] if stderr else ""
        raise MediaDownloadError(f"ffmpeg 合流失败（退出码 {process.returncode}）: {detail}")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise MediaDownloadError("ffmpeg 合流产物为空")

    logger.info(
        "[merge_audio_video] 合流完成: %s (%d bytes)",
        output_path.name,
        output_path.stat().st_size,
    )
