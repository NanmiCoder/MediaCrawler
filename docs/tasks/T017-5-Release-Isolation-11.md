T017-5-Release-Isolation-11：实际形成 A-D 顺序提交候选并最终复核。

本轮允许实际暂存 A-D 四组候选提交内容，但禁止 commit。每组暂存后必须检查 staged diff、运行对应测试、记录结果，然后 reset，确保最终暂存区为空。

## 当前状态

```text
T017-5：功能已 CLOSED
T017-5 Release-1：继续 NO-GO
T017-5-Release-Isolation-10：PASS
```

Isolation-10 已完成：

```text
A-D 代码边界已拆分
五个独立测试文件已建立
py_compile PASS
A-D + selector：19 passed
test_core.py：27 passed
api/tests.py::TestTaskManager：10 passed
git diff --check：PASS
暂存区为空
未 commit
```

## 本轮目标

实际形成并复核四组候选提交：

```text
A. T016 标准搜索输出
B. T017-2 评论 raw/clean 输出
C. T017-3 标题清洗输出
D. T017-4 script sources/raw/clean 输出
```

本轮只做暂存与复核，不提交。

## 禁止

```text
禁止 git commit
禁止 git add .
禁止 git add web/
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
允许按文件/patch 暂存 A-D 候选内容
允许 git diff --cached 检查
允许运行对应 pytest
允许 git reset 取消暂存
禁止 commit
```

## 一、执行前检查

```powershell
git status --short
git diff --cached --name-status
git diff --check
python -m py_compile douyin_scraper\core.py api\routes.py api\tasks.py
```

要求：

```text
暂存区为空
git diff --check PASS
py_compile PASS
api/webui 不纳入
```

## 二、A 组候选提交复核

Commit message：

```text
feat(scraper): standardize search outputs in task workspaces
```

目标范围：

```text
douyin_scraper/core.py
api/routes.py
api/tasks.py
douyin_scraper/tests/test_search_outputs.py
douyin_scraper/tests/test_task_result_selection.py
```

只能包含：

```text
search_result.jsonl
search_result.csv
workspace 输出
CSV UTF-8-SIG
标准 18 字段
aweme_id / aweme_url 去重
total_engagement
search/run_all selector
A 组测试
```

不得包含：

```text
comments
title_clean
scripts
content_asset
runtime port
api/webui
```

执行暂存后检查：

```powershell
git diff --cached --stat
git diff --cached --name-status
git diff --cached -- douyin_scraper/core.py api/routes.py api/tasks.py
python -m pytest douyin_scraper\tests\test_search_outputs.py -q
python -m pytest douyin_scraper\tests\test_task_result_selection.py -q
```

记录：

```text
staged 文件数
insertions/deletions
测试结果
是否存在越界内容
```

然后 reset：

```powershell
git reset -- douyin_scraper/core.py api/routes.py api/tasks.py douyin_scraper/tests/test_search_outputs.py douyin_scraper/tests/test_task_result_selection.py
git diff --cached --name-status
```

## 三、B 组候选提交复核

Commit message：

```text
feat(scraper): add raw and cleaned comment outputs
```

目标范围：

```text
douyin_scraper/core.py
api/routes.py
api/tasks.py
douyin_scraper/tests/test_comments_outputs.py
```

如 `crawl_comments_v2.py` 已经被拆清且不含 CDP/9222 越界内容，可列入；否则继续暂缓，不纳入 B。

只能包含：

```text
comments_raw.jsonl/csv
comments_clean.jsonl/csv
comments endpoint
comments selector
comments tests
```

不得包含：

```text
真实 CDP 修复
9222/19222 端口契约调整
title_clean
scripts
content_asset
```

执行：

```powershell
git diff --cached --stat
git diff --cached --name-status
git diff --cached -- douyin_scraper/core.py api/routes.py api/tasks.py
python -m pytest douyin_scraper\tests\test_comments_outputs.py -q
```

然后 reset 对应文件，确保暂存区为空。

## 四、C 组候选提交复核

Commit message：

```text
feat(scraper): add cleaned search title outputs
```

目标范围：

```text
douyin_scraper/core.py
api/routes.py
douyin_scraper/tests/test_title_clean.py
```

只能包含：

```text
search_title_clean.jsonl/csv
title clean helper
hashtags
topic
pain_point
teaching_angle
title path
search response title payload
title tests
```

不得包含：

```text
scripts
content_asset
comments
runtime port
```

执行：

```powershell
git diff --cached --stat
git diff --cached --name-status
git diff --cached -- douyin_scraper/core.py api/routes.py
python -m pytest douyin_scraper\tests\test_title_clean.py -q
```

然后 reset，暂存区清空。

## 五、D 组候选提交复核

Commit message：

```text
feat(scraper): add script source raw and clean outputs
```

目标范围：

```text
douyin_scraper/core.py
api/routes.py
api/tasks.py
douyin_scraper/tests/test_script_outputs.py
```

`pyproject.toml` 仅在可单独抽取 whisper 可选依赖 hunk 且不重写项目元数据时纳入；否则暂缓。

只能包含：

```text
script_sources.jsonl/csv
script_raw.jsonl/csv
script_clean.jsonl/csv
dependency_missing 降级
scripts endpoint
scripts selector
scripts tests
```

不得包含：

```text
content_asset builder
真实 Whisper/ASR 集成
安装依赖动作
runtime port
api/webui
```

执行：

```powershell
git diff --cached --stat
git diff --cached --name-status
git diff --cached -- douyin_scraper/core.py api/routes.py api/tasks.py
python -m pytest douyin_scraper\tests\test_script_outputs.py -q
```

然后 reset，暂存区清空。

## 六、总体验证

```powershell
python -m py_compile douyin_scraper\core.py api\routes.py api\tasks.py
python -m pytest douyin_scraper\tests\test_search_outputs.py douyin_scraper\tests\test_comments_outputs.py douyin_scraper\tests\test_title_clean.py douyin_scraper\tests\test_script_outputs.py douyin_scraper\tests\test_task_result_selection.py -q
python -m pytest douyin_scraper\tests\test_core.py -q
python -m pytest api\tests.py::TestTaskManager -q
git diff --check
git diff --cached --name-status
```

要求：

```text
py_compile PASS
A-D + selector PASS
test_core.py PASS
api/tests.py::TestTaskManager PASS
git diff --check PASS
最终暂存区为空
```

## 七、最终报告

输出：

```markdown
# T017-5-Release-Isolation-11 报告

## 1. 执行结论

## 2. A 组候选提交复核

## 3. B 组候选提交复核

## 4. C 组候选提交复核

## 5. D 组候选提交复核

## 6. 总体验证结果

## 7. 暂存区最终状态

## 8. 是否允许进入 Isolation-12 / Release-1
```

## 通过标准

```text
A-D 均可形成候选提交
每组 staged diff 无越界内容
每组对应测试 PASS
总体验证 PASS
暂存区最终为空
未 commit
api/webui 未处理
Release-1 仍需等待最终提交授权
```

## 下一步建议

若 Isolation-11 PASS：

```text
Isolation-12：A-D 实际提交授权前最终检查
```

Release-1 仍不要直接开启，除非明确授权开始逐组 commit。
