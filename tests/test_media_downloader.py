# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_media_downloader.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""MediaDownloader 单测。

全部基于 ``tests/media_server.py`` 提供的本地 HTTP 服务器，真实走 socket 与 httpx，
不使用任何 mock，也不访问外网。
"""

from __future__ import annotations

import os
import shutil
import subprocess

import httpx
from pathlib import Path

import pytest

from media_downloader import MediaDownloader, MediaItem, MediaType
from media_downloader.paths import (
    build_media_dir,
    build_media_path,
    ensure_within,
    guess_extension,
    redact_url,
    sanitize_component,
    url_fingerprint,
)
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
    yield


@pytest.fixture
def downloader(server: MediaTestServer, tmp_path: Path) -> MediaDownloader:
    """重试间隔调到毫秒级，避免测试因退避等待变慢"""
    return MediaDownloader(
        platform="xhs",
        base_dir=tmp_path,
        max_retries=2,
        retry_base_delay=0.001,
        retry_max_delay=0.005,
    )


def make_item(server: MediaTestServer, path: str, **overrides) -> MediaItem:
    params = {
        "url": server.url(path),
        "media_type": MediaType.IMAGE,
        "content_id": "note-1",
        "stem": "001",
    }
    params.update(overrides)
    return MediaItem(**params)


def part_path_for(tmp_path: Path, item: MediaItem, url: str) -> Path:
    directory = build_media_dir(tmp_path, "xhs", item.content_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{item.stem}.{url_fingerprint(url)}.{os.getpid()}.part"


# --------------------------------------------------------------------------- 基础


@pytest.mark.asyncio
async def test_download_success_and_layout(server, downloader, tmp_path):
    item = make_item(server, "/ok/photo")
    result = await downloader.download(item)

    assert result == tmp_path / "xhs" / "media" / "note-1" / "001.jpg"
    assert result.read_bytes() == DEFAULT_CONTENT
    assert not list(result.parent.glob("*.part")), "下载完成后不应残留临时文件"


@pytest.mark.asyncio
async def test_download_all_shares_one_client(server, downloader, monkeypatch):
    """同一帖子的多个媒体必须复用同一个 AsyncClient（而不是每个文件新建一个连接池）"""
    import media_downloader.downloader as downloader_module

    created_clients = []
    original = downloader_module.make_async_client

    def counting_make_async_client(**kwargs):
        client = original(**kwargs)
        created_clients.append(client)
        return client

    monkeypatch.setattr(downloader_module, "make_async_client", counting_make_async_client)

    items = [
        make_item(server, "/ok/a", stem="001"),
        make_item(server, "/ok/b", stem="002"),
        make_item(server, "/ok/c", stem="003"),
    ]
    paths = await downloader.download_all(items)

    assert len(paths) == 3
    assert [path.name for path in paths] == ["001.jpg", "002.jpg", "003.jpg"]
    assert server.request_count == 3
    assert len(created_clients) == 1, f"3 个文件应共用一个 client，实际创建了 {len(created_clients)} 个"


@pytest.mark.asyncio
async def test_download_all_empty(downloader):
    assert await downloader.download_all([]) == []


# --------------------------------------------------------------------------- 跳过与覆盖


@pytest.mark.asyncio
async def test_existing_file_is_skipped_without_request(server, downloader):
    item = make_item(server, "/ok/photo")
    first = await downloader.download(item)
    assert first is not None

    server.reset()
    second = await downloader.download(item)

    assert second == first
    assert server.request_count == 0, "已下载完成的文件不应再次发起请求"


@pytest.mark.asyncio
async def test_overwrite_forces_redownload(server, tmp_path):
    downloader = MediaDownloader(
        platform="xhs",
        base_dir=tmp_path,
        max_retries=0,
        overwrite=True,
    )
    item = make_item(server, "/ok/photo")
    await downloader.download(item)

    server.reset()
    await downloader.download(item)

    assert server.request_count == 1


@pytest.mark.asyncio
async def test_zero_byte_file_is_treated_as_broken(server, downloader):
    item = make_item(server, "/ok/photo")
    target = downloader.base_dir / "xhs" / "media" / "note-1" / "001.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"")

    server.reset()
    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT
    assert server.request_count == 1


# --------------------------------------------------------------------------- 续传


@pytest.mark.asyncio
async def test_resume_from_partial_file(server, downloader, tmp_path):
    """预置半个片段 -> 必须带 Range 请求，且大小校验以 Content-Range 的总长为准。

    这是关键回归：206 响应的 Content-Length 只是剩余长度（3072），
    若被误当成文件总长，4096 != 3072 会误判为失败。
    """
    item = make_item(server, "/ok/photo")
    part = part_path_for(tmp_path, item, item.url)
    part.write_bytes(DEFAULT_CONTENT[:1024])

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT
    assert server.request_count == 1
    assert server.requests[0].headers.get("range") == "bytes=1024-"


@pytest.mark.asyncio
async def test_server_ignoring_range_falls_back_to_full_download(server, downloader, tmp_path):
    item = make_item(server, "/no-range/photo")
    part = part_path_for(tmp_path, item, item.url)
    part.write_bytes(DEFAULT_CONTENT[:1024])

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT, "服务端不支持 Range 时应截断重写，而不是拼接"


@pytest.mark.asyncio
async def test_truncated_response_retries_with_range(server, downloader, tmp_path):
    """服务端中途断流 -> 重试时带 Range 续传 -> 最终拼接出完整文件"""
    item = make_item(server, "/truncated/photo?fail=1")

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT
    assert server.request_count == 2
    assert server.requests[1].headers.get("range") == f"bytes={len(DEFAULT_CONTENT) // 2}-"


@pytest.mark.asyncio
async def test_stale_part_larger_than_remote_triggers_416_restart(server, downloader, tmp_path):
    """本地残留片段比远端还大 -> 416 -> 清空片段重来"""
    item = make_item(server, "/ok/photo")
    oversized = len(DEFAULT_CONTENT) + 5000
    part = part_path_for(tmp_path, item, item.url)
    part.write_bytes(b"z" * oversized)

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT
    # 第一次带越界的 Range 拿到 416，片段被丢弃后第二次必须不带 Range 重新下载
    assert server.request_count == 2
    assert server.requests[0].headers.get("range") == f"bytes={oversized}-"
    assert server.requests[1].headers.get("range") is None


@pytest.mark.asyncio
async def test_mismatched_content_range_start_discards_partial_file(server, downloader, tmp_path):
    """服务端返回的 Range 起点与请求不符时必须丢弃片段重下，而不是把错位内容拼进去"""
    item = make_item(server, "/wrong-range/photo?delta=100&fail=1")
    part = part_path_for(tmp_path, item, item.url)
    part.write_bytes(DEFAULT_CONTENT[:1024])

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT
    assert server.request_count == 2
    assert server.requests[0].headers.get("range") == "bytes=1024-"
    assert server.requests[1].headers.get("range") is None, "片段被丢弃后应重新完整下载"


@pytest.mark.asyncio
async def test_mismatched_content_range_never_produces_corrupt_file(server, downloader, tmp_path):
    """服务端持续返回错位 Range 时应放弃下载，绝不落盘内容错位的文件"""
    item = make_item(server, "/wrong-range/broken?delta=100")
    part = part_path_for(tmp_path, item, item.url)
    part.write_bytes(DEFAULT_CONTENT[:1024])

    result = await downloader.download(item)

    assert result is None
    directory = build_media_dir(downloader.base_dir, "xhs", item.content_id)
    assert not list(directory.glob("*.jpg")), "内容错位的响应不能落盘"


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_content_type", ["text/html", "text/plain", "application/json"])
async def test_error_page_with_200_is_rejected(server, downloader, bad_content_type):
    """CDN 防盗链页常以 200 + text/html 返回，不能当成媒体文件落盘"""
    server.set_content_type("errpage", bad_content_type)
    item = make_item(server, "/ctyped/errpage")

    result = await downloader.download(item)

    assert result is None
    directory = build_media_dir(downloader.base_dir, "xhs", item.content_id)
    assert not list(directory.glob("*.jpg")), "错误页不应被保存为媒体文件"


@pytest.mark.asyncio
async def test_content_type_mismatch_preserves_partial_progress(server, downloader, tmp_path):
    """错误页在读 body 之前就被拦下，本地已有的片段必须保留以便续传"""
    server.set_content_type("limited", "text/html")
    item = make_item(server, "/ctyped/limited")
    part = part_path_for(tmp_path, item, item.url)
    part.write_bytes(DEFAULT_CONTENT[:3000])

    result = await downloader.download(item)

    assert result is None
    # 每一次尝试都要基于已有片段续传，而不是丢掉 3000 字节从头再来
    ranges = [record.headers.get("range") for record in server.requests]
    assert ranges == ["bytes=3000-"] * server.request_count, (
        f"被拦截的响应没有消耗任何字节，已下载的进度不应被丢弃，实际: {ranges}"
    )


@pytest.mark.asyncio
async def test_unsolicited_partial_response_is_rejected(server, downloader):
    """未发 Range 却收到起点非 0 的 206 时必须拒绝。

    这里用"长度自洽但内容错位"的毒响应，确保拦住它的是起点守卫本身，
    而不是被大小校验代偿（后者在长度恰好吻合时就失效了）。
    """
    item = make_item(server, "/poison-206/photo?start=100")

    result = await downloader.download(item)

    assert result is None
    directory = build_media_dir(downloader.base_dir, "xhs", item.content_id)
    assert not list(directory.glob("*.jpg")), "起点错位的内容不能落盘"


@pytest.mark.asyncio
async def test_partial_206_with_unknown_total_is_rejected(server, downloader):
    """206 的 total 为 * 时无法确认完整性（服务端可能只给了区间的一部分），必须重下"""
    item = make_item(server, "/unknown-total/photo")

    result = await downloader.download(item)

    assert result is None
    directory = build_media_dir(downloader.base_dir, "xhs", item.content_id)
    assert not list(directory.glob("*.jpg")), "无法确认完整性的内容不能落盘"


@pytest.mark.asyncio
async def test_partial_response_without_content_range_is_rejected(server, downloader, tmp_path):
    """206 缺少 Content-Range 时服务端行为不可预期（可能回全量体），必须丢弃片段重下"""
    item = make_item(server, "/no-content-range/photo")
    part = part_path_for(tmp_path, item, item.url)
    part.write_bytes(DEFAULT_CONTENT[:1024])

    result = await downloader.download(item)

    assert result is None
    assert not part.exists(), "无法确认区间语义的片段必须删除"


def test_total_size_semantics():
    """总长只能来自 Content-Range；total 未知时不反推，chunked 时忽略 Content-Length"""
    # 206：以 Content-Range 的 total 为准
    response = httpx.Response(206, headers={"content-range": "bytes 100-999/1000"})
    content_range = MediaDownloader._parse_content_range(response)
    assert content_range == (100, 999, 1000)
    assert MediaDownloader._resolve_total_size(content_range, response, 206) == 1000

    # total 为 *（服务端只返回部分区间）：不能拿 剩余长度+已下载量 反推出"总长"
    response = httpx.Response(
        206, headers={"content-range": "bytes 100-999/*", "content-length": "900"}
    )
    content_range = MediaDownloader._parse_content_range(response)
    assert content_range == (100, 999, None)
    assert MediaDownloader._resolve_total_size(content_range, response, 206) is None

    # 缺少 Content-Range 的 206 无法判定区间语义
    assert MediaDownloader._resolve_total_size(None, httpx.Response(206), 206) is None

    # chunked 响应即使带了 Content-Length 也必须忽略（RFC 7230）
    response = httpx.Response(200, headers={"transfer-encoding": "chunked", "content-length": "999"})
    assert MediaDownloader._resolve_total_size(None, response, 200) is None

    # 普通 200 用 Content-Length
    response = httpx.Response(200, headers={"content-length": "4096"})
    assert MediaDownloader._resolve_total_size(None, response, 200) == 4096


@pytest.mark.asyncio
async def test_chunked_response_ignores_bogus_content_length(server, downloader):
    """RFC 7230：有 Transfer-Encoding 时必须忽略 Content-Length，否则完整响应会被误判"""
    item = make_item(server, "/chunked-bogus-cl/photo")

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT


@pytest.mark.asyncio
async def test_gzip_response_still_lands_decoded_bytes(server, downloader):
    """服务端无视 identity 强制压缩时，落盘的应是解码后的原始字节"""
    item = make_item(server, "/gzip/photo")

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT


@pytest.mark.asyncio
async def test_malformed_url_in_backup_chain_does_not_abort(server, downloader):
    """畸形备用地址不能终止整条回退链（httpx.InvalidURL 不是 HTTPError 的子类）"""
    item = make_item(
        server,
        "/status/500",
        backup_urls=("http://h/a\nb.jpg", server.url("/ok/backup-after-bad")),
    )

    result = await downloader.download(item)

    assert result is not None, "畸形地址应被跳过，继续尝试后面的候选"


@pytest.mark.asyncio
async def test_backup_candidates_are_capped(server, tmp_path):
    """备用地址数量必须有上限，否则超长 url_list 会放大成几十次请求"""
    downloader = MediaDownloader("dy", base_dir=tmp_path, max_retries=0, max_candidates=2)
    item = make_item(
        server,
        "/status/500",
        backup_urls=tuple(server.url(f"/status/50{i}") for i in range(10)),
    )

    result = await downloader.download(item)

    assert result is None
    assert server.request_count == 2, f"候选总数应被裁剪到 2，实际请求 {server.request_count} 次"


@pytest.mark.asyncio
async def test_non_string_url_never_escapes_contract(server, downloader):
    """MediaItem 是公开契约，非字符串 url 必须收敛为 None 而不是抛异常"""
    for bad_url in (123, ["http://x"], {"url": "http://x"}, None):
        item = MediaItem(url=bad_url, media_type=MediaType.IMAGE, content_id="c")
        assert await downloader.download(item) is None


@pytest.mark.asyncio
async def test_part_file_name_is_sanitized(server, downloader, tmp_path):
    """stem 未清洗时 .part 会写到 base_dir 之外，临时文件名同样要清洗"""
    item = make_item(server, "/ok/photo", stem="../../../../tmp/ESCAPED")

    result = await downloader.download(item)

    assert result is not None
    assert result.is_relative_to(tmp_path)
    assert not list(Path("/tmp").glob("ESCAPED*")), "临时文件不得落在 base_dir 之外"


@pytest.mark.asyncio
async def test_update_credentials_switches_proxy(server, tmp_path, monkeypatch):
    """代理池就地刷新后，下载器必须跟着换代理，否则长跑时媒体下载会一直走失效代理"""
    import media_downloader.downloader as downloader_module

    used_proxies = []
    original = downloader_module.make_async_client

    def spy(**kwargs):
        used_proxies.append(kwargs.get("proxy"))
        return original(**kwargs)

    monkeypatch.setattr(downloader_module, "make_async_client", spy)
    downloader = MediaDownloader("xhs", base_dir=tmp_path, max_retries=0)

    await downloader.download(make_item(server, "/ok/cred-1"))
    downloader.update_credentials(proxy="http://new-proxy:8080")
    await downloader.download(make_item(server, "/ok/cred-2", stem="002"))

    assert used_proxies == [None, "http://new-proxy:8080"]


@pytest.mark.asyncio
async def test_binary_content_type_is_accepted(server, downloader):
    """通用二进制类型无法判定内容，应当放行（CDN 常见）"""
    server.set_content_type("blob", "application/octet-stream")
    item = make_item(server, "/ctyped/blob")

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT


@pytest.mark.asyncio
async def test_video_content_type_accepted_for_audio_stream(server, downloader):
    """DASH 音频轨的 Content-Type 是 audio/*，属于视频任务的一部分，必须放行"""
    server.set_content_type("audio-track", "audio/mp4")
    item = make_item(server, "/ctyped/audio-track", media_type=MediaType.VIDEO, stem="audio")

    result = await downloader.download(item)

    assert result is not None
    assert result.suffix == ".m4a"


@pytest.mark.asyncio
async def test_stale_part_from_other_url_is_discarded(server, downloader, tmp_path):
    """URL 变化时旧的临时片段必须作废（不能把新内容拼到旧半成品上），且下载成功后清理干净"""
    item = make_item(server, "/ok/photo")
    stale_part = part_path_for(tmp_path, item, server.url("/ok/other"))
    stale_part.write_bytes(b"y" * 1024)

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT
    assert server.requests[0].headers.get("range") is None, "不同 URL 的片段不应被当作续传基础"
    assert not stale_part.exists(), "成功后应清理同 stem 的陈旧片段"
    assert not list(result.parent.glob("*.part"))


# --------------------------------------------------------------------------- 错误处理


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [403, 404, 410])
async def test_fatal_status_is_not_retried(server, downloader, status):
    item = make_item(server, f"/status/{status}")

    result = await downloader.download(item)

    assert result is None
    assert server.request_count == 1, f"HTTP {status} 不应重试"


@pytest.mark.asyncio
async def test_server_error_is_retried_until_success(server, tmp_path):
    downloader = MediaDownloader(
        platform="xhs",
        base_dir=tmp_path,
        max_retries=3,
        retry_base_delay=0.001,
        retry_max_delay=0.005,
    )
    item = make_item(server, "/flaky/photo?fail=2")

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT
    assert server.request_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted_returns_none(server, downloader):
    item = make_item(server, "/status/500")

    result = await downloader.download(item)

    assert result is None
    assert server.request_count == 3  # 1 次 + 2 次重试


@pytest.mark.asyncio
async def test_empty_body_is_rejected(server, downloader):
    item = make_item(server, "/empty/photo")

    result = await downloader.download(item)

    assert result is None


@pytest.mark.asyncio
async def test_timeout_returns_none(server, tmp_path):
    downloader = MediaDownloader(
        platform="xhs",
        base_dir=tmp_path,
        timeout=0.2,
        max_retries=0,
    )
    item = make_item(server, "/slow/photo?s=2")

    result = await downloader.download(item)

    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_url",
    [
        "",
        "//cdn.example.com/x.jpg",  # 协议相对地址，httpx 无法处理
        "ftp://cdn.example.com/x.jpg",
        "not-a-url",
    ],
)
async def test_invalid_url_is_rejected_without_request(server, downloader, bad_url):
    item = MediaItem(url=bad_url, media_type=MediaType.IMAGE, content_id="note-1")

    assert await downloader.download(item) is None
    assert server.request_count == 0


# --------------------------------------------------------------------------- 备用地址


@pytest.mark.asyncio
async def test_backup_url_used_after_primary_fails(server, downloader):
    item = make_item(
        server,
        "/status/403",
        backup_urls=(server.url("/ok/backup"),),
    )

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT
    assert server.request_count == 2
    assert server.paths() == ["/status/403", "/ok/backup"]


# --------------------------------------------------------------------------- 响应头行为


@pytest.mark.asyncio
async def test_chunked_response_without_content_length(server, downloader):
    item = make_item(server, "/chunked/photo")

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT


@pytest.mark.asyncio
async def test_redirect_is_followed(server, downloader):
    item = make_item(server, "/redirect/photo")

    result = await downloader.download(item)

    assert result is not None
    assert result.read_bytes() == DEFAULT_CONTENT


@pytest.mark.asyncio
async def test_extension_inferred_from_content_type(server, downloader):
    server.set_content_type("anon", "image/webp")
    item = make_item(server, "/ctyped/anon")

    result = await downloader.download(item)

    assert result is not None
    assert result.suffix == ".webp"


@pytest.mark.asyncio
async def test_explicit_extension_wins(server, downloader):
    item = make_item(server, "/ctyped/anon", extension=".png")

    result = await downloader.download(item)

    assert result is not None
    assert result.suffix == ".png"


@pytest.mark.asyncio
async def test_request_headers(server, downloader):
    item = make_item(server, "/ok/photo")

    await downloader.download(item)

    headers = server.requests[0].headers
    assert headers.get("accept-encoding") == "identity", (
        "必须显式声明不压缩，否则解码后字节数与 Content-Length 不等，大小校验会误判"
    )
    assert "user-agent" in headers
    # 下载器不认识平台，Referer 必须由平台侧注入（见 test_xhs_core_sends_referer）
    assert headers.get("referer") is None


@pytest.mark.asyncio
async def test_item_headers_override_defaults(server, downloader):
    item = make_item(server, "/ok/photo", headers={"Cookie": "session=abc"})

    await downloader.download(item)

    assert server.requests[0].headers.get("cookie") == "session=abc"


@pytest.mark.asyncio
async def test_extra_headers_are_applied(server, tmp_path):
    """平台侧注入的 Referer 等反爬头必须真正发出去"""
    downloader = MediaDownloader(
        platform="bili",
        base_dir=tmp_path,
        max_retries=0,
        extra_headers={"Referer": "https://www.bilibili.com/"},
    )
    item = make_item(server, "/ok/photo")

    await downloader.download(item)

    headers = server.requests[0].headers
    assert headers.get("referer") == "https://www.bilibili.com/"


@pytest.mark.asyncio
async def test_proxy_is_passed_to_client(server, tmp_path, monkeypatch):
    import media_downloader.downloader as downloader_module

    captured: dict = {}
    original = downloader_module.make_async_client

    def spy(**kwargs):
        captured.update(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(downloader_module, "make_async_client", spy)
    downloader = MediaDownloader(
        platform="xhs",
        base_dir=tmp_path,
        proxy="http://127.0.0.1:9",
        max_retries=0,
    )
    item = make_item(server, "/ok/photo")

    # 代理不可用会失败，但我们要断言的是参数透传
    await downloader.download(item)

    assert captured.get("proxy") == "http://127.0.0.1:9"
    assert captured.get("follow_redirects") is True


# --------------------------------------------------------------------------- 路径安全


@pytest.mark.asyncio
async def test_malicious_content_id_stays_inside_base_dir(server, downloader, tmp_path):
    item = make_item(
        server,
        "/ok/photo",
        content_id="../../../etc",
        stem="../../passwd",
    )

    result = await downloader.download(item)

    assert result is not None
    assert result.resolve().is_relative_to(tmp_path.resolve())


# --------------------------------------------------------------------------- DASH 合流


def _make_dash_streams(tmp_path: Path) -> tuple[bytes, bytes]:
    """用 ffmpeg 生成一对真实的 DASH 分轨素材（视频轨 / 音频轨）"""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("本机未安装 ffmpeg")
    video = tmp_path / "_src_video.m4s"
    audio = tmp_path / "_src_audio.m4s"
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "color=c=blue:s=160x120:d=1", "-c:v", "mpeg4", "-f", "mp4", str(video)],
        check=True, capture_output=True,
    )
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "sine=f=440:d=1", "-c:a", "aac", "-f", "mp4", str(audio)],
        check=True, capture_output=True,
    )
    return video.read_bytes(), audio.read_bytes()


@pytest.mark.asyncio
async def test_dash_streams_are_downloaded_and_merged(server, tmp_path):
    video_bytes, audio_bytes = _make_dash_streams(tmp_path)
    server.set_content("dash-v", video_bytes)
    server.set_content("dash-a", audio_bytes)
    downloader = MediaDownloader("bili", base_dir=tmp_path / "out", max_retries=0)

    item = MediaItem(
        url=server.url("/ok/dash-v?ct=video/mp4"),
        audio_url=server.url("/ok/dash-a?ct=audio/mp4"),
        media_type=MediaType.VIDEO,
        content_id="BV1test",
        stem="video",
    )
    result = await downloader.download(item)

    assert result is not None
    assert result.suffix == ".mp4"
    assert result.stat().st_size > 0
    assert server.request_count == 2, "分轨应各下载一次"
    assert not list(result.parent.glob(".tmp-*")), "合流完成后必须清理临时目录"

    probe = shutil.which("ffprobe")
    if probe:
        stream_types = subprocess.run(
            [probe, "-v", "error", "-show_entries", "stream=codec_type",
             "-of", "csv=p=0", str(result)],
            check=True, capture_output=True, text=True,
        ).stdout
        assert "video" in stream_types and "audio" in stream_types


@pytest.mark.asyncio
async def test_dash_failure_cleans_up_temp_dir(server, tmp_path):
    video_bytes, _ = _make_dash_streams(tmp_path)
    server.set_content("dash-v2", video_bytes)
    downloader = MediaDownloader("bili", base_dir=tmp_path / "out", max_retries=0)

    item = MediaItem(
        url=server.url("/ok/dash-v2?ct=video/mp4"),
        audio_url=server.url("/status/403"),
        media_type=MediaType.VIDEO,
        content_id="BV1fail",
        stem="video",
    )
    result = await downloader.download(item)

    assert result is None
    media_dir = tmp_path / "out" / "bili" / "media" / "BV1fail"
    assert media_dir.is_dir()
    assert not list(media_dir.glob(".tmp-*")), "失败的 DASH 下载同样要清理临时目录"


# --------------------------------------------------------------------------- paths 纯函数


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("note-123_ab", "note-123_ab"),
        ("../../etc/passwd", "___etc_passwd"),
        ("", "unknown"),
        ("...", "unknown"),
        ("a" * 100, "a" * 64),
        ("CON", "_CON"),
        ("con.txt", "_con.txt"),
    ],
)
def test_sanitize_component(raw, expected):
    assert sanitize_component(raw) == expected


@pytest.mark.parametrize("raw", ["..", ".", "", "   "])
def test_sanitize_component_fallback_used_for_empty(raw):
    assert sanitize_component(raw, fallback="fb") == "fb"


@pytest.mark.parametrize(
    ("url", "content_type", "explicit", "expected"),
    [
        ("https://cdn.com/a/b.jpg", None, None, ".jpg"),
        ("https://cdn.com/a/b.jpeg?x=1", None, None, ".jpeg"),
        ("https://cdn.com/a/b.mp4!large", None, None, ".mp4"),
        ("https://cdn.com/a/b", "image/webp; charset=utf-8", None, ".webp"),
        ("https://cdn.com/a/b.unknownext", "video/mp4", None, ".mp4"),
        ("https://cdn.com/a/b.jpg", "image/png", ".png", ".png"),
        ("https://cdn.com/a/b.exe", None, None, ".jpg"),
        ("", None, None, ".jpg"),
    ],
)
def test_guess_extension(url, content_type, explicit, expected):
    assert guess_extension(url, content_type=content_type, explicit=explicit, default=".jpg") == expected


def test_guess_extension_ignores_explicit_outside_whitelist():
    assert guess_extension("https://cdn.com/a.jpg", explicit=".exe", default=".jpg") == ".jpg"


@pytest.mark.parametrize(
    ("platform", "content_id", "expected"),
    [
        ("xhs", "note-1", "xhs/media/note-1"),
        ("dy", "../../evil", "dy/media/___evil"),
    ],
)
def test_build_media_dir(tmp_path, platform, content_id, expected):
    assert build_media_dir(tmp_path, platform, content_id) == tmp_path / expected


def test_build_media_path_normalizes_extension():
    path = build_media_path("/base", "xhs", "note-1", "cover", "JPG")
    assert path == Path("/base/xhs/media/note-1/cover.jpg")


def test_ensure_within_rejects_escape(tmp_path):
    with pytest.raises(ValueError):
        ensure_within(tmp_path, tmp_path / ".." / "outside.mp4")


def test_url_fingerprint_is_stable_and_short():
    fingerprint = url_fingerprint("https://cdn.com/a.jpg?sig=1")
    assert fingerprint == url_fingerprint("https://cdn.com/a.jpg?sig=1")
    assert fingerprint != url_fingerprint("https://cdn.com/a.jpg?sig=2")
    assert len(fingerprint) == 8


def test_redact_url_drops_query():
    assert redact_url("https://cdn.com/a.jpg?sign=secret&t=1") == "https://cdn.com/a.jpg"
    assert redact_url("not-a-url") == "<invalid-url>"
