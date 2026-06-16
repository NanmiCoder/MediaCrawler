"""
douyin_scraper.api.main — FastAPI 应用入口
=============================================
v6 新增：Web API 服务入口。

启动方式：
  uvicorn api.main:app --host 0.0.0.0 --port 8000

或通过环境变量配置：
  DY_API_HOST=0.0.0.0 DY_API_PORT=8000 uvicorn api.main:app

我实际执行时踩过的坑：
  - 直接在 HTTP handler 中跑采集 → 请求超时
  - 无任务隔离 → 并发互相覆盖状态
  - 无健康检查 → 运维无法判断服务是否正常
  - 日志无结构化 → 排查问题时翻几小时日志
"""

import asyncio
import logging
import os
import platform
import shutil
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from douyin_scraper.utils import (
    check_command_exists,
    check_disk_space,
    check_port_in_use,
    setup_ffmpeg,
)

from .routes import router, set_task_manager
from .login import router as login_router
from .tasks import TaskManager
from .ws import ws_manager
from .schemas import LogEntry

logger = logging.getLogger("douyin_scraper.api")

# ═══════════════════════════════════════════════════════════════
# 日志广播后台任务（把 crawler_manager 的日志队列推给 WebSocket 前端）
# ═══════════════════════════════════════════════════════════════

_log_broadcaster_task: Optional[asyncio.Task] = None


async def log_broadcaster():
    """
    后台任务：从 crawler_manager 的日志队列读取 LogEntry，
    通过 ws_manager.broadcast() 推送给所有连接的 WebSocket 前端。
    消息格式：{"type": "log", "data": {...}}
    """
    from .services.crawler_manager import CrawlerManager
    from .ws import ws_manager

    # 获取 crawler_manager 单例（在 services/__init__.py 中定义）
    from .services import crawler_manager

    queue = crawler_manager.get_log_queue()
    logger.info("[LogBroadcaster] 启动，等待日志消息...")

    while True:
        try:
            entry = await queue.get()
            # 广播给所有连接的 WS 客户端
            msg = {
                "type": "log",
                "data": entry.model_dump() if hasattr(entry, "model_dump") else str(entry),
            }
            await ws_manager.broadcast(msg)
        except asyncio.CancelledError:
            logger.info("[LogBroadcaster] 被取消，退出")
            break
        except Exception as e:
            logger.warning("[LogBroadcaster] 错误: %s", e)
            await asyncio.sleep(0.1)


# ═══════════════════════════════════════════════════════════════
# 全局配置
# ═══════════════════════════════════════════════════════════════

API_HOST = os.environ.get("DY_API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("DY_API_PORT", "8000"))
WORKSPACE_DIR = os.environ.get("DY_WORKSPACE_DIR", "./workspaces")
CHROME_PORT = int(os.environ.get("DY_CHROME_PORT", "9222"))
LOG_LEVEL = os.environ.get("DY_LOG_LEVEL", "INFO")


# ═══════════════════════════════════════════════════════════════
# 结构化日志格式
# ═══════════════════════════════════════════════════════════════

class JSONFormatter(logging.Formatter):
    """
    JSON Lines 日志格式化器。
    ★ 我实际执行时：纯文本日志无法被 ELK/Grafana 解析。★
    """

    def format(self, record: logging.LogRecord) -> str:
        import json
        entry = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = str(record.exc_info[1])
        return json.dumps(entry, ensure_ascii=False)


def _setup_logging() -> None:
    """配置结构化日志"""
    log_dir = Path(WORKSPACE_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 控制台：人类可读格式
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    ))
    console.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # 文件：JSON Lines 格式（自动轮转 100MB × 5）
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        str(log_dir / "api.jsonl"),
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))
    file_handler.setLevel(logging.DEBUG)

    # 配置根 logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(console)
    root.addHandler(file_handler)

    # 降低第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# ═══════════════════════════════════════════════════════════════
# 应用生命周期
# ═══════════════════════════════════════════════════════════════

