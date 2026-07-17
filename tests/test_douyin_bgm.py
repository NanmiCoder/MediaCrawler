# -*- coding: utf-8 -*-
"""
抖音 BGM(背景音乐)提取/下载功能单元测试。

覆盖:
1. _extract_music_info: 正常提取 + music 字段缺失不崩
2. update_douyin_aweme: 产出含 music_title/author/duration/cover_url/download_url
3. DouyinAweme ORM 列对齐(captured keys ⊆ ORM columns)
4. SQLite 端到端落库(music 字段写入 DB)
5. update_dy_aweme_bgm: 落盘音频 + 写清单行
6. get_aweme_bgm 主路径(music URL 直链下载成功)
7. get_aweme_bgm ffmpeg 兜底(主路径失败 + video.mp4 存在)
8. get_aweme_bgm 开关关闭(ENABLE_GET_BGM=False 立即返回)
9. get_aweme_bgm 无视频兜底跳过(ENABLE_GET_MEIDAS=False 且主路径失败)
"""
import asyncio
import os
import inspect
from typing import Dict, List

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

import config
import store.douyin as ds
from database import db_session
from database.models import Base, DouyinAweme
from media_platform.douyin.core import DouYinCrawler


# ----------------------------- mock payload -----------------------------

def _build_aweme_item_with_music() -> dict:
    """含完整 music 字段的 mock aweme_item(歌名/作者/时长/封面/play_url 全有)。"""
    return {
        "aweme_id": "7234567890123456",
        "aweme_type": 0,
        "desc": "结婚MV",
        "create_time": 1700000000,
        "author": {"uid": "9876543210", "nickname": "婚礼摄影师"},
        "statistics": {"digg_count": 100, "collect_count": 5, "comment_count": 20, "share_count": 3},
        "video": {
            "play_addr": {"url_list": ["", "http://x/video.mp4"]},
            "play_addr_h264": {"url_list": ["", "http://x/video_h264.mp4"]},
        },
        "music": {
            "title": "Perfect - Ed Sheeran",
            "author": "Ed Sheeran",
            "duration": 263,
            "cover_medium": {"url_list": ["small.jpg", "medium.jpg", "large.jpg"]},
            "play_url": {"uri": "http://x/music.m4a", "url_list": ["", "http://x/music.m4a"]},
        },
    }


def _build_aweme_item_no_music() -> dict:
    """music 字段缺失的 mock aweme_item。"""
    return {
        "aweme_id": "7234567890123457",
        "aweme_type": 0,
        "desc": "无BGM视频",
        "create_time": 1700000000,
        "author": {"uid": "9876543211", "nickname": "测试号"},
        "statistics": {"digg_count": 1, "collect_count": 0, "comment_count": 0, "share_count": 0},
        "video": {"play_addr": {"url_list": ["", "http://x/v.mp4"]}},
    }


# ----------------------------- 辅助 -----------------------------

class _FakeStore:
    """捕获存储 dict,不真正落库。"""

    def __init__(self):
        self.contents: List[Dict] = []

    async def store_content(self, content_item):
        self.contents.append(dict(content_item))


@pytest.fixture(autouse=True)
def _reset_config():
    """每个测试前后保存/恢复 config 状态,避免测试间污染。"""
    saved = {
        "ENABLE_GET_BGM": config.ENABLE_GET_BGM,
        "ENABLE_GET_MEIDAS": config.ENABLE_GET_MEIDAS,
    }
    config.ENABLE_GET_BGM = True
    config.ENABLE_GET_MEIDAS = True
    yield
    for k, v in saved.items():
        setattr(config, k, v)


# ----------------------------- 测试 1: _extract_music_info -----------------------------

def test_extract_music_info_full():
    aweme = _build_aweme_item_with_music()
    info = ds._extract_music_info(aweme)
    assert info["music_title"] == "Perfect - Ed Sheeran"
    assert info["music_author"] == "Ed Sheeran"
    assert info["music_duration"] == 263
    assert info["music_cover_url"] == "large.jpg"  # 取 url_list 最后一个
    assert info["music_download_url"] == "http://x/music.m4a"


