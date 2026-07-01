T017-5-Release-Web-1：web baseline / runtime web / Content Asset UX 三组实际提交。

本轮允许按顺序创建 3 个 Web commit，但必须严格分组。禁止提交 api/webui 构建产物，禁止提交 Docs，禁止提交后端，禁止提交 runtime 全局端口契约。

## 当前状态

```text
A-D 前序成果已提交
Builder 已提交
API 已提交
API commit: adcc7f29 feat(api): expose content asset result preview and export
暂存区为空
未 push
```

## 目标提交顺序

```text
1. feat(web): establish Vite frontend baseline
2. chore(web): align frontend API and dev ports
3. feat(web): add content asset preview and download UX
```

## 严禁

```text
禁止 git add .
禁止 git add web/
禁止提交 api/webui
禁止提交 Docs
禁止提交后端
禁止提交 runtime 全局端口契约
禁止提交 crawl_comments_v2.py
禁止提交 pyproject.toml
禁止处理 CDP
禁止处理真实 Whisper/ASR
禁止接 AI/LLM
禁止 push
```

## Commit 1：web baseline

Message：

```text
feat(web): establish Vite frontend baseline
```

只允许提交 39 个 checkpoint baseline 文件。

必须先显式恢复 baseline，再显式暂存 39 路径。

禁止整目录 restore：

```powershell
git checkout aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 -- web/
git restore --source=aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 --worktree -- web/
```

使用显式路径：

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
git add -- $webBaseline
```

提交前检查：

```powershell
git diff --cached --stat
git diff --cached --name-status
git diff --cached --check
git diff --cached -- web/src/utils/constants.ts web/vite.config.ts
git diff --cached -- web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx web/src/api/client.ts web/src/api/types.ts
```

要求：

```text
只包含 39 个 web baseline 文件
不包含 18080 / 15173 runtime port patch
不包含 Content Asset UX
不包含 api/webui
不包含 node_modules
不包含 tsbuildinfo
```

提交：

```powershell
git commit -m "feat(web): establish Vite frontend baseline"
```

## Commit 2：runtime web port

Message：

```text
chore(web): align frontend API and dev ports
```

应用 patch：

```powershell
git apply --check C:\tmp\t0175-release\runtime-port-web.patch
git apply C:\tmp\t0175-release\runtime-port-web.patch
```

只允许暂存：

```text
web/src/utils/constants.ts
web/vite.config.ts
```

```powershell
git add web/src/utils/constants.ts web/vite.config.ts
```

提交前检查：

```powershell
git diff --cached --stat
git diff --cached --name-status
git diff --cached --check
git diff --cached -- web/src/utils/constants.ts web/vite.config.ts
```

要求：

```text
只包含 API/WS 18080、Web dev 15173、Vite 环境变量化
不包含 Content Asset UX
不包含 api/webui
```

提交：

```powershell
git commit -m "chore(web): align frontend API and dev ports"
```

## Commit 3：T017-5 frontend UX

Message：

```text
feat(web): add content asset preview and download UX
```

应用 patch：

```powershell
git apply --check C:\tmp\t0175-release\t017-5-frontend.patch
git apply C:\tmp\t0175-release\t017-5-frontend.patch
```

只允许暂存：

```text
web/src/api/client.ts
web/src/api/types.ts
web/src/pages/DataPage.tsx
web/src/pages/TaskDetailPage.tsx
```

```powershell
git add web/src/api/client.ts web/src/api/types.ts web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx
```

提交前检查：

```powershell
git diff --cached --stat
git diff --cached --name-status
git diff --cached --check
git diff --cached -- web/src/api/client.ts web/src/api/types.ts web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx
```

要求：

```text
只包含 Content Asset 展示、下载、preview limit、核心列切换、API/type helper
不包含 runtime port
不包含 api/webui
```

提交：

```powershell
git commit -m "feat(web): add content asset preview and download UX"
```

## 三个 commit 完成后验证

```powershell
cd web
npm.cmd run build
cd ..

git status --short
git diff --check
git log --oneline -10
```

注意：

```text
npm build 可能刷新 api/webui。
api/webui 不得提交，本轮只记录。
```

## 最终报告

输出：

```markdown
# T017-5-Release-Web-1 报告

## 1. 执行结论

## 2. Web baseline commit hash

## 3. Runtime web commit hash

## 4. Content Asset frontend commit hash

## 5. 构建验证结果

## 6. api/webui 状态

## 7. 剩余工作区状态

## 8. 是否允许进入 Docs 提交阶段
```

## 通过标准

```text
3 个 Web commit 创建成功
baseline 不含 runtime/content_asset
runtime 不含 content_asset
frontend 不含 runtime
api/webui 未提交
npm build PASS 或明确失败原因
暂存区最终为空
未 push
```
