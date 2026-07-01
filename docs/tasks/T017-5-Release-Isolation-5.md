T017-5-Release-Isolation-5：临时补丁生成与 checkpoint 恢复演练。

本轮允许生成临时 patch 文件和临时目录验证，但禁止提交 commit，禁止正式暂存，禁止整目录 checkout，禁止污染真实 Git index。

## 当前状态

```text
T017-5：功能已 CLOSED
T017-5 Release-1：继续 NO-GO
T017-5-Release-Isolation-4：PASS
```

Isolation-4 已确认：

```text
checkpoint tree 可访问：
aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9

checkpoint 类型：
tree

web/ 中包含历史 node_modules，因此禁止：
git checkout aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 -- web/
```

## 本轮目标

只做恢复演练，不进入提交阶段：

```text
1. 使用临时索引生成 patch
2. 验证 T017-5 前端 patch 可保存
3. 验证 runtime port web patch 可保存
4. 验证 api/README.md patch 可保存
5. 验证 api/tests.py patch 可保存
6. 验证 checkpoint 中 39 个 web baseline 文件可显式恢复
7. 输出下一步 Isolation-6 是否可以进入
```

## 禁止

```text
禁止 git add
禁止 git commit
禁止 git checkout <tree> -- web/
禁止 git restore 整个 web/
禁止污染真实 Git index
禁止修改业务代码
禁止修改前端逻辑
禁止修改后端逻辑
禁止修改 api/webui
禁止删除 node_modules
禁止删除 workspaces
禁止处理 CDP
禁止处理 ASR
禁止接 AI/LLM
禁止改端口
```

## 允许

仅允许：

```text
生成临时 patch 文件
使用临时 GIT_INDEX_FILE
使用临时目录验证
只读检查 Git 对象
```

临时文件建议放到仓库外，例如：

```text
C:\tmp\t0175-release\
```

## 一、准备临时目录

```powershell
New-Item -ItemType Directory -Force C:\tmp\t0175-release | Out-Null
```

## 二、验证 checkpoint

```powershell
git cat-file -t aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9
git ls-tree -r --name-only aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 -- web | Measure-Object
git ls-tree -r --name-only aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 -- api/README.md
git ls-tree -r --name-only aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 -- api/tests.py
```

确认：

```text
checkpoint 类型为 tree
web/ 中文件很多，但合法 baseline 只取显式 39 个路径
api/README.md 存在
api/tests.py 存在
```

## 三、使用临时索引生成 patch

注意：必须使用临时索引，不污染真实 index。

```powershell
$env:GIT_INDEX_FILE='C:\tmp\t0175-release\checkpoint.index'
git read-tree aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9
```

生成 patch：

```powershell
git diff -- web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx web/src/api/client.ts web/src/api/types.ts > C:\tmp\t0175-release\t017-5-frontend.patch

git diff -- web/src/utils/constants.ts web/vite.config.ts > C:\tmp\t0175-release\runtime-port-web.patch

git diff -- api/README.md > C:\tmp\t0175-release\api-readme.patch

git diff -- api/tests.py > C:\tmp\t0175-release\api-tests.patch
```

清理临时索引环境变量：

```powershell
Remove-Item Env:GIT_INDEX_FILE
```

验证真实暂存区没有被污染：

```powershell
git diff --cached --name-status
git status --short
```

要求：

```text
git diff --cached --name-status 为空
真实工作区除已有改动外，不应新增 staged 内容
```

## 四、验证 patch 文件

检查 patch 是否存在且非空：

```powershell
Get-Item C:\tmp\t0175-release\*.patch | Select-Object Name,Length
```

要求：

```text
t017-5-frontend.patch 非空
runtime-port-web.patch 非空
api-readme.patch 非空
api-tests.patch 非空
```

如果某个 patch 为空，说明当前文件与 checkpoint 无差异，需在报告中说明。

## 五、显式 39 路径恢复演练方案

