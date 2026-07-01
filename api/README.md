# 抖音采集工具 API

抖音关键词批量采集工具的 RESTful API 服务。

## 快速启动

```bash
# 1. 安装依赖
pip install -r api/requirements.txt
pip install -e .

# 2. 启动服务（宿主机开发端口）
uvicorn api.main:app --host 127.0.0.1 --port 18080

# 3. 访问文档
# http://localhost:18080/docs
```

Docker/compose 部署时，容器内部 API 端口保持 `8000`，宿主访问端口固定为 `18080`。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DY_API_HOST` | `127.0.0.1` | 本机直启监听地址；Compose 覆盖为容器内 `0.0.0.0` |
| `DY_API_PORT` | `8000` | 容器内部监听端口 |
| `DY_API_PUBLIC_PORT` | `18080` | 宿主访问端口 |
| `DY_API_BASE_URL` | `http://localhost:18080` | 宿主 API 访问地址 |
| `DY_API_KEY` / `API_KEY` | 空 | 非空时启用 API Key 鉴权；优先读取 `DY_API_KEY` |
| `DY_API_AUTH_REQUIRED` | `0` | 为 `1` 且未配置密钥时拒绝启动；Compose 固定为 `1` |
| `DY_WORKSPACE_DIR` | `./workspaces` | 工作目录 |
| `DY_CHROME_PORT` | `19222` | 宿主 Chrome CDP 端口 |
| `DY_CHROME_CDP_URL` | `http://localhost:19222` | 宿主 Chrome CDP 地址 |
| `WEB_DEV_PORT` | `15173` | 前端开发服务端口 |
| `VITE_API_BASE_URL` | `http://localhost:18080` | 前端 API 地址 |
| `VITE_WS_BASE_URL` | `ws://localhost:18080` | 前端 WebSocket 地址 |
| `DY_LOG_LEVEL` | `INFO` | 日志级别 |
| `DY_CORS_ALLOW_ORIGINS` / `CORS_ALLOW_ORIGINS` | 四个本地来源 | 逗号分隔的 CORS 来源；兼容旧名 `DY_CORS_ORIGINS` |
| `DY_RELOAD` | `0` | 开发热重载 |

## API Key 鉴权

生产或局域网部署时应配置一个长随机密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

将生成值写入 `.env`：

```dotenv
DY_API_KEY=<生成的随机密钥>
DY_API_AUTH_REQUIRED=1
```

- REST API 通过 `X-API-Key` 请求头传递密钥。
- WebUI 可在“设置”页面保存同一个密钥。
- WebSocket 使用子协议传递密钥，避免密钥出现在 URL 和访问日志中。
- `/`、`/health`、`/docs`、`/redoc`、`/openapi.json` 和 `/ui/` 保持公开。
- `DY_API_KEY` 为空时鉴权关闭，仅适合可信的本机开发环境。
- Docker Compose 默认要求密钥；未设置 `DY_API_KEY` 时容器会拒绝启动。

## CORS 安全默认值

未配置 CORS 环境变量时，仅允许：

```text
http://localhost:15173
http://127.0.0.1:15173
http://localhost:18080
http://127.0.0.1:18080
```

增加其他可信前端来源时使用逗号分隔：

```dotenv
DY_CORS_ALLOW_ORIGINS=https://crawler.example.com,https://admin.example.com
```

只有在可信的临时开发环境中才可显式设置：

```dotenv
CORS_ALLOW_ORIGINS=*
```

服务会记录风险警告。生产、局域网共享或公网部署不建议使用通配符来源。

> 安全提示：如果本地 `.env` 曾保存非空 LLM/API Key，建议轮换这些密钥，并在部署环境中改用 Docker/Kubernetes secret 或其他 secret 注入机制。

## API 端点

