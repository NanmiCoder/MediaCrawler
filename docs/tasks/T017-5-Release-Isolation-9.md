T017-5-Release-Isolation-9：前序 A-D patch manifest 转实际拆分演练。

本轮只做前序成果拆分演练，不提交 commit。允许临时暂存并 reset，禁止实际提交。

## 当前状态

```text
T017-5：功能已 CLOSED
T017-5 Release-1：继续 NO-GO
T017-5-Release-Isolation-8：PASS
```

Isolation-8 已确认 web 三组未来提交边界：

```text
1. web baseline：39 个 checkpoint 文件
2. runtime web port：constants.ts + vite.config.ts
3. T017-5 frontend：client.ts + types.ts + DataPage.tsx + TaskDetailPage.tsx
```

但 Release-1 仍阻断，因为：

```text
前序 A-D 尚未形成独立提交
API 测试尚未迁移或明确处理
runtime port 全局契约仍需统一
api/webui 仍暂缓
```

## 本轮目标

验证前序 A-D 是否可以拆成独立提交组：

```text
A. T016 search_result.csv 标准化与 workspace 输出
B. T017-2 comments_clean 输出
C. T017-3 search_title_clean 输出
D. T017-4 script_sources / script_raw / script_clean 输出
```

本轮只演练，不 commit。

## 禁止

```text
禁止 git commit
禁止 git add .
禁止整文件提交 core.py / routes.py
禁止处理 api/webui
禁止修改业务逻辑
禁止格式化
禁止删除文件
禁止处理 CDP
禁止处理 ASR
禁止接 AI/LLM
```

## 允许

```text
允许 git add -p 演练
允许 git diff --cached 检查
允许 git reset 取消暂存
允许运行指定测试
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
web/node_modules / workspaces ignored
```

## 二、A 组：T016 标准搜索输出演练

目标 commit：

```text
feat(scraper): standardize search outputs in task workspaces
```

候选范围：

```text
douyin_scraper/core.py
api/routes.py
api/tasks.py
搜索输出相关测试
```

只演练暂存以下能力：

```text
search_result.jsonl / search_result.csv
workspace 输出
CSV UTF-8-SIG
标准 18 字段
result 优先 search_result.csv
```

检查 staged diff：

```powershell
git diff --cached -- douyin_scraper/core.py api/routes.py api/tasks.py
```

要求：

```text
不包含 comments_clean
不包含 title_clean
不包含 script_sources/raw/clean
不包含 content_asset
```

演练后取消暂存：

```powershell
git reset -- douyin_scraper/core.py api/routes.py api/tasks.py
git diff --cached --name-status
```

## 三、B 组：comments_clean 输出演练

目标 commit：

```text
feat(scraper): add raw and cleaned comment outputs
```

候选范围：

```text
douyin_scraper/core.py
api/routes.py
api/tasks.py
crawl_comments_v2.py
评论输出相关测试
```

只演练暂存以下能力：

```text
comments_raw.jsonl/csv
comments_clean.jsonl/csv
comment_data_status 前置能力
comments result selector
```

要求：

```text
不包含 title_clean
不包含 script_clean
不包含 content_asset
不处理 CDP 真实采集修复
```

演练后 reset，保持暂存区为空。

## 四、C 组：search_title_clean 输出演练

目标 commit：

```text
feat(scraper): add cleaned search title outputs
```

候选范围：

```text
douyin_scraper/core.py
api/routes.py
标题清洗相关测试
```

只演练暂存：

```text
search_title_clean.jsonl/csv
topic / pain_point / teaching_angle
title noise clean
```

要求：

```text
不包含 scripts
不包含 content_asset
```

演练后 reset。

## 五、D 组：script_sources / script_raw / script_clean 输出演练

目标 commit：

```text
feat(scraper): add script source raw and clean outputs
```

候选范围：

```text
douyin_scraper/core.py
api/routes.py
api/tasks.py
pyproject.toml 可选依赖 hunk
script 相关测试
```

只演练暂存：

```text
script_sources.jsonl/csv
script_raw.jsonl/csv
script_clean.jsonl/csv
dependency_missing 降级
script result selector
```

要求：

```text
不安装 whisper
不处理真实 ASR
不包含 content_asset builder
```

演练后 reset。

## 六、测试拆分判断

当前综合测试不适合直接提交。请判断并输出建议：

```text
test_search_outputs.py
test_comments_outputs.py
test_title_clean.py
test_script_outputs.py
```

回答：

```text
1. 哪些现有测试应该迁移到哪个文件？
2. 是否必须先迁移测试再进入 Release-1？
3. 哪些测试可以先暂缓？
```

本轮不迁移，只判断。

## 七、最终检查

```powershell
git diff --cached --name-status
git status --short
```

要求：

```text
暂存区为空
未 commit
工作区不因演练产生新改动
```

## 八、最终报告

输出：

```markdown
# T017-5-Release-Isolation-9 报告

## 1. 执行结论

## 2. A 组 T016 暂存演练结果

## 3. B 组 comments 暂存演练结果

## 4. C 组 title 暂存演练结果

## 5. D 组 scripts 暂存演练结果

## 6. 测试拆分建议

## 7. 暂存区最终状态

## 8. 是否允许进入 Isolation-10 / Release-1
```

## 判断标准

```text
明确 A-D 是否可独立暂存
明确哪些 hunk 难以拆分
明确测试拆分方案
演练后暂存区为空
未 commit
Release-1 继续 NO-GO，除非 A-D 和测试拆分已清楚到可执行
```
