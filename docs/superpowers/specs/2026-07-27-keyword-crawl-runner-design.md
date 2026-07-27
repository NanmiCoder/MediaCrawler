# 小红书关键词自动采集队列设计

> 日期：2026-07-27
>
> 状态：已确认，待实施

## 1. 目标

新增一个独立的关键词队列程序，读取《首批可立即使用的搜索词.md》中“建议首先执行的20个词”，逐个调用 MediaCrawler 本地 API 完成小红书公开笔记采集。

程序必须在每个关键词完成后持久化进度。中途失败或程序重启后，不重复提交已经成功的关键词，并能继续处理未完成项。

本阶段采用以下固定配置：

- 平台：小红书。
- 类型：关键词搜索。
- 登录方式：二维码或现有 Chrome 登录态。
- 每个关键词：请求20条笔记。
- 一级评论：关闭。
- 二级评论：关闭。
- 保存格式：JSON。
- 关键词失败：记录后继续下一个。

## 2. 非目标

本阶段不实现：

- AI 内容筛选。
- 作者 ID 提取或创作者模式采集。
- 数据库存储。
- WebUI 队列管理页面。
- Windows 服务、定时任务或常驻调度器。
- 全量运行词表中的其他批次。
- 评论、图片或视频采集。
- 自动修改、扩展或组合搜索词。

## 3. 目录

新增独立目录：

```text
D:\red_note_rich_search\keyword_crawl_runner
├── run_keywords.py
├── crawl_progress.json
└── README.md
```

`run_keywords.py` 使用 Python 标准库调用本机 HTTP API，不引入新的第三方依赖。

`crawl_progress.json` 为运行时状态文件，不应提交 Git。首次运行时自动创建。

## 4. 输入词表解析

默认输入文件：

```text
C:\Users\15377\Documents\民生银行课题\首批可立即使用的搜索词.md
```

程序只读取二级标题：

```text
## 建议首先执行的20个词
```

并只解析该标题下紧随的 `text` 代码块。后续章节不在本阶段处理。

解析规则：

1. 去除每行首尾空白。
2. 忽略空行。
3. 按首次出现顺序去重。
4. 最终必须恰好得到20个关键词。
5. 标题不存在、代码块格式错误或结果不是20个时立即退出，不启动爬虫。

程序为解析出的有序关键词列表计算 SHA-256 摘要，并写入进度文件。以后启动时若摘要变化，程序必须停止并提示用户确认，不得把旧进度错误套用到新词表。

## 5. API 调用

默认 API 地址：

```text
http://127.0.0.1:8080/api
```

程序启动时先调用：

```text
GET /crawler/status
```

确认后端在线。每个关键词使用一次：

```text
POST /crawler/start
```

请求体固定为：

```json
{
  "platform": "xhs",
  "login_type": "qrcode",
  "crawler_type": "search",
  "keywords": "当前关键词",
  "start_page": 1,
  "enable_comments": false,
  "enable_sub_comments": false,
  "save_option": "json",
  "cookies": "",
  "headless": false,
  "max_notes_count": 20
}
```

提交后每2秒调用一次 `GET /crawler/status`，直到对应任务结束。一个关键词结束后等待5秒，再提交下一个关键词。

程序不得并发启动多个关键词任务。

## 6. API 状态增强

当前 MediaCrawler 在子进程结束后只暴露 `status="idle"`，无法区分成功与失败。为支持可靠断点续跑，需要给现有状态增加：

| 字段 | 含义 |
|---|---|
| `task_id` | 当前或最近一次任务的 UUID |
| `last_exit_code` | 最近一次子进程退出码；运行中为 `null` |
| `finished_at` | 最近一次任务结束时间；运行中为 `null` |

`POST /crawler/start` 成功响应同时返回本次 `task_id`：

```json
{
  "status": "ok",
  "message": "Crawler started successfully",
  "task_id": "UUID"
}
```

`GET /crawler/status` 示例：

```json
{
  "status": "idle",
  "platform": null,
  "crawler_type": null,
  "started_at": "2026-07-27T10:00:00+08:00",
  "error_message": null,
  "task_id": "UUID",
  "last_exit_code": 0,
  "finished_at": "2026-07-27T10:02:00+08:00"
}
```

任务开始时，服务生成新的 `task_id`，并将 `last_exit_code`、`finished_at` 清空。子进程结束后记录退出码和结束时间。

API 重启后不要求保留历史任务结果。跨 API 重启的不确定任务由队列程序标记为 `needs_review`。

## 7. 进度状态

`crawl_progress.json` 示例：

```json
{
  "source_file": "C:\\Users\\15377\\Documents\\民生银行课题\\首批可立即使用的搜索词.md",
  "keywords_sha256": "词表摘要",
  "created_at": "2026-07-27T10:00:00+08:00",
  "updated_at": "2026-07-27T10:02:00+08:00",
  "keywords": [
    {
      "keyword": "重庆企业主资产配置",
      "status": "succeeded",
      "attempts": 1,
      "task_id": "UUID",
      "started_at": "2026-07-27T10:00:00+08:00",
      "finished_at": "2026-07-27T10:02:00+08:00",
      "exit_code": 0,
      "error": null
    },
    {
      "keyword": "重庆公私资产隔离",
      "status": "failed",
      "attempts": 1,
      "task_id": "UUID",
      "started_at": "2026-07-27T10:03:00+08:00",
      "finished_at": "2026-07-27T10:04:00+08:00",
      "exit_code": 1,
      "error": "crawler exited with code 1"
    }
  ]
}
```

允许的关键词状态：