### 采集操作

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/scrape/search` | 搜索采集 |
| POST | `/scrape/comments` | 评论采集 |
| POST | `/scrape/scripts` | 文案提取 |
| POST | `/scrape/merge` | 合并 CSV |
| POST | `/scrape/run-all` | 一键执行 |
| POST | `/scrape/reset` | 重置步骤 |

### Content Asset task-id 模式

`POST /scrape/merge` 提供 `search_task_id` 时，会读取已完成任务的标准输出，并在新的 merge task workspace 中生成 `content_asset.jsonl` 和 `content_asset.csv`。

```json
{
  "search_task_id": "<search_task_id>",
  "comments_task_id": "<comments_task_id>",
  "scripts_task_id": "<scripts_task_id>"
}
```

- `search_task_id` 必需。
- `comments_task_id`、`scripts_task_id` 可选。
- merge 响应返回的 `task_id` 用于 status、result、preview 和 export。
- 没有评论或 scripts task 时仍可生成资产表，并通过状态字段标记缺失或 pending。

### 任务管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/scrape/status/{task_id}` | 查询任务状态 |
| GET | `/scrape/result/{task_id}` | 下载结果文件 |
| GET | `/scrape/tasks` | 列出所有任务 |
| DELETE | `/scrape/tasks/{task_id}` | 删除任务及受管 workspace；校验 task_id 和路径边界 |
| POST | `/scrape/cleanup` | 清理过期任务记录 |

### 数据预览与导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/scrape/data/preview/{task_id}` | 预览与 result 相同的主结果文件 |
| GET | `/scrape/data/export?task_id={task_id}` | 原样下载主结果文件，保留 content_asset 完整 schema 和 BOM |
| POST | `/scrape/data/export` | 批量归一化导出旧七字段 CSV/TXT |

merge task 的主结果优先级为 `content_asset.csv`、`content_asset.jsonl`、旧合并 CSV。`GET /scrape/result/{task_id}`、preview 和 GET export 共用主结果选择语义。

POST export 保持旧七字段兼容契约：

```text
video_id
platform
script_text
likes
favorites
shares
comments
```

它不是 content_asset 完整字段导出。完整字段、状态枚举、fallback 边界和验收命令见 [Content Asset 数据字典与验收说明](../docs/CONTENT_ASSET.md)。

### 系统

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/` | 根路径 |
| GET | `/docs` | OpenAPI 文档 |

## 使用示例

```bash
# 1. 搜索采集
curl -X POST http://localhost:18080/scrape/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $DY_API_KEY" \
  -d '{"keywords": ["短视频运营", "抖音带货"], "max_count": 20}'

# 返回: {"task_id": "a1b2c3d4e5f6", "status": "submitted", "type": "search"}

# 2. 查询状态
curl -H "X-API-Key: $DY_API_KEY" \
  http://localhost:18080/scrape/status/a1b2c3d4e5f6

# 3. 下载结果
curl -H "X-API-Key: $DY_API_KEY" \
  -O http://localhost:18080/scrape/result/a1b2c3d4e5f6

# 4. 预览主结果
curl -H "X-API-Key: $DY_API_KEY" \
  "http://localhost:18080/scrape/data/preview/a1b2c3d4e5f6?limit=20"

# 5. 原样导出主结果
curl -H "X-API-Key: $DY_API_KEY" \
  -o content_asset.csv \
  "http://localhost:18080/scrape/data/export?task_id=a1b2c3d4e5f6"

# 6. 健康检查
curl http://localhost:18080/health
```

## systemd 部署（Linux）

```bash
# 自动化部署
chmod +x api/deploy.sh
sudo ./api/deploy.sh

# 手动部署
sudo cp api/douyin-scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable douyin-scraper
sudo systemctl start douyin-scraper

# 查看日志
sudo journalctl -u douyin-scraper -f
```

## Windows 部署

```powershell
# 使用 NSSM 注册为 Windows 服务
nssm install DouyinScraper "C:\path\to\python.exe" "-m" "uvicorn" "api.main:app" "--host" "0.0.0.0" "--port" "18080"
nssm start DouyinScraper
```

## 错误码

| 退出码 | HTTP 状态码 | 含义 |
|--------|------------|------|
| 1 | 503 | 可重试错误（网络超时、HTTP 5xx） |
| 2 | 400 | 不可重试错误（配置错误、参数无效） |
| 3 | 500 | 致命错误（磁盘满、内存不足） |
