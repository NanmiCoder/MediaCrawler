T017-5-Release-Isolation-7：web baseline / runtime patch / frontend patch 暂存分组演练。

本轮允许进行暂存分组演练，但禁止 commit。目标是验证 web baseline、runtime web patch、T017-5 frontend patch 能否被安全拆成 3 个提交组。

## 当前状态

```text
T017-5：功能已 CLOSED
T017-5 Release-1：继续 NO-GO
T017-5-Release-Isolation-6R：PASS
```

Isolation-6R 已完成：

```text
39 个 web baseline 文件已显式恢复
runtime-port-web.patch 已应用
t017-5-frontend.patch 已应用
npm run build PASS
暂存区为空
web/ 仍为未跟踪
api/webui 有构建变化但未处理
```

## 本轮目标

验证以下 3 组能否安全暂存：

```text
1. web baseline
2. runtime web port patch
3. T017-5 frontend patch
```

本轮只做 staged diff 演练，不提交 commit。

## 禁止

```text
禁止 git commit
禁止处理 api/webui
禁止提交 api/webui
禁止修改后端
禁止修改 builder
禁止处理 CDP
禁止处理 ASR
禁止接 AI/LLM
禁止整目录 git add web/
禁止 git add .
禁止删除文件
禁止改端口以外内容
```

## 允许

```text
允许 git add -N 指定 web baseline 文件
允许 git add -p 指定文件
允许 git diff --cached 检查 staged 内容
允许 git reset 取消暂存
允许 git status 检查
禁止 commit
```

## 一、执行前检查

```powershell
git status --short
git diff --cached --name-status
git status --short api/webui
git status --ignored --short
```

要求：

```text
暂存区为空
web/node_modules ignored
web/tsconfig.tsbuildinfo ignored
workspaces ignored
api/webui 有变化但本轮不处理
```

## 二、定义 39 个 web baseline 文件

使用 Isolation-6R 的 39 路径：

```powershell
$webBaseline = @(
  'web/index.html',
  'web/package.json',
  'web/package-lock.json',
  'web/postcss.config.js',
  'web/public/vite.svg',
  'web/tailwind.config.ts',
  'web/tsconfig.json',
  'web/tsconfig.node.json',
  'web/vite.config.ts',
  'web/src/App.tsx',
  'web/src/index.css',
  'web/src/main.tsx',
  'web/src/vite-env.d.ts',
  'web/src/api/client.ts',
  'web/src/api/types.ts',
  'web/src/hooks/usePolling.ts',
  'web/src/hooks/useWebSocket.ts',
  'web/src/store/useSettingsStore.ts',
  'web/src/store/useTaskStore.ts',
  'web/src/theme/theme.ts',
  'web/src/utils/constants.ts',
  'web/src/utils/format.ts',
  'web/src/pages/AnalyticsPage.tsx',
  'web/src/pages/CreateTaskPage.tsx',
  'web/src/pages/DashboardPage.tsx',
  'web/src/pages/DataPage.tsx',
  'web/src/pages/SettingsPage.tsx',
  'web/src/pages/TaskDetailPage.tsx',
  'web/src/pages/TaskListPage.tsx',
  'web/src/components/dashboard/HealthPanel.tsx',
  'web/src/components/dashboard/RecentTasks.tsx',
  'web/src/components/dashboard/StatsCards.tsx',
  'web/src/components/layout/AppLayout.tsx',
  'web/src/components/shared/ConnectionIndicator.tsx',
  'web/src/components/shared/ErrorAlert.tsx',
  'web/src/components/shared/LoadingOverlay.tsx',
  'web/src/components/task/DeleteConfirmDialog.tsx',
  'web/src/components/task/StatusBadge.tsx',
  'web/src/components/task/TaskTypeIcon.tsx'
)
```

## 三、暂存组 1：web baseline 演练

由于 web/ 当前是未跟踪，不能直接 `git add web/`。

建议方式：

```powershell
git add -N -- $webBaseline
```

