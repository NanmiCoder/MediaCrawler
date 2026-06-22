# Content Asset API

本页说明 Content Asset 的 task-id 构建流程、主结果选择、预览与导出契约。完整字段和状态定义见 [Content Asset 数据字典与验收说明](../docs/CONTENT_ASSET.md)。

## task-id merge workflow

`POST /scrape/merge` 提供 `search_task_id` 时，会读取已完成任务的标准输出，并在新的 merge task workspace 中生成 `content_asset.jsonl` 和 `content_asset.csv`。

```json
{
  "search_task_id": "<search_task_id>",
  "comments_task_id": "<comments_task_id>",
  "scripts_task_id": "<scripts_task_id>"
}
```

- `search_task_id` 必需，且对应任务必须已完成并包含 `search_result.csv`。
- `comments_task_id`、`scripts_task_id` 可选；提供时对应任务必须已完成。
- 没有评论或 scripts task 时仍可生成资产表，并通过状态字段标记缺失或 pending。
- merge 响应返回的 `task_id` 用于后续 status、result、preview 和 export。

任务完成后，status 响应的 `result` 包含：

```text
content_asset_jsonl
content_asset_csv
content_asset_stats
```

## result、preview 与 export

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/scrape/result/{task_id}` | 下载主结果文件 |
| GET | `/scrape/data/preview/{task_id}?limit=20` | 预览与 result 相同的主结果 |
| GET | `/scrape/data/export?task_id={task_id}` | 原样下载主结果文件 |
| POST | `/scrape/data/export` | 批量归一化导出旧七字段 CSV/TXT |

merge task 的主结果优先级为：

```text
content_asset.csv
content_asset.jsonl
douyin_koubo_data.csv
```

`result`、preview 和 GET export 共用该选择语义。GET export 保留 `content_asset.csv` 的完整 schema 和原文件 BOM。

preview 返回：

```text
task_id
file_name
format
total_rows
rows
```

## POST export 兼容字段

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

Content Asset 映射关系：
