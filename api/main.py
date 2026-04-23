# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/main.py
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
MediaCrawler WebUI API Server
Start command: uvicorn api.main:app --port 8080 --reload
Or: python -m api.main
"""
import asyncio
import os
import shutil
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routers import crawler_router, data_router, websocket_router, notes_router, zhihu_router, bilibili_router, douyin_router, subscriptions_router, trends_router, image_queue_router
from .services import file_watcher, image_task_db, image_downloader, image_queue_service
from .services.file_watcher import PLATFORMS
from .routers.websocket import broadcast_stats_update, broadcast_platform_update


# Data directory for JSONL files
DATA_DIR = Path(__file__).parent.parent / "data"


async def on_file_change_callback(platform: str):
    """
    Callback for file watcher when a platform's data changes.
    Broadcasts both platform-specific update and global stats update.

    Args:
        platform: The platform identifier (e.g., "xhs", "dy", "bili", "zhihu")
    """
    # Broadcast platform-specific update (for viewer components)
    await broadcast_platform_update(platform)
    # Broadcast global stats update (for WebUI compatibility)
    await broadcast_stats_update(platform)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - start/stop file watcher for all platforms."""
    # Initialize task database
    await image_task_db.init_db()

    # Initialize image downloader
    await image_downloader.init()

    # Start queue service (launches consumers)
    image_queue_service.start()

    # Startup - watch all platform directories
    file_watcher.start(
        platforms=PLATFORMS,
        base_callback=on_file_change_callback,
        base_path=str(DATA_DIR)
    )
    app.state.file_watcher = file_watcher

    yield

    # Shutdown
    image_queue_service.stop()
    await image_downloader.close()
    file_watcher.stop()


app = FastAPI(
    title="MediaCrawler WebUI API",
    description="API for controlling MediaCrawler from WebUI",
    version="1.0.0",
    lifespan=lifespan
)

# Get webui static files directory
WEBUI_DIR = os.path.join(os.path.dirname(__file__), "webui")

# CORS configuration - allow frontend dev server access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Backup port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(crawler_router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(zhihu_router, prefix="/api")
app.include_router(bilibili_router, prefix="/api")
app.include_router(douyin_router, prefix="/api")
app.include_router(subscriptions_router, prefix="/api")
app.include_router(trends_router, prefix="/api")
app.include_router(image_queue_router, prefix="/api")


@app.get("/")
async def serve_frontend():
    """Return frontend page"""
    index_path = os.path.join(WEBUI_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "MediaCrawler WebUI API",
        "version": "1.0.0",
        "docs": "/docs",
        "note": "WebUI not found, please build it first: cd webui && npm run build"
    }


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/env/check")
async def check_environment():
    """Check if MediaCrawler environment is configured correctly"""
    # Simple check - just verify uv is available
    uv_path = shutil.which("uv")

    return {
        "success": uv_path is not None,
        "message": "Environment ready" if uv_path else "uv not found",
        "uv_path": uv_path
    }


@app.get("/api/config/platforms")
async def get_platforms():
    """Get list of supported platforms"""
    return {
        "platforms": [
            {"value": "xhs", "label": "Xiaohongshu", "icon": "book-open"},
            {"value": "dy", "label": "Douyin", "icon": "music"},
            {"value": "ks", "label": "Kuaishou", "icon": "video"},
            {"value": "bili", "label": "Bilibili", "icon": "tv"},
            {"value": "wb", "label": "Weibo", "icon": "message-circle"},
            {"value": "tieba", "label": "Baidu Tieba", "icon": "messages-square"},
            {"value": "zhihu", "label": "Zhihu", "icon": "help-circle"},
        ]
    }


@app.get("/api/config/options")
async def get_config_options():
    """Get all configuration options"""
    return {
        "login_types": [
            {"value": "qrcode", "label": "QR Code Login"},
            {"value": "cookie", "label": "Cookie Login"},
        ],
        "crawler_types": [
            {"value": "search", "label": "Search Mode"},
            {"value": "detail", "label": "Detail Mode"},
            {"value": "creator", "label": "Creator Mode"},
        ],
        "save_options": [
            {"value": "jsonl", "label": "JSONL File"},
            {"value": "json", "label": "JSON File"},
            {"value": "csv", "label": "CSV File"},
            {"value": "excel", "label": "Excel File"},
            {"value": "sqlite", "label": "SQLite Database"},
            {"value": "db", "label": "MySQL Database"},
            {"value": "mongodb", "label": "MongoDB Database"},
        ],
    }


# Mount static resources - must be placed after all routes
if os.path.exists(WEBUI_DIR):
    assets_dir = os.path.join(WEBUI_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    # Mount logos directory
    logos_dir = os.path.join(WEBUI_DIR, "logos")
    if os.path.exists(logos_dir):
        app.mount("/logos", StaticFiles(directory=logos_dir), name="logos")
    # Mount other static files (e.g., vite.svg)
    app.mount("/static", StaticFiles(directory=WEBUI_DIR), name="webui-static")

# Mount viewer static files
VIEWER_DIR = os.path.join(os.path.dirname(__file__), "..", "viewer", "static")
if os.path.exists(VIEWER_DIR):
    app.mount("/viewer", StaticFiles(directory=VIEWER_DIR, html=True), name="viewer")

# Mount images directory for note images
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "xhs", "images")
if os.path.exists(IMAGES_DIR):
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
