# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

"""
Image storage service for path generation, format validation, and cleanup.
"""
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image


# Default storage configuration
DATA_DIR = Path(__file__).parent.parent.parent / "data"
MAX_STORAGE_BYTES = 5 * 1024 * 1024 * 1024  # 5GB default


class ImageStorageService:
    """
    Service for managing image storage:
    - Path generation: {data_dir}/{platform}/images/{year}/{month}/{day}/{hash}.jpg
    - Format validation: Detect invalid images (HTML error pages)
    - Storage cleanup: Remove oldest files when exceeding threshold
    """

    def __init__(self, data_dir: Path = DATA_DIR, max_storage_bytes: int = MAX_STORAGE_BYTES):
        self._data_dir = data_dir
        self._max_storage_bytes = max_storage_bytes

    def get_storage_path(self, url: str, platform: str = "xhs", ext: str = ".jpg") -> Tuple[Path, str]:
        """
        Generate storage path for an image URL.
        Path format: {data_dir}/{platform}/images/{year}/{month}/{day}/{hash}.jpg

        Args:
            url: Image URL to generate path for
            platform: Platform identifier (xhs, dy, bili, zhihu)
            ext: File extension (default .jpg)

        Returns:
            Tuple of (full_path, url_hash)
        """
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        now = datetime.now()
        date_dir = (
            self._data_dir / platform / "images" /
            str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        )
        date_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{url_hash}{ext}"
        return date_dir / filename, url_hash

    def validate_image(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate that a file is a valid image.
        Detects HTML error pages and other non-image content.

        Args:
            file_path: Path to the file to validate

        Returns:
            Tuple of (is_valid, actual_extension)
            - is_valid: True if file is a valid image
            - actual_extension: '.jpg', '.png', '.gif', '.webp' or None
        """
        if not file_path.exists():
            return False, None

        try:
            # First check magic bytes for common formats
            with open(file_path, "rb") as f:
                header = f.read(16)

            # JPEG: FF D8 FF
            if header[:3] == b"\xff\xd8\xff":
                ext = ".jpg"
            # PNG: 89 50 4E 47
            elif header[:4] == b"\x89PNG":
                ext = ".png"
            # GIF: 47 49 46 38
            elif header[:4] == b"GIF8":
                ext = ".gif"
            # WebP: 52 49 46 46 ... 57 45 42 50
            elif header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                ext = ".webp"
            else:
                # Not a recognized image format
                return False, None

            # Verify with PIL
            with Image.open(file_path) as img:
                img.verify()

            return True, ext

        except Exception:
            return False, None

    def get_storage_size(self, platform: Optional[str] = None) -> int:
        """
        Get total storage size in bytes.

        Args:
            platform: Optional platform identifier to limit scope

        Returns:
            Total size in bytes
        """
        if platform:
            images_dirs = [self._data_dir / platform / "images"]
        else:
            images_dirs = [
                self._data_dir / p / "images"
                for p in ["xhs", "dy", "bili", "zhihu"]
                if (self._data_dir / p / "images").exists()
            ]

        total_size = 0
        for images_dir in images_dirs:
            if not images_dir.exists():
                continue
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                for file_path in images_dir.rglob(f"*{ext}"):
                    try:
                        total_size += file_path.stat().st_size
                    except OSError:
                        pass
        return total_size

    def cleanup_by_size(self, platform: Optional[str] = None) -> int:
        """
        Clean up storage if exceeding threshold.
        Removes oldest files until below threshold.

        Args:
            platform: Optional platform identifier to limit scope

        Returns:
            Number of files deleted
        """
        if platform:
            images_dirs = [self._data_dir / platform / "images"]
        else:
            images_dirs = [
                self._data_dir / p / "images"
                for p in ["xhs", "dy", "bili", "zhihu"]
                if (self._data_dir / p / "images").exists()
            ]

        current_size = self.get_storage_size(platform)
        if current_size <= self._max_storage_bytes:
            return 0

        # Collect all image files with their modification times
        files: List[Tuple[Path, float, int]] = []
        for images_dir in images_dirs:
            if not images_dir.exists():
                continue
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                for file_path in images_dir.rglob(f"*{ext}"):
                    try:
                        files.append((
                            file_path,
                            file_path.stat().st_mtime,
                            file_path.stat().st_size
                        ))
                    except OSError:
                        pass

        if not files:
            return 0

        # Sort by modification time (oldest first)
        files.sort(key=lambda x: x[1])

        deleted = 0
        for file_path, _, file_size in files:
            if current_size <= self._max_storage_bytes:
                break
            try:
                file_path.unlink()
                current_size -= file_size
                deleted += 1
            except OSError:
                pass

        if deleted > 0:
            platform_str = platform or "all platforms"
            print(f"[ImageStorage] Cleaned up {deleted} files for {platform_str}")
        return deleted

    def get_local_path(self, url: str, platform: str = "xhs") -> Optional[Path]:
        """
        Find existing local path for a URL by hash.

        Args:
            url: Image URL to find
            platform: Platform identifier

        Returns:
            Path to existing file, or None if not found
        """
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        images_dir = self._data_dir / platform / "images"

        if not images_dir.exists():
            return None

        # Search for any file matching the hash
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            matches = list(images_dir.rglob(f"{url_hash}{ext}"))
            if matches:
                return matches[0]

        return None

    def delete_invalid_image(self, file_path: Path) -> bool:
        """
        Delete an invalid image file.

        Args:
            file_path: Path to the file to delete

        Returns:
            True if deleted successfully
        """
        try:
            if file_path.exists():
                file_path.unlink()
                print(f"[ImageStorage] Deleted invalid image: {file_path}")
                return True
        except OSError as e:
            print(f"[ImageStorage] Failed to delete {file_path}: {e}")
        return False


# Global singleton
image_storage = ImageStorageService()