_task_manager_instance = None
_start_time: float = 0
_ffmpeg_available: Optional[bool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _task_manager_instance, _start_time
    _start_time = time.time()

    # 启动时初始化
    _setup_logging()
    logger.info("API 服务启动中...")

    _task_manager_instance = TaskManager(base_dir=WORKSPACE_DIR)
    app.state.task_manager = _task_manager_instance
    set_task_manager(_task_manager_instance)

    # 启动时清理过期任务
    _task_manager_instance.cleanup_old_tasks(max_age_hours=72)

    # 启动时检测 ffmpeg 可用性（仅一次，避免健康检查副作用）
    global _ffmpeg_available
    _ffmpeg_available = setup_ffmpeg()

    logger.info(
        "API 服务就绪: host=%s port=%d workspace=%s",
        API_HOST, API_PORT, WORKSPACE_DIR,
    )

    # 启动日志广播后台任务（把 crawler_manager 的日志推送给 WebSocket 前端）
    global _log_broadcaster_task
    _log_broadcaster_task = asyncio.create_task(log_broadcaster())
    logger.info("日志广播后台任务已启动")

    yield

    # 关闭时取消日志广播任务
    if _log_broadcaster_task and not _log_broadcaster_task.done():
        _log_broadcaster_task.cancel()
        try:
            await _log_broadcaster_task
        except asyncio.CancelledError:
            pass
    logger.info("API 服务已关闭")


# ═══════════════════════════════════════════════════════════════
# FastAPI 应用
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title="抖音采集工具 API",
    description=(
        "抖音关键词批量采集工具的 RESTful API。"
        "支持搜索采集、评论采集、文案提取、数据合并。"
        "所有长时间操作异步执行，通过 task_id 查询进度。"
    ),
    version="6.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS（根据环境配置来源列表，allow_credentials=False 与通配符来源兼容）
_cors_origins = os.environ.get("DY_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False if "*" in _cors_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)
app.include_router(login_router)


# ═══════════════════════════════════════════════════════════════
# WebSocket 端点（直接注册在 app，不走 /scrape 前缀）
# ═══════════════════════════════════════════════════════════════

@app.websocket("/ws/tasks")
async def websocket_tasks(ws: WebSocket):
    """WebSocket 端点：推送任务状态变更"""
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

# ═══════════════════════════════════════════════════════════════
# 静态文件挂载（Web UI）
# ═══════════════════════════════════════════════════════════════
# 挂在 /ui 而非 /，避免拦截 WebSocket (/ws/tasks) 和 API (/scrape/*)
from fastapi.staticfiles import StaticFiles

_webui_dir = Path(__file__).parent / "webui"
if _webui_dir.exists() and (_webui_dir / "index.html").exists():
    app.mount("/ui", StaticFiles(directory=str(_webui_dir), html=True), name="webui")


# ═══════════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════════

@app.get("/health", summary="健康检查", tags=["system"])
async def health_check() -> Dict[str, Any]:
    """
    健康检查端点。

    返回：
    - 服务运行时间
    - Chrome CDP 端口状态
    - 磁盘空间
    - 依赖版本
    - 任务统计
    """
    uptime = time.time() - _start_time if _start_time else 0

    # Chrome CDP 端口检查
    cdp_ok = check_port_in_use(CHROME_PORT)

    # 磁盘空间
    workspace_path = Path(WORKSPACE_DIR)
    disk_ok = True
    free_gb = 0.0
    try:
        usage = shutil.disk_usage(str(workspace_path))
        free_gb = usage.free / (1024**3)
        disk_ok = free_gb > 1.0
    except OSError:
        pass

    # 依赖检查（使用启动时缓存的结果，避免副作用）
    ffmpeg_ok = _ffmpeg_available if _ffmpeg_available is not None else check_command_exists("ffmpeg")
    python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # 任务统计
    task_stats = {}
    if _task_manager_instance:
        task_stats = _task_manager_instance.get_stats()

    health = {
        "status": "healthy" if (disk_ok and cdp_ok) else "degraded",
        "uptime_seconds": round(uptime, 1),
        "checks": {
            "chrome_cdp": {
                "port": CHROME_PORT,
                "status": "ok" if cdp_ok else "not_running",
            },
            "disk": {
                "free_gb": round(free_gb, 2),
                "status": "ok" if disk_ok else "low",
            },
            "ffmpeg": {
                "status": "ok" if ffmpeg_ok else "missing",
            },
        },
        "system": {
            "python": python_ver,
            "platform": platform.platform(),
            "workspace": str(workspace_path.resolve()),
        },
        "tasks": task_stats,
    }

    return health


@app.get("/", summary="根路径", tags=["system"])
async def root() -> Dict[str, str]:
    """API 根路径，返回基本信息"""
    return {
        "name": "抖音采集工具 API",
        "version": "6.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# ═══════════════════════════════════════════════════════════════
# 直接运行入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=os.environ.get("DY_RELOAD", "0") == "1",
        log_level=LOG_LEVEL.lower(),
    )
