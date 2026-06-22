T017-5-Release-Isolation-8：web baseline / runtime web / T017-5 frontend 三组提交前最终验证。

本轮只做最终验证和提交前清单确认，不执行 commit。允许临时暂存并 reset，但禁止提交。

## 当前状态

```text
T017-5：功能已 CLOSED
T017-5 Release-1：继续 NO-GO
T017-5-Release-Isolation-7：PASS
```

Isolation-7 已确认：

```text
web baseline 可独立暂存，但必须先恢复 checkpoint baseline，再显式暂存 39 路径
runtime web patch 可独立暂存
T017-5 frontend patch 可独立暂存
api/webui 未处理、未暂存
真实暂存区最终为空
```

## 本轮目标

最终确认以下三组未来 commit 的安全边界：

```text
1. web baseline commit
2. runtime web port commit
3. T017-5 frontend commit
```

本轮只验证，不提交。

## 禁止

```text
禁止 git commit
禁止 git add .
禁止 git add web/
禁止提交 api/webui
禁止修改后端
禁止修改 builder
禁止处理 CDP
禁止处理 ASR
禁止接 AI/LLM
禁止删除 node_modules
禁止删除 workspaces
禁止修改业务逻辑
```

## 允许

```text
允许 git status / git diff 检查
允许 git add -N / git add -p 演练
允许 git diff --cached 检查
允许 git reset 取消暂存
允许 npm run build 验证
禁止 commit
```

## 一、执行前检查

```powershell
git status --short
git diff --cached --name-status
git status --ignored --short
git status --short api/webui
```

要求：

```text
暂存区为空
web/node_modules ignored
web/tsconfig.tsbuildinfo ignored
workspaces ignored
api/webui 不纳入本轮
```

## 二、确认三组未来 commit

### Commit 1：web baseline

```text
feat(web): establish Vite frontend baseline
```

文件范围：39 个 checkpoint baseline 文件。

要求：

```text
不包含 runtime 18080 / 15173 改动
不包含 content_asset 前端 UX
不包含 api/webui
不包含 node_modules
不包含 tsbuildinfo
```

### Commit 2：runtime web port

```text
chore(web): align frontend API and dev ports
```

文件范围：

```text
web/src/utils/constants.ts
web/vite.config.ts
```

要求：

```text
仅包含 API/WS 18080、Web dev 15173、Vite 环境变量化
不包含 content_asset 前端 UX
```

### Commit 3：T017-5 frontend

```text
feat(web): add content asset preview and download UX
```

文件范围：

```text
web/src/api/client.ts
web/src/api/types.ts
web/src/pages/DataPage.tsx
web/src/pages/TaskDetailPage.tsx
```

要求：

```text
仅包含 Content Asset 展示、下载、preview limit、核心列切换、API/type helper
不包含 runtime port
不包含 api/webui
```

## 三、验证 web baseline 文件清单

确认 39 个文件存在：

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

$missing = $webBaseline | Where-Object { -not (Test-Path $_) }
$missing
```

要求：

```text
missing = 空
```

## 四、验证 patch 文件仍可用

```powershell
Test-Path C:\tmp\t0175-release\runtime-port-web.patch
Test-Path C:\tmp\t0175-release\t017-5-frontend.patch
```

并记录 patch 大小：

```powershell
Get-Item C:\tmp\t0175-release\runtime-port-web.patch
Get-Item C:\tmp\t0175-release\t017-5-frontend.patch
```

## 五、三组提交前验证方式

本轮不要 commit，只输出建议命令和验证结果。

未来真正提交顺序应是：

```text
1. 恢复 checkpoint baseline
2. git add 显式 39 路径
3. commit web baseline
4. apply runtime-port-web.patch
5. git add constants.ts vite.config.ts
6. commit runtime web ports
7. apply t017-5-frontend.patch
8. git add DataPage/TaskDetailPage/client/types
9. commit T017-5 frontend
```

但本轮不提交。

## 六、前端构建验证

```powershell
cd web
npm run build
cd ..
```

记录结果。

注意：

```text
构建可能刷新 api/webui。
api/webui 不属于本轮提交。
只记录状态，不暂存、不提交。
```

## 七、最终状态检查

```powershell
git diff --cached --name-status
git status --short
git status --ignored --short
git status --short api/webui
```

要求：

```text
最终暂存区为空
未 commit
api/webui 未暂存
ignored 正常
```

## 八、最终报告

输出：

```markdown
# T017-5-Release-Isolation-8 报告

## 1. 执行结论

## 2. 三组未来 commit 边界

## 3. 39 文件清单验证

## 4. patch 文件验证

## 5. npm run build 结果

## 6. api/webui 状态

## 7. 最终暂存区状态

## 8. 是否允许进入 Isolation-9 / Release-1
```

## 判断标准

```text
明确三组 commit 边界
39 文件清单完整
patch 文件仍可用
npm run build 通过或明确失败原因
api/webui 未纳入
暂存区最终为空
Release-1 继续 NO-GO
```

## 下一步

如果 Isolation-8 PASS：

```text
Isolation-9：前序 A-D patch manifest 转实际拆分演练
```

Release-1 仍需等待前序 A-D、API 测试迁移、runtime port 全局一致性、api/webui 策略完成。
