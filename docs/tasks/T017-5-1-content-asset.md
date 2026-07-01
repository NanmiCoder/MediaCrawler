T017-5-1：content_asset.csv schema 与 builder 第一版实现。

本轮允许改代码，但只做 content_asset 第一版生成能力。不要改 preview/export/result，不接 AI，不处理 whisper/CDP，不改 run_all 主流程，不混修端口。

## 当前基线

T017 主线已完成到：

```text
search_result.csv/jsonl
search_title_clean.csv/jsonl
comments_clean.csv/jsonl
script_sources.csv/jsonl
script_raw.csv/jsonl
script_clean.csv/jsonl
```

T017-5-0 查询结论：

```text
merge_to_csv.py 是旧合并雏形，不适合作为主实现
run_all.py 是旧流程，不作为 T017-5 主入口
content_asset.csv 建议归属 merge_task workspace
推荐新增 douyin_scraper/content_asset.py
由 DouyinScraper 增加薄 helper 调用
```

## 固定端口规则

MediaCrawler 固定端口：

```text
API 宿主：http://localhost:18080
API 容器内部：8000
前端 dev：15173
Chrome/CDP：19222
```

本轮不要改端口。

## 禁止

```text
禁止接 AI/LLM
禁止处理 whisper/ASR 依赖
禁止处理 CDP 真实评论采集
禁止改 preview/export/result
禁止改 run_all.py 主流程
禁止直接复用旧 merge_to_csv.py 作为主实现
禁止新增 /scrape/content-asset-v2 之类重复接口
禁止混修端口
禁止删除或覆盖原始 CSV/JSONL
```

## 开发前先查

先检查并输出：

```text
douyin_scraper/core.py
douyin_scraper/content_asset.py 是否存在
merge_to_csv.py
run_all.py
api/routes.py
api/tasks.py
douyin_scraper/tests/
```

回答：

```text
1. 当前 /scrape/merge 在哪里？
2. DouyinScraper 当前 merge 入口在哪里？
3. merge task workspace 如何创建？
4. 当前 task result 如何返回 merge 结果？
5. content_asset.py 是否已存在？
6. 本次新增/修改哪些文件？
```

没有完成查询，不要写代码。

## 目标

基于多个 task 的 outputs，生成：

```text
workspace/<merge_task_id>/outputs/content_asset.jsonl
workspace/<merge_task_id>/outputs/content_asset.csv
```

输入建议：

```json
{
  "search_task_id": "<search_task_id>",
  "comments_task_id": "<comments_task_id>",
  "scripts_task_id": "<scripts_task_id>"
}
```

如当前 `/scrape/merge` schema 不支持这些字段，可最小范围扩展现有 merge request。不要新增新接口。

## 输入文件优先级

从 task outputs 读取：

### search task

```text
search_result.csv
search_title_clean.csv
```

### comments task，可选

```text
comments_clean.csv
```

没有 comments task 或没有 comments_clean.csv 时，不失败，标记：

```text
comment_data_status=pending_cdp 或 missing
```

### scripts task，可选

```text
script_sources.csv
script_raw.csv
script_clean.csv
```

没有 scripts task 或没有 script_clean.csv 时，不失败，标记：

```text
asr_data_status=missing 或 pending_asr
```

## 关联规则

按以下优先级关联：

```text
aweme_id
video_id
aweme_url
```

要求：

```text
search_result 是主表
title_clean 按 aweme_id/video_id/aweme_url 补充
comments_clean 按 aweme_id/video_id 聚合
script_clean 按 aweme_id/video_id/aweme_url 补充
缺失不崩溃
```

## content_asset 字段

第一版 CSV/JSONL 至少包含：

```text
source_keyword
platform
video_id
aweme_id
aweme_url

raw_title
clean_title
desc
clean_desc
topic
pain_point
teaching_angle

nickname
liked_count
collected_count
comment_count
share_count
total_engagement

valid_comment_count
top_valid_comments
comment_pain_tags

script_source_status
script_source_quality
script_clean_text
script_clean_source
script_clean_quality

comment_data_status
asr_data_status
asset_quality
created_at
```

## 聚合规则

### comments_clean 聚合

只统计：

```text
is_valid=true
```

输出：

```text
valid_comment_count
top_valid_comments
comment_pain_tags
```

规则：

```text
top_valid_comments 取前 3 条 clean_content，用 | 拼接
comment_pain_tags 去重后用 | 拼接
如果没有 comments_clean.csv：valid_comment_count=0，comment_data_status=pending_cdp
如果有文件但无有效评论：comment_data_status=empty
如果有有效评论：comment_data_status=available
```

### script_clean 合并

优先读取：

```text
script_clean_text
script_clean_source
script_clean_quality
script_clean_status
```