- `pending`：尚未提交。
- `running`：已提交，等待 API 结果。
- `succeeded`：对应任务退出码为0。
- `failed`：对应任务明确返回非零退出码或启动失败。
- `needs_review`：无法判断上次任务是否完成，禁止自动重跑。

每次状态变化后立即保存进度文件。保存采用同目录临时文件加原子替换，避免中断产生半写入 JSON。

## 8. 首次运行、继续与重试

### 8.1 首次运行

1. 解析并验证20个关键词。
2. 创建全部为 `pending` 的进度文件。
3. 确认 API 在线且当前没有其他爬虫任务。
4. 从第一个关键词开始逐个运行。

如果 API 已有非本程序提交的任务，程序停止并提示用户，不接管、不终止该任务。

### 8.2 中断后继续

重新启动时：

- 跳过 `succeeded`。
- 继续处理 `pending`。
- `failed` 默认不在同一轮立即循环重试，留到后续重试模式。
- 对 `running` 比较进度文件和 API 返回的 `task_id`。

当 `running` 的 `task_id` 与 API 相同：

- API 仍在运行：继续等待。
- API 已结束：根据 `last_exit_code` 补记为 `succeeded` 或 `failed`。

当 API 不在线、已重启或 `task_id` 不匹配时，将该关键词标记为 `needs_review`，避免自动重复爬取。

### 8.3 重试失败项

提供显式参数：

```powershell
--retry-failed
```

该模式只把 `failed` 重置为 `pending`，仍然跳过 `succeeded` 和 `needs_review`。每次提交前增加 `attempts`。

`needs_review` 必须由用户检查数据后手工改为 `succeeded` 或 `failed`，程序不自动猜测。

## 9. 数据输出与重复控制

MediaCrawler 继续按现有逻辑把笔记写入：

```text
D:\red_note_rich_search\MediaCrawler\data\xhs\json
```

每条记录已有 `source_keyword`，可以追溯到原始搜索词。

队列程序通过不重复提交 `succeeded` 关键词，避免整词重复采集。明确失败的任务可能已经写入部分笔记，重试后可能产生重复记录。本阶段不修改 MediaCrawler 的 JSON 写入器；后续 AI 粗筛前按 `(note_id, source_keyword)` 去重。

## 10. 控制台输出

程序运行时输出紧凑进度：

```text
[3/20] 开始：重庆公司分红资金安排
[3/20] 成功：退出码 0，用时 82 秒
[4/20] 开始：重庆股权退出资产配置
[4/20] 失败：退出码 1，继续下一项
```

结束时汇总：

```text
成功 18，失败 2，待处理 0，需要人工确认 0
```

不在控制台重复打印完整爬虫日志。详细日志继续通过 MediaCrawler WebUI 或 `/api/crawler/logs` 查看。

## 11. 错误处理

以下错误立即停止队列，已保存进度不丢失：

- 词表文件不存在或格式不符合约定。
- 词表摘要与已有进度不一致。
- MediaCrawler API 不在线。
- API 已有其他任务运行。
- 进度文件损坏或不可写。
- API 返回无法解析的数据。

以下错误记录当前关键词失败后继续：

- `/crawler/start` 对当前关键词返回服务端错误。
- 子进程退出码非0。
- 单个任务明确报告爬取失败。

网络超时不得直接判定任务失败。程序先查询状态；若仍无法确认，则保存为 `needs_review` 并停止，避免重复提交。

## 12. 命令行接口

默认运行：

```powershell
cd D:\red_note_rich_search\MediaCrawler

uv run python `
  ..\keyword_crawl_runner\run_keywords.py `
  --source "C:\Users\15377\Documents\民生银行课题\首批可立即使用的搜索词.md"
```

重试明确失败项：

```powershell
uv run python `
  ..\keyword_crawl_runner\run_keywords.py `
  --source "C:\Users\15377\Documents\民生银行课题\首批可立即使用的搜索词.md" `
  --retry-failed
```

可选参数仅包括：

- `--source`：词表路径。
- `--api-base`：本地 API 基础地址，默认 `http://127.0.0.1:8080/api`。
- `--progress`：进度文件路径，默认使用程序目录下的 `crawl_progress.json`。
- `--retry-failed`：重试明确失败项。

不为当前固定研究流程增加通用平台、评论、并发或保存格式参数。

## 13. 测试与验收

自动化测试至少覆盖：

1. 只解析“建议首先执行的20个词”。
2. 去重后不足或超过20个时拒绝运行。
3. 词表摘要变化时拒绝复用旧进度。
4. `succeeded` 关键词不会再次提交。
5. 某关键词失败后继续提交下一项。
6. 进度文件在每次状态变化后更新。
7. `running` 任务能通过相同 `task_id` 恢复等待。
8. 无法确认的任务转为 `needs_review`，不自动重跑。
9. `--retry-failed` 只重试 `failed`。
10. API 状态正确暴露退出码和结束时间。

测试使用 Python 标准库的临时目录和本地假 HTTP 服务，不连接小红书。

人工验收：

1. 后端和 Chrome 9222 正常运行。
2. 用前两个关键词进行受控试跑。
3. 人工中断队列程序，但保留后端任务。
4. 重新启动后能恢复当前任务并跳过已成功关键词。
5. 完成20个关键词后，进度文件显示20项终态。
6. 输出笔记中 `source_keyword` 与任务关键词一致。

## 14. 使用边界

- 仅用于个人、非商业研究。
- 仅采集公开笔记。
- 控制请求频率，不并发运行关键词。
- 不采集评论、联系方式或非公开信息。
- 不用于自动营销触达或个人画像定性。
- 遵守 MediaCrawler 许可证和目标平台规则。
