# Content Asset 数据字典与验收说明

## 1. 定位

`content_asset` 是 T017-5 输出的内容资产表，用于把搜索结果、标题清洗、评论清洗和文案处理结果汇总为一行一个视频的宽表。

必须正确理解它的能力边界：

- content_asset 当前是结构完整、质量可标注的内容资产表。
- 它不等于全量真实评论和真实语音文案均已完成。
- 真实评论仍依赖 CDP，当前真实评论 CDP 采集仍为 pending。
- 真实 ASR 仍依赖 Whisper/ASR，当前全量真实 ASR 仍为 pending。
- 标题或描述生成的 fallback 文案不能表述为真实语音文案。

## 2. 全链路流程

1. `POST /scrape/search` 创建 search task，生成 `search_result.csv` 和 `search_title_clean.csv`。
2. 可选：创建 comments task，生成 `comments_clean.csv`。
3. 可选：创建 scripts task，生成 `script_sources.csv`、`script_raw.csv` 和 `script_clean.csv`。
4. `POST /scrape/merge` 输入 `search_task_id`，并按需输入 `comments_task_id`、`scripts_task_id`。
5. merge task 生成 `content_asset.jsonl` 和 `content_asset.csv`。
6. `GET /scrape/status/{merge_task_id}` 查看任务状态和结果信息。
7. `GET /scrape/result/{merge_task_id}` 下载主结果。
8. `GET /scrape/data/preview/{merge_task_id}` 预览主结果。
9. `GET /scrape/data/export?task_id={merge_task_id}` 原样下载主结果。
10. 在前端 DataPage 或 TaskDetailPage 查看和下载内容资产表。

`search_task_id` 模式用于生成 `content_asset`。不传 task id、改传旧 JSONL 路径参数时，`/scrape/merge` 仍保留旧合并模式；两种模式不要混淆。

## 3. 输入 task_id

| 参数 | 是否必需 | 用途 |
|---|---|---|
| `search_task_id` | 是 | 提供 `search_result.csv` 和 `search_title_clean.csv`，触发 content_asset 构建模式 |
| `comments_task_id` | 否 | 提供 `comments_clean.csv` |
| `scripts_task_id` | 否 | 提供 `script_sources.csv`、`script_raw.csv`、`script_clean.csv` |
| `merge_task_id` | merge 创建后返回 | 用于 status、result、preview、export 和前端访问 |

输入约束：

- search task 必须已完成，且必须存在 `search_result.csv`。
- 没有 `comments_task_id` 不应导致构建失败；`comment_data_status` 会标记为 `pending_cdp`。
- 没有 `scripts_task_id` 不应导致构建失败；`asr_data_status` 会根据现有输入标记为 `pending_asr` 或 `missing`。
- 提供 comments/scripts task id 时，对应任务必须已完成。

## 4. 输出文件

merge task 的输出位于自己的 workspace：

```text
workspaces/<merge_task_id>/outputs/content_asset.jsonl
workspaces/<merge_task_id>/outputs/content_asset.csv
```

格式要求：

- CSV 使用 UTF-8-SIG 编码，文件头带 BOM，表头顺序固定。
- JSONL 使用 UTF-8 编码和 `ensure_ascii=False`，中文不转义。
- 缺失的文本字段写空字符串，缺失的计数字段写 `0`。
- 可选输入文件缺失或读取失败时，详情写入 `content_asset_stats.errors`。

## 5. 字段数据字典