def test_extract_music_info_missing():
    info = ds._extract_music_info(_build_aweme_item_no_music())
    assert info["music_title"] == ""
    assert info["music_author"] == ""
    assert info["music_duration"] == 0
    assert info["music_cover_url"] == ""
    assert info["music_download_url"] == ""


# ----------------------------- 测试 2: update_douyin_aweme 含 music 字段 -----------------------------

@pytest.mark.asyncio
async def test_update_douyin_aweme_contains_music_info(monkeypatch):
    fake = _FakeStore()
    monkeypatch.setattr(ds.DouyinStoreFactory, "create_store", staticmethod(lambda: fake))
    aweme = _build_aweme_item_with_music()
    await ds.update_douyin_aweme(aweme_item=aweme)
    assert len(fake.contents) == 1
    captured = fake.contents[0]
    assert captured["music_title"] == "Perfect - Ed Sheeran"
    assert captured["music_author"] == "Ed Sheeran"
    assert captured["music_duration"] == "263"  # store 层转 str
    assert captured["music_cover_url"] == "large.jpg"
    assert captured["music_download_url"] == "http://x/music.m4a"


# ----------------------------- 测试 3: ORM 列对齐 -----------------------------

def test_douyin_bgm_orm_columns():
    orm_cols = {c.name for c in DouyinAweme.__table__.columns}
    for col in ["music_title", "music_author", "music_duration", "music_cover_url", "music_download_url"]:
        assert col in orm_cols, f"ORM 缺列: {col}"


@pytest.mark.asyncio
async def test_captured_keys_subset_of_orm_columns(monkeypatch):
    fake = _FakeStore()
    monkeypatch.setattr(ds.DouyinStoreFactory, "create_store", staticmethod(lambda: fake))
    await ds.update_douyin_aweme(aweme_item=_build_aweme_item_with_music())
    captured = fake.contents[0]
    orm_cols = {c.name for c in DouyinAweme.__table__.columns}
    # captured 里多余的 key 会导致 DouyinAweme(**captured) TypeError
    extra = set(captured.keys()) - orm_cols
    assert extra == set(), f"captured 含 ORM 不存在的列: {extra}"
    # 构造 ORM 对象不抛异常
    DouyinAweme(**captured)


# ----------------------------- 测试 4: SQLite 端到端落库 -----------------------------

def test_douyin_bgm_store_end_to_end_sqlite(monkeypatch):
    aweme = _build_aweme_item_with_music()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    # 让 db_session 用内存 engine;SAVE_DATA_OPTION=db 让工厂走 DouyinDbStoreImplement
    monkeypatch.setattr(db_session, "get_async_engine", lambda *a, **kw: engine)
    monkeypatch.setattr(config, "SAVE_DATA_OPTION", "db")

    async def _scenario():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await ds.update_douyin_aweme(aweme_item=aweme)
        async with db_session.get_session() as session:
            res = await session.execute(
                select(DouyinAweme).where(DouyinAweme.aweme_id == aweme["aweme_id"])
            )
            row = res.scalar_one_or_none()
        await engine.dispose()
        return row

    row = asyncio.run(_scenario())
    assert row is not None, "作品未写入 SQLite"
    assert row.aweme_id == aweme["aweme_id"]
    assert row.music_title == "Perfect - Ed Sheeran"
    assert row.music_author == "Ed Sheeran"
    assert row.music_duration == "263"
    assert row.music_cover_url == "large.jpg"
    assert row.music_download_url == "http://x/music.m4a"


# ----------------------------- 测试 5: update_dy_aweme_bgm 落盘 + 清单 -----------------------------

