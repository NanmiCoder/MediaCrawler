# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/services/image_downloader.py
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

"""
Image download service for downloading images from URLs.
Supports jitter interval to avoid rate limiting.
"""
import asyncio
import hashlib
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx


# Default download directory
DOWNLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "downloads"

# Configuration
DOWNLOAD_TIMEOUT = 30.0  # seconds
MIN_INTERVAL = 0.5  # seconds
MAX_INTERVAL = 2.0  # seconds


@dataclass
class DownloadResult:
    """Result of a download operation."""
    success: bool
    local_path: Optional[str] = None
    error: Optional[str] = None


class ImageDownloader:
    """
    Service for downloading images with jitter interval.

    Features:
    - HTTP download with timeout
    - Jitter interval to avoid rate limiting
    - Automatic file naming with URL hash
    - Date-based directory structure
    """

    def __init__(
        self,
        download_dir: Path = DOWNLOAD_DIR,
        timeout: float = DOWNLOAD_TIMEOUT,
        min_interval: float = MIN_INTERVAL,
        max_interval: float = MAX_INTERVAL
    ):
        self._download_dir = download_dir
        self._timeout = timeout
        self._min_interval = min_interval
        self._max_interval = max_interval
        self._client: Optional[httpx.AsyncClient] = None

    async def init(self) -> None:
        """Initialize the downloader - create directory and HTTP client."""
        self._download_dir.mkdir(parents=True, exist_ok=True)
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        print(f"[ImageDownloader] Initialized, download dir: {self._download_dir}")

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def download(self, url: str) -> DownloadResult:
        """
        Download an image from URL.

        Args:
            url: The image URL to download

        Returns:
            DownloadResult with success status, local path, or error message
        """
        if not self._client:
            return DownloadResult(success=False, error="Downloader not initialized")

        try:
            response = await self._client.get(url)
            response.raise_for_status()

            # Generate filename from URL hash
            url_hash = hashlib.md5(url.encode()).hexdigest()[:16]

            # Determine extension from content-type
            content_type = response.headers.get("content-type", "")
            ext = self._get_extension(content_type)

            # Create dated subdirectory
            now = datetime.now()
            date_dir = self._download_dir / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
            date_dir.mkdir(parents=True, exist_ok=True)

            # Save file
            filename = f"{url_hash}{ext}"
            file_path = date_dir / filename

            with open(file_path, "wb") as f:
                f.write(response.content)

            print(f"[ImageDownloader] Downloaded: {url} -> {file_path}")
            return DownloadResult(success=True, local_path=str(file_path))

        except httpx.TimeoutException:
            error = f"Timeout downloading {url}"
            print(f"[ImageDownloader] {error}")
            return DownloadResult(success=False, error=error)
        except httpx.HTTPStatusError as e:
            error = f"HTTP {e.response.status_code} for {url}"
            print(f"[ImageDownloader] {error}")
            return DownloadResult(success=False, error=error)
        except Exception as e:
            error = f"Error downloading {url}: {str(e)}"
            print(f"[ImageDownloader] {error}")
            return DownloadResult(success=False, error=error)

    def _get_extension(self, content_type: str) -> str:
        """Get file extension from content-type."""
        content_type = content_type.lower()
        if "jpeg" in content_type or "jpg" in content_type:
            return ".jpg"
        elif "png" in content_type:
            return ".png"
        elif "gif" in content_type:
            return ".gif"
        elif "webp" in content_type:
            return ".webp"
        return ".jpg"  # Default to jpg

    def get_jitter_interval(self) -> float:
        """Get random interval for jitter."""
        return random.uniform(self._min_interval, self._max_interval)


# Global singleton
image_downloader = ImageDownloader()