| 字段 | 来源 | 含义 | 空值/默认值 | 备注 |
|---|---|---|---|---|
| `source_keyword` | `search_result.csv` | 产生该视频的搜索关键词 | 空字符串 | 原始搜索上下文 |
| `platform` | `search_result.csv` | 内容平台 | `douyin` | 输入为空时由 builder 补默认值 |
| `video_id` | `search_result.csv` | 标准视频 ID | 空字符串 | 缺失时回退使用 `aweme_id` |
| `aweme_id` | `search_result.csv` | 抖音作品 ID | 空字符串 | 关联评论和文案的优先键 |
| `aweme_url` | `search_result.csv` | 作品页面地址 | 空字符串 | 也可作为标题/文案关联兜底键 |
| `raw_title` | `search_result.csv`、`search_title_clean.csv` | 原始标题 | 空字符串 | 优先 `search_result.title`，再取 `raw_title` |
| `clean_title` | `search_title_clean.csv`、`search_result.csv` | 清洗后的标题 | 空字符串 | 优先标题清洗结果 |
| `desc` | `search_result.csv`、`search_title_clean.csv` | 原始描述 | 空字符串 | 优先 `search_result.desc`，再取 `raw_desc` |
| `clean_desc` | `search_title_clean.csv`、`search_result.csv` | 清洗后的描述 | 空字符串 | 优先标题清洗结果 |
| `topic` | `search_title_clean.csv` | 规则提取的主题 | 空字符串 | 不是 AI/LLM 生成字段 |
| `pain_point` | `search_title_clean.csv` | 规则提取的痛点 | 空字符串 | 依赖标题清洗输入质量 |
| `teaching_angle` | `search_title_clean.csv` | 规则提取的教学角度 | 空字符串 | 依赖标题清洗输入质量 |
| `nickname` | `search_result.csv` | 作者昵称 | 空字符串 | 原始搜索元数据 |
| `liked_count` | `search_result.csv` | 点赞数 | `0` | 非法或空值归零 |
| `collected_count` | `search_result.csv` | 收藏数 | `0` | 非法或空值归零 |
| `comment_count` | `search_result.csv` | 平台展示的评论总数 | `0` | 不等于本次采集到的有效评论数 |
| `share_count` | `search_result.csv` | 分享数 | `0` | 非法或空值归零 |
| `total_engagement` | `search_result.csv`、builder 派生 | 总互动数 | `0` | 输入为空或为 0 时按点赞、收藏、评论、分享求和 |
| `valid_comment_count` | `comments_clean.csv`、builder 派生 | 本次清洗后有效评论数 | `0` | 只统计 `is_valid=true` |
| `top_valid_comments` | `comments_clean.csv`、builder 派生 | 代表性有效评论 | 空字符串 | 最多取前 3 条 `clean_content`，使用竖线拼接 |
| `comment_pain_tags` | `comments_clean.csv`、builder 派生 | 有效评论中的痛点标签 | 空字符串 | 去重后使用竖线拼接 |
| `script_source_status` | `script_sources.csv` | 文案来源准备状态 | 空字符串 | 常见值为 `available`、`planned`、`missing` |
| `script_source_quality` | `script_sources.csv` | 文案来源基础质量 | 空字符串 | 常见值为 `medium`、`weak`、`low`、`missing` |
| `script_clean_text` | `script_clean.csv` | 当前可用的清洗文案 | 空字符串 | 可能是真实 ASR，也可能是 fallback，必须结合 source/status 判断 |
| `script_clean_source` | `script_clean.csv` | 清洗文案来源 | 空字符串 | `asr_raw` 才表示真实 ASR |
| `script_clean_quality` | `script_clean.csv` | 清洗文案质量标记 | 空字符串 | 上游文案清洗结果的透传值 |
| `comment_data_status` | builder 派生 | 评论数据可用状态 | `pending_cdp`、`empty` 或 `available` | 由评论文件是否存在及有效评论数决定 |
| `asr_data_status` | `script_raw.csv`、`script_clean.csv`、builder 派生 | ASR 或 fallback 使用状态 | `missing` 等 | 明确区分真实 ASR、fallback 和依赖缺失 |
| `asset_quality` | builder 派生 | 当前资产完整度/可用度 | `low` 等 | 不是绝对内容质量评分 |
| `created_at` | builder 派生 | 资产记录生成时间 | UTC 时间 | 同一批构建记录使用同一时间，格式为 ISO 风格 UTC 字符串 |

记录关联优先使用 `aweme_id`，再使用 `video_id`；标题和文案数据还可使用 `aweme_url` 兜底。评论聚合仅按 `aweme_id`、`video_id` 关联。

