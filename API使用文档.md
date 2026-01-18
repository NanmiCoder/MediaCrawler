# 📡 MediaCrawler API 使用文档

## 🎯 概述

MediaCrawler API 是一个统一的 REST API 服务，支持：
- ✅ **抖音 (dy)** - 短视频、用户、评论
- ✅ **小红书 (xhs)** - 笔记、用户、评论
- ✅ **知乎 (zhihu)** - 问答、用户、评论

---

## 🚀 启动 API 服务

### 方法 1: 直接启动
```bash
cd /Users/kangbing/112/pythontest/tiktok/test_projects/MediaCrawler
source venv/bin/activate
python api_server.py
```

### 方法 2: 使用启动脚本
```bash
cd /Users/kangbing/112/pythontest/tiktok/test_projects/MediaCrawler
./start_api.sh
```

启动后访问：
- 🌐 API 文档: http://localhost:8080/docs
- 📊 API 首页: http://localhost:8080/

---

## 📡 API 端点

### 1. 获取支持的平台

**请求**:
```bash
GET http://localhost:8080/api/platforms
```

**响应示例**:
```json
{
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
```

---

### 2. 创建搜索任务

**请求**:
```bash
POST http://localhost:8080/api/search
Content-Type: application/json

{
  "platform": "dy",
  "keyword": "美食教程",
  "max_count": 10,
  "enable_comments": true,
  "enable_media": false
}
```

**参数说明**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| platform | string | 是 | 平台代码: dy(抖音), xhs(小红书), zhihu(知乎) |
| keyword | string | 是 | 搜索关键词 |
| max_count | integer | 否 | 最大采集数量，默认10，范围1-50 |
| enable_comments | boolean | 否 | 是否采集评论，默认true |
| enable_media | boolean | 否 | 是否下载媒体文件，默认false |

**响应示例**:
```json
{
  "task_id": "dy_20260118113000_abc123",
  "status": "pending",
  "message": "任务已创建，正在后台执行。使用 GET /api/task/dy_20260118113000_abc123 查询进度",
  "data": null
}
```

---

### 3. 查询任务状态

**请求**:
```bash
GET http://localhost:8080/api/task/{task_id}
```

**响应示例**:
```json
{
  "task_id": "dy_20260118113000_abc123",
  "status": "running",
  "progress": "正在采集数据...",
  "result_file": null,
  "error": null
}
```

**状态说明**:
- `pending` - 等待执行
- `running` - 正在执行
- `completed` - 已完成
- `failed` - 执行失败

---

### 4. 获取任务结果

**请求**:
```bash
GET http://localhost:8080/api/task/{task_id}/result
```

**响应示例**:
```json
{
  "task_id": "dy_20260118113000_abc123",
  "status": "completed",
  "platform": "dy",
  "keyword": "美食教程",
  "data": {
    "total": 10,
    "keyword": "美食教程",
    "platform": "dy",
    "file_path": "data/dy/json/search_contents_2026-01-18.json",
    "items": [
      {
        "aweme_id": "7563156848669478184",
        "title": "只用3种食材，就能解锁一锅下饭硬菜",
        "nickname": "日食记",
        "user_id": "64117131714",
        "liked_count": "1386088",
        "comment_count": "16379",
        "aweme_url": "https://www.douyin.com/video/7563156848669478184"
      }
    ]
  },
  "result_file": "data/dy/json/search_contents_2026-01-18.json"
}
```

---

### 5. 获取所有任务列表

**请求**:
```bash
GET http://localhost:8080/api/tasks
```

**响应示例**:
```json
{
  "total": 3,
  "tasks": [
    {
      "task_id": "dy_20260118113000_abc123",
      "platform": "dy",
      "keyword": "美食教程",
      "status": "completed",
      "created_at": "2026-01-18T11:30:00"
    }
  ]
}
```

---

### 6. 删除任务

**请求**:
```bash
DELETE http://localhost:8080/api/task/{task_id}
```

**响应示例**:
```json
{
  "message": "任务 dy_20260118113000_abc123 已删除"
}
```

---

## 💻 使用示例

