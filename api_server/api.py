# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import argparse
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from fastapi_offline import FastAPIOffline
import uvicorn

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 尝试导入配置
try:
    from config import base_config
    from config import db_config
    print("✅ 配置文件导入成功")
except ImportError as e:
    print(f"⚠️ 警告: 无法导入配置文件: {e}")
    print("将使用默认配置")
    base_config = None
    db_config = None

# 全局变量
tasks: Dict[str, 'TaskInfo'] = {}  # 任务存储
running_processes: Dict[str, subprocess.Popen] = {}  # 运行中的进程

# 服务器配置
class ServerConfig:
    """服务器配置类"""
    def __init__(self):
        # 支持环境变量配置，提供默认值
        self.host: str = os.getenv("API_HOST", "0.0.0.0")
        self.port: int = int(os.getenv("API_PORT", "8000"))
        self.reload: bool = os.getenv("API_RELOAD", "true").lower() == "true"
        self.debug: bool = os.getenv("API_DEBUG", "false").lower() == "true"
        
    def get_api_docs_url(self) -> str:
        """获取API文档URL"""
        return f"http://localhost:{self.port}/docs"
        
    def get_redoc_url(self) -> str:
        """获取ReDoc文档URL"""
        return f"http://localhost:{self.port}/redoc"
        
    def get_server_url(self) -> str:
        """获取服务器URL"""
        return f"http://{self.host}:{self.port}"
        
    def update_port(self, port: int) -> None:
        """动态更新端口号"""
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError("端口号必须是1-65535之间的整数")
        self.port = port
        
    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            "host": self.host,
            "port": self.port,
            "reload": self.reload,
            "debug": self.debug,
            "api_docs_url": self.get_api_docs_url(),
            "redoc_url": self.get_redoc_url(),
            "server_url": self.get_server_url()
        }
        
    def __str__(self) -> str:
        """字符串表示"""
        return f"ServerConfig(host={self.host}, port={self.port}, reload={self.reload}, debug={self.debug})"

# 全局服务器配置实例
server_config = ServerConfig()

def update_server_config(host: Optional[str] = None, port: Optional[int] = None, 
                        reload: Optional[bool] = None, debug: Optional[bool] = None):
    """更新全局服务器配置"""
    if host is not None:
        server_config.host = host
    if port is not None:
        server_config.update_port(port)
    if reload is not None:
        server_config.reload = reload
    if debug is not None:
        server_config.debug = debug

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动事件
    print("="*60)
    print("MediaCrawler API 服务器启动成功!")
    print("="*60)
    print(f"项目根目录: {project_root}")
    print(f"服务器配置: {server_config}")
    print("-"*40)
    print("📚 文档地址:")
    print(f"  • Swagger UI: {server_config.get_api_docs_url()}")
    print(f"  • ReDoc:      {server_config.get_redoc_url()}")
    print(f"🌐 服务器地址: {server_config.get_server_url()}")
    print("="*60)
    
    if server_config.debug:
        print("🐛 调试模式已启用")
        config_info = server_config.get_config_info()
        print("详细配置信息:")
        for key, value in config_info.items():
            print(f"  {key}: {value}")
        print("-"*40)
    
    yield
    
    # 关闭事件
    print("正在关闭MediaCrawler API服务器...")
    
    # 终止所有运行中的进程
    for task_id, process in running_processes.items():
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            try:
                process.kill()
            except:
                pass
    
    print("MediaCrawler API服务器已关闭")

