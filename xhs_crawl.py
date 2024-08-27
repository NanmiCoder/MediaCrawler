from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from typing import AsyncIterator
from pydantic import BaseModel
from media_platform.xhs import XiaoHongShuCrawler
import asyncio
import config
import uvicorn
import time

# app = FastAPI()
crawler: XiaoHongShuCrawler

class KeywordRequest(BaseModel):
    keyword: str

# 替换之前的 @app.on_event 装饰器
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 在这里执行启动时的初始化
    global crawler
    crawler = XiaoHongShuCrawler()
    await crawler.init_proxy()
    await crawler.initialize_playwright()
    await crawler.init_and_check_client()
    config.KEYWORDS = "IPhone"  # 如果需要，可以设置默认关键字

    yield
    # 在这里执行关闭时的清理
    await crawler.cleanup_playwright()
        
app = FastAPI(lifespan=lifespan)

@app.post("/search")
async def search(request: KeywordRequest):
    global crawler
    config.KEYWORDS = request.keyword
    
    start_time = time.time()  # 记录任务开始时间

    # 创建任务并检查其完成状态
    task = asyncio.create_task(crawler.search())
    while not task.done():
        await asyncio.sleep(0.1)  # 等待一会儿再检查任务是否完成
    
    # 获取任务结果
    result = await task
    
    end_time = time.time()  # 记录任务结束时间
    elapsed_time = end_time - start_time  # 计算运行时间
    return {"result_length": len(result), "results": result, "elapsed_time": elapsed_time}

# 为了调试目的，你可以添加一个简单的路由来检查服务是否运行
@app.get("/")
async def root():
    return {"message": "服务正在运行"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

