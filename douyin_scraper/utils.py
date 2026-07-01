"""
douyin_scraper.utils — 工具函数
================================
v5 重构：从 v4 common_utils 中拆出工具函数。

保留 v4 验证过的所有生产级特性：
  - append_record: os.open + fallback
  - retry: 指数退避 + 随机抖动
  - setup_ffmpeg: imageio-ffmpeg → 系统 ffmpeg → 手动提示
  - ensure_dir_writable: 写前检测
  - check_disk_space: 磁盘空间预检
  - 日志轮转
"""

import functools
import logging
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence, Set, Tuple, Type, Union

from douyin_scraper.exceptions import (
    FatalError,
    NonRetryableError,
    RetryableError,
    ScraperError,
)

logger = logging.getLogger("douyin_scraper")

# 退出码
EXIT_RETRYABLE = 1
EXIT_NON_RETRYABLE = 2
EXIT_FATAL = 3


# ═══════════════════════════════════════════════════════════════════
# 1. 错误分类
# ═══════════════════════════════════════════════════════════════════

_MESSAGE_PATTERNS: dict = {
    EXIT_RETRYABLE: [
        "timeout", "timed out", "connection refused", "connection reset",
        "connection error", "429", "rate limit",
        "temporarily unavailable", "retry", "503", "502", "500",
        "broken pipe", "eof", "network", "socket",
    ],
    EXIT_NON_RETRYABLE: [
        "not found", "404", "403", "forbidden", "unauthorized",
        "permission denied", "config error", "invalid argument",
        "version mismatch", "syntax error",
        "module not found", "no module named",
        "file not found", "no such file",
    ],
    EXIT_FATAL: [
        "no space left", "disk full", "out of memory", "cannot allocate memory",
        "memoryerror",
    ],
}


def classify_error(e: Exception) -> int:
    """
    根据异常类型 + 消息内容判断退出码。

    我实际执行时：OSError 既可能是磁盘满（致命）也可能是临时网络断（可重试）。
    检查顺序：自定义异常 → 标准异常子类 → 消息内容 → 默认不可重试。
    """
    # 1. 自定义异常（精确匹配）
    if isinstance(e, FatalError):
        return EXIT_FATAL
    if isinstance(e, (NonRetryableError,)):
        return EXIT_NON_RETRYABLE
    if isinstance(e, RetryableError):
        return EXIT_RETRYABLE

    # 2. 标准异常子类（PermissionError 是 OSError 子类，须先检查）
    if isinstance(e, MemoryError):
        return EXIT_FATAL
    if isinstance(e, PermissionError):
        return EXIT_NON_RETRYABLE
    if isinstance(e, (ConnectionError, TimeoutError)):
        return EXIT_RETRYABLE
    if isinstance(e, OSError):
        pass  # fall through to message analysis

    # 3. 消息内容关键词匹配
    msg_lower = str(e).lower()
    for exit_code, patterns in _MESSAGE_PATTERNS.items():
        for pattern in patterns:
            if pattern in msg_lower:
                return exit_code

    # 4. OSError 没匹配到消息 → 默认可重试
    if isinstance(e, OSError):
        return EXIT_RETRYABLE

    # 5. 默认不可重试
    return EXIT_NON_RETRYABLE


# ═══════════════════════════════════════════════════════════════════
# 2. 安全文件写入
# ═══════════════════════════════════════════════════════════════════