@pytest.mark.asyncio
async def test_update_dy_aweme_bgm_writes_audio_and_playlist(monkeypatch, tmp_path):
    captured_audio = {}
    captured_playlist = {}

    async def _fake_store_bgm(self, item):
        captured_audio["aweme_id"] = item.get("aweme_id")
        captured_audio["bgm_content"] = item.get("bgm_content")
        captured_audio["extension_file_name"] = item.get("extension_file_name")

    async def _fake_write_jsonl(self, item, item_type):
        captured_playlist["item"] = dict(item)
        captured_playlist["item_type"] = item_type

    monkeypatch.setattr(ds.DouYinBGM, "store_bgm", _fake_store_bgm)
    monkeypatch.setattr(ds.AsyncFileWriter, "write_to_jsonl", _fake_write_jsonl)

    bgm_bytes = b"FAKE_AUDIO_BYTES_12345"
    await ds.update_dy_aweme_bgm(
        aweme_id="7234567890123456",
        bgm_content=bgm_bytes,
        extension_file_name="bgm.m4a",
        bgm_meta={
            "keyword": "结婚",
            "aweme_url": "http://www.douyin.com/video/7234567890123456",
            "video_download_url": "http://x/video.mp4",
            "music_title": "Perfect - Ed Sheeran",
            "music_author": "Ed Sheeran",
            "music_duration": 263,
            "music_url": "http://x/music.m4a",
            "bgm_source": "primary_url",
            "local_path": "data/douyin/bgm/7234567890123456/bgm.m4a",
        },
    )

    # 音频落盘参数
    assert captured_audio["aweme_id"] == "7234567890123456"
    assert captured_audio["bgm_content"] == bgm_bytes
    assert captured_audio["extension_file_name"] == "bgm.m4a"

    # 清单行
    assert captured_playlist["item_type"] == "bgm_playlist"
    p = captured_playlist["item"]
    assert p["keyword"] == "结婚"
    assert p["aweme_id"] == "7234567890123456"
    assert p["music_title"] == "Perfect - Ed Sheeran"
    assert p["music_author"] == "Ed Sheeran"
    assert p["bgm_source"] == "primary_url"
    assert p["local_path"] == "data/douyin/bgm/7234567890123456/bgm.m4a"


# ----------------------------- 测试 6-9: get_aweme_bgm -----------------------------

def _make_crawler():
    """构造一个最小 DouYinCrawler 实例(mock 掉浏览器相关属性)。"""
    c = DouYinCrawler.__new__(DouYinCrawler)
    c.dy_client = None  # 测试里手动塞 mock
    return c


@pytest.mark.asyncio
async def test_get_aweme_bgm_primary_path(monkeypatch):
    """主路径: music URL 直链下载成功。"""
    crawler = _make_crawler()
    aweme = _build_aweme_item_with_music()

    downloaded_urls = []

    class _FakeClient:
        async def get_aweme_media(self, url):
            downloaded_urls.append(url)
            # 必须 >1024 字节,否则被防盗链检测(<1024B)误判
            return b"FAKE_M4A_AUDIO_BYTES" + b"\x00" * 2048

    crawler.dy_client = _FakeClient()

    saved_meta = {}
    async def _fake_update(aweme_id, bgm_content, extension_file_name, bgm_meta):
        saved_meta["aweme_id"] = aweme_id
        saved_meta["bgm_content"] = bgm_content
        saved_meta["extension_file_name"] = extension_file_name
        saved_meta["bgm_meta"] = dict(bgm_meta)

    monkeypatch.setattr(ds, "update_dy_aweme_bgm", _fake_update)
    # 禁用 ffmpeg 兜底(不应被触发)
    async def _no_fallback(self, aweme_id):
        raise AssertionError("ffmpeg fallback should not be called in primary path test")
    monkeypatch.setattr(DouYinCrawler, "_extract_bgm_from_local_video", _no_fallback)

    await crawler.get_aweme_bgm(aweme)

    assert downloaded_urls == ["http://x/music.m4a"]
    assert saved_meta["aweme_id"] == "7234567890123456"
    # 假音频带了 padding(>1024B 绕过防盗链检测),这里只校验前缀
    assert saved_meta["bgm_content"].startswith(b"FAKE_M4A_AUDIO_BYTES")
    assert saved_meta["extension_file_name"] == "bgm.m4a"
    assert saved_meta["bgm_meta"]["bgm_source"] == "primary_url"
    assert saved_meta["bgm_meta"]["music_title"] == "Perfect - Ed Sheeran"


