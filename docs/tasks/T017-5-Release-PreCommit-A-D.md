T017-5-Release-PreCommit-A-D：按 A→B→C→D 顺序实际提交前序成果。

本轮允许按顺序实际创建 4 个 commit，但必须严格按 A、B、C、D 分组执行。每个 commit 前必须暂存对应范围、检查 staged diff、运行对应测试；每个 commit 后必须记录 commit hash，并确认暂存区为空后再进入下一组。

## 当前状态

```text
T017-5：功能已 CLOSED
T017-5-Release-Isolation-12：PASS
A-D 实际逐组 commit：已获准
```

## 严禁

```text
禁止 git add .
禁止 git add web/
禁止处理 api/webui
禁止提交 content_asset
禁止提交 web 前端
禁止提交 runtime port
禁止提交 crawl_comments_v2.py
禁止提交 pyproject.toml
禁止处理 CDP
禁止处理真实 Whisper/ASR
禁止接 AI/LLM
禁止格式化无关文件
```

## Commit A

Message：

```text
feat(scraper): standardize search outputs in task workspaces
```

范围仅限：

```text
标准 search_result.jsonl/csv
workspace 输出
18 字段
UTF-8-SIG/BOM
去重
total_engagement
search/run_all selector
test_search_outputs.py
test_task_result_selection.py 的 search/run_all 部分
```

提交前验证：

```powershell
git diff --cached --check
python -m pytest douyin_scraper\tests\test_search_outputs.py -q
python -m pytest douyin_scraper\tests\test_task_result_selection.py -q
```

提交后记录 commit hash。

## Commit B

Message：

```text
feat(scraper): add raw and cleaned comment outputs
```

范围仅限：

```text
comments_raw.jsonl/csv
comments_clean.jsonl/csv
comments endpoint
comments selector
test_comments_outputs.py
```

不得包含：

```text
crawl_comments_v2.py
真实 CDP 修复
9222/19222 端口契约
title_clean
scripts
content_asset
```

验证：

```powershell
git diff --cached --check
python -m pytest douyin_scraper\tests\test_comments_outputs.py -q
```

## Commit C

Message：

```text
feat(scraper): add cleaned search title outputs
```

范围仅限：

```text
search_title_clean.jsonl/csv
title clean helper
hashtags
topic
pain_point
teaching_angle
title path
search response title payload
test_title_clean.py
```

验证：

```powershell
git diff --cached --check
python -m pytest douyin_scraper\tests\test_title_clean.py -q
```

## Commit D

Message：

```text
feat(scraper): add script source raw and clean outputs
```

范围仅限：

```text
script_sources.jsonl/csv
script_raw.jsonl/csv
script_clean.jsonl/csv
dependency_missing 降级
scripts endpoint
scripts selector
test_script_outputs.py
```

不得包含：

```text
content_asset builder
真实 Whisper/ASR 集成
pyproject.toml
安装依赖动作
runtime port
api/webui
```

验证：

```powershell
git diff --cached --check
python -m pytest douyin_scraper\tests\test_script_outputs.py -q
```

## 四个 commit 完成后总体验证

```powershell
python -m py_compile douyin_scraper\core.py api\routes.py api\tasks.py
python -m pytest douyin_scraper\tests\test_search_outputs.py douyin_scraper\tests\test_comments_outputs.py douyin_scraper\tests\test_title_clean.py douyin_scraper\tests\test_script_outputs.py douyin_scraper\tests\test_task_result_selection.py -q
python -m pytest douyin_scraper\tests\test_core.py -q
python -m pytest api\tests.py::TestTaskManager -q
git diff --check
git status --short
```

## 最终报告

输出：

```markdown
# T017-5-Release-PreCommit-A-D 报告

## 1. 执行结论

## 2. Commit A 结果与 hash

## 3. Commit B 结果与 hash

## 4. Commit C 结果与 hash

## 5. Commit D 结果与 hash

## 6. 总体验证结果

## 7. 剩余工作区状态

## 8. 是否允许进入 T017-5 Builder/API/Web/Docs 提交阶段
```
