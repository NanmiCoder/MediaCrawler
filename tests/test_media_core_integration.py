# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_media_core_integration.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""平台 core 的 ``download_media`` 与统一下载器的集成测试。

用本地 HTTP 服务器冒充平台 CDN，验证「core 编排 -> 平台 URL 提取 -> 统一下载器 -> 落盘」
的完整链路，不依赖外部网络、浏览器与登录态。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import config
import httpx
import pytest

from media_platform.bilibili.core import BilibiliCrawler
from media_platform.douyin.core import DouYinCrawler
from media_platform.kuaishou.core import KuaishouCrawler
from media_platform.weibo.core import WeiboCrawler
from media_platform.xhs.core import XiaoHongShuCrawler
from tests.media_server import DEFAULT_CONTENT, MediaTestServer, start_server


@pytest.fixture(scope="module")
def server():
    srv, _thread = start_server()
    yield srv
    srv.shutdown()
    srv.server_close()


@pytest.fixture(autouse=True)
def _reset_server(server: MediaTestServer):
    server.reset()


@pytest.fixture(autouse=True)
def _media_config(monkeypatch, tmp_path: Path):
    """打开媒体下载开关并把落盘根目录指到临时目录"""
    monkeypatch.setattr(config, "ENABLE_GET_MEDIA", True)
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))
    monkeypatch.setattr(config, "XHS_INTERNATIONAL", False)
    # 平台在媒体下载之间会按爬虫限速 sleep，测试里不需要真的等
    monkeypatch.setattr(config, "CRAWLER_MAX_SLEEP_SEC", 0)


def media_dir(tmp_path: Path, platform: str, content_id: str) -> Path:
    return tmp_path / platform / "media" / content_id


def assert_downloaded(directory: Path, filename: str) -> Path:
    path = directory / filename
    assert path.is_file(), f"缺少文件 {path}，目录内容: {sorted(p.name for p in directory.iterdir())}"
    assert path.stat().st_size == len(DEFAULT_CONTENT)
    return path


# --------------------------------------------------------------------------- xhs


@pytest.mark.asyncio
async def test_xhs_core_downloads_cover_and_video(server, tmp_path):
    note = {
        "note_id": "xhs-e2e-video",
        "type": "video",
        "image_list": [],
        "video": {
            # 不带 origin_video_key，走 master_url 分支以便指向本地服务器
            "media": {"stream": {"h264": [{"master_url": server.url("/ok/xhs-video?ct=video/mp4")}]}},
            "cover": {"url_default": server.url("/ok/xhs-cover")},
        },
    }
    crawler = XiaoHongShuCrawler()
    crawler.xhs_client = SimpleNamespace(proxy=None)
    crawler.user_agent = "integration-test-agent"

    await crawler.download_media(note)

    directory = media_dir(tmp_path, "xhs", "xhs-e2e-video")
    assert_downloaded(directory, "cover.jpg")
    assert_downloaded(directory, "video.mp4")
    assert server.request_count == 2


@pytest.mark.asyncio
async def test_xhs_core_downloads_numbered_images(server, tmp_path):
    note = {
        "note_id": "xhs-e2e-images",
        "type": "normal",
        "image_list": [
            {"url_default": server.url("/ok/xhs-img-1")},
            {"url_default": server.url("/ok/xhs-img-2")},
        ],
    }
    crawler = XiaoHongShuCrawler()
    crawler.xhs_client = SimpleNamespace(proxy=None)
    crawler.user_agent = "integration-test-agent"

    await crawler.download_media(note)

    directory = media_dir(tmp_path, "xhs", "xhs-e2e-images")
    assert_downloaded(directory, "001.jpg")
    assert_downloaded(directory, "002.jpg")
    assert not (directory / "cover.jpg").exists(), "图文笔记不应再单独下载一份封面"


