"""
小红书账号监控模块

功能：
1. 监控对标账号的新内容
2. 自动识别爆款内容
3. 提供 API 接口供 Skills 调用
"""

from .hot_content_detector import HotContentDetector, HotLevel
from .scheduler import MonitorScheduler, monitor_scheduler

__all__ = [
    "HotContentDetector",
    "HotLevel",
    "MonitorScheduler",
    "monitor_scheduler"
]
