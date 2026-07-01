"""
douyin_scraper.exceptions — 自定义异常
======================================
v5 新增：所有异常包含 step / exit_code / details 属性。
我实际执行时：异常只有消息字符串，无法判断来自哪个步骤、
是否可重试，导致 run_all.py 中的错误分类只能靠字符串匹配。
"""

from typing import Optional


class ScraperError(Exception):
    """采集工具基础异常"""

    def __init__(
        self,
        message: str,
        step: str = "",
        exit_code: int = 1,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message)
        self.step = step
        self.exit_code = exit_code
        self.details = details or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"step={self.step!r}, exit_code={self.exit_code}, "
            f"message={str(self)!r})"
        )


class RetryableError(ScraperError):
    """可重试错误：网络超时、HTTP 5xx、临时文件锁"""

    def __init__(
        self,
        message: str = "",
        step: str = "",
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message, step=step, exit_code=1, details=details)


class NonRetryableError(ScraperError):
    """不可重试错误：配置错误、权限不足、Python 版本不对"""

    def __init__(
        self,
        message: str = "",
        step: str = "",
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message, step=step, exit_code=2, details=details)


class ConfigError(ScraperError):
    """配置错误：缺少必需配置项、配置文件格式错误"""

    def __init__(
        self,
        message: str = "",
        step: str = "",
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message, step=step, exit_code=2, details=details)


class FatalError(ScraperError):
    """致命错误：磁盘满、内存不足"""

    def __init__(
        self,
        message: str = "",
        step: str = "",
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message, step=step, exit_code=3, details=details)
