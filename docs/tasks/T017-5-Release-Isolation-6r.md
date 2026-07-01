T017-5-Release-Isolation-6R：修订版 web baseline 恢复与 patch 应用验证。

本轮允许显式恢复 39 个 web baseline 文件，并重新应用已生成 patch，但必须先确认当前文件已是 patch 后版本。禁止 commit，禁止整目录 checkout/restore，禁止处理 api/webui。

## 当前状态

```text
T017-5-Release-Isolation-6：STOP
原因：patch 正向 apply-check 失败，反向 apply-check 通过
判断：当前 web 文件已经处于 patch 应用后的已验收版本
```

上一轮未执行：

```text
39路径恢复
patch 应用
npm run build
git add
git commit
```

暂存区仍为空。

## 本轮目标

修订执行顺序：

```text
1. 确认当前六个 web 文件是 patch 后版本
2. 保存当前状态备份信息
3. 显式恢复 39 个 web baseline 文件
4. 恢复后检查 patch 正向 apply-check
5. 应用 runtime-port-web.patch
6. 应用 t017-5-frontend.patch
7. 运行 npm run build
8. 确认暂存区为空
9. 判断是否允许进入 Isolation-7
```

## 禁止

```text
禁止 git commit
禁止 git add
禁止 git checkout <tree> -- web/
禁止 git restore --source=<tree> --worktree -- web/
禁止整目录恢复 web/
禁止修改 api/webui
禁止处理后端业务代码
禁止处理 CDP
禁止处理 ASR
禁止接 AI/LLM
禁止删除 node_modules
禁止删除 workspaces
```

## 允许

```text
允许 git restore 显式 39 路径
允许 git apply runtime-port-web.patch
允许 git apply t017-5-frontend.patch
允许运行 npm run build
允许 git status / git diff 检查
禁止 commit
```

## 一、执行前确认当前状态

```powershell
git status --short
git diff --cached --name-status
git apply --reverse --check C:\tmp\t0175-release\runtime-port-web.patch
git apply --reverse --check C:\tmp\t0175-release\t017-5-frontend.patch
```

要求：

```text
暂存区为空
两个 patch 的 reverse check 通过
```

如果 reverse check 不通过，停止并报告。

## 二、记录当前已应用状态

输出这六个文件当前状态：

```powershell
git status --short web/src/utils/constants.ts web/vite.config.ts
git status --short web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx web/src/api/client.ts web/src/api/types.ts
```

说明：

```text
这些文件当前应是 patch 后版本。
接下来恢复 baseline 会暂时覆盖它们。
patch 文件已保存在 C:\tmp\t0175-release\。
```

## 三、显式恢复 39 个 web baseline 文件

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

禁止执行：

```powershell
git checkout aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 -- web/
git restore --source=aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 --worktree -- web/
```

## 四、恢复 baseline 后检查

```powershell
git status --short web
git apply --check C:\tmp\t0175-release\runtime-port-web.patch
git apply --check C:\tmp\t0175-release\t017-5-frontend.patch
```

要求：

```text
两个 patch 的正向 apply-check 必须通过
```

如果不通过，停止，不要强行 apply。

## 五、应用 runtime-port-web.patch

```powershell
git apply C:\tmp\t0175-release\runtime-port-web.patch
```

验证：

```powershell
git diff -- web/src/utils/constants.ts web/vite.config.ts
git apply --reverse --check C:\tmp\t0175-release\runtime-port-web.patch
```

要求：

```text
只影响 constants.ts 和 vite.config.ts
reverse check 通过
```

## 六、应用 T017-5 frontend patch

```powershell
git apply C:\tmp\t0175-release\t017-5-frontend.patch
```

验证：

```powershell
git diff -- web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx web/src/api/client.ts web/src/api/types.ts
git apply --reverse --check C:\tmp\t0175-release\t017-5-frontend.patch
```

要求：

```text
只影响四个 T017-5 前端文件
reverse check 通过
```

## 七、前端构建验证

```powershell
cd web
npm run build
cd ..
```

如果缺依赖，不要安装，停止并报告。

注意：

```text
npm run build 可能刷新 api/webui。
本轮不要提交 api/webui。
只记录 api/webui 状态。
```

## 八、最终状态检查

```powershell
git diff --cached --name-status
git status --short
git status --ignored --short
git status --short api/webui
```

要求：

```text
暂存区为空
未 commit
web/node_modules 仍 ignored
workspaces 仍 ignored
api/webui 如有变化只记录，不处理
```

## 九、最终报告

输出：

```markdown
# T017-5-Release-Isolation-6R 报告

## 1. 执行结论

## 2. 执行前 reverse check 结果

## 3. 39 路径 baseline 恢复结果

## 4. patch 正向检查结果

## 5. runtime-port-web.patch 应用结果

## 6. t017-5-frontend.patch 应用结果

## 7. npm run build 结果

## 8. api/webui 变化情况

## 9. git status / 暂存区状态

## 10. 是否允许进入 Isolation-7 / Release-1
```

## 通过标准

```text
执行前 reverse check 通过
39 个 web baseline 文件显式恢复
未恢复整个 web/
未带入 node_modules
未带入 tsbuildinfo
runtime patch 正向检查并应用成功
frontend patch 正向检查并应用成功
npm run build 通过或明确失败原因
暂存区为空
未 commit
api/webui 未提交
Release-1 继续 NO-GO
```