## 6. 状态字段说明

### comment_data_status

| 值 | 含义 |
|---|---|
| `available` | 存在 `comments_clean.csv`，且该视频有至少一条有效评论 |
| `empty` | 存在 `comments_clean.csv`，但该视频没有有效评论 |
| `pending_cdp` | 未提供 comments task，或缺少 `comments_clean.csv` |

`comment_count` 是搜索结果中的平台展示值；`valid_comment_count` 和 `comment_data_status` 描述的是本次评论采集与清洗结果，二者不能互相替代。

### asr_data_status

实际判断按以下顺序执行：

| 值 | 含义 |
|---|---|
| `dependency_missing` | `script_raw.asr_status` 或 `script_clean.asr_status` 为 `dependency_missing` |
| `pending_asr` | 缺少 `script_clean.csv`，但 `script_sources.csv` 标记 `source_asr_planned=true` |
| `missing` | 缺少可用文案，或缺少 scripts task 且没有可判定的 ASR 计划 |
| `available` | `script_clean_source=asr_raw` 且 `script_clean_text` 非空，表示使用真实 ASR 文案 |
| `fallback_title` | `script_clean_source=source_clean_title` 且文本非空 |
| `fallback_desc` | `script_clean_source=source_title_desc` 且文本非空 |

### script_clean_source

| 值 | 含义 |
|---|---|
| `asr_raw` | 真实 ASR 文案 |
| `source_clean_title` | 清洗标题/描述组成的 fallback |
| `source_title_desc` | 原始标题/描述组成的 fallback |
| `missing` | 无可用文案 |

不得只根据 `script_clean_text` 非空就宣称存在真实 ASR。真实 ASR 必须同时满足 `script_clean_source=asr_raw` 和 `asr_data_status=available`。

## 7. asset_quality 实际优先级

`asset_quality` 不是绝对内容质量评分，而是当前资产完整度/可用度标记。代码按下列顺序从上到下判断，命中后立即返回：

| 优先级 | 值 | 实际条件 |
|---:|---|---|
| 1 | `high` | `valid_comment_count > 0`，且 `script_clean_source=asr_raw`，且文案非空 |
| 2 | `missing` | 原始/清洗标题和描述全部为空，且文案为空 |
| 3 | `medium` | 存在 `clean_title` 或 `clean_desc`，且文案来源为 `source_clean_title` 或 `source_title_desc`，且文案非空 |
| 4 | `partial` | 文案非空，且评论状态不是 `available`，或 ASR 状态不是 `available` |
| 5 | `low` | 未命中以上条件 |

当前实现中，medium 优先于 partial。因此，有清洗标题或清洗描述、并使用标题类 fallback 文案时，即使缺少真实 ASR，通常也会先标记为 `medium`。`partial` 用于未达到 `medium` 条件、但仍有文案且评论或真实 ASR 不完整的情况。

边界示例：

- 有有效评论和真实 ASR：`high`。
- 有清洗标题和标题 fallback：`medium`。
- 无任何标题/描述且无文案：`missing`。
- 有真实 ASR 文案但评论不可用：`partial`。
- 只有搜索标题等基础信息、没有文案：`low`。

## 8. 真实数据与 fallback 边界

| 数据 | 可视为真实采集 | 说明 |
|---|---:|---|
| `search_result.csv` 中的作品和互动元数据 | 是 | 来自搜索采集结果，但仍受平台返回值和采集质量影响 |
| `comments_clean.csv` 中的评论 | 是 | 前提是 comments task 实际通过 CDP 完成评论采集；清洗字段属于规则派生 |
| `script_clean_source=asr_raw` 的文案 | 是 | 表示使用真实 ASR 转写结果 |
| `source_clean_title` 文案 | 否 | 清洗标题/描述 fallback |
| `source_title_desc` 文案 | 否 | 原始标题/描述 fallback |
| `topic`、`pain_point`、`teaching_angle` | 派生字段 | 当前为规则清洗/提取结果，不是原始平台字段 |
| `asset_quality` 和状态字段 | 派生字段 | 用于显式标注数据完整度和来源质量 |