@pytest.mark.asyncio
async def test_get_aweme_bgm_ffmpeg_fallback(monkeypatch, tmp_path):
    """ffmpeg 兜底: 主路径失败 + video.mp4 存在,从视频分离音轨。"""
    crawler = _make_crawler()
    aweme = _build_aweme_item_with_music()
    aweme["aweme_id"] = "fallback_test_001"

    # 主路径失败(返回 None)
    class _FakeClient:
        async def get_aweme_media(self, url):
            return None
    crawler.dy_client = _FakeClient()

    # 准备一个真实小视频文件作为 video.mp4
    base = config.SAVE_DATA_PATH if config.SAVE_DATA_PATH else "data"
    video_dir = f"{base}/douyin/videos/fallback_test_001"
    os.makedirs(video_dir, exist_ok=True)
    video_path = f"{video_dir}/video.mp4"
    # 写一个最小有效 mp4 头(ffmpeg 会识别失败,但我们 mock 掉 ffmpeg 调用)
    with open(video_path, "wb") as f:
        f.write(b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00")

    # mock 掉真实的 ffmpeg 子进程,直接返回假音频
    fake_mp3_bytes = b"FAKE_MP3_FROM_FFMPEG"
    async def _fake_extract(self, aweme_id):
        return fake_mp3_bytes, "mp3"
    monkeypatch.setattr(DouYinCrawler, "_extract_bgm_from_local_video", _fake_extract)

    saved_meta = {}
    async def _fake_update(aweme_id, bgm_content, extension_file_name, bgm_meta):
        saved_meta["aweme_id"] = aweme_id
        saved_meta["bgm_content"] = bgm_content
        saved_meta["extension_file_name"] = extension_file_name
        saved_meta["bgm_meta"] = dict(bgm_meta)
    monkeypatch.setattr(ds, "update_dy_aweme_bgm", _fake_update)

    await crawler.get_aweme_bgm(aweme)

    assert saved_meta["bgm_content"] == fake_mp3_bytes
    assert saved_meta["extension_file_name"] == "bgm.mp3"
    assert saved_meta["bgm_meta"]["bgm_source"] == "ffmpeg_fallback"

    # 清理
    import shutil
    shutil.rmtree(video_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_get_aweme_bgm_disabled():
    """开关关闭时立即返回,不调用任何下载。"""
    config.ENABLE_GET_BGM = False
    crawler = _make_crawler()
    called = {"n": 0}

    class _FakeClient:
        async def get_aweme_media(self, url):
            called["n"] += 1
            return b"should_not_reach"
    crawler.dy_client = _FakeClient()

    await crawler.get_aweme_bgm(_build_aweme_item_with_music())
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_get_aweme_bgm_no_video_fallback_skipped(monkeypatch):
    """主路径失败 + ENABLE_GET_MEIDAS=False(无 video.mp4) → 兜底跳过,不写清单不崩。"""
    config.ENABLE_GET_MEIDAS = False
    crawler = _make_crawler()
    aweme = _build_aweme_item_with_music()
    aweme["aweme_id"] = "no_video_skip_001"

    class _FakeClient:
        async def get_aweme_media(self, url):
            return None
    crawler.dy_client = _FakeClient()

    saved_meta = {"called": False}
    async def _fake_update(aweme_id, bgm_content, extension_file_name, bgm_meta):
        saved_meta["called"] = True
    monkeypatch.setattr(ds, "update_dy_aweme_bgm", _fake_update)

    # 不应抛异常
    await crawler.get_aweme_bgm(aweme)
    assert saved_meta["called"] is False, "主路径失败且无视频兜底时不应写清单"