@pytest.mark.asyncio
async def test_xhs_core_sends_referer(server, tmp_path):
    note = {
        "note_id": "xhs-e2e-referer",
        "type": "normal",
        "image_list": [{"url_default": server.url("/ok/xhs-referer")}],
    }
    crawler = XiaoHongShuCrawler()
    crawler.xhs_client = SimpleNamespace(proxy=None)
    crawler.user_agent = "integration-test-agent"

    await crawler.download_media(note)

    assert server.requests[0].headers.get("referer") == "https://www.xiaohongshu.com/"
    assert server.requests[0].headers.get("user-agent") == "integration-test-agent"


# --------------------------------------------------------------------------- douyin


@pytest.mark.asyncio
async def test_douyin_core_downloads_cover_and_video(server, tmp_path):
    aweme = {
        "aweme_id": "dy-e2e-video",
        "video": {
            "play_addr_h264": {"url_list": [server.url("/ok/dy-video?ct=video/mp4")]},
            "raw_cover": {"url_list": [server.url("/ok/dy-cover")]},
        },
    }
    crawler = DouYinCrawler()
    # client.headers 里带上 Cookie，用于验证它不会被透传到 CDN 请求上
    crawler.dy_client = SimpleNamespace(
        proxy=None, headers={"User-Agent": "dy-agent", "Cookie": "session=secret"}
    )

    await crawler.download_media(aweme)

    directory = media_dir(tmp_path, "dy", "dy-e2e-video")
    assert_downloaded(directory, "cover.jpg")
    assert_downloaded(directory, "video.mp4")
    sent = server.requests[0].headers
    assert sent.get("referer") == "https://www.douyin.com/"
    assert sent.get("user-agent") == "dy-agent"
    assert sent.get("cookie") is None, "不应把平台 Cookie 带到 CDN 请求上"


@pytest.mark.asyncio
async def test_douyin_core_downloads_images(server, tmp_path):
    aweme = {
        "aweme_id": "dy-e2e-images",
        "images": [
            {"url_list": [server.url("/ok/dy-img-1")]},
            {"url_list": [server.url("/ok/dy-img-2")]},
        ],
    }
    crawler = DouYinCrawler()
    crawler.dy_client = SimpleNamespace(proxy=None, headers={})

    await crawler.download_media(aweme)

    directory = media_dir(tmp_path, "dy", "dy-e2e-images")
    assert_downloaded(directory, "001.jpg")
    assert_downloaded(directory, "002.jpg")


# --------------------------------------------------------------------------- kuaishou


@pytest.mark.asyncio
async def test_kuaishou_core_downloads_cover_and_video(server, tmp_path):
    video_item = {
        "photo": {
            "id": "ks-e2e-video",
            "photoUrl": server.url("/ok/ks-video?ct=video/mp4"),
            "coverUrl": server.url("/ok/ks-cover"),
        }
    }
    crawler = KuaishouCrawler()
    crawler.ks_client = SimpleNamespace(proxy=None, headers={})

    await crawler.download_media(video_item)

    directory = media_dir(tmp_path, "ks", "ks-e2e-video")
    assert_downloaded(directory, "cover.jpg")
    assert_downloaded(directory, "video.mp4")
    assert server.requests[0].headers.get("referer") == "https://www.kuaishou.com/"


# --------------------------------------------------------------------------- weibo


@pytest.mark.asyncio
async def test_weibo_core_downloads_cover_and_video(server, tmp_path):
    mblog = {
        "id": "wb-e2e-video",
        "page_info": {
            "type": "video",
            "page_pic": {"url": server.url("/ok/wb-cover")},
            "media_info": {"mp4_hd_mp4": server.url("/ok/wb-video?ct=video/mp4")},
        },
    }
    crawler = WeiboCrawler()
    crawler.wb_client = SimpleNamespace(proxy=None, headers={})

    await crawler.download_media(mblog)

    directory = media_dir(tmp_path, "wb", "wb-e2e-video")
    assert_downloaded(directory, "cover.jpg")
    assert_downloaded(directory, "video.mp4")


# --------------------------------------------------------------------------- bilibili