即使 content_asset 的 schema 完整，也不能表述为“全量真实评论和真实语音文案已经完成”。应结合 `comment_data_status`、`asr_data_status`、`script_clean_source` 和 `content_asset_stats` 判断实际质量。

## 9. API 使用方式

以下示例使用 `$API_BASE_URL` 表示当前环境配置的 API 地址：

```powershell
$API_BASE_URL = "http://localhost:<api-port>"
```

### POST /scrape/merge

task-id 模式：

```powershell
curl.exe -X POST "$API_BASE_URL/scrape/merge" `
  -H "Content-Type: application/json" `
  -d '{"search_task_id":"<search_task_id>","comments_task_id":"<comments_task_id>","scripts_task_id":"<scripts_task_id>"}'
```

只有 search task 时：

```powershell
curl.exe -X POST "$API_BASE_URL/scrape/merge" `
  -H "Content-Type: application/json" `
  -d '{"search_task_id":"<search_task_id>"}'
```

`comments_task_id` 和 `scripts_task_id` 可选。响应中的 `task_id` 是后续使用的 `merge_task_id`。

### GET /scrape/status/{task_id}

```powershell
curl.exe "$API_BASE_URL/scrape/status/<merge_task_id>"
```

任务完成后，返回对象的 `result` 中应包含：

```text
content_asset_jsonl
content_asset_csv
content_asset_stats
```

### GET /scrape/result/{task_id}

```powershell
curl.exe -o content_asset.csv "$API_BASE_URL/scrape/result/<merge_task_id>"
```

merge task 存在 `content_asset.csv` 时，主结果选择器会优先返回该文件。

### GET /scrape/data/preview/{task_id}

```powershell
curl.exe "$API_BASE_URL/scrape/data/preview/<merge_task_id>?limit=20"
```

返回结构：

```text
task_id
file_name
format
total_rows
rows
```

正常情况下 `file_name` 为 `content_asset.csv`。

### GET /scrape/data/export?task_id={task_id}

```powershell
curl.exe -o content_asset_export.csv "$API_BASE_URL/scrape/data/export?task_id=<merge_task_id>"
```

GET export 是原始主结果文件下载，保留 `content_asset.csv` 的完整 schema 和原文件 BOM。

### POST /scrape/data/export

```powershell
curl.exe -X POST "$API_BASE_URL/scrape/data/export" `
  -H "Content-Type: application/json" `
  -d '{"task_ids":["<merge_task_id>"],"format":"csv","limit":200}' `
  -o content_asset_legacy_export.csv
```

POST export 是批量旧七字段归一化导出，输出字段为：

```text
video_id
platform
script_text
likes
favorites
shares
comments
```

它不是 content_asset 完整字段导出。映射关系包括：

```text
script_text <- script_clean_text
likes       <- liked_count
favorites   <- collected_count
shares      <- share_count
comments    <- comment_count
```

## 10. 前端使用方式

### DataPage

- 后端 `/scrape/data/list` 仍返回 task workspace 中的多个结果文件。
- DataPage 按优先级为每个 task 选择一个主结果文件展示。
- merge task 的 `content_asset.csv` 显示为“内容资产表”。
- 预览默认展示核心列，避免宽表横向过长。
- 可使用“查看全部字段 / 只看核心字段”切换。
- “下载原始文件”使用 GET export，保留完整 `content_asset.csv`。
- “批量导出旧七字段”使用 POST export，输出旧兼容格式。

### TaskDetailPage

- merge task 显示“主结果：内容资产表”和文件名 `content_asset.csv`。
- 下载按钮显示为“下载内容资产表”。
- `content_asset_stats` 以结构化方式展示，包括输入/输出行数、评论、文案、ASR、fallback 和错误信息。

当前前端创建 merge 任务的页面尚未提供 `search_task_id`、`comments_task_id`、`scripts_task_id` 输入；task-id 模式请直接调用 API。这不影响 DataPage 和 TaskDetailPage 的查看、预览和下载能力。

## 11. API 验收清单

### 生成与状态

先准备一个已完成的 search task；comments/scripts task 可选。调用 merge 后记录返回的 `merge_task_id`：

```powershell
curl.exe -X POST "$API_BASE_URL/scrape/merge" `
  -H "Content-Type: application/json" `
  -d '{"search_task_id":"<search_task_id>","comments_task_id":"<comments_task_id>","scripts_task_id":"<scripts_task_id>"}'
