# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_media_e2e.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""真实平台端到端测试（默认跳过）。

会真实访问 B 站接口与 CDN 并下载一个完整视频（约几十 MB），因此只在人工验证时运行：

    MEDIA_E2E=1 .venv/bin/python -m pytest tests/test_media_e2e.py -v

B 站无需登录即可获取公开视频的基础清晰度，wbi 签名是纯算法，
所以这里不依赖浏览器与账号，只验证「提取 -> 下载 -> 合流」的真实链路。
请勿把本文件接入 CI：它会对目标平台产生真实流量。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import config
import httpx
import pytest

from media_downloader import MediaDownloader, is_ffmpeg_available
from media_platform.bilibili import media as bili_media
from media_platform.bilibili.help import BilibiliSign

pytestmark = pytest.mark.skipif(
    os.getenv("MEDIA_E2E") != "1",
    reason="真实平台测试，设置 MEDIA_E2E=1 后运行",
)

BV_ID = os.getenv("MEDIA_E2E_BVID", "BV1dwuKzmE26")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


async def _fetch_wbi_keys(client: httpx.AsyncClient) -> tuple[str, str]:
    """从 nav 接口获取 wbi 签名所需的 img_key / sub_key（无需登录）"""
    response = await client.get(
        "https://api.bilibili.com/x/web-interface/nav", headers={"User-Agent": USER_AGENT}
    )
    wbi_img = response.json()["data"]["wbi_img"]
    img_key = wbi_img["img_url"].rsplit("/", 1)[1].split(".")[0]
    sub_key = wbi_img["sub_url"].rsplit("/", 1)[1].split(".")[0]
    return img_key, sub_key


@pytest.mark.asyncio
async def test_bilibili_downloads_cover_and_video(tmp_path: Path):
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        view_response = await client.get(
            "https://api.bilibili.com/x/web-interface/view",
            params={"bvid": BV_ID},
            headers={"User-Agent": USER_AGENT},
        )
        view_data = view_response.json()["data"]
        aid, cid, pic = view_data["aid"], view_data["cid"], view_data["pic"]

        img_key, sub_key = await _fetch_wbi_keys(client)
        params = {
            "avid": aid,
            "cid": cid,
            "qn": 80,
            "fourk": 1,
            "fnval": bili_media.DASH_FNVAL,
            "platform": "pc",
        }
        signed = BilibiliSign(img_key, sub_key).sign(params)
        play_response = await client.get(
            "https://api.bilibili.com/x/player/wbi/playurl",
            params=signed,
            headers={"User-Agent": USER_AGENT, "Referer": "https://www.bilibili.com"},
        )
        payload = play_response.json()
        assert payload.get("code") == 0, f"playurl 接口返回异常: {payload}"
        play_info = payload["data"]

    view = {"aid": aid, "cid": cid, "bvid": BV_ID, "pic": pic}
    cover_item = bili_media.build_cover_item(view, BV_ID)

    # 生产路径由 core._media_headers() 注入 Referer；这里绕过 core 直接构造下载器，
    # 必须自行带上，否则 B 站 CDN 一律 403
    downloader = MediaDownloader(
        "bili",
        base_dir=tmp_path,
        max_retries=2,
        timeout=120.0,
        extra_headers={"Referer": "https://www.bilibili.com/", "User-Agent": USER_AGENT},
    )
    cover_path = await downloader.download(cover_item)

    # 与 core 的编排保持一致：未登录时 B 站会返回高清晰度 URL 但取流被 CDN 403，
    # 需要逐档降级到实际可下载的档位
    video_item = None
    video_path = None
    if is_ffmpeg_available():
        quality = getattr(config, "BILI_QN", 80)
        while quality is not None:
            candidate = bili_media.build_dash_item(play_info, BV_ID, preferred_quality=quality)
            if candidate is None:
                break
            video_item = candidate
            video_path = await downloader.download(candidate)
            if video_path is not None:
                break
            lower_quality = bili_media.next_lower_quality(play_info, quality)
            if lower_quality is None:
                break
            print(f"[e2e] 清晰度 {quality} 取流失败，降级到 {lower_quality}")
            quality = lower_quality

    if video_path is None:
        video_item = bili_media.build_durl_item(play_info, BV_ID)
        if video_item is None:
            fallback = await _fetch_play_info_for_mp4(aid, cid)
            video_item = bili_media.build_durl_item(fallback or {}, BV_ID)
        if video_item is not None:
            video_path = await downloader.download(video_item)

    assert video_item is not None, "未能从 playurl 响应中提取到视频流"

    assert cover_path is not None and cover_path.stat().st_size > 0
    assert cover_path.read_bytes()[:2] == b"\xff\xd8", "封面应为 JPEG"

    assert video_path is not None and video_path.stat().st_size > 0
    if video_item.is_dash:
        assert video_path.suffix == ".mp4", "DASH 合流产物应为 mp4"
        assert not list(video_path.parent.glob(".tmp-*")), "临时目录应被清理"

        probe = shutil.which("ffprobe")
        if probe:
            result = subprocess.run(
                [probe, "-v", "error", "-show_entries", "stream=codec_type",
                 "-of", "csv=p=0", str(video_path)],
                check=True, capture_output=True, text=True,
            )
            stream_types = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            assert "video" in stream_types and "audio" in stream_types, (
                f"DASH 合流后应同时包含视频轨与音频轨，实际: {stream_types}"
            )

async def _fetch_play_info_for_mp4(aid: int, cid: int) -> dict:
    """按 mp4 格式再取一次播放地址（DASH 响应里不带 durl）"""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        img_key, sub_key = await _fetch_wbi_keys(client)
        params = {
            "avid": aid,
            "cid": cid,
            "qn": 80,
            "fourk": 1,
            "fnval": bili_media.MP4_FNVAL,
            "platform": "pc",
        }
        signed = BilibiliSign(img_key, sub_key).sign(params)
        response = await client.get(
            "https://api.bilibili.com/x/player/wbi/playurl",
            params=signed,
            headers={"User-Agent": USER_AGENT, "Referer": "https://www.bilibili.com"},
        )
        payload = response.json()
        return payload.get("data") or {}