@pytest.mark.asyncio
async def test_bilibili_core_downloads_cover_even_without_play_info(server, tmp_path, monkeypatch):
    """playurl 拿不到时，封面仍应正常落盘（两者是独立的下载任务）"""
    crawler = BilibiliCrawler()
    crawler.bili_client = SimpleNamespace(proxy=None, headers={})

    async def fake_play_url(*args, **kwargs):
        return None

    monkeypatch.setattr(crawler, "get_video_play_url_task", fake_play_url)

    video_item = {
        "View": {
            "aid": 1,
            "cid": 2,
            "bvid": "BV1e2e",
            "pic": server.url("/ok/bili-cover"),
        }
    }

    await crawler.download_media(video_item, asyncio.Semaphore(1))

    directory = media_dir(tmp_path, "bili", "BV1e2e")
    assert_downloaded(directory, "cover.jpg")
    assert not (directory / "video.mp4").exists()


@pytest.mark.asyncio
async def test_bilibili_core_skips_dash_when_ffmpeg_unavailable(server, tmp_path, monkeypatch):
    """ffmpeg 不可用时应直接走直链：DASH 流的地址一次都不该被请求"""
    import media_platform.bilibili.core as bili_core
    from media_platform.bilibili.media import DASH_FNVAL, MP4_FNVAL

    monkeypatch.setattr(bili_core, "is_ffmpeg_available", lambda: False)
    crawler = BilibiliCrawler()
    crawler.bili_client = SimpleNamespace(proxy=None, headers={})

    requested_fnvals = []

    async def fake_play_url(aid, cid, semaphore, fnval=None):
        requested_fnvals.append(fnval if fnval is not None else DASH_FNVAL)
        return {
            "dash": {
                "video": [{"id": 80, "base_url": server.url("/ok/dash-video-unused?ct=video/mp4")}],
                "audio": [{"id": 30280, "base_url": server.url("/ok/dash-audio-unused?ct=audio/mp4")}],
            },
            "durl": [{"url": server.url("/ok/bili-durl?ct=video/mp4"), "size": 100}],
        }

    monkeypatch.setattr(crawler, "get_video_play_url_task", fake_play_url)

    video_item = {"View": {"aid": 1, "cid": 2, "bvid": "BV1fallback", "pic": server.url("/ok/bili-cover2")}}

    await crawler.download_media(video_item, asyncio.Semaphore(1))

    directory = media_dir(tmp_path, "bili", "BV1fallback")
    # 直链产物刻意与 DASH 产物（video.mp4）区分，避免低清文件阻塞后续的高清路径
    assert_downloaded(directory, "video-durl.mp4")
    assert requested_fnvals == [MP4_FNVAL], "ffmpeg 不可用时应直接按 MP4 格式请求，不做无用的 DASH 请求"

    requested_paths = server.paths()
    assert not any("unused" in path for path in requested_paths), (
        f"ffmpeg 不可用时不应下载 DASH 分轨，实际请求: {requested_paths}"
    )


@pytest.mark.asyncio
async def test_core_download_media_never_raises_on_malformed_payload(server, tmp_path):
    """平台返回畸形结构时，download_media 只能记日志，不能把异常抛给爬取主流程"""
    crawler = XiaoHongShuCrawler()
    crawler.xhs_client = SimpleNamespace(proxy=None)
    crawler.user_agent = "integration-test-agent"

    # video 字段是字符串，提取器若不做防御会 AttributeError
    await crawler.download_media({"note_id": "x", "type": "video", "video": "oops"})

    assert server.request_count == 0


@pytest.mark.asyncio
async def test_core_survives_extractor_exception(server, tmp_path, monkeypatch):
    """提取器抛异常时必须被 core 的壳层兜住（直接锁定 try/except，去掉它此用例会失败）"""
    crawler = XiaoHongShuCrawler()
    crawler.xhs_client = SimpleNamespace(proxy=None)
    crawler.user_agent = "integration-test-agent"

    def boom(_raw):
        raise RuntimeError("extractor exploded")

    monkeypatch.setattr("media_platform.xhs.core.xhs_media.build_media_items", boom)

    await crawler.download_media({"note_id": "boom"})

    assert server.request_count == 0