```

轮询状态：

```powershell
curl.exe "$API_BASE_URL/scrape/status/<merge_task_id>"
```

验收点：

- task 状态为 `completed`。
- `result.content_asset_jsonl`、`result.content_asset_csv`、`result.content_asset_stats` 存在。
- merge task workspace 的 `outputs/` 中存在两个 content_asset 文件。

### result、preview 与 export

```powershell
curl.exe -o result.csv "$API_BASE_URL/scrape/result/<merge_task_id>"
curl.exe "$API_BASE_URL/scrape/data/preview/<merge_task_id>?limit=20"
curl.exe -o export.csv "$API_BASE_URL/scrape/data/export?task_id=<merge_task_id>"
```

验收点：

- result 下载文件为 `content_asset.csv`。
- preview 返回 `file_name=content_asset.csv`，并包含 `format`、`total_rows`、`rows`。
- GET export 与主结果原文件内容一致，保留完整字段和 BOM。

### BOM 检查

PowerShell 可执行命令：

```powershell
@'
from pathlib import Path
for name in ["result.csv", "export.csv"]:
    p = Path(name)
    print(name, p.read_bytes()[:3])
'@ | python -
```

期望输出：

```text
b'\xef\xbb\xbf'
```

### 本地测试与静态检查

```powershell
python -m pytest douyin_scraper\tests\test_content_asset.py -q
python -m pytest douyin_scraper\tests\test_content_asset_api.py -q
python -m pytest douyin_scraper\tests\test_task_result_selection.py -q
python -m py_compile api\tasks.py api\routes.py douyin_scraper\content_asset.py
```

## 12. 前端验收清单

### 构建

```powershell
cd web
npm run build
```

项目当前没有独立的 `lint` 或 `typecheck` npm 脚本；类型检查已包含在 `npm run build` 的 `tsc -b` 中。bundle size warning 属既有警告，不阻断 T017-5。

### 浏览器检查

打开当前环境的前端地址，检查：

- DataPage 每个 task 只展示一个主结果。
- merge task 显示“内容资产表”和 `content_asset.csv`。
- content_asset 预览默认显示核心列。
- 可切换查看全部字段。
- “下载原始文件”下载完整 content_asset schema。
- “批量导出旧七字段”文案明确，导出七字段兼容格式。
- TaskDetailPage 显示“主结果：内容资产表 content_asset.csv”。
- 下载按钮为“下载内容资产表”。
- `content_asset_stats` 不显示为 `[object Object]`，而是结构化信息。

## 13. Pending 风险

| 风险 | 是否阻断 T017-5 功能封版 | 后续处理 |
|---|---:|---|
| CDP 真实评论采集未完成 | 否 | 独立评论采集任务 |
| 真实 ASR 未完成 | 否 | 独立 Whisper/ASR 任务 |
| POST export 保持旧七字段契约 | 否 | 作为兼容契约保留，若升级需独立版本设计 |
| content_asset 的 comment/asr 状态依赖已有输入质量 | 否 | 通过状态字段和数据质量文档持续管理 |
| 后端 `/data/list` 仍返回多文件，前端做展示过滤 | 否 | 可在后续统一后端主结果语义 |
| 前端创建 merge 尚未提供 task_id 输入 | 否 | 独立前端创建流程任务 |

这些风险不阻断 T017-5 功能封版，但必须作为后续独立任务管理，不能把 pending 能力描述成已经完成。
