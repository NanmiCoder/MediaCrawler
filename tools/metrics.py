# 轻量级下载指标统计工具
# 统计全局下载的媒体字节数，用于程序结束时计算总体平均速度

from __future__ import annotations
import threading

__all__ = [
    "add_downloaded_bytes",
    "get_downloaded_bytes",
    "reset",
]

_lock = threading.Lock()
_total_downloaded_bytes = 0

def add_downloaded_bytes(n: int) -> None:
    global _total_downloaded_bytes
    if n is None:
        return
    if n < 0:
        return
    with _lock:
        _total_downloaded_bytes += n

def get_downloaded_bytes() -> int:
    with _lock:
        return _total_downloaded_bytes

def reset() -> None:
    global _total_downloaded_bytes
    with _lock:
        _total_downloaded_bytes = 0
