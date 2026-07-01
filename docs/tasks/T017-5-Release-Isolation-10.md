T017-5-Release-Isolation-10：手工生成 A-D 独立 patch、拆分 search/get_paths/selector、迁移四组测试。

本轮允许修改文件以完成前序 A-D 的可提交拆分，但禁止 commit。允许新增测试文件、迁移测试、手工拆分混合 hunk。完成后必须保持暂存区为空，输出报告。

## 当前状态

```text
T017-5：功能已 CLOSED
T017-5 Release-1：继续 NO-GO
T017-5-Release-Isolation-9：PASS
```

Isolation-9 结论：

```text
A-D 功能测试通过，但不能直接形成完整独立提交。
阻塞点：
1. search() 混合 A/C/D
2. get_paths() 混合 A/B/C/D/Content Asset
3. api/tasks.py selector 混合 search/comments/scripts/merge
4. 标准 18 字段转换、comments_clean、title_clean、scripts 实现处于大混合 hunk
5. 测试仍在综合 test_core.py / api/tests.py 中，未拆分
```

## 本轮目标

把前序 A-D 变成后续可独立提交的结构：

```text
A. T016 search_result.csv 标准化与 workspace 输出
B. T017-2 comments_raw/comments_clean 输出
C. T017-3 search_title_clean 输出
D. T017-4 script_sources/script_raw/script_clean 输出
```

本轮允许修改，但不提交 commit。

## 禁止

```text
禁止 git commit
禁止 git add .
禁止整文件提交 core.py / routes.py
禁止处理 api/webui
禁止处理 T017-5 content_asset
禁止处理 CDP 真实采集修复
禁止处理真实 Whisper/ASR
禁止接 AI/LLM
禁止端口契约修改
禁止格式化无关文件
```

## 允许

```text
允许修改 douyin_scraper/core.py
允许修改 api/routes.py
允许修改 api/tasks.py
允许新增/拆分测试文件
允许从 test_core.py 迁移测试
允许从 api/tests.py 迁移 selector 测试
允许运行 pytest
允许生成临时 patch
禁止 commit
```

## 一、执行前检查

```powershell
git status --short
git diff --cached --name-status
git diff --stat
```

要求：

```text
暂存区为空
api/webui 不纳入
web 三组状态保持不处理
```

## 二、拆分原则

### 1. `search()` 拆分

将混合逻辑整理为可独立理解的 helper，避免 A/C/D 混在同一 hunk 中。

建议结构：

```text
search()
  - 负责搜索任务主流程
  - 生成标准 search_result.jsonl/csv
  - 可调用后续增强 helper，但每个 helper 独立

A helper:
  - _convert_jsonl_to_standard_csv()
  - 标准 18 字段
  - UTF-8-SIG
  - 去重
  - total_engagement

C helper:
  - _do_clean_search_titles()

D helper:
  - _build_script_sources()
```

### 2. `get_paths()` 拆分

避免一个大 dict 混合全部输出字段。建议整理成分组 helper 或至少保持分块清晰：

```text
base paths
search paths
comments paths
title paths
script paths
content_asset paths
```

Content Asset 三项必须保留，但不要混入 A-D patch。

### 3. `api/tasks.py` selector 拆分

建议从单一混合 selector 改成清晰的 task type priority map：

```text
search/run_all selector
comments selector
scripts selector
merge/content_asset selector
fallback selector
```

后续提交时可以分别暂存：

```text
A: search/run_all
B: comments
D: scripts
T017-5: merge/content_asset
```

### 4. `api/routes.py` 拆分

保持 endpoint 分区清楚：

```text
search endpoint
comments endpoint
scripts endpoint
merge/content_asset endpoint
preview/export endpoint
```

不要把 T017-5 merge/export 与 A-D 混在同一个新增块里。

## 三、测试文件迁移

新增或整理以下测试文件：

```text
douyin_scraper/tests/test_search_outputs.py
douyin_scraper/tests/test_comments_outputs.py
douyin_scraper/tests/test_title_clean.py
douyin_scraper/tests/test_script_outputs.py
```

### A：`test_search_outputs.py`

迁移/新增：

```text
搜索 workspace 输出测试
search_result.jsonl 生成测试
search_result.csv 生成测试
标准 18 字段测试
UTF-8-SIG 测试
aweme_id / aweme_url 去重测试
total_engagement 测试
```

### B：`test_comments_outputs.py`

迁移：

```text
test_comments_raw_csv_export
test_comments_clean_rule_export
test_fetch_comments_writes_workspace_outputs
test_fetch_comments_subprocess_failure_keeps_outputs
```

