# MediaCrawler API服务器使用说明

## 概述

MediaCrawler API服务器是一个基于FastAPI构建的RESTful API服务，提供了对多个社交媒体平台的数据爬取功能。支持同步和异步两种爬取模式，并提供完整的任务管理功能。

## 快速开始

### 1. 启动服务器

#### 方式一：使用Python直接启动
```bash
# 进入api_server目录
cd api_server

# 启动服务器（默认配置）
python api.py

# 或使用uv运行
uv run python api.py
```

#### 方式二：使用命令行参数
```bash
# 自定义主机和端口
python api.py --host 0.0.0.0 --port 8080

# 启用调试模式
python api.py --debug

# 禁用热重载
python api.py --no-reload
```

#### 方式三：使用环境变量
```bash
# 设置环境变量
export API_HOST=0.0.0.0
export API_PORT=8080
export API_DEBUG=true
export API_RELOAD=false

# 启动服务器
python api.py
```

### 2. 访问API文档

服务器启动后，可以通过以下地址访问API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 配置说明

### 服务器配置

| 配置项 | 环境变量 | 命令行参数 | 默认值 | 说明 |
|--------|----------|------------|--------|---------|
| 主机地址 | `API_HOST` | `--host` | `0.0.0.0` | 服务器绑定的IP地址 |
| 端口号 | `API_PORT` | `--port` | `8000` | 服务器监听端口 |
| 热重载 | `API_RELOAD` | `--no-reload` | `true` | 开发模式下的热重载 |
| 调试模式 | `API_DEBUG` | `--debug` | `false` | 启用详细日志输出 |

### 配置优先级

1. 命令行参数（最高优先级）
2. 环境变量
3. 默认值（最低优先级）

## API接口说明

### 基础接口

#### 1. 健康检查
```http
GET /health
```

**响应示例：**
```json
{
  "success": true,
  "message": "API服务器运行正常",
  "timestamp": "2024-01-01T12:00:00",
  "version": "1.0.0"
}
```

#### 2. 根路径
```http
GET /
```

**响应示例：**
```json
{
  "message": "MediaCrawler API Server",
  "version": "1.0.0",
  "docs_url": "/docs",
  "redoc_url": "/redoc"
}
```

#### 3. 获取支持的平台
```http
GET /crawler/platforms
```

**响应示例：**
```json
{
  "success": true,
  "message": "获取支持平台列表成功",
  "data": [
    {
      "value": "xhs",
      "label": "小红书",
      "description": "小红书平台数据采集"
    },
    {
      "value": "dy",
      "label": "抖音",
      "description": "抖音平台数据采集"
    },
    {
      "value": "bili",
      "label": "B站",
      "description": "哔哩哔哩平台数据采集"
    }
  ]
}
```

### 爬虫任务接口

#### 1. 同步执行爬虫任务
```http
POST /crawler/run
```

**请求参数：**
```json
{
  "platform": "bili",
  "crawler_type": "search",
  "keywords": "大胃袋",
  "max_notes": 10,
  "save_data_option": "json",
  "cookies": "your_cookies_here",
  "start_page": 1,
  "enable_login": false
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "爬虫任务执行成功",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "data": {
    "total_count": 10,
    "results": [...]
  }
}
```

#### 2. 异步执行爬虫任务
```http
POST /crawler/run-async
```

**请求参数：** 与同步接口相同

