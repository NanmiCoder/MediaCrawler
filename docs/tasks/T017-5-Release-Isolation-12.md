T017-5-Release-Isolation-12：A-D 实际提交授权前最终检查。

本轮只做最终检查和提交授权前确认，不执行 commit。目标是确认 A-D 四个前序候选提交是否已经可以进入实际逐组 commit 阶段。

## 当前状态

```text
T017-5：功能已 CLOSED
T017-5 Release-1：继续 NO-GO
T017-5-Release-Isolation-10：PASS
T017-5-Release-Isolation-11：A-D 候选复核通过
T017-5-Release-Isolation-11F：PASS
```

Isolation-11F 已完成：

```text
api/webui 已跟踪文件已恢复到 HEAD
全局 git diff --check PASS
未跟踪新 bundle 暂缓
A-D 业务 diff 未受影响
暂存区为空
未 commit
```

## 本轮目标

最终确认以下内容：

```text
1. A-D 四个候选提交边界是否仍然有效
2. A-D 对应测试是否仍然通过
3. git diff --check 是否通过
4. api/webui 是否仍保持暂缓、不纳入
5. 未跟踪新 bundle 是否仍不纳入
6. 是否允许进入实际逐组 commit 阶段
```

## 禁止

```text
禁止 git commit
禁止 git add .
禁止 git add web/
禁止处理 api/webui
禁止删除未跟踪新 bundle
禁止处理 T017-5 content_asset
禁止处理 CDP 真实采集修复
禁止处理真实 Whisper/ASR
禁止接 AI/LLM
禁止端口契约修改
禁止格式化无关文件
```

## 允许

```text
允许 git status / git diff 检查
允许临时暂存 A-D 候选并检查 staged diff
允许 git reset 清空暂存区
允许运行测试
禁止 commit
```

## 一、执行前检查

```powershell
git status --short
git diff --cached --name-status
git diff --check
git status --short api/webui
git status --ignored --short
```

要求：

```text
暂存区为空
git diff --check PASS
api/webui 已跟踪文件无修改/删除
未跟踪新 bundle 仍暂缓
web/node_modules、web/tsconfig.tsbuildinfo、workspaces 正常 ignored
```

## 二、确认 A-D 候选提交边界

### A 组

Commit message：

```text
feat(scraper): standardize search outputs in task workspaces
```

范围：

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

不得包含：

```text
comments
title_clean
scripts
content_asset
runtime port
api/webui
```

### B 组

Commit message：

```text
feat(scraper): add raw and cleaned comment outputs
```

范围：

```text
comments_raw.jsonl/csv
comments_clean.jsonl/csv
comments endpoint
comments selector
test_comments_outputs.py
```

不得包含：

```text
真实 CDP 修复
9222/19222 端口契约
title_clean
scripts
content_asset
```

`crawl_comments_v2.py` 仍不纳入，除非已经被拆清且不含 CDP/9222 越界内容。

### C 组

Commit message：

```text
feat(scraper): add cleaned search title outputs
```

范围：

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

不得包含：

```text
scripts
content_asset
comments
runtime port
```

### D 组

Commit message：

```text
feat(scraper): add script source raw and clean outputs
```

范围：

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
安装依赖动作
runtime port
api/webui
```

`pyproject.toml` 仍暂缓，除非 Whisper 可选依赖 hunk 已能独立抽取且不重写项目元数据。

## 三、重新运行总体验证

```powershell
python -m py_compile douyin_scraper\core.py api\routes.py api\tasks.py

python -m pytest douyin_scraper\tests\test_search_outputs.py douyin_scraper\tests\test_comments_outputs.py douyin_scraper\tests\test_title_clean.py douyin_scraper\tests\test_script_outputs.py douyin_scraper\tests\test_task_result_selection.py -q

python -m pytest douyin_scraper\tests\test_core.py -q

python -m pytest api\tests.py::TestTaskManager -q

git diff --check
```

要求：

```text
py_compile PASS
A-D + selector PASS
test_core.py PASS
api/tests.py::TestTaskManager PASS
git diff --check PASS
```

完整 `api/tests.py` 路由部分如果仍受 Starlette/httpx TestClient 版本影响，继续记录为既有问题，不在本轮处理。

## 四、A-D staged diff 最终抽查

本轮不 commit，只抽查可暂存性。

对每组临时暂存后检查：

```powershell
git diff --cached --stat
git diff --cached --name-status
git diff --cached --check
```

每组检查完必须 reset：

```powershell
git reset -- <本组文件>
git diff --cached --name-status
```

最终要求：

```text
每组 staged diff 无越界内容
每组 staged diff --check PASS
每组测试 PASS
最终暂存区为空
```

## 五、api/webui 暂缓确认

检查：

```powershell
git status --short api/webui
git diff --name-status -- api/webui
```

要求：

```text
已跟踪 api/webui 文件不应参与 A-D
未跟踪新 bundle 不纳入
api/webui 保持 build(webui) 阶段再处理
```

## 六、最终报告

输出：

```markdown
# T017-5-Release-Isolation-12 报告

## 1. 执行结论

## 2. A-D 候选提交边界最终确认

## 3. 测试运行结果

## 4. staged diff 最终抽查结果

## 5. api/webui 暂缓确认

## 6. 暂存区最终状态

## 7. 是否允许进入实际逐组 commit / Release-1
```

## 通过标准

```text
A-D 候选提交边界仍准确
测试全部通过
git diff --check PASS
api/webui 不纳入
暂存区最终为空
未 commit
可以明确判断是否允许进入实际逐组 commit
```

## 下一步

如果 Isolation-12 PASS：

```text
下一步不是自动 Release-1，而是等待明确授权：
“开始按 A-D 顺序实际提交”
```

只有收到明确授权后，才允许逐组 commit。
