# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_downloader/downloader.py
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

"""统一媒体下载器。

设计要点（与常见实现的关键差异）：

1. **零额外请求**：不做 HEAD 探测（大量 CDN 对 HEAD 返回 403/405 或与 GET 不一致），
   大小、类型、是否支持续传全部从一次 ``stream GET`` 的响应头判定。
2. **大小校验按 HTTP 语义**：206 响应的 ``Content-Length`` 是"剩余长度"，
   文件总大小必须取自 ``Content-Range`` 的 ``T``，否则续传场景必然误判失败。
3. **显式 ``Accept-Encoding: identity``**：httpx 默认协商 gzip，若 CDN 压缩，
   解码后的字节数与 ``Content-Length`` 不等，大小校验会 100% 误判。
4. **临时文件带 URL 指纹**：URL 变化时自动作废旧片段，避免把新内容拼到旧半成品上。
5. **失败不打断爬虫**：所有异常在 ``download`` 内部收敛为返回值与日志。
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import shutil
import uuid
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence
from urllib.parse import urlsplit

import httpx

from tools.httpx_util import make_async_client

from .ffmpeg import merge_audio_video
from .paths import (
    ALLOWED_EXTENSIONS,
    build_file_path,
    build_media_dir,
    build_media_path,
    ensure_within,
    guess_extension,
    redact_url,
    sanitize_component,
    url_fingerprint,
)
from .types import MediaDownloadError, MediaFatalError, MediaItem, MediaRetryableError, MediaType

logger = logging.getLogger("MediaCrawler.media_downloader")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
FALLBACK_EXTENSIONS = {MediaType.IMAGE: ".jpg", MediaType.VIDEO: ".mp4"}

_CONTENT_RANGE = re.compile(r"bytes\s+(\d+)-(\d+)/(\d+|\*)", re.IGNORECASE)

# 各媒体类型可接受的 Content-Type 前缀
_EXPECTED_CONTENT_TYPES = {
    MediaType.IMAGE: ("image/",),
    # 音频单独成轨时素材类型仍是视频（DASH），因此一并接受
    MediaType.VIDEO: ("video/", "audio/"),
}
# 这些类型无法用于判定内容是否正常，一律放行
_NEUTRAL_CONTENT_TYPES = (
    "application/octet-stream",
    "binary/octet-stream",
    "application/x-www-form-urlencoded",
    # 少数 CDN 会用 application/* 返回真实媒体，不能当成错误页拒掉
    "application/mp4",
    "application/x-m4a",
)
# 注意：HLS 播放列表（application/x-mpegurl、application/vnd.apple.mpegurl）
# **不能**放进中性名单——m3u8 是文本清单而不是媒体，放行会把它存成几十 KB 的假视频，
# 且会被"已存在即跳过"永久信任。下载器不支持 HLS，交给类型校验直接拒绝。


def is_expected_content_type(content_type: Optional[str], media_type: MediaType) -> bool:
    """判断响应的 Content-Type 是否与媒体类型相容。

    CDN 的防盗链页、限流页常以 HTTP 200 + ``text/html`` 返回，
    若不拦截会被当作媒体文件落盘，并且因为文件非空而被永久跳过。
    """
    if not content_type:
        return True

    main_type = content_type.split(";")[0].strip().lower()
    if not main_type or main_type in _NEUTRAL_CONTENT_TYPES:
        return True

    expected_prefixes = _EXPECTED_CONTENT_TYPES.get(media_type)
    if not expected_prefixes:
        return True

    return main_type.startswith(expected_prefixes)


class MediaDownloader:
    """把 MediaItem 流式下载到本地磁盘。

    平台差异只通过构造参数（proxy/extra_headers）与 MediaItem 字段注入。
    ``platform`` 仅用于决定落盘目录，下载器不对平台名做任何分支判断
    （Referer 等反爬头由平台侧的 ``_media_headers()`` 提供）。
    """

    # 这些状态码重试没有意义：403 多为签名过期，404/410 为资源不存在
    FATAL_STATUS_CODES = frozenset({400, 401, 403, 404, 405, 410, 451})

    def __init__(
        self,
        platform: str,
        *,
        proxy: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 30.0,
        max_candidates: int = 3,
        base_dir: Optional[Path] = None,
        overwrite: bool = False,
    ) -> None:
        self.platform = platform
        self.proxy = proxy
        self.extra_headers = dict(extra_headers or {})
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay
        # 主地址 + 备用地址的总数上限，防止个别平台给出超长 url_list 造成请求放大
        self.max_candidates = max(1, max_candidates)
        self._base_dir = Path(base_dir) if base_dir is not None else None
        self.overwrite = overwrite

    # ------------------------------------------------------------------ 对外 API

    @property
    def base_dir(self) -> Path:
        """媒体根目录，未显式指定时取 config.SAVE_DATA_PATH（为空则 data/）"""
        if self._base_dir is None:
            import config

            self._base_dir = Path(getattr(config, "SAVE_DATA_PATH", "") or "data")
        return self._base_dir

    async def download_all(self, items: Sequence[MediaItem]) -> list[Path]:
        """串行下载一个帖子的全部媒体，共享同一个 httpx 连接池"""
        if not items:
            return []
        downloaded: list[Path] = []
        async with make_async_client(
            proxy=self.proxy, follow_redirects=True, timeout=self.timeout
        ) as client:
            for item in items:
                path = await self.download(item, client=client)
                if path is not None:
                    downloaded.append(path)
        if len(downloaded) < len(items):
            logger.warning(
                "[download] 本组媒体部分失败: 成功 %d / 共 %d（失败项见上方日志）",
                len(downloaded),
                len(items),
            )
        return downloaded

    async def download(self, item: MediaItem, client: Optional[httpx.AsyncClient] = None) -> Optional[Path]:
        """下载单个媒体；成功返回最终路径，失败返回 None（不抛异常）。

        续传的作用范围是"本次调用内的重试"：``.part`` 片段带进程号，
        且媒体直链的签名通常跨运行就失效，因此不承诺跨进程续传。
        """
        try:
            if not self.is_supported_url(item.url):
                # 平台响应里偶尔会出现协议相对地址（//cdn/...）或空值，httpx 会直接报错
                logger.warning("[download] 非法媒体地址，跳过: %s", redact_url(item.url))
                return None

            existing = self._find_existing(item)
            if existing is not None and not self.overwrite:
                logger.info("[download] 已存在，跳过: %s", existing)
                return existing

            if client is not None:
                return await self._download_item(client, item)
            async with make_async_client(
                proxy=self.proxy, follow_redirects=True, timeout=self.timeout
            ) as own_client:
                return await self._download_item(own_client, item)
        except Exception as exc:  # 兜底：任何异常都不能打断爬虫
            logger.error("[download] 下载失败 %s: %s", redact_url(item.url), exc)
            return None

    def update_credentials(
        self,
        proxy: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        """同步平台 client 的最新代理与请求头。

        代理池刷新与 Cookie 续期都是就地改 client 的属性，而下载器是惰性创建、
        长期复用的；不主动同步就会一直用创建时的旧代理/旧凭证，
        表现为 API 请求正常但媒体下载持续失败。
        """
        self.proxy = proxy
        if extra_headers:
            self.extra_headers.update(extra_headers)

    def build_path(self, item: MediaItem, extension: Optional[str] = None) -> Path:
        """最终落盘路径（纯函数，便于测试与断言）"""
        ext = extension or item.extension or guess_extension(
            item.url, default=FALLBACK_EXTENSIONS.get(item.media_type, ".bin")
        )
        return build_media_path(self.base_dir, self.platform, item.content_id, item.stem, ext)

    # ------------------------------------------------------------------ 内部实现

    def _find_existing(self, item: MediaItem) -> Optional[Path]:
        """查找已下载完成的同名文件（0 字节视为损坏，重新下载）"""
        directory = build_media_dir(self.base_dir, self.platform, item.content_id)
        if not directory.is_dir():
            return None

        if item.extension:
            candidate = self.build_path(item, item.extension)
            if candidate.is_file() and candidate.stat().st_size > 0:
                return candidate
            return None

        for candidate in sorted(directory.glob(f"{item.stem}.*")):
            if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            if candidate.is_file() and candidate.stat().st_size > 0:
                return candidate
        return None

    async def _download_item(self, client: httpx.AsyncClient, item: MediaItem) -> Optional[Path]:
        directory = build_media_dir(self.base_dir, self.platform, item.content_id)
        directory.mkdir(parents=True, exist_ok=True)

        if item.is_dash:
            return await self._download_dash(client, item, directory)

        return await self._download_single(
            client, item, directory, item.url, item.backup_urls, item.stem, item.extension
        )

    async def _download_single(
        self,
        client: httpx.AsyncClient,
        item: MediaItem,
        target_dir: Path,
        url: str,
        backup_urls: Iterable[str],
        stem: str,
        extension: Optional[str] = None,
    ) -> Optional[Path]:
        """按 主地址 -> 备用地址 的顺序下载到 ``target_dir``，每个地址内部做重试。

        ``stem`` 与 ``extension`` 由调用方给出：DASH 的两路流会用不同的文件名
        落在同一个临时目录里，不能共用 MediaItem 上的 stem。
        """
        # 临时文件名也要清洗：stem 来自 MediaItem 的公开契约，未清洗的 stem
        # 会把 .part 写到 base_dir 之外（最终路径有 build_file_path 兜底，临时路径没有）
        safe_stem = sanitize_component(stem, "media")
        # 备用地址数量要有上限：抖音的 url_list 长度不可控，逐个试会放大成几十次请求
        candidates = [url, *[candidate for candidate in backup_urls if candidate]][: self.max_candidates]

        for candidate in candidates:
            if not candidate:
                continue
            part_path = target_dir / f"{safe_stem}.{url_fingerprint(candidate)}.{os.getpid()}.part"
            try:
                content_type = await self._fetch_with_retry(client, item, candidate, part_path)
            except MediaFatalError as exc:
                logger.warning("[download] 放弃地址 %s: %s", redact_url(candidate), exc)
                continue
            except MediaDownloadError as exc:
                logger.warning("[download] 地址重试耗尽 %s: %s", redact_url(candidate), exc)
                continue

            resolved_extension = extension or guess_extension(
                candidate,
                content_type=content_type,
                explicit=item.extension,
                default=FALLBACK_EXTENSIONS.get(item.media_type, ".bin"),
            )
            try:
                final_path = ensure_within(
                    self.base_dir, build_file_path(target_dir, stem, resolved_extension)
                )
            except ValueError as exc:
                logger.error("[download] %s", exc)
                part_path.unlink(missing_ok=True)
                return None

            os.replace(part_path, final_path)
            self._cleanup_parts(target_dir, safe_stem, keep=None)
            logger.info(
                "[download] 下载完成: %s (%d bytes)",
                final_path,
                final_path.stat().st_size,
            )
            return final_path

        # 调用内重试会复用 .part 做续传；全部地址都失败后则不再保留，
        # 否则每次失败都会在媒体目录里留下一个再也用不上的残片（媒体直链签名每次都会变）
        self._cleanup_parts(target_dir, safe_stem)
        logger.error("[download] 媒体下载失败，已尝试全部地址: %s", redact_url(url))
        return None

    @staticmethod
    def _cleanup_parts(target_dir: Path, safe_stem: str, keep: Optional[Path] = None) -> None:
        """清掉该 stem 的临时片段。

        成功下载后也要清理：某个候选地址中途失败、回退到下一个候选成功时，
        前一个候选的残片不会自己消失。
        """
        for stale_part in target_dir.glob(f"{safe_stem}.*.part"):
            if keep is not None and stale_part == keep:
                continue
            stale_part.unlink(missing_ok=True)

    async def _download_dash(
        self, client: httpx.AsyncClient, item: MediaItem, directory: Path
    ) -> Optional[Path]:
        """DASH 音视频分轨：两路流下载到临时目录，ffmpeg 合流后原子替换"""
        tmp_dir = directory / f".tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            video_path = await self._download_single(
                client, item, tmp_dir, item.url, item.backup_urls, "video", ".m4s"
            )
            if video_path is None:
                logger.error("[download] DASH 视频轨下载失败: %s", redact_url(item.url))
                return None

            audio_url = item.audio_url or ""
            audio_path = await self._download_single(
                client, item, tmp_dir, audio_url, item.audio_backup_urls, "audio", ".m4s"
            )
            if audio_path is None:
                logger.error("[download] DASH 音频轨下载失败: %s", redact_url(audio_url))
                return None

            merged_path = tmp_dir / "merged.mp4"
            await merge_audio_video(video_path, audio_path, merged_path)

            final_path = ensure_within(self.base_dir, self.build_path(item, ".mp4"))
            os.replace(merged_path, final_path)
            logger.info(
                "[download] DASH 合流完成: %s (%d bytes)",
                final_path,
                final_path.stat().st_size,
            )
            return final_path
        except MediaDownloadError as exc:
            logger.error("[download] DASH 合流失败 %s: %s", redact_url(item.url), exc)
            return None
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _fetch_with_retry(
        self,
        client: httpx.AsyncClient,
        item: MediaItem,
        url: str,
        part_path: Path,
    ) -> Optional[str]:
        """带指数退避重试的单文件抓取，返回 Content-Type"""
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                return await self._fetch_once(client, item, url, part_path)
            except MediaFatalError:
                raise
            # httpx.InvalidURL 不是 HTTPError 的子类（它是 Exception 的直接子类），
            # 漏掉它会让一个畸形地址直接终止整条候选回退链
            except (MediaRetryableError, httpx.HTTPError, httpx.InvalidURL, OSError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    delay = self._retry_delay(attempt)
                    logger.warning(
                        "[download] 第 %d/%d 次重试 %s（%.1fs 后）: %s",
                        attempt + 1,
                        self.max_retries,
                        redact_url(url),
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
        if last_error is None:
            raise MediaRetryableError("未知错误")
        # 部分网络异常的 str() 为空，带上类型名才有排查线索
        raise MediaRetryableError(f"{type(last_error).__name__}: {last_error}")

    def _retry_delay(self, attempt: int) -> float:
        """指数退避 + full jitter，避免多个任务同步重试"""
        ceiling = min(self.retry_base_delay * (2**attempt), self.retry_max_delay)
        return random.uniform(0, ceiling)

    async def _fetch_once(
        self,
        client: httpx.AsyncClient,
        item: MediaItem,
        url: str,
        part_path: Path,
    ) -> Optional[str]:
        """执行一次流式 GET，成功返回 Content-Type。

        续传语义：
        - 本地存在 ``.part`` 片段 -> 带 ``Range`` 请求
        - 206 -> 追加写；200（服务端忽略 Range）-> 截断重写；416 -> 片段失效，重来
        """
        resume_from = part_path.stat().st_size if part_path.exists() else 0
        headers = self._build_headers(item)
        if resume_from > 0:
            headers["Range"] = f"bytes={resume_from}-"

        async with client.stream("GET", url, headers=headers) as response:
            status = response.status_code
            if status in self.FATAL_STATUS_CODES:
                raise MediaFatalError(f"HTTP {status}")
            if status == 416:
                part_path.unlink(missing_ok=True)
                raise MediaRetryableError("HTTP 416：本地残留片段已失效，重新下载")
            if status not in (200, 206):
                raise MediaRetryableError(f"HTTP {status}")

            content_type = response.headers.get("content-type")
            if not is_expected_content_type(content_type, item.media_type):
                # 典型的防盗链/限流错误页：HTTP 200 但返回 text/html。
                # 此时尚未读取响应体，本地 .part 仍是合法前缀，保留以便下次续传
                raise MediaRetryableError(
                    f"响应类型 {content_type} 与媒体类型 {item.media_type.value} 不符，疑似错误页"
                )

            if status == 200 and resume_from > 0:
                logger.debug("[download] 服务端不支持 Range，从头下载: %s", redact_url(url))
                resume_from = 0

            content_range = self._parse_content_range(response)
            if status == 206:
                # RFC 9110 要求 206 必须带可解析的 Content-Range。缺失时服务端的实际行为
                # 不可预期（有 CDN 会对带 Range 的请求回 206 + 全量体），此时若继续 append
                # 会把整份内容接到本地片段后面，而"总长"又是按剩余长度反推的，大小校验
                # 反而会通过 —— 只能拒绝并丢弃片段重下。
                if content_range is None:
                    part_path.unlink(missing_ok=True)
                    raise MediaRetryableError("206 响应缺少 Content-Range，丢弃片段重新下载")
                if content_range[0] != resume_from:
                    # 起点不符会得到内容错位或头部缺失的文件；未发 Range（resume_from=0）
                    # 却收到非 0 起点的 206 同样要拒绝
                    part_path.unlink(missing_ok=True)
                    raise MediaRetryableError(
                        f"服务端返回的 Range 起点 {content_range[0]} 与请求的 {resume_from} 不符"
                    )
                if content_range[2] is None:
                    # total 为 * 表示服务端只返回了区间的一部分且不告知总长，
                    # 这种响应无法确认完整性（落盘的就是截断文件），丢弃片段后
                    # 以无 Range 的方式重新请求完整内容
                    part_path.unlink(missing_ok=True)
                    raise MediaRetryableError("206 的 Content-Range 未给出总长（*），重新完整下载")

            use_append = status == 206 and resume_from > 0
            total_size = self._resolve_total_size(content_range, response, status)
            # 服务端若无视 identity 强制压缩，落盘的是解码后的字节，与 Content-Length 不等
            encoded = response.headers.get("content-encoding", "").strip().lower() not in ("", "identity")

            written = resume_from if use_append else 0
            mode = "ab" if use_append else "wb"
            with open(part_path, mode) as file_obj:
                # 必须使用不带 chunk_size 的 aiter_bytes()：传入 chunk_size 时 httpx 会
                # 缓冲满该长度才产出数据，响应中途断开会让已接收的字节全部丢失，
                # 断点续传与"截断后重试"都会退化成从头再来。
                async for chunk in response.aiter_bytes():
                    if not chunk:
                        continue
                    file_obj.write(chunk)
                    written += len(chunk)

        if written == 0:
            part_path.unlink(missing_ok=True)
            raise MediaRetryableError("响应体为空")

        if encoded:
            logger.warning("[download] 服务端返回压缩内容，跳过大小校验: %s", redact_url(url))
        elif total_size is None:
            logger.warning(
                "[download] 响应无 Content-Length，跳过大小校验: %s", redact_url(url)
            )
        elif written != total_size:
            raise MediaRetryableError(f"大小不符：实际 {written} 字节，期望 {total_size} 字节")

        return content_type

    @staticmethod
    def _parse_content_range(response: httpx.Response) -> Optional[tuple[int, int, Optional[int]]]:
        """解析 ``Content-Range: bytes 100-999/1000``，返回 (start, end, total)"""
        match = _CONTENT_RANGE.search(response.headers.get("content-range", ""))
        if not match:
            return None
        total = None if match.group(3) == "*" else int(match.group(3))
        return int(match.group(1)), int(match.group(2)), total

    @staticmethod
    def _resolve_total_size(
        content_range: Optional[tuple[int, int, Optional[int]]],
        response: httpx.Response,
        status: int,
    ) -> Optional[int]:
        """解析文件总大小。

        206 响应的 Content-Length 只是"剩余长度"，文件总长只能取自 Content-Range 的 total。
        total 为 ``*``（未知）时不能拿"剩余长度 + 已下载量"反推：服务端有权只返回请求区间的
        一部分，反推出来的"总长"会让截断的文件恰好通过校验。
        """
        if status == 206:
            return content_range[2] if content_range else None
        return MediaDownloader._parse_content_length(response)

    @staticmethod
    def _parse_content_length(response: httpx.Response) -> Optional[int]:
        # RFC 7230：存在 Transfer-Encoding 时必须忽略 Content-Length，
        # 否则一个 chunked 的完整响应会因为服务端多写的 CL 被误判为"大小不符"
        if response.headers.get("transfer-encoding"):
            return None
        raw = response.headers.get("content-length", "")
        if raw.isdigit():
            return int(raw)
        return None

    def _build_headers(self, item: MediaItem) -> dict:
        """拼装请求头：通用 UA + 调用方覆盖 + 单项覆盖。

        平台特有的反爬头（Referer 等）由平台侧通过 ``extra_headers`` 注入，
        下载器不认识任何平台名。Cookie 同理不会出现在默认头里，避免所有平台的
        媒体请求都带上账号凭证；注意 httpx 在重定向时一律剥离 Cookie（同源跳转也会剥），
        所以注入的 Cookie 只对首跳生效。
        """
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "*/*",
            # 必须显式声明不压缩：否则解码后字节数与 Content-Length 不等，大小校验必然误判
            "Accept-Encoding": "identity",
        }
        headers.update(self.extra_headers)
        if item.headers:
            headers.update(item.headers)
        return headers

    @staticmethod
    def is_supported_url(url) -> bool:
        """URL 是否为可下载的 http(s) 地址。

        平台响应里的字段可能是 int/list/dict，``urlsplit`` 对非字符串会抛
        TypeError/AttributeError，这里必须一并挡住，否则会击穿 "download 不抛异常" 的契约。
        """
        if not isinstance(url, str):
            return False
        try:
            parts = urlsplit(url)
        except ValueError:
            return False
        return parts.scheme in ("http", "https") and bool(parts.netloc)