@pytest.mark.asyncio
async def test_bilibili_dash_success_skips_durl_fallback(server, tmp_path, monkeypatch):
    """DASH 下载成功后必须立即结束，不能再下一份低清直链。

    这是 B 站的主路径（装好 ffmpeg 的机器），此前完全没有测试覆盖。
    """
    import media_downloader.downloader as downloader_module
    import media_platform.bilibili.core as bili_core

    monkeypatch.setattr(bili_core, "is_ffmpeg_available", lambda: True)

    async def fake_merge(video_path, audio_path, output_path, timeout=300.0):
        output_path.write_bytes(b"merged-mp4")

    monkeypatch.setattr(downloader_module, "merge_audio_video", fake_merge)

    crawler = BilibiliCrawler()
    crawler.bili_client = SimpleNamespace(proxy=None, headers={})

    async def fake_play_url(aid, cid, semaphore, fnval=None):
        return {
            "dash": {
                "video": [{"id": 80, "codecid": 7, "base_url": server.url("/ok/dash-best?ct=video/mp4")}],
                "audio": [{"id": 30280, "base_url": server.url("/ok/dash-audio?ct=audio/mp4")}],
            },
            "durl": [{"url": server.url("/ok/low-quality-durl?ct=video/mp4"), "size": 1}],
        }

    monkeypatch.setattr(crawler, "get_video_play_url_task", fake_play_url)

    video_item = {
        "View": {"aid": 1, "cid": 2, "bvid": "BV1dashok", "pic": server.url("/ok/bili-cover-5")}
    }
    await crawler.download_media(video_item, asyncio.Semaphore(1))

    directory = media_dir(tmp_path, "bili", "BV1dashok")
    assert (directory / "video.mp4").is_file(), "DASH 合流产物应落在 video.mp4"
    assert not (directory / "video-durl.mp4").exists(), "DASH 成功后不应再走直链"
    assert not any("low-quality" in path for path in server.paths()), (
        f"DASH 成功时不应请求直链，实际请求: {server.paths()}"
    )


@pytest.mark.asyncio
async def test_bilibili_falls_back_to_lower_quality_when_cdn_rejects(server, tmp_path, monkeypatch):
    """高清流取流被 CDN 拒绝时（未登录/权限不足的真实场景），应逐档降级而不是直接放弃"""
    import media_downloader.downloader as downloader_module
    import media_platform.bilibili.core as bili_core

    monkeypatch.setattr(bili_core, "is_ffmpeg_available", lambda: True)
    monkeypatch.setattr(config, "BILI_QN", 80)

    async def fake_merge(video_path, audio_path, output_path, timeout=300.0):
        output_path.write_bytes(b"merged-sd")

    monkeypatch.setattr(downloader_module, "merge_audio_video", fake_merge)

    crawler = BilibiliCrawler()
    crawler.bili_client = SimpleNamespace(proxy=None, headers={})

    async def fake_play_url(aid, cid, semaphore, fnval=None):
        return {
            "dash": {
                "video": [
                    {"id": 80, "codecid": 7, "base_url": server.url("/status/403")},  # 高清被 CDN 拒绝
                    {"id": 32, "codecid": 7, "base_url": server.url("/ok/dash-sd?ct=video/mp4")},
                ],
                "audio": [{"id": 30280, "base_url": server.url("/ok/dash-sd-audio?ct=audio/mp4")}],
            }
        }

    monkeypatch.setattr(crawler, "get_video_play_url_task", fake_play_url)

    video_item = {"View": {"aid": 1, "cid": 2, "bvid": "BV1degrade", "pic": server.url("/ok/bili-cover-8")}}
    await crawler.download_media(video_item, asyncio.Semaphore(1))

    directory = media_dir(tmp_path, "bili", "BV1degrade")
    assert (directory / "video.mp4").read_bytes() == b"merged-sd"
    assert any("dash-sd" in path for path in server.paths()), "应降级到低清晰度流"


