# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_media_ffmpeg.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""ffmpeg 音视频合流测试。

本机没装 ffmpeg 时整体跳过（不影响其他测试）。素材用 ffmpeg 内置的 lavfi 源生成，
不依赖任何外部文件。
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest

from media_downloader import merge_audio_video
from media_downloader.ffmpeg import ffmpeg_path, is_available
from media_downloader.types import MediaDownloadError

pytestmark = pytest.mark.skipif(not is_available(), reason="本机未安装 ffmpeg")


def _ffprobe_path() -> str:
    probe = shutil.which("ffprobe")
    if not probe:
        pytest.skip("本机未安装 ffprobe")
    return probe


def _make_video(path: Path, seconds: int = 1) -> None:
    # 显式 -f mp4：.m4s 不是 ffmpeg 能自动识别的容器后缀，需模拟 DASH 分段的真实形态
    subprocess.run(
        [
            ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"color=c=red:s=320x240:d={seconds}",
            "-c:v", "mpeg4", "-pix_fmt", "yuv420p", "-f", "mp4", str(path),
        ],
        check=True,
        capture_output=True,
    )


def _make_audio(path: Path, seconds: int = 1) -> None:
    subprocess.run(
        [
            ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"sine=f=440:d={seconds}",
            "-c:a", "aac", "-f", "mp4", str(path),
        ],
        check=True,
        capture_output=True,
    )


def _stream_types(path: Path) -> list[str]:
    result = subprocess.run(
        [
            _ffprobe_path(), "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_merge_produces_playable_file_with_both_streams(tmp_path):
    video = tmp_path / "video.m4s"
    audio = tmp_path / "audio.m4s"
    merged = tmp_path / "merged.mp4"
    _make_video(video)
    _make_audio(audio)

    await merge_audio_video(video, audio, merged)

    assert merged.exists()
    assert merged.stat().st_size > 0
    assert _stream_types(merged) == ["video", "audio"]


@pytest.mark.asyncio
async def test_merge_rejects_corrupt_input(tmp_path):
    video = tmp_path / "video.m4s"
    bad_audio = tmp_path / "audio.m4s"
    merged = tmp_path / "merged.mp4"
    _make_video(video)
    bad_audio.write_bytes(b"this is definitely not an audio stream")

    with pytest.raises(MediaDownloadError):
        await merge_audio_video(video, bad_audio, merged)


@pytest.mark.asyncio
async def test_merge_kills_subprocess_when_cancelled(tmp_path, monkeypatch):
    """任务被取消（Ctrl-C / abort）时不能留下孤儿 ffmpeg 进程"""
    import media_downloader.ffmpeg as ffmpeg_module

    # 必须用 exec：否则 sh 会另起一个 sleep 子进程，它继承着 stderr 管道，
    # 即便 kill 掉 sh，管道清理仍会阻塞到 sleep 自然结束
    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    fake_ffmpeg.write_text("#!/bin/sh\nexec sleep 60\n")
    fake_ffmpeg.chmod(0o755)
    monkeypatch.setattr(ffmpeg_module, "ffmpeg_path", lambda: str(fake_ffmpeg))

    task = asyncio.create_task(
        ffmpeg_module.merge_audio_video(
            tmp_path / "v.m4s", tmp_path / "a.m4s", tmp_path / "o.mp4", timeout=60
        )
    )
    await asyncio.sleep(0.4)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0.4)

    probe = subprocess.run(["pgrep", "-f", str(fake_ffmpeg)], capture_output=True, text=True)
    assert probe.returncode != 0, f"取消后子进程仍在运行: {probe.stdout.strip()}"


@pytest.mark.asyncio
async def test_merge_reports_missing_ffmpeg(tmp_path, monkeypatch):
    import media_downloader.ffmpeg as ffmpeg_module

    monkeypatch.setattr(ffmpeg_module, "ffmpeg_path", lambda: None)
    video = tmp_path / "video.m4s"
    audio = tmp_path / "audio.m4s"
    video.write_bytes(b"x")
    audio.write_bytes(b"y")

    with pytest.raises(MediaDownloadError, match="ffmpeg"):
        await merge_audio_video(video, audio, tmp_path / "out.mp4")


def test_is_available_matches_executable():
    assert is_available() is bool(ffmpeg_path())