**响应示例：**
```json
{
  "success": true,
  "message": "爬虫任务已提交，正在后台执行",
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

#### 3. 查询任务状态
```http
GET /crawler/task/{task_id}
```

**响应示例：**
```json
{
  "success": true,
  "message": "获取任务状态成功",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "data": {
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "completed",
    "platform": "bili",
    "crawler_type": "search",
    "keywords": "大胃袋",
    "created_at": "2024-01-01T12:00:00",
    "completed_at": "2024-01-01T12:05:00",
    "result_data": {...}
  }
}
```

#### 4. 获取任务列表
```http
GET /crawler/tasks?limit=50&offset=0
```

**查询参数：**
- `limit`: 返回任务数量限制（默认50）
- `offset`: 偏移量（默认0）

**响应示例：**
```json
{
  "success": true,
  "message": "获取任务列表成功",
  "data": [
    {
      "task_id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "completed",
      "platform": "bili",
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "total": 1
}
```

#### 5. 取消/删除任务
```http
DELETE /crawler/task/{task_id}
```

**响应示例：**
```json
{
  "success": true,
  "message": "任务已取消"
}
```

## 请求参数详解

### CrawlerRequest 模型

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|---------|
| `platform` | string | 是 | - | 平台类型（xhs/dy/ks/bili/wb/tieba/zhihu） |
| `crawler_type` | string | 是 | - | 爬取类型（search/detail/creator） |
| `keywords` | string | 是 | - | 搜索关键词 |
| `max_notes` | integer | 否 | 10 | 最大爬取数量 |
| `save_data_option` | string | 否 | json | 数据保存格式（json/csv/db） |
| `cookies` | string | 否 | "" | 用户Cookie |
| `start_page` | integer | 否 | 1 | 起始页码 |
| `enable_login` | boolean | 否 | false | 是否启用登录 |

### 平台支持

| 平台代码 | 平台名称 | 支持的爬取类型 |
|----------|----------|----------------|
| `xhs` | 小红书 | search, detail, creator |
| `dy` | 抖音 | search, detail, creator |
| `ks` | 快手 | search, detail, creator |
| `bili` | B站 | search, detail, creator |
| `wb` | 微博 | search, detail, creator |
| `tieba` | 贴吧 | search, detail |
| `zhihu` | 知乎 | search, detail, creator |

### 任务状态

| 状态 | 说明 |
|------|------|
| `pending` | 任务已创建，等待执行 |
| `running` | 任务正在执行中 |
| `completed` | 任务执行完成 |
| `failed` | 任务执行失败 |
| `cancelled` | 任务被取消 |

## 使用示例

### Python 示例

```python
import httpx
import asyncio

class MediaCrawlerAPI:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def run_async_crawler(self, platform, keywords, max_notes=10):
        """异步执行爬虫任务"""
        data = {
            "platform": platform,
            "crawler_type": "search",
            "keywords": keywords,
            "max_notes": max_notes,
            "save_data_option": "json"
        }
        
        response = await self.client.post(
            f"{self.base_url}/crawler/run-async",
            json=data
        )
        return response.json()
    
    async def get_task_status(self, task_id):
        """获取任务状态"""
        response = await self.client.get(
            f"{self.base_url}/crawler/task/{task_id}"
        )
        return response.json()
    
    async def wait_for_completion(self, task_id, timeout=300):
        """等待任务完成"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = await self.get_task_status(task_id)
            status = result["data"]["status"]
            
            if status in ["completed", "failed", "cancelled"]:
                return result
            
            await asyncio.sleep(2)
        
        raise TimeoutError("任务执行超时")

# 使用示例
async def main():
    api = MediaCrawlerAPI()
    
    # 提交异步任务
    result = await api.run_async_crawler(
        platform="bili",
        keywords="大胃袋",
        max_notes=20
    )
    
    task_id = result["task_id"]
    print(f"任务已提交，ID: {task_id}")
    
    # 等待任务完成
    final_result = await api.wait_for_completion(task_id)
    print(f"任务完成，状态: {final_result['data']['status']}")
    
    await api.client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
```

### JavaScript 示例

```javascript
class MediaCrawlerAPI {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async runAsyncCrawler(platform, keywords, maxNotes = 10) {
        const response = await fetch(`${this.baseUrl}/crawler/run-async`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                platform,
                crawler_type: 'search',
                keywords,
                max_notes: maxNotes,
                save_data_option: 'json'
            })
        });
        
        return await response.json();
    }
    
    async getTaskStatus(taskId) {
        const response = await fetch(`${this.baseUrl}/crawler/task/${taskId}`);
        return await response.json();
    }
    
    async waitForCompletion(taskId, timeout = 300000) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < timeout) {
            const result = await this.getTaskStatus(taskId);
            const status = result.data.status;
            
            if (['completed', 'failed', 'cancelled'].includes(status)) {
                return result;
            }
            
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        
        throw new Error('任务执行超时');
    }
}

// 使用示例
async function main() {
    const api = new MediaCrawlerAPI();
    
    try {
        // 提交异步任务
        const result = await api.runAsyncCrawler('bili', '大胃袋', 20);
        const taskId = result.task_id;
        console.log(`任务已提交，ID: ${taskId}`);
        
        // 等待任务完成
        const finalResult = await api.waitForCompletion(taskId);
        console.log(`任务完成，状态: ${finalResult.data.status}`);
        
    } catch (error) {
        console.error('错误:', error.message);
    }
}

main();
```

## 错误处理

### 常见错误码

| 状态码 | 错误类型 | 说明 |
|--------|----------|------|
| 400 | Bad Request | 请求参数错误 |
| 404 | Not Found | 资源不存在（如任务ID不存在） |
| 422 | Validation Error | 数据验证失败 |
| 500 | Internal Server Error | 服务器内部错误 |

### 错误响应格式

```json
{
  "success": false,
  "message": "错误描述",
  "timestamp": "2024-01-01T12:00:00"
}
```

## 性能优化建议

### 1. 合理设置爬取数量
- 建议单次爬取数量不超过100条
- 大量数据建议分批次爬取

### 2. 使用异步接口
- 对于耗时较长的任务，建议使用异步接口
- 通过轮询方式获取任务状态

### 3. Cookie管理
- 提供有效的Cookie可以提高爬取成功率
- 定期更新Cookie以避免失效

### 4. 错误重试
- 实现自动重试机制
- 对于网络错误，建议指数退避重试

## 部署说明

### 生产环境部署

```bash
# 使用Gunicorn部署
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 或使用Docker
docker build -t mediacrawler-api .
docker run -p 8000:8000 mediacrawler-api
```

### 环境变量配置

```bash
# .env 文件
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false
API_RELOAD=false
```

## 注意事项

1. **合规使用**: 请遵守各平台的使用条款和robots.txt规则
2. **频率限制**: 避免过于频繁的请求，以免被平台限制
3. **数据隐私**: 妥善处理爬取的数据，保护用户隐私
4. **Cookie安全**: 不要在日志中记录敏感的Cookie信息
5. **资源管理**: 及时清理不需要的任务记录，避免内存泄漏

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持7个主流社交媒体平台
- 提供同步和异步两种爬取模式
- 完整的任务管理功能
- 自动生成API文档

## 技术支持

如果在使用过程中遇到问题，请：

1. 查看API文档：http://localhost:8000/docs
2. 检查服务器日志
3. 提交Issue到项目仓库
4. 联系开发团队

---

**MediaCrawler API服务器** - 让数据采集变得简单高效！