def safe_write_line(filepath: Path, line: str, fallback_dir: Path) -> Path:
    """
    使用 os.open 低级 I/O 追加写入一行。
    返回实际写入的文件路径（可能是 fallback）。

    ★ 禁止在 async 函数内使用 open() ★
    我实际执行时：open() 在 Windows asyncio 中导致 Bad file descriptor。
    """
    if not line.endswith("\n"):
        line += "\n"
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    try:
        fd = os.open(str(filepath), flags, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
        return filepath
    except OSError:
        # fallback
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_path = fallback_dir / filepath.name
        fd = os.open(str(fallback_path), flags, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
        logger.warning("原路径写入失败，fallback 到: %s", fallback_path)
        return fallback_path


def append_record(filepath: Path, record: dict, fallback_dir: Path) -> Path:
    """
    追加写入一条 JSON 记录到 JSONL 文件。
    ★ 每完成一个最小原子操作，必须调用此函数立即写盘 ★
    """
    import json
    line = json.dumps(record, ensure_ascii=False)
    return safe_write_line(filepath, line, fallback_dir)


# ═══════════════════════════════════════════════════════════════════
# 3. 数值字段解析
# ═══════════════════════════════════════════════════════════════════


def parse_count(value) -> int:
    """
    将抖音可能返回的 '1.2万', '10.3w' 等格式转为整数。

    抖音 API 返回的数值字段可能是：
    - 整数 / 浮点数：直接转换
    - 字符串带中文/英文单位：'1.2万', '10.3w', '500k'
    - None / 空字符串：返回 0
    - 无法解析的字符串：返回 0

    Args:
        value: 原始数值，可能是 int/float/str/None

    Returns:
        解析后的整数
    """
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if not s:
            return 0
        multiplier = 1
        if s.endswith(("万", "w")):
            multiplier = 10000
            s = s[:-1]
        elif s.endswith("k"):
            multiplier = 1000
            s = s[:-1]
        try:
            return int(float(s) * multiplier)
        except ValueError:
            return 0
    return 0


# ═══════════════════════════════════════════════════════════════════
# 4. 自动重试装饰器
# ═══════════════════════════════════════════════════════════════════

def retry(
    max_retries: int = 3,
    base_delay: float = 5.0,
    backoff_factor: float = 3.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        OSError, ConnectionError, TimeoutError, RetryableError
    ),
) -> Callable:
    """
    指数退避 + 随机抖动重试装饰器。
    delay = base_delay * backoff_factor^(attempt-1) + random.uniform(0, 1)

    ★ 禁止在重试循环中不加 random 抖动 ★
    我实际执行时：多任务同时重试导致请求集中，触发更严厉的风控。
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Optional[Exception] = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_error = e
                    delay = base_delay * (backoff_factor ** (attempt - 1))
                    jitter = random.uniform(0, 1)
                    total_delay = delay + jitter
                    logger.warning(
                        "[%s] 失败 (attempt %d/%d): %s, %.1fs 后重试",
                        func.__name__, attempt, max_retries, e, total_delay,
                    )
                    if attempt < max_retries:
                        time.sleep(total_delay)
            raise last_error
        return wrapper
    return decorator


def retry_with_degradation(
    step_name: str,
    state_manager: Any,
    max_retries: int = 3,
    base_delay: float = 5.0,
    backoff_factor: float = 3.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        OSError, ConnectionError, TimeoutError, RetryableError
    ),
) -> Callable:
    """
    带安全降级的重试装饰器。重试耗尽后标记步骤为 failed 而非崩溃。

    我实际执行时：重试耗尽后直接 raise，导致整个脚本崩溃且无状态记录。
    v5：重试耗尽 → mark_step_failed → 抛出原始异常。
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Optional[Exception] = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_error = e
                    delay = base_delay * (backoff_factor ** (attempt - 1))
                    jitter = random.uniform(0, 1)
                    total_delay = delay + jitter
                    logger.warning(
                        "[%s] 失败 (attempt %d/%d): %s, %.1fs 后重试",
                        func.__name__, attempt, max_retries, e, total_delay,
                    )
                    if attempt < max_retries:
                        time.sleep(total_delay)

            # ★ 重试耗尽：安全降级 ★
            exit_code = classify_error(last_error)
            state_manager.mark_step_failed(
                step_name,
                error_summary=str(last_error)[:200],
                exit_code=exit_code,
            )
            raise last_error
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════
# 4. 文件名安全处理
# ═══════════════════════════════════════════════════════════════════

def get_safe_filename(name: str) -> str:
    """
    将任意字符串转换为安全的文件名。

    替换 Windows/Linux 上非法的文件名字符（\\/*?:<>|）为下划线，
    去除首尾空格和点号（Windows 不允许以点或空格结尾）。

    Args:
        name: 原始字符串

    Returns:
        安全的文件名字符串
    """
    # 替换所有非法字符为下划线
    safe = re.sub(r'[\\/*?:<>|]', '_', name)
    # 去除首尾空格
    safe = safe.strip()
    # 去除首尾点号（Windows 不允许以点结尾）
    safe = safe.strip('.')
    # 如果结果为空，使用默认名
    if not safe:
        safe = "unnamed"
    # 截断至合理长度（大多数文件系统限制 255 字节）
    max_len = 200
    if len(safe) > max_len:
        safe = safe[:max_len]
    return safe


# ═══════════════════════════════════════════════════════════════════
# 5. 环境检测
# ═══════════════════════════════════════════════════════════════════

def check_command_exists(cmd: str) -> bool:
    """检查系统命令是否存在"""
    return shutil.which(cmd) is not None


def check_port_in_use(port: int) -> bool:
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def kill_process_on_port(port: int) -> bool:
    """安全地终止占用指定端口的进程（使用 psutil，无 shell 注入风险）。"""
    try:
        import psutil
    except ImportError:
        logger.warning("psutil 未安装，无法安全终止端口 %d 上的进程", port)
        return False

    killed = False
    try:
        # 使用 net_connections 替代已弃用的 proc.connections()
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr.port == port:
                try:
                    proc = psutil.Process(conn.pid)
                    proc.terminate()
                    # 等待进程退出，避免僵尸进程
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        logger.warning(
                            "进程 PID=%d terminate 后 5s 未退出，强制 kill",
                            proc.pid,
                        )
                        proc.kill()
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            logger.warning("进程 PID=%d kill 后仍未退出", proc.pid)
                    killed = True
                    logger.info("已杀掉端口 %d 上的进程 PID=%s 名称=%s",
                                port, proc.pid, proc.name())
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
    except psutil.AccessDenied:
        logger.warning("无权限获取网络连接信息，无法终止端口 %d 上的进程", port)
        return False
    return killed


def setup_ffmpeg() -> bool:
    """
    将 imageio-ffmpeg 内置的 ffmpeg 加入 PATH。
    返回 True 表示 ffmpeg 可用。

    我实际执行时：忘了装 ffmpeg，运行 whisper 报 FileNotFoundError。
    降级策略：imageio-ffmpeg → 系统 ffmpeg → 手动提示。
    """
    # 方案 A: imageio-ffmpeg
    try:
        import imageio_ffmpeg
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except RuntimeError:
            logger.warning("imageio_ffmpeg.get_ffmpeg_exe() 抛出 RuntimeError，等待 2 秒后重试")
            time.sleep(2)
            try:
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            except RuntimeError:
                logger.error("imageio_ffmpeg.get_ffmpeg_exe() 重试仍失败")
                ffmpeg_exe = None

        if ffmpeg_exe and os.path.isfile(ffmpeg_exe):
            ffmpeg_dir = os.path.dirname(ffmpeg_exe)
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
            os.environ["FFMPEG_BINARY"] = ffmpeg_exe
            logger.info("ffmpeg (imageio-ffmpeg): %s", ffmpeg_exe)
            return True
    except ImportError:
        pass

    # 方案 B: 系统 ffmpeg
    if check_command_exists("ffmpeg"):
        logger.info("ffmpeg (系统 PATH)")
        return True

    # 方案 C: 手动提示
    logger.error("ffmpeg 不可用！请执行: pip install imageio-ffmpeg")
    return False


def setup_env_vars() -> None:
    """
    设置必要的环境变量。
    我实际执行时：PATHEXT 为空导致 execjs 找不到 node.exe。
    """
    if sys.platform == "win32" and not os.environ.get("PATHEXT"):
        os.environ["PATHEXT"] = ".COM;.EXE;.BAT;.CMD;.VBS;.JS"
    os.environ["MPLBACKEND"] = "Agg"


def check_disk_space(path: Path, min_gb: float = 1.0) -> bool:
    """检查磁盘剩余空间"""
    try:
        usage = shutil.disk_usage(str(path))
        free_gb = usage.free / (1024**3)
        return free_gb >= min_gb
    except OSError as e:
        logger.warning("磁盘空间检查失败: %s", e)
        return False


def check_disk_space_enforced(path: Path, min_gb: float = 1.0) -> None:
    """
    检查磁盘剩余空间，不足则抛 FatalError。
    ★ 在写入大文件前必须调用此函数 ★
    """
    try:
        usage = shutil.disk_usage(str(path))
        free_gb = usage.free / (1024**3)
        if free_gb < min_gb:
            raise FatalError(
                f"磁盘空间不足: {free_gb:.2f}GB < {min_gb}GB (path={path})"
            )
    except OSError as e:
        logger.error("磁盘空间检查失败: %s", e)
        raise FatalError(
            f"磁盘空间检查失败: {e} (path={path})"
        ) from e


def ensure_dir_writable(dir_path: Path, fallback_dir: Path) -> Path:
    """
    检测目录可写性并自动选择可用路径。
    ★ 在写入数据前必须调用此函数 ★
    我实际执行时：沙箱环境中写入 G 盘被拦截，但没有预检测。
    """
    dir_path = Path(dir_path)
    fallback_dir = Path(fallback_dir)

    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        test_file = dir_path / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        return dir_path
    except (PermissionError, OSError):
        logger.warning("目录不可写: %s，fallback 到 %s", dir_path, fallback_dir)
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir


# ═══════════════════════════════════════════════════════════════════
# 5. 日志轮转
# ═══════════════════════════════════════════════════════════════════

def _douyin_scraper_logger() -> logging.Logger:
    return logging.getLogger("douyin_scraper")


def _rotating_handler_path(handler: RotatingFileHandler) -> Optional[Path]:
    base = getattr(handler, "baseFilename", None)
    if not base:
        return None
    try:
        return Path(base).resolve()
    except OSError:
        return None


def close_log_handler(log_path: Path) -> None:
    """Close and remove the RotatingFileHandler for a specific execution log."""
    target = Path(log_path).resolve()
    lib_logger = _douyin_scraper_logger()
    for handler in list(lib_logger.handlers):
        if not isinstance(handler, RotatingFileHandler):
            continue
        handler_path = _rotating_handler_path(handler)
        if handler_path is None or handler_path != target:
            continue
        try:
            handler.close()
        except OSError:
            pass
        lib_logger.removeHandler(handler)


def close_log_handlers_under(workspace: Path) -> None:
    """Close execution log handlers whose files live under a task workspace."""
    root = Path(workspace).resolve()
    lib_logger = _douyin_scraper_logger()
    for handler in list(lib_logger.handlers):
        if not isinstance(handler, RotatingFileHandler):
            continue
        handler_path = _rotating_handler_path(handler)
        if handler_path is None:
            continue
        try:
            handler_path.relative_to(root)
        except ValueError:
            continue
        try:
            handler.close()
        except OSError:
            pass
        lib_logger.removeHandler(handler)


def close_all_log_handlers() -> None:
    """Close every RotatingFileHandler attached to the douyin_scraper logger."""
    lib_logger = _douyin_scraper_logger()
    for handler in list(lib_logger.handlers):
        if not isinstance(handler, RotatingFileHandler):
            continue
        try:
            handler.close()
        except OSError:
            pass
        lib_logger.removeHandler(handler)


def setup_log_rotation(
    log_path: Path,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> RotatingFileHandler:
    """
    配置日志文件自动轮转。
    我实际执行时：execution_log.jsonl 增长到几百 MB，占满磁盘。
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    close_log_handler(log_path)

    handler = RotatingFileHandler(
        str(log_path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))

    lib_logger = _douyin_scraper_logger()
    lib_logger.setLevel(logging.DEBUG)
    lib_logger.addHandler(handler)

    return handler