`asr_data_status` 规则：

```text
script_clean_source=asr_raw -> available
script_clean_source=source_clean_title -> fallback_title
script_clean_source=source_title_desc -> fallback_desc
script_clean_source=missing 或 script_clean_text 空 -> missing
如果 script_raw 中 asr_status=dependency_missing -> dependency_missing
```

### asset_quality 规则

建议：

```text
high：有有效评论 + script_clean_source=asr_raw
medium：有 title_clean + 有 fallback script_clean_text
low：只有 search/title 基础信息
partial：缺评论或缺真实 ASR，但有 fallback 文案
missing：关键标题和文案都缺失
```

注意：不能把 fallback 文案伪装成真实 ASR 文案。

## 新增文件建议

允许新增：

```text
douyin_scraper/content_asset.py
```

职责：

```text
读取标准 CSV
按 aweme_id/video_id/aweme_url 合并
聚合 comments_clean
合并 script_clean
计算 comment_data_status/asr_data_status/asset_quality
写 content_asset.jsonl/csv
```

`core.py` 只保留薄 helper 调用，不要继续膨胀过多。

## status 返回

扩展现有 merge task result，返回：

```text
content_asset_jsonl
content_asset_csv
content_asset_stats
```

`content_asset_stats` 至少包含：

```text
rows_in
rows_out
comments_available
scripts_available
valid_comments_total
asr_available
fallback_script_total
missing_script_total
content_asset_csv_generated
errors
```

不要改 `/scrape/result` 显式优先级，不改 preview/export。本轮只保证 status result 有字段，文件真实生成。

## 输出要求

```text
JSONL ensure_ascii=False
CSV utf-8-sig
CSV 表头顺序固定
缺字段填空字符串或 0
输入文件缺失不崩溃，写入 stats.errors
```

## 测试要求

至少覆盖：

```text
仅 search_result + title_clean 也能生成 content_asset
comments_clean 存在时聚合 valid_comment_count/top_valid_comments/comment_pain_tags
comments_clean 缺失时 comment_data_status=pending_cdp
script_clean 存在时填 script_clean_text/script_clean_source/script_clean_quality
script_raw asr_status=dependency_missing 时 asr_data_status=dependency_missing
fallback 文案时 asset_quality 不标 high
按 aweme_id 优先关联
按 video_id 兜底关联
CSV utf-8-sig
JSONL ensure_ascii=False
```

## 本地验收命令

```powershell
python -m py_compile douyin_scraper\core.py douyin_scraper\content_asset.py api\routes.py
python -m pytest douyin_scraper\tests\test_core.py -q
```

如果新增独立测试文件，也一起跑：

```powershell
python -m pytest douyin_scraper\tests\ -q
```

## Docker/API 验收

统一使用：

```text
宿主：http://localhost:18080
容器内部：http://localhost:8000
```

验收流程：

```text
1. 准备已有 search task / comments task / scripts task
2. 调用 /scrape/merge，传 search_task_id/comments_task_id/scripts_task_id
3. 确认 merge task completed
4. status 返回 content_asset_jsonl/content_asset_csv/content_asset_stats
5. 检查 outputs/content_asset.jsonl
6. 检查 outputs/content_asset.csv
7. 检查 CSV BOM = ef bb bf
8. 检查 comment_data_status / asr_data_status / asset_quality
```

示例检查：

```powershell
curl.exe http://localhost:18080/scrape/status/<merge_task_id>

docker exec mediacrawler-api-1 sh -lc "ls -lh /app/workspaces/<merge_task_id>/outputs/"
docker exec mediacrawler-api-1 sh -lc "head -n 3 /app/workspaces/<merge_task_id>/outputs/content_asset.csv"
docker exec mediacrawler-api-1 sh -lc "python - <<'PY'
from pathlib import Path
p = Path('/app/workspaces/<merge_task_id>/outputs/content_asset.csv')
print(p.read_bytes()[:3])
PY"
```

期望：

```text
b'\xef\xbb\xbf'
```

## 最终报告

输出：

```text
1. 开发前查询结果
2. 新增/修改文件
3. content_asset 字段说明
4. 聚合规则说明
5. 数据质量状态说明
6. 测试结果
7. Docker/API 验收结果
8. 是否允许进入 T017-5-2
```

## 通过标准

```text
生成 content_asset.jsonl
生成 content_asset.csv
CSV UTF-8-SIG
JSONL 中文正常
status 返回 content_asset_jsonl/content_asset_csv/content_asset_stats
保留 comment_data_status/asr_data_status/asset_quality
不改 preview/export/result
不接 AI
不处理 whisper/CDP
不新增重复接口
测试通过
Docker/API 验收通过
```
