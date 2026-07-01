T017-5-Release-Isolation-6：实际恢复 web baseline 与 patch 应用验证。

本轮允许实际恢复显式 39 个 web baseline 文件，允许应用已生成并验证通过的 frontend/runtime patch，但禁止 commit，禁止处理 api/webui，禁止整目录 checkout/restore。

## 当前状态

```text
T017-5：功能已 CLOSED
T017-5 Release-1：继续 NO-GO
T017-5-Release-Isolation-5：PASS
```

Isolation-5 已完成：

```text
checkpoint tree 可访问：
aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9

四个 patch 已生成并 apply-check PASS：
C:\tmp\t0175-release\t017-5-frontend.patch
C:\tmp\t0175-release\runtime-port-web.patch
C:\tmp\t0175-release\api-readme.patch
C:\tmp\t0175-release\api-tests.patch

39 个 web baseline 路径已验证存在。
临时 baseline 无 node_modules、无 tsbuildinfo。
真实 Git index 未污染。
```

## 本轮目标

```text
1. 显式恢复 39 个 web baseline 文件
2. 验证 web baseline 状态
3. 应用 runtime-port-web.patch
4. 验证 runtime web patch
5. 应用 t017-5-frontend.patch
6. 验证 frontend patch
7. 不提交 commit
8. 判断是否允许进入 Isolation-7
```

## 禁止

```text
禁止 git commit
禁止 git checkout <tree> -- web/
禁止 git restore --source=<tree> --worktree -- web/
禁止整目录恢复 web/
禁止修改 api/webui/
禁止处理后端业务代码
禁止处理 CDP
禁止处理 ASR
禁止接 AI/LLM
禁止改端口以外文件
禁止删除 node_modules
禁止删除 workspaces
```

## 允许

```text
允许 git restore 显式 39 路径
允许 git apply runtime-port-web.patch
允许 git apply t017-5-frontend.patch
允许运行 npm build 验证
允许 git status / git diff 检查
禁止 commit
```

## 一、执行前检查

```powershell
git status --short
git diff --cached --name-status
Test-Path C:\tmp\t0175-release\t017-5-frontend.patch
Test-Path C:\tmp\t0175-release\runtime-port-web.patch
git apply --check C:\tmp\t0175-release\runtime-port-web.patch
git apply --check C:\tmp\t0175-release\t017-5-frontend.patch
```

要求：

```text
暂存区为空
patch 文件存在
apply-check 通过
```

如果 apply-check 在当前工作区失败，先停止并报告，不要强行 apply。

## 二、显式恢复 39 个 web baseline 文件

必须使用显式路径变量，不允许恢复整个 web 目录。

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

git restore --source=aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 --worktree -- $webBaseline
```

恢复后检查：

```powershell
git status --short web
git ls-files web
Get-ChildItem web -Recurse -File | Where-Object { $_.FullName -match 'node_modules|tsbuildinfo' } | Select-Object -First 20
```

要求：

```text
web baseline 文件出现在未跟踪列表中
不能出现 web/node_modules 普通未跟踪
不能出现 tsbuildinfo
```

## 三、应用 runtime-port-web.patch

```powershell
git apply --check C:\tmp\t0175-release\runtime-port-web.patch
git apply C:\tmp\t0175-release\runtime-port-web.patch
```

验证：

```powershell
git diff -- web/src/utils/constants.ts web/vite.config.ts
git status --short web/src/utils/constants.ts web/vite.config.ts
```

要求：

```text
只影响 constants.ts 和 vite.config.ts
端口应符合：
API 宿主 18080
前端 dev 15173
不要引入 8000 宿主访问
```

## 四、应用 T017-5 frontend patch

```powershell
git apply --check C:\tmp\t0175-release\t017-5-frontend.patch
git apply C:\tmp\t0175-release\t017-5-frontend.patch
```

验证：

```powershell
git diff -- web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx web/src/api/client.ts web/src/api/types.ts
git status --short web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx web/src/api/client.ts web/src/api/types.ts
```

要求：

```text
只影响四个 T017-5 前端文件
DataPage / TaskDetailPage / client / types 恢复为已验收版本
```

## 五、前端构建验证

```powershell
cd web
npm run build
cd ..
```

如果缺依赖：

```text
不要重新安装 node_modules，先报告。
```

如果 build 通过，记录结果。

注意：

```text
npm run build 可能刷新 api/webui。
如果刷新 api/webui，本轮不要提交 api/webui。
只记录变化。
```

## 六、确认 api/webui 未被本轮纳入

```powershell
git status --short api/webui
git diff --name-status -- api/webui
```

要求：

```text
api/webui 可有 build 产生的变化，但本轮不得提交。
如 build 刷新了 api/webui，只记录，不处理。
```

## 七、最终状态检查

```powershell
git diff --cached --name-status
git status --short
git status --ignored --short
```

要求：

```text
暂存区仍为空
web/node_modules 仍 ignored
workspaces 仍 ignored
无 git add
无 git commit
```

## 八、最终报告

输出：

```markdown
# T017-5-Release-Isolation-6 报告

## 1. 执行结论

## 2. 39 路径恢复结果

## 3. runtime-port-web.patch 应用结果

## 4. t017-5-frontend.patch 应用结果

## 5. 前端构建结果

## 6. api/webui 变化情况

## 7. git status / 暂存区状态

## 8. 是否允许进入 Isolation-7 / Release-1
```

## 判断标准

```text
39 个 web baseline 文件已显式恢复
未恢复整个 web/
未带入 node_modules
未带入 tsbuildinfo
runtime web patch 应用成功
T017-5 frontend patch 应用成功
npm run build 通过或明确失败原因
暂存区为空
未 commit
api/webui 未被提交
Release-1 继续 NO-GO
```

## 下一步建议

如果 Isolation-6 PASS，Isolation-7 建议定位为：

```text
T017-5-Release-Isolation-7：web baseline / runtime patch / frontend patch 暂存分组演练
```

仍然先不 commit。