然后只暂存 baseline 版本，排除 6 个已应用 patch 文件中的后续改动。

需要检查：

```powershell
git diff --cached --name-status -- web
git diff --cached --stat -- web
```

目标 staged 内容：

```text
39 个 web baseline 文件作为新增文件
但不能包含 runtime port patch 和 T017-5 frontend patch 的改动
```

注意：如果 `git add -N` 后无法把 baseline 和 patch 后内容拆开，则报告：web baseline 与后续 patch 在当前工作区仍需通过重新恢复 baseline 后单独暂存，而不是在当前状态直接暂存。

建议验证方式：

```powershell
git diff --cached -- web/src/utils/constants.ts web/vite.config.ts
git diff --cached -- web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx web/src/api/client.ts web/src/api/types.ts
```

要求：

```text
baseline commit 不应包含 18080/15173 runtime patch
baseline commit 不应包含 content_asset 前端 UX patch
```

如果 staged diff 已包含这些内容，立即 `git reset -- web`，并报告当前状态不适合直接拆 baseline。

## 四、取消暂存

无论成功与否，组 1 演练结束后都取消暂存：

```powershell
git reset -- web
git diff --cached --name-status
```

要求暂存区为空。

## 五、暂存组 2：runtime web patch 演练

这组文件：

```text
web/src/utils/constants.ts
web/vite.config.ts
```

前提：web baseline 已能作为独立提交存在。当前只是演练。

命令建议：

```powershell
git add -p -- web/src/utils/constants.ts web/vite.config.ts
```

检查 staged diff：

```powershell
git diff --cached -- web/src/utils/constants.ts web/vite.config.ts
```

目标：

```text
只包含 18080 / 15173 等 runtime web port 改动
不包含 content_asset 前端 UX
不包含无关格式化
```

演练后取消暂存：

```powershell
git reset -- web/src/utils/constants.ts web/vite.config.ts
git diff --cached --name-status
```

## 六、暂存组 3：T017-5 frontend patch 演练

这组文件：

```text
web/src/pages/DataPage.tsx
web/src/pages/TaskDetailPage.tsx
web/src/api/client.ts
web/src/api/types.ts
```

前提：web baseline 和 runtime patch 已能独立提交。当前只是演练。

命令建议：

```powershell
git add -p -- web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx web/src/api/client.ts web/src/api/types.ts
```

检查 staged diff：

```powershell
git diff --cached -- web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx web/src/api/client.ts web/src/api/types.ts
```

目标：

```text
只包含 content_asset 展示、下载、preview limit、核心列/全部字段切换、类型/API helper
不包含 runtime port
不包含无关前端基线
```

演练后取消暂存：

```powershell
git reset -- web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx web/src/api/client.ts web/src/api/types.ts
git diff --cached --name-status
```

## 七、最终检查

```powershell
git diff --cached --name-status
git status --short
git status --ignored --short
```

要求：

```text
暂存区为空
未 commit
web/node_modules ignored
web/tsconfig.tsbuildinfo ignored
workspaces ignored
api/webui 未被暂存
```

## 八、最终报告

输出：

```markdown
# T017-5-Release-Isolation-7 报告

## 1. 执行结论

## 2. web baseline 暂存演练结果

## 3. runtime web patch 暂存演练结果

## 4. T017-5 frontend patch 暂存演练结果

## 5. api/webui 是否保持未处理

## 6. 暂存区最终状态

## 7. 是否允许进入 Isolation-8 / Release-1
```

## 判断标准

```text
明确 web baseline 是否可独立暂存
明确 runtime web patch 是否可独立暂存
明确 T017-5 frontend patch 是否可独立暂存
所有演练后暂存区为空
未 commit
api/webui 未处理
Release-1 继续 NO-GO
```

## 下一步建议

如果 Isolation-7 PASS：

```text
Isolation-8：实际 web baseline / runtime web / frontend 三组提交前最终验证
```

仍然不进入 Release-1，直到前序 A-D 和 API 测试拆分也完成。
