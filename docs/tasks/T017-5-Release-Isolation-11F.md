T017-5-Release-Isolation-11F：api/webui diff-check 污染隔离/豁免方案确认。

本轮只处理全局 `git diff --check` 被既有 `api/webui/index.html` 尾随空格阻断的问题。目标是确认是否恢复、暂缓、还是在 A-D 提交流程中使用范围限定 diff-check。禁止提交 commit。

## 当前状态

```text
T017-5：功能已 CLOSED
T017-5 Release-1：继续 NO-GO
T017-5-Release-Isolation-11：条件性 NO-GO
```

Isolation-11 结果：

```text
A-D 候选提交复核全部通过
A-D 范围 git diff --check：PASS
全局 git diff --check：FAIL
失败仅涉及既有 api/webui/index.html 尾随空格
api/webui 当前禁止处理、未暂存、未提交
最终暂存区为空
```

## 本轮目标

确认以下问题：

```text
1. api/webui/index.html 的尾随空格是否来自构建产物既有污染
2. 是否可以恢复 api/webui 到 HEAD 来解除全局 diff-check 阻断
3. 如果不能恢复，是否允许 A-D 提交使用范围限定 git diff --check
4. 是否需要建立“api/webui 暂缓区”规则
5. 是否允许重新进入 Isolation-12
```

## 禁止

```text
禁止 git commit
禁止处理 A-D 业务代码
禁止处理 T017-5 content_asset
禁止处理 web 源码
禁止处理 CDP
禁止处理 ASR
禁止接 AI/LLM
禁止 git add .
禁止提交 api/webui
```

## 允许

```text
允许只读检查 api/webui
允许 git diff --check -- api/webui/index.html
允许 git diff --name-status -- api/webui
允许判断是否恢复 api/webui 到 HEAD
如果明确选择恢复，允许只恢复 api/webui 到 HEAD，但不得暂存或提交
```

## 一、执行前检查

```powershell
git status --short
git diff --cached --name-status
git diff --check
git diff --check -- api/webui/index.html
git diff --name-status -- api/webui
```

记录：

```text
全局 diff-check 是否只因 api/webui/index.html 失败
api/webui 当前有哪些修改/删除/新增
暂存区是否为空
```

## 二、判断 api/webui 是否应恢复

api/webui 当前是构建产物区，Isolation-8/6R 已多次确认：

```text
旧 bundle 删除
新 bundle 未跟踪
index.html / vite.svg 修改
5 个 Logo 删除
当前不允许提交
```

请判断：

```text
1. api/webui 当前变化是否全部属于构建产物/静态资源变化？
2. 当前阶段是否应恢复 api/webui 到 HEAD？
3. 恢复 api/webui 是否会影响 A-D、web baseline、runtime patch、frontend patch？
4. 恢复 api/webui 是否会删除新 bundle 未跟踪文件？
5. 是否需要额外清理未跟踪新 bundle？本轮默认不删除，除非明确确认。
```

## 三、方案选择

输出三种方案并推荐一种。

### 方案 A：恢复 api/webui 到 HEAD

用途：

```text
解除全局 git diff --check 阻断
保证 Release 隔离阶段不被构建产物污染
```

建议命令：

```powershell
git restore --worktree -- api/webui
```

然后检查：

```powershell
git status --short api/webui
git diff --check
git diff --cached --name-status
```

注意：

```text
此命令只恢复已跟踪的 api/webui 文件。
未跟踪的新 bundle 可能仍存在。
本轮不要删除未跟踪新 bundle，除非报告确认它们仍干扰 status 且需要清理。
```

### 方案 B：不恢复 api/webui，A-D 使用范围限定 diff-check

用途：

```text
保留当前构建产物状态，A-D 提交时只对 A-D 范围执行 git diff --check
```

建议命令模式：

```powershell
git diff --check -- douyin_scraper/core.py api/routes.py api/tasks.py douyin_scraper/tests/test_search_outputs.py douyin_scraper/tests/test_comments_outputs.py douyin_scraper/tests/test_title_clean.py douyin_scraper/tests/test_script_outputs.py douyin_scraper/tests/test_task_result_selection.py
```

风险：

```text
全局 diff-check 仍失败
提交前门禁不干净
容易遗漏非 A-D 污染
```

### 方案 C：将 api/webui 作为独立污染区暂缓

用途：

```text
明确 api/webui 不参与 A-D/T017-5 源码提交
只在最后 build(webui) 阶段统一处理
```

可与方案 A 或 B 组合。

## 四、推荐判断

优先推荐：

```text
如果 api/webui 当前变化全部是构建产物污染，执行方案 A：恢复已跟踪 api/webui 到 HEAD。
未跟踪新 bundle 暂不删除，只记录。
如果恢复后全局 diff-check PASS，则允许进入 Isolation-12。
```

如果不能恢复：

```text
明确采用方案 B + C：
A-D 提交只使用范围限定 diff-check
api/webui 保持暂缓
Release-1 仍需更严格审批
```

## 五、最终检查

```powershell
git diff --cached --name-status
git status --short
git diff --check
git status --short api/webui
```

要求：

```text
暂存区为空
未 commit
A-D 业务文件未改变
api/webui 处理策略明确
```

## 六、最终报告

输出：

```markdown
# T017-5-Release-Isolation-11F 报告

## 1. 执行结论

## 2. diff-check 失败来源确认

## 3. api/webui 当前状态

## 4. 方案选择与理由

## 5. 是否恢复 api/webui 到 HEAD

## 6. 最终 git diff --check 结果

## 7. 暂存区最终状态

## 8. 是否允许进入 Isolation-12 / Release-1
```

## 通过标准

```text
确认 diff-check 阻断来源
明确 api/webui 是恢复还是豁免
暂存区最终为空
未 commit
A-D 候选提交不被破坏
允许或不允许进入 Isolation-12 有明确依据
Release-1 继续等待最终授权
```