### C：`test_title_clean.py`

迁移/新增：

```text
标题清洗规则测试
hashtag 提取
topic / pain_point / teaching_angle
从混合 search 测试中拆出 title-clean 断言
```

### D：`test_script_outputs.py`

迁移：

```text
test_script_sources_export_from_search_csv
test_script_sources_fallback_to_search_jsonl
test_script_raw_from_script_sources_jsonl_success_and_skips
test_script_raw_fallback_to_csv_download_failed_and_empty_asr
test_script_raw_dependency_missing_does_not_download
test_script_clean_priority_from_raw_sources_and_title_clean
```

### API selector 测试

从 `api/tests.py` 迁移 search/comments/scripts selector 相关测试。

建议新增：

```text
douyin_scraper/tests/test_task_result_selection.py
```

内容：

```text
search selector
comments selector
scripts selector
fallback selector
```

merge/content_asset selector 留给 T017-5 API 独立提交，不混入 A-D。

## 四、A-D patch 验证

完成修改后，分别验证 A-D 是否可独立暂存。

### A 组验证

```powershell
git add -p -- douyin_scraper/core.py api/routes.py api/tasks.py douyin_scraper/tests/test_search_outputs.py douyin_scraper/tests/test_task_result_selection.py
git diff --cached --stat
git diff --cached -- douyin_scraper/core.py api/routes.py api/tasks.py
```

要求：

```text
只包含 search_result.jsonl/csv、workspace、18字段、UTF-8-SIG、去重、search selector
不包含 comments
不包含 title
不包含 scripts
不包含 content_asset
```

验证后 reset：

```powershell
git reset -- douyin_scraper/core.py api/routes.py api/tasks.py douyin_scraper/tests/test_search_outputs.py douyin_scraper/tests/test_task_result_selection.py
```

### B 组验证

```powershell
git add -p -- douyin_scraper/core.py api/routes.py api/tasks.py douyin_scraper/tests/test_comments_outputs.py
git diff --cached --stat
```

要求：

```text
只包含 comments_raw/comments_clean、comments endpoint、comments selector、comments tests
不包含 title/scripts/content_asset/CDP真实修复
```

验证后 reset。

### C 组验证

```powershell
git add -p -- douyin_scraper/core.py api/routes.py douyin_scraper/tests/test_title_clean.py
git diff --cached --stat
```

要求：

```text
只包含 search_title_clean、title helper、title path、title tests
不包含 scripts/content_asset
```

验证后 reset。

### D 组验证

```powershell
git add -p -- douyin_scraper/core.py api/routes.py api/tasks.py douyin_scraper/tests/test_script_outputs.py
git diff --cached --stat
```

要求：

```text
只包含 script_sources/script_raw/script_clean、dependency_missing 降级、scripts endpoint、scripts selector、scripts tests
不包含 content_asset builder
不安装 whisper
```

验证后 reset。

## 五、测试运行

运行：

```powershell
python -m py_compile douyin_scraper\core.py api\routes.py api\tasks.py

python -m pytest douyin_scraper\tests\test_search_outputs.py -q
python -m pytest douyin_scraper\tests\test_comments_outputs.py -q
python -m pytest douyin_scraper\tests\test_title_clean.py -q
python -m pytest douyin_scraper\tests\test_script_outputs.py -q
python -m pytest douyin_scraper\tests\test_task_result_selection.py -q
```

如有失败：

```text
只修复与 A-D 拆分直接相关的问题。
不要顺手修复 CDP/ASR/T017-5。
```

## 六、最终状态检查

```powershell
git diff --cached --name-status
git status --short
git diff --stat
```

要求：

```text
暂存区为空
未 commit
api/webui 未处理
A-D 测试文件已拆分
工作区改动仅限本轮允许范围
```

## 七、最终报告

输出：

```markdown
# T017-5-Release-Isolation-10 报告

## 1. 执行结论

## 2. 代码拆分结果

## 3. 测试迁移结果

## 4. A 组暂存验证结果

## 5. B 组暂存验证结果

## 6. C 组暂存验证结果

## 7. D 组暂存验证结果

## 8. 测试运行结果

## 9. 暂存区最终状态

## 10. 是否允许进入 Isolation-11 / Release-1
```

## 通过标准

```text
A-D 逻辑边界清晰
测试文件已拆分
A-D 均可独立暂存验证
py_compile PASS
A-D 对应测试 PASS
暂存区最终为空
未 commit
api/webui 未处理
Release-1 继续 NO-GO，除非 A-D 已完全可执行提交
```