def create_app() -> FastAPIOffline:
    """创建FastAPI应用实例"""
    return FastAPIOffline(
        title="MediaCrawler API",
        description="MediaCrawler异步后端API服务器 - 多平台自媒体数据采集工具",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

# 创建FastAPI应用 - 使用fastapi-offline支持离线文档
app = create_app()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 枚举定义
class PlatformEnum(str, Enum):
    """支持的平台枚举"""
    XHS = "xhs"  # 小红书
    DY = "dy"    # 抖音
    KS = "ks"    # 快手
    BILI = "bili"  # B站
    WB = "wb"    # 微博
    TIEBA = "tieba"  # 贴吧
    ZHIHU = "zhihu"  # 知乎

class LoginTypeEnum(str, Enum):
    """登录类型枚举"""
    QRCODE = "qrcode"  # 二维码登录
    PHONE = "phone"    # 手机号登录
    COOKIE = "cookie"  # Cookie登录

class CrawlerTypeEnum(str, Enum):
    """爬取类型枚举"""
    SEARCH = "search"    # 关键词搜索
    DETAIL = "detail"    # 指定帖子ID
    CREATOR = "creator"  # 指定创作者主页

class SaveDataOptionEnum(str, Enum):
    """数据保存选项枚举"""
    CSV = "csv"
    DB = "db"
    JSON = "json"

class TaskStatusEnum(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"    # 等待中
    RUNNING = "running"    # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"      # 失败
    CANCELLED = "cancelled"  # 已取消

# 请求模型
class CrawlerRequest(BaseModel):
    """爬虫请求模型"""
    platform: PlatformEnum = Field(..., description="平台选择")
    login_type: LoginTypeEnum = Field(default=LoginTypeEnum.QRCODE, description="登录类型")
    crawler_type: CrawlerTypeEnum = Field(default=CrawlerTypeEnum.SEARCH, description="爬取类型")
    start_page: int = Field(default=1, ge=1, description="起始页码")
    keywords: Optional[str] = Field(default="", description="搜索关键词")
    get_comment: bool = Field(default=False, description="是否获取一级评论")
    get_sub_comment: bool = Field(default=False, description="是否获取二级评论")
    save_data_option: SaveDataOptionEnum = Field(default=SaveDataOptionEnum.JSON, description="数据保存选项")
    cookies: Optional[str] = Field(default="", description="Cookie字符串")
    
    @field_validator('keywords', mode='after')
    @classmethod
    def validate_keywords(cls, v):
        """验证关键词"""
        # 注意：在Pydantic V2中，单字段验证器无法直接访问其他字段
        # 这里我们简化验证逻辑，或者可以使用model_validator进行整体验证
        return v
    
    def model_post_init(self, __context) -> None:
        """模型初始化后验证"""
        if self.crawler_type == CrawlerTypeEnum.SEARCH and not self.keywords:
            raise ValueError('搜索类型必须提供关键词')
        super().model_post_init(__context) if hasattr(super(), 'model_post_init') else None

# 响应模型
class TaskInfo(BaseModel):
    """任务信息模型"""
    task_id: str
    status: TaskStatusEnum
    platform: str
    crawler_type: str
    keywords: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None

class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

class CrawlerResponse(BaseResponse):
    """爬虫响应模型"""
    data: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None

class TaskListResponse(BaseResponse):
    """任务列表响应模型"""
    data: List[TaskInfo]
    total: int

class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"



def str2bool(v: str) -> bool:
    """字符串转布尔值"""
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ValueError('Boolean value expected.')

def build_command(request: CrawlerRequest) -> List[str]:
    """构建爬虫命令"""
    cmd = [sys.executable, "main.py"]
    
    # 基础参数
    cmd.extend(["--platform", request.platform])
    cmd.extend(["--lt", request.login_type])
    cmd.extend(["--type", request.crawler_type])
    
    # 关键词参数
    if request.keywords:
        cmd.extend(["--keywords", request.keywords])
    
    # 可选参数
    if request.start_page is not None:
        cmd.extend(["--start", str(request.start_page)])
    
    if request.get_comment is not None:
        cmd.extend(["--get_comment", str(request.get_comment).lower()])
    
    if request.get_sub_comment is not None:
        cmd.extend(["--get_sub_comment", str(request.get_sub_comment).lower()])
    
    if request.save_data_option:
        cmd.extend(["--save", request.save_data_option])
    
    if request.cookies:
        cmd.extend(["--cookies", request.cookies])
    
    return cmd

def run_crawler_subprocess(task_id: str, command: List[str]):
    """在子进程中运行爬虫"""
    try:
        # 更新任务状态为运行中
        if task_id in tasks:
            tasks[task_id].status = TaskStatusEnum.RUNNING
            tasks[task_id].started_at = datetime.now()
        
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # 启动子进程
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            cwd=str(project_root),
            env=env
        )
        
        # 保存进程引用
        running_processes[task_id] = process
        
        # 等待进程完成
        stdout, stderr = process.communicate()
        
        # 移除进程引用
        if task_id in running_processes:
            del running_processes[task_id]
        
        # 更新任务状态
        if task_id in tasks:
            tasks[task_id].completed_at = datetime.now()
            
            if process.returncode == 0:
                tasks[task_id].status = TaskStatusEnum.COMPLETED
                tasks[task_id].result_data = {
                    "stdout": stdout,
                    "stderr": stderr,
                    "return_code": process.returncode
                }
            else:
                tasks[task_id].status = TaskStatusEnum.FAILED
                tasks[task_id].error_message = stderr or "进程异常退出"
                tasks[task_id].result_data = {
                    "stdout": stdout,
                    "stderr": stderr,
                    "return_code": process.returncode
                }
    
    except Exception as e:
        # 更新任务状态为失败
        if task_id in tasks:
            tasks[task_id].status = TaskStatusEnum.FAILED
            tasks[task_id].error_message = str(e)
            tasks[task_id].completed_at = datetime.now()
        
        # 清理进程引用
        if task_id in running_processes:
            del running_processes[task_id]

# API路由
@app.get("/", response_model=HealthResponse)
async def root():
    """根路径 - 服务状态"""
    return HealthResponse()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse()

@app.post("/crawler/run", response_model=CrawlerResponse)
async def run_crawler_sync(request: CrawlerRequest):
    """同步运行爬虫任务"""
    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务信息
        task_info = TaskInfo(
            task_id=task_id,
            status=TaskStatusEnum.PENDING,
            platform=request.platform.value,
            crawler_type=request.crawler_type.value,
            keywords=request.keywords,
            created_at=datetime.now()
        )
        
        # 保存任务
        tasks[task_id] = task_info
        
        # 构建命令
        command = build_command(request)
        
        # 同步执行爬虫
        run_crawler_subprocess(task_id, command)
        
        # 获取最新任务状态
        final_task = tasks[task_id]
        
        if final_task.status == TaskStatusEnum.COMPLETED:
            return CrawlerResponse(
                success=True,
                message="爬虫任务执行成功",
                task_id=task_id,
                data=final_task.result_data
            )
        else:
            return CrawlerResponse(
                success=False,
                message=f"爬虫任务执行失败: {final_task.error_message}",
                task_id=task_id,
                data=final_task.result_data
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.post("/crawler/run-async", response_model=CrawlerResponse)
async def run_crawler_async(request: CrawlerRequest, background_tasks: BackgroundTasks):
    """异步运行爬虫任务"""
    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务信息
        task_info = TaskInfo(
            task_id=task_id,
            status=TaskStatusEnum.PENDING,
            platform=request.platform.value,
            crawler_type=request.crawler_type.value,
            keywords=request.keywords,
            created_at=datetime.now()
        )
        
        # 保存任务
        tasks[task_id] = task_info
        
        # 构建命令
        command = build_command(request)
        
        # 添加后台任务
        background_tasks.add_task(run_crawler_subprocess, task_id, command)
        
        return CrawlerResponse(
            success=True,
            message="爬虫任务已提交，正在后台执行",
            task_id=task_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.get("/crawler/task/{task_id}", response_model=CrawlerResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    return CrawlerResponse(
        success=True,
        message="获取任务状态成功",
        task_id=task_id,
        data=task.dict()
    )

@app.get("/crawler/tasks", response_model=TaskListResponse)
async def get_all_tasks(limit: int = 50, offset: int = 0):
    """获取所有任务列表"""
    all_tasks = list(tasks.values())
    # 按创建时间倒序排列
    all_tasks.sort(key=lambda x: x.created_at, reverse=True)
    
    # 分页
    paginated_tasks = all_tasks[offset:offset + limit]
    
    return TaskListResponse(
        success=True,
        message="获取任务列表成功",
        data=paginated_tasks,
        total=len(all_tasks)
    )

@app.delete("/crawler/task/{task_id}", response_model=BaseResponse)
async def cancel_task(task_id: str):
    """取消/删除任务"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    
    # 如果任务正在运行，尝试终止进程
    if task.status == TaskStatusEnum.RUNNING and task_id in running_processes:
        try:
            process = running_processes[task_id]
            process.terminate()
            # 等待进程终止
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()  # 强制杀死进程
            
            # 更新任务状态
            task.status = TaskStatusEnum.CANCELLED
            task.completed_at = datetime.now()
            task.error_message = "任务被用户取消"
            
            # 清理进程引用
            if task_id in running_processes:
                del running_processes[task_id]
            
            return BaseResponse(success=True, message="任务已取消")
        except Exception as e:
            return BaseResponse(success=False, message=f"取消任务失败: {str(e)}")
    
    # 删除任务记录
    del tasks[task_id]
    
    return BaseResponse(success=True, message="任务已删除")

@app.get("/crawler/platforms")
async def get_supported_platforms():
    """获取支持的平台列表"""
    platforms = [
        {"value": "xhs", "label": "小红书", "description": "小红书平台数据采集"},
        {"value": "dy", "label": "抖音", "description": "抖音平台数据采集"},
        {"value": "ks", "label": "快手", "description": "快手平台数据采集"},
        {"value": "bili", "label": "B站", "description": "哔哩哔哩平台数据采集"},
        {"value": "wb", "label": "微博", "description": "微博平台数据采集"},
        {"value": "tieba", "label": "贴吧", "description": "百度贴吧平台数据采集"},
        {"value": "zhihu", "label": "知乎", "description": "知乎平台数据采集"}
    ]
    
    return {
        "success": True,
        "message": "获取支持平台列表成功",
        "data": platforms
    }

# 异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"服务器内部错误: {str(exc)}",
            "timestamp": datetime.now().isoformat()
        }
    )



def start_server(host: Optional[str] = None, port: Optional[int] = None, 
                reload: Optional[bool] = None, debug: Optional[bool] = None):
    """启动服务器的函数
    
    Args:
        host: 服务器主机地址，默认使用配置中的值
        port: 服务器端口号，默认使用配置中的值
        reload: 是否启用热重载，默认使用配置中的值
        debug: 是否启用调试模式，默认使用配置中的值
    """
    # 在启动前更新全局配置，确保启动事件能获取到正确配置
    update_server_config(host=host, port=port, reload=reload, debug=debug)
    
    # 显示启动前的配置信息
    print(f"🚀 准备启动服务器，配置: {server_config}")
    
    # 启动服务器
    try:
        if server_config.reload:
            # 热重载模式：使用模块字符串
            uvicorn.run(
                "api:app",
                host=server_config.host,
                port=server_config.port,
                reload=server_config.reload,
                reload_dirs=[str(project_root)],
                log_level="debug" if server_config.debug else "info"
            )
        else:
            # 非热重载模式：直接使用应用实例
            uvicorn.run(
                app,
                host=server_config.host,
                port=server_config.port,
                reload=False,
                log_level="debug" if server_config.debug else "info"
            )
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        raise

def main():
    """主函数，支持命令行参数"""
    
    parser = argparse.ArgumentParser(description="MediaCrawler API 服务器")
    parser.add_argument("--host", type=str, help="服务器主机地址")
    parser.add_argument("--port", type=int, help="服务器端口号")
    parser.add_argument("--no-reload", action="store_true", help="禁用热重载")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    
    args = parser.parse_args()
    
    # 将命令行参数设置为环境变量，确保热重载时配置不丢失
    if args.host:
        os.environ["API_HOST"] = args.host
    if args.port:
        os.environ["API_PORT"] = str(args.port)
    if args.no_reload:
        os.environ["API_RELOAD"] = "false"
    if args.debug:
        os.environ["API_DEBUG"] = "true"
    
    # 重新创建配置实例以读取环境变量
    global server_config
    server_config = ServerConfig()
    
    # 启动服务器
    start_server(
        host=args.host,
        port=args.port,
        reload=not args.no_reload if args.no_reload else None,
        debug=args.debug if args.debug else None
    )

if __name__ == "__main__":
    # 运行服务器
    main()