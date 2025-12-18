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
启动命令: uvicorn api.main:app --port 8080 --reload
或者: python -m api.main
"""
import asyncio
import os
import subprocess
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routers import crawler_router, data_router, websocket_router

app = FastAPI(
    title="MediaCrawler WebUI API",
    description="API for controlling MediaCrawler from WebUI",
    version="1.0.0"
)

# 获取 webui 静态文件目录
WEBUI_DIR = os.path.join(os.path.dirname(__file__), "webui")

# CORS 配置 - 允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # 备用端口
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(crawler_router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")


@app.get("/")
async def serve_frontend():
    """返回前端页面"""
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
    """检测 MediaCrawler 环境是否配置正确"""
    try:
        # 运行 uv run main.py --help 命令检测环境
        process = await asyncio.create_subprocess_exec(
            "uv", "run", "main.py", "--help",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="."  # 项目根目录
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=30.0  # 30秒超时
        )

        if process.returncode == 0:
            return {
                "success": True,
                "message": "MediaCrawler 环境配置正确",
                "output": stdout.decode("utf-8", errors="ignore")[:500]  # 截取前500字符
            }
        else:
            error_msg = stderr.decode("utf-8", errors="ignore") or stdout.decode("utf-8", errors="ignore")
            return {
                "success": False,
                "message": "环境检测失败",
                "error": error_msg[:500]
            }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "message": "环境检测超时",
            "error": "命令执行超过30秒"
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": "未找到 uv 命令",
            "error": "请确保已安装 uv 并配置到系统 PATH"
        }
    except Exception as e:
        return {
            "success": False,
            "message": "环境检测出错",
            "error": str(e)
        }


@app.get("/api/config/platforms")
async def get_platforms():
    """获取支持的平台列表"""
    return {
        "platforms": [
            {"value": "xhs", "label": "小红书", "icon": "book-open"},
            {"value": "dy", "label": "抖音", "icon": "music"},
            {"value": "ks", "label": "快手", "icon": "video"},
            {"value": "bili", "label": "哔哩哔哩", "icon": "tv"},
            {"value": "wb", "label": "微博", "icon": "message-circle"},
            {"value": "tieba", "label": "百度贴吧", "icon": "messages-square"},
            {"value": "zhihu", "label": "知乎", "icon": "help-circle"},
        ]
    }


@app.get("/api/config/options")
async def get_config_options():
    """获取所有配置选项"""
    return {
        "login_types": [
            {"value": "qrcode", "label": "二维码登录"},
            {"value": "cookie", "label": "Cookie登录"},
        ],
        "crawler_types": [
            {"value": "search", "label": "搜索模式"},
            {"value": "detail", "label": "详情模式"},
            {"value": "creator", "label": "创作者模式"},
        ],
        "save_options": [
            {"value": "json", "label": "JSON 文件"},
            {"value": "csv", "label": "CSV 文件"},
            {"value": "excel", "label": "Excel 文件"},
            {"value": "sqlite", "label": "SQLite 数据库"},
            {"value": "db", "label": "MySQL 数据库"},
            {"value": "mongodb", "label": "MongoDB 数据库"},
        ],
    }


# 挂载静态资源 - 必须放在所有路由之后
if os.path.exists(WEBUI_DIR):
    assets_dir = os.path.join(WEBUI_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    # 挂载 logos 目录
    logos_dir = os.path.join(WEBUI_DIR, "logos")
    if os.path.exists(logos_dir):
        app.mount("/logos", StaticFiles(directory=logos_dir), name="logos")
    # 挂载其他静态文件（如 vite.svg）
    app.mount("/static", StaticFiles(directory=WEBUI_DIR), name="webui-static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