@pytest.mark.asyncio
async def test_bilibili_durl_does_not_block_later_dash_download(server, tmp_path, monkeypatch):
    """先前降级下载的低清直链产物，不能阻止之后（装好 ffmpeg）走 DASH 拿高清"""
    import media_downloader.downloader as downloader_module
    import media_platform.bilibili.core as bili_core

    directory = media_dir(tmp_path, "bili", "BV1upgrade")
    directory.mkdir(parents=True)
    (directory / "video-durl.mp4").write_bytes(b"low-resolution-durl-file")

    monkeypatch.setattr(bili_core, "is_ffmpeg_available", lambda: True)

    async def fake_merge(video_path, audio_path, output_path, timeout=300.0):
        output_path.write_bytes(b"high-resolution-dash-file")

    monkeypatch.setattr(downloader_module, "merge_audio_video", fake_merge)

    crawler = BilibiliCrawler()
    crawler.bili_client = SimpleNamespace(proxy=None, headers={})

    async def fake_play_url(aid, cid, semaphore, fnval=None):
        return {
            "dash": {
                "video": [{"id": 80, "codecid": 7, "base_url": server.url("/ok/dash-up?ct=video/mp4")}],
                "audio": [{"id": 30280, "base_url": server.url("/ok/dash-up-a?ct=audio/mp4")}],
            }
        }

    monkeypatch.setattr(crawler, "get_video_play_url_task", fake_play_url)

    video_item = {
        "View": {"aid": 1, "cid": 2, "bvid": "BV1upgrade", "pic": server.url("/ok/bili-cover-6")}
    }
    await crawler.download_media(video_item, asyncio.Semaphore(1))

    assert (directory / "video.mp4").read_bytes() == b"high-resolution-dash-file"
    assert server.request_count > 0, "已有的低清直链产物不应让 DASH 路径被跳过"


@pytest.mark.asyncio
async def test_bilibili_download_media_survives_play_url_failure(server, tmp_path, monkeypatch):
    """playurl 抛出非 DataFetchError 的异常（如网络超时）时，壳层必须兜住。

    这条用例锁定的正是 core 里的 try/except：去掉它，异常会直接击穿爬取主流程。
    """
    crawler = BilibiliCrawler()
    crawler.bili_client = SimpleNamespace(proxy=None, headers={})

    async def boom(*args, **kwargs):
        raise httpx.ReadTimeout("simulated timeout")

    monkeypatch.setattr(crawler, "get_video_play_url_task", boom)

    video_item = {
        "View": {"aid": 1, "cid": 2, "bvid": "BV1boom", "pic": server.url("/ok/bili-cover-3")}
    }

    await crawler.download_media(video_item, asyncio.Semaphore(1))

    # 封面在 playurl 之前下载，失败不影响它
    directory = media_dir(tmp_path, "bili", "BV1boom")
    assert_downloaded(directory, "cover.jpg")
    assert not (directory / "video.mp4").exists()


# --------------------------------------------------------------------------- 开关


@pytest.mark.asyncio
async def test_media_switch_off_downloads_nothing(server, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ENABLE_GET_MEDIA", False)
    note = {
        "note_id": "xhs-switch-off",
        "type": "normal",
        "image_list": [{"url_default": server.url("/ok/should-not-download")}],
    }
    crawler = XiaoHongShuCrawler()
    crawler.xhs_client = SimpleNamespace(proxy=None)
    crawler.user_agent = "integration-test-agent"

    await crawler.download_media(note)

    assert server.request_count == 0
    assert not media_dir(tmp_path, "xhs", "xhs-switch-off").exists()


@pytest.mark.asyncio
async def test_download_all_keeps_going_after_one_failure(server, tmp_path):
    """单个媒体失败不应影响同帖其它媒体"""
    note = {
        "note_id": "xhs-partial-failure",
        "type": "normal",
        "image_list": [
            {"url_default": server.url("/status/500")},
            {"url_default": server.url("/ok/xhs-good-image")},
        ],
    }
    crawler = XiaoHongShuCrawler()
    crawler.xhs_client = SimpleNamespace(proxy=None)
    crawler.user_agent = "integration-test-agent"

    await crawler.download_media(note)

    directory = media_dir(tmp_path, "xhs", "xhs-partial-failure")
    assert not (directory / "001.jpg").exists()
    assert_downloaded(directory, "002.jpg")
