"""
MediaCrawler API Server
提供统一的 REST API 接口，支持抖音、小红书、知乎数据采集
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from tools import utils

# 创建 FastAPI 应用
app = FastAPI(
    title="MediaCrawler API",
    description="统一的社交媒体数据采集 API - 支持抖音、小红书、知乎",
    version="1.0.0"
)

# ==================== 数据模型 ====================

class SearchRequest(BaseModel):
    """搜索请求"""
    platform: str = Field(..., description="平台代码: dy(抖音), xhs(小红书), zhihu(知乎)")
    keyword: str = Field(..., description="搜索关键词")
    max_count: int = Field(10, description="最大采集数量", ge=1, le=50)
    enable_comments: bool = Field(True, description="是否采集评论")
    enable_media: bool = Field(False, description="是否下载媒体文件")

class SearchResponse(BaseModel):
    """搜索响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending, running, completed, failed")
    message: str = Field(..., description="消息")
    data: Optional[Dict] = Field(None, description="结果数据")

class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    status: str
    progress: Optional[str] = None
    result_file: Optional[str] = None
    error: Optional[str] = None

# ==================== 全局变量 ====================

# 任务队列
tasks_status = {}

# ==================== 辅助函数 ====================

def validate_platform(platform: str) -> bool:
    """验证平台代码"""
    valid_platforms = ["dy", "xhs", "zhihu"]
    return platform in valid_platforms

async def run_crawler_task(task_id: str, platform: str, keyword: str,
                           max_count: int, enable_comments: bool, enable_media: bool):
    """运行爬虫任务"""
    try:
        # 更新任务状态
        tasks_status[task_id]["status"] = "running"
        tasks_status[task_id]["progress"] = "初始化爬虫..."

        # 加载平台Cookie配置
        try:
            from test_platform_cookies import get_cookie_for_platform
            platform_cookie = get_cookie_for_platform(platform)
            if platform_cookie:
                config.COOKIES = platform_cookie
                utils.logger.info(f"[API] Loaded cookie for platform: {platform}")
            else:
                utils.logger.warning(f"[API] No cookie configured for platform: {platform}")
        except ImportError:
            utils.logger.warning("[API] test_platform_cookies.py not found, using default cookie")

        # 动态修改配置
        config.PLATFORM = platform
        config.KEYWORDS = keyword
        config.CRAWLER_MAX_NOTES_COUNT = max_count
        config.ENABLE_GET_COMMENTS = enable_comments
        config.ENABLE_GET_MEIDAS = enable_media

        # 根据平台导入相应的爬虫
        if platform == "dy":
            from media_platform.douyin import DouYinCrawler
            crawler = DouYinCrawler()
        elif platform == "xhs":
            from media_platform.xhs import XiaoHongShuCrawler
            crawler = XiaoHongShuCrawler()
        elif platform == "zhihu":
            from media_platform.zhihu import ZhihuCrawler
            crawler = ZhihuCrawler()
        else:
            raise ValueError(f"不支持的平台: {platform}")

        tasks_status[task_id]["progress"] = "开始采集数据..."

        # 运行爬虫
        await crawler.start()

        # 查找生成的数据文件
        data_dir = Path(f"data/{platform}/json")
        today = datetime.now().strftime("%Y-%m-%d")

        result_files = []
        if data_dir.exists():
            result_files = list(data_dir.glob(f"*{today}*.json"))

        if result_files:
            # 读取最新的数据文件
            latest_file = max(result_files, key=lambda p: p.stat().st_mtime)
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            tasks_status[task_id]["status"] = "completed"
            tasks_status[task_id]["progress"] = "采集完成"
            tasks_status[task_id]["result_file"] = str(latest_file)
            tasks_status[task_id]["data"] = {
                "total": len(data) if isinstance(data, list) else 1,
                "keyword": keyword,
                "platform": platform,
                "file_path": str(latest_file),
                "items": data[:5] if isinstance(data, list) else data  # 只返回前5条预览
            }
        else:
            tasks_status[task_id]["status"] = "completed"
            tasks_status[task_id]["progress"] = "采集完成，但未找到数据文件"
            tasks_status[task_id]["data"] = {"message": "采集完成，但未找到数据文件"}

    except Exception as e:
        tasks_status[task_id]["status"] = "failed"
        tasks_status[task_id]["error"] = str(e)
        utils.logger.error(f"[API] Task {task_id} failed: {e}")