本轮不要实际恢复仓库文件，只输出命令清单。

必须使用显式路径，不允许整目录恢复。

39 个 web baseline 路径使用 Isolation-4 确认清单：

```text
web/index.html
web/package.json
web/package-lock.json
web/postcss.config.js
web/public/vite.svg
web/tailwind.config.ts
web/tsconfig.json
web/tsconfig.node.json
web/vite.config.ts
web/src/App.tsx
web/src/index.css
web/src/main.tsx
web/src/vite-env.d.ts
web/src/api/client.ts
web/src/api/types.ts
web/src/hooks/usePolling.ts
web/src/hooks/useWebSocket.ts
web/src/store/useSettingsStore.ts
web/src/store/useTaskStore.ts
web/src/theme/theme.ts
web/src/utils/constants.ts
web/src/utils/format.ts
web/src/pages/AnalyticsPage.tsx
web/src/pages/CreateTaskPage.tsx
web/src/pages/DashboardPage.tsx
web/src/pages/DataPage.tsx
web/src/pages/SettingsPage.tsx
web/src/pages/TaskDetailPage.tsx
web/src/pages/TaskListPage.tsx
web/src/components/dashboard/HealthPanel.tsx
web/src/components/dashboard/RecentTasks.tsx
web/src/components/dashboard/StatsCards.tsx
web/src/components/layout/AppLayout.tsx
web/src/components/shared/ConnectionIndicator.tsx
web/src/components/shared/ErrorAlert.tsx
web/src/components/shared/LoadingOverlay.tsx
web/src/components/task/DeleteConfirmDialog.tsx
web/src/components/task/StatusBadge.tsx
web/src/components/task/TaskTypeIcon.tsx
```

后续真正恢复时，应使用：

```powershell
git restore --source=aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 --worktree -- <39个明确路径>
```

禁止：

```powershell
git checkout aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 -- web/
git restore --source=aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 --worktree -- web/
```

## 六、patch 应用演练方案

本轮不要应用到真实工作区。只输出后续建议命令。

后续顺序建议：

```text
1. 保存 patch
2. 显式 39 路径恢复 web baseline
3. 提交 web baseline
4. 应用 runtime-port-web.patch
5. 提交 runtime port web 部分
6. 应用 t017-5-frontend.patch
7. 提交 T017-5 frontend
```

patch 检查命令建议：

```powershell
git apply --check C:\tmp\t0175-release\t017-5-frontend.patch
git apply --check C:\tmp\t0175-release\runtime-port-web.patch
```

注意：只有在恢复 baseline 后再执行 `git apply --check` 才有意义。

## 七、api/README.md 与 api/tests.py 后续方案

输出建议：

```text
api/README.md:
1. 先从 checkpoint 恢复 baseline
2. 提交 API README baseline
3. 应用 runtime/API 文档 patch
4. 应用 content_asset 文档 patch

api/tests.py:
1. 不建议直接应用综合 patch
2. 建议迁移 content_asset API 测试到 douyin_scraper/tests/test_content_asset_api.py
3. 建议迁移 task result selector 测试到 douyin_scraper/tests/test_task_result_selection.py
4. api/tests.py baseline 是否提交，后续单独决定
```

## 八、最终报告

输出：

```markdown
# T017-5-Release-Isolation-5 报告

## 1. 执行结论

## 2. checkpoint 验证结果

## 3. 临时 patch 生成结果

## 4. 真实 Git index 是否被污染

## 5. 39 路径恢复命令清单

## 6. patch 应用顺序建议

## 7. api/README.md 与 api/tests.py 后续处理

## 8. 是否允许进入 Isolation-6 / Release-1
```

## 判断标准

```text
临时 patch 已生成
真实 Git index 未污染
未执行 git add
未执行 git commit
未整目录 checkout web/
未修改 api/webui
明确 39 路径恢复方案
明确后续 patch 应用顺序
Release-1 继续 NO-GO
```
