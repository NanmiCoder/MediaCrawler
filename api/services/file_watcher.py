# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/services/file_watcher.py
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
File watcher service for detecting JSONL file changes and triggering callbacks.
Uses watchdog library for cross-platform file system monitoring.
"""

import asyncio
import os
import threading
from pathlib import Path
from typing import Callable, Dict, Optional, Set

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class FileWatcherService:
    """
    Service that monitors a directory for JSONL file changes and triggers
    a callback after a debounce period.

    Thread Safety:
    - Uses threading.Lock for _pending_events access
    - Uses asyncio.run_coroutine_threadsafe for async callback bridge
    """

    DEBOUNCE_SECONDS = 0.2  # 200ms debounce window

    def __init__(self):
        self._observer: Optional[Observer] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._debounce_timer: Optional[threading.Timer] = None
        self._pending_events: Set[str] = set()
        self._lock = threading.Lock()
        self._file_sizes: Dict[str, int] = {}
        self._callback: Optional[Callable] = None
        self._watch_path: Optional[str] = None
        self._started = False

    def start(self, path: str, callback: Callable) -> None:
        """
        Start watching the specified directory for file changes.

        Args:
            path: Directory path to watch (e.g., "data/xhs/jsonl/")
            callback: Async callable to invoke on file changes (no arguments)
        """
        if self._started:
            return

        self._watch_path = path
        self._callback = callback
        self._event_loop = asyncio.get_running_loop()

        # Create directory if it doesn't exist
        Path(path).mkdir(parents=True, exist_ok=True)

        # Initialize file sizes for existing files
        self._initialize_file_sizes()

        # Create event handler
        handler = _JsonlEventHandler(self)

        # Create and start observer
        self._observer = Observer()
        self._observer.schedule(handler, path, recursive=False)
        self._observer.start()

        self._started = True
        print(f"[FileWatcher] Started watching: {path}")

    def stop(self) -> None:
        """Stop the file watcher and wait for observer thread to finish."""
        if not self._started:
            return

        # Cancel any pending debounce timer
        if self._debounce_timer:
            self._debounce_timer.cancel()
            self._debounce_timer = None

        # Stop observer
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None

        self._started = False
        print("[FileWatcher] Stopped")

    def _initialize_file_sizes(self) -> None:
        """Initialize file sizes for existing JSONL files."""
        if not self._watch_path:
            return

        watch_dir = Path(self._watch_path)
        if not watch_dir.exists():
            return

        for file_path in watch_dir.glob("*.jsonl"):
            try:
                self._file_sizes[str(file_path)] = file_path.stat().st_size
            except OSError:
                pass

    def _on_file_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification event (called from observer thread).

        Only triggers for .jsonl files where size has increased (append detection).
        """
        if event.is_directory:
            return

        # Only process .jsonl files
        if not event.src_path.endswith(".jsonl"):
            return

        file_path = event.src_path

        try:
            new_size = os.path.getsize(file_path)
        except OSError:
            return

        old_size = self._file_sizes.get(file_path, 0)

        # Only trigger if file size increased (append detection)
        if new_size > old_size:
            self._file_sizes[file_path] = new_size
            self._schedule_debounce()

    def _schedule_debounce(self) -> None:
        """Schedule or reschedule the debounce timer."""
        # Cancel existing timer
        if self._debounce_timer:
            self._debounce_timer.cancel()

        # Schedule new timer
        self._debounce_timer = threading.Timer(
            self.DEBOUNCE_SECONDS,
            self._do_callback
        )
        self._debounce_timer.start()

    def _do_callback(self) -> None:
        """Execute the callback on the main event loop (called from timer thread)."""
        if self._callback and self._event_loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._callback(),
                    self._event_loop
                )
            except Exception as e:
                print(f"[FileWatcher] Callback error: {e}")


class _JsonlEventHandler(FileSystemEventHandler):
    """Event handler for JSONL file changes."""

    def __init__(self, service: FileWatcherService):
        self._service = service
        super().__init__()

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification event."""
        self._service._on_file_modified(event)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation event - treat as modification for new files."""
        if not event.is_directory and event.src_path.endswith(".jsonl"):
            # Initialize size for new file
            try:
                self._service._file_sizes[event.src_path] = 0
            except Exception:
                pass
            self._service._on_file_modified(event)


# Global singleton
file_watcher = FileWatcherService()