### Python 示例

```python
import requests
import time

# API 基础URL
BASE_URL = "http://localhost:8080"

# 1. 创建搜索任务
response = requests.post(f"{BASE_URL}/api/search", json={
    "platform": "dy",
    "keyword": "美食教程",
    "max_count": 10,
    "enable_comments": True,
    "enable_media": False
})

task_id = response.json()["task_id"]
print(f"任务ID: {task_id}")

# 2. 轮询查询任务状态
while True:
    response = requests.get(f"{BASE_URL}/api/task/{task_id}")
    status_data = response.json()

    print(f"状态: {status_data['status']}, 进度: {status_data.get('progress')}")

    if status_data["status"] == "completed":
        print("任务完成！")
        break
    elif status_data["status"] == "failed":
        print(f"任务失败: {status_data.get('error')}")
        break

    time.sleep(5)  # 每5秒查询一次

# 3. 获取结果
response = requests.get(f"{BASE_URL}/api/task/{task_id}/result")
result = response.json()
print(f"采集到 {result['data']['total']} 条数据")
print(f"数据文件: {result['result_file']}")
```

---

### cURL 示例

#### 创建任务（抖音）
```bash
curl -X POST "http://localhost:8080/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "dy",
    "keyword": "美食教程",
    "max_count": 10,
    "enable_comments": true,
    "enable_media": false
  }'
```

#### 创建任务（小红书）
```bash
curl -X POST "http://localhost:8080/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "xhs",
    "keyword": "美妆教程",
    "max_count": 10,
    "enable_comments": true,
    "enable_media": false
  }'
```

#### 创建任务（知乎）
```bash
curl -X POST "http://localhost:8080/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "zhihu",
    "keyword": "Python教程",
    "max_count": 10,
    "enable_comments": true,
    "enable_media": false
  }'
```

#### 查询任务状态
```bash
curl "http://localhost:8080/api/task/dy_20260118113000_abc123"
```

#### 获取任务结果
```bash
curl "http://localhost:8080/api/task/dy_20260118113000_abc123/result"
```

---

### JavaScript/Node.js 示例

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8080';

async function searchDouyin(keyword) {
  // 1. 创建任务
  const createResponse = await axios.post(`${BASE_URL}/api/search`, {
    platform: 'dy',
    keyword: keyword,
    max_count: 10,
    enable_comments: true,
    enable_media: false
  });

  const taskId = createResponse.data.task_id;
  console.log(`任务ID: ${taskId}`);

  // 2. 等待任务完成
  while (true) {
    const statusResponse = await axios.get(`${BASE_URL}/api/task/${taskId}`);
    const status = statusResponse.data;

    console.log(`状态: ${status.status}, 进度: ${status.progress || ''}`);

    if (status.status === 'completed') {
      break;
    } else if (status.status === 'failed') {
      throw new Error(`任务失败: ${status.error}`);
    }

    await new Promise(resolve => setTimeout(resolve, 5000));
  }

  // 3. 获取结果
  const resultResponse = await axios.get(`${BASE_URL}/api/task/${taskId}/result`);
  return resultResponse.data;
}

