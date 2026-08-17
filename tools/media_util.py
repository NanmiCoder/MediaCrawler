# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tools/media_util.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对目标平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional

import config
from tools import utils


def _find_ffmpeg() -> Optional[str]:
    """Find ffmpeg executable, with common Windows install paths fallback."""
    ffmpeg_cmd = shutil.which("ffmpeg")
    if ffmpeg_cmd:
        return ffmpeg_cmd

    # Common Windows winget install path for Gyan.FFmpeg
    user_profile = os.environ.get("USERPROFILE", "")
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    ]
    if user_profile:
        base = Path(user_profile) / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
        if base.exists():
            for folder in base.glob("Gyan.FFmpeg*"):
                candidate = folder / "ffmpeg-*-full_build" / "bin" / "ffmpeg.exe"
                candidates.extend(sorted(candidate.parent.glob("ffmpeg.exe"), reverse=True))

    for candidate in candidates:
        if Path(candidate).exists():
            return str(candidate)
    return None


async def extract_audio_from_video(
    video_path: str,
    audio_path: Optional[str] = None,
    audio_format: Optional[str] = None,
    sample_rate: int = 16000,
    channels: int = 1,
) -> Optional[str]:
    """
    Extract audio from a video file using ffmpeg.

    Args:
        video_path: Path to the source video file.
        audio_path: Path to save the extracted audio. If None, inferred from video_path.
        audio_format: Audio output format, e.g. 'mp3' or 'aac'. Defaults to config.AUDIO_FORMAT.
        sample_rate: Audio sample rate. Default 16000, suitable for ASR.
        channels: Number of audio channels. Default 1 (mono).

    Returns:
        The path of the extracted audio file, or None if extraction failed.
    """
    video_file = Path(video_path)
    if not video_file.exists():
        utils.logger.error(f"[media_util.extract_audio_from_video] Video file not found: {video_path}")
        return None

    fmt = (audio_format or config.AUDIO_FORMAT).lower()
    if fmt not in ("mp3", "aac"):
        utils.logger.warning(f"[media_util.extract_audio_from_video] Unsupported audio format '{fmt}', falling back to mp3")
        fmt = "mp3"

    if audio_path is None:
        audio_path = str(video_file.with_suffix(f".{fmt}"))

    audio_file = Path(audio_path)
    audio_file.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "mp3":
        codec = "libmp3lame"
    else:
        codec = "aac"

    ffmpeg_cmd = _find_ffmpeg()
    if not ffmpeg_cmd:
        utils.logger.error("[media_util.extract_audio_from_video] ffmpeg not found in PATH, please install ffmpeg first")
        return None

    cmd = [
        ffmpeg_cmd,
        "-y",
        "-i", str(video_file),
        "-vn",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-c:a", codec,
        str(audio_file),
    ]

    try:
        utils.logger.info(f"[media_util.extract_audio_from_video] Extracting audio: {video_file.name} -> {audio_file.name}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="ignore")[-500:]
            utils.logger.error(f"[media_util.extract_audio_from_video] ffmpeg failed: {error_msg}")
            return None

        utils.logger.info(f"[media_util.extract_audio_from_video] Audio saved: {audio_file}")

        if not config.KEEP_ORIGINAL_VIDEO and video_file.exists():
            video_file.unlink()
            utils.logger.info(f"[media_util.extract_audio_from_video] Deleted original video: {video_file}")

        return str(audio_file)
    except Exception as e:
        utils.logger.error(f"[media_util.extract_audio_from_video] Exception: {e}")
        return None