# ==================== API 路由 ====================

@app.get("/")
async def root():
    """API 首页"""
    return {
        "name": "MediaCrawler API",
        "version": "1.0.0",
        "description": "统一的社交媒体数据采集 API",
        "supported_platforms": {
            "dy": "抖音",
            "xhs": "小红书",
            "zhihu": "知乎"
        },
        "endpoints": {
            "search": "POST /api/search - 搜索并采集数据",
            "status": "GET /api/task/{task_id} - 查询任务状态",
            "platforms": "GET /api/platforms - 获取支持的平台列表"
        },
        "docs": "/docs"
    }

@app.get("/api/platforms")
async def get_platforms():
    """获取支持的平台列表"""
    return {
        "platforms": [
            {
                "code": "dy",
                "name": "抖音",
                "description": "短视频平台",
                "supported_types": ["搜索", "用户", "视频详情"]
            },
            {
                "code": "xhs",
                "name": "小红书",
                "description": "生活方式分享平台",
                "supported_types": ["搜索", "用户", "笔记详情"]
            },
            {
                "code": "zhihu",
                "name": "知乎",
                "description": "问答社区",
                "supported_types": ["搜索", "用户", "问题详情"]
            }
        ]
    }

@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest, background_tasks: BackgroundTasks):
    """
    搜索并采集数据

    - **platform**: 平台代码 (dy/xhs/zhihu)
    - **keyword**: 搜索关键词
    - **max_count**: 最大采集数量 (1-50)
    - **enable_comments**: 是否采集评论
    - **enable_media**: 是否下载媒体文件
    """
    # 验证平台
    if not validate_platform(request.platform):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的平台: {request.platform}，支持的平台: dy, xhs, zhihu"
        )

    # 生成任务ID
    import random
    import string
    random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    task_id = f"{request.platform}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random_id}"

    # 初始化任务状态
    tasks_status[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "platform": request.platform,
        "keyword": request.keyword,
        "max_count": request.max_count,
        "created_at": datetime.now().isoformat(),
        "progress": None,
        "result_file": None,
        "error": None,
        "data": None
    }

    # 在后台运行爬虫任务
    background_tasks.add_task(
        run_crawler_task,
        task_id,
        request.platform,
        request.keyword,
        request.max_count,
        request.enable_comments,
        request.enable_media
    )

    return SearchResponse(
        task_id=task_id,
        status="pending",
        message=f"任务已创建，正在后台执行。使用 GET /api/task/{task_id} 查询进度",
        data=None
    )

@app.get("/api/task/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """
    查询任务状态

    - **task_id**: 任务ID
    """
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks_status[task_id]

    return TaskStatus(
        task_id=task["task_id"],
        status=task["status"],
        progress=task.get("progress"),
        result_file=task.get("result_file"),
        error=task.get("error")
    )

@app.get("/api/task/{task_id}/result")
async def get_task_result(task_id: str):
    """
    获取任务结果

    - **task_id**: 任务ID
    """
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks_status[task_id]

    if task["status"] != "completed":
        return JSONResponse(
            status_code=400,
            content={
                "error": "任务尚未完成",
                "status": task["status"],
                "progress": task.get("progress")
            }
        )

    return {
        "task_id": task_id,
        "status": task["status"],
        "platform": task["platform"],
        "keyword": task["keyword"],
        "data": task.get("data"),
        "result_file": task.get("result_file")
    }

@app.get("/api/tasks")
async def list_tasks():
    """获取所有任务列表"""
    return {
        "total": len(tasks_status),
        "tasks": [
            {
                "task_id": task_id,
                "platform": task["platform"],
                "keyword": task["keyword"],
                "status": task["status"],
                "created_at": task["created_at"]
            }
            for task_id, task in tasks_status.items()
        ]
    }

@app.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    """删除任务记录"""
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail="任务不存在")

    del tasks_status[task_id]
    return {"message": f"任务 {task_id} 已删除"}

# ==================== 启动服务 ====================

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════╗
║                    MediaCrawler API Server                     ║
║                                                                ║
║  🚀 API 文档: http://localhost:8080/docs                      ║
║  📊 支持平台: 抖音 | 小红书 | 知乎                            ║
║  🔗 API 端点: http://localhost:8080/api/search               ║
╚════════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