// 使用示例
searchDouyin('美食教程').then(result => {
  console.log(`采集到 ${result.data.total} 条数据`);
  console.log(result.data.items);
}).catch(error => {
  console.error('错误:', error.message);
});
```

---

## 🎨 平台配置

### 小红书配置

小红书需要单独配置 Cookie：

1. 在本地浏览器访问 https://www.xiaohongshu.com
2. 登录账号
3. F12 → Console → 执行 `document.cookie`
4. 将 Cookie 配置到 `config/base_config.py`:

```python
# 小红书 Cookie
XHS_COOKIES = "你的小红书Cookie"
```

### 知乎配置

知乎同样需要配置 Cookie：

1. 在本地浏览器访问 https://www.zhihu.com
2. 登录账号
3. F12 → Console → 执行 `document.cookie`
4. 将 Cookie 配置到 `config/base_config.py`:

```python
# 知乎 Cookie
ZHIHU_COOKIES = "你的知乎Cookie"
```

---

## 📊 数据格式

### 抖音数据格式
```json
{
  "aweme_id": "7563156848669478184",
  "title": "视频标题",
  "nickname": "用户昵称",
  "user_id": "用户ID",
  "sec_uid": "安全用户ID",
  "avatar": "用户头像URL",
  "liked_count": "点赞数",
  "comment_count": "评论数",
  "collected_count": "收藏数",
  "share_count": "分享数",
  "aweme_url": "视频链接",
  "video_download_url": "视频下载链接",
  "cover_url": "封面图链接"
}
```

### 小红书数据格式
```json
{
  "note_id": "笔记ID",
  "title": "笔记标题",
  "desc": "笔记描述",
  "user_id": "用户ID",
  "nickname": "用户昵称",
  "avatar": "用户头像URL",
  "liked_count": "点赞数",
  "collected_count": "收藏数",
  "comment_count": "评论数",
  "share_count": "分享数",
  "note_url": "笔记链接",
  "image_list": ["图片URL列表"]
}
```

### 知乎数据格式
```json
{
  "question_id": "问题ID",
  "title": "问题标题",
  "answer_id": "回答ID",
  "content": "回答内容",
  "author_id": "作者ID",
  "author_name": "作者昵称",
  "voteup_count": "赞同数",
  "comment_count": "评论数",
  "created_time": "创建时间",
  "question_url": "问题链接",
  "answer_url": "回答链接"
}
```

---

## 🔧 高级配置

### 修改 API 端口
编辑 `api_server.py` 最后一行：
```python
uvicorn.run(
    "api_server:app",
    host="0.0.0.0",
    port=8080,  # 修改端口号
    reload=True
)
```

### 后台运行
```bash
nohup python api_server.py > api.log 2>&1 &
```

### 使用 PM2 管理（推荐）
```bash
# 安装 PM2
npm install -g pm2

# 启动 API 服务
pm2 start api_server.py --interpreter python --name mediacrawler-api

# 查看状态
pm2 status

# 查看日志
pm2 logs mediacrawler-api

# 停止服务
pm2 stop mediacrawler-api

# 重启服务
pm2 restart mediacrawler-api
```

---

## ⚠️ 注意事项

1. **Cookie 有效期**
   - Cookie 通常几周到几个月后会过期
   - 过期后需要重新获取并更新配置

2. **频率限制**
   - 避免频繁调用 API
   - 建议每次采集间隔 10-30 分钟
   - 单次采集数量建议不超过 50

3. **资源占用**
   - 每个任务会启动浏览器，占用较多资源
   - 建议同时运行的任务不超过 3 个
   - 如果不需要媒体文件，设置 `enable_media=false` 可加快速度

4. **数据存储**
   - 数据默认保存在 `data/{platform}/json/` 目录
   - 定期清理旧数据以节省磁盘空间
   - 重要数据建议导入数据库

---

## 🐛 常见问题

### Q1: API 启动失败
**解决**:
```bash
# 检查端口是否被占用
lsof -i:8080

# 杀掉占用端口的进程
kill -9 <PID>

# 或修改 API 端口
```

### Q2: 任务一直处于 pending 状态
**解决**:
- 检查 Cookie 是否配置正确
- 查看 API 日志是否有错误信息
- 尝试手动运行 `python main.py` 确认配置正确

### Q3: 数据采集失败
**解决**:
- 检查网络连接
- 确认 Cookie 是否有效
- 查看平台是否有反爬虫限制

---

## 📞 支持

- 📖 完整文档: `最终使用指南.md`
- 🔧 配置文件: `config/base_config.py`
- 📊 项目路径: `/Users/kangbing/112/pythontest/tiktok/test_projects/MediaCrawler`

---

## 🎉 总结

MediaCrawler API 提供了：
- ✅ 统一的 REST API 接口
- ✅ 支持抖音、小红书、知乎
- ✅ 异步任务处理
- ✅ 自动生成文档
- ✅ 简单易用的接口设计

**立即开始使用：**
```bash
python api_server.py
```

然后访问 http://localhost:8080/docs 查看交互式 API 文档！
