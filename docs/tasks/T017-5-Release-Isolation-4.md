T017-5-Release-Isolation-4：精确暂存清单、checkpoint 恢复步骤和逐 commit patch manifest。

本轮只做只读查询和方案输出，不修改文件，不暂存，不提交 commit。

## 当前状态

```text
T017-5：功能已 CLOSED
T017-5 Release-1：继续 NO-GO
T017-5-Release-Isolation-1：PASS
T017-5-Release-Isolation-2：PASS
T017-5-Release-Isolation-3：PASS
```

Isolation-3 发现可恢复前功能基线：

```text
Codex checkpoint tree:
aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9

时间：
2026-06-17 13:38:16 UTC+8
```

注意：这是内部 tree ref，不是普通 Git commit。必须先验证可访问性和恢复方式。本轮只查询，不执行恢复。

## 本轮目标

输出可执行但本轮不执行的 release 隔离 manifest：

```text
1. checkpoint tree 可访问性验证方案
2. web baseline 39 文件恢复方案
3. api/README.md baseline 恢复方案
4. api/tests.py baseline / 测试迁移方案
5. 前序 A-D patch 暂存 manifest
6. T017-5 builder/API/frontend/docs patch manifest
7. api/webui 构建产物处理方案
8. 是否允许进入 Isolation-5
9. Release-1 是否仍 NO-GO
```

## 禁止

```text
禁止修改文件
禁止 git add
禁止 git commit
禁止 git checkout / restore 实际恢复文件
禁止删除文件
禁止格式化
禁止改业务代码
禁止改前端
禁止改后端
禁止改 api/webui
禁止处理 CDP
禁止处理 ASR
禁止接 AI/LLM
禁止改端口
```

## 必须只读查询

```bash
git status --short
git diff --stat
git cat-file -t aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9
git ls-tree -r --name-only aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 -- web
git ls-tree -r --name-only aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 -- api/README.md
git ls-tree -r --name-only aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 -- api/tests.py
git status --short web
git status --short api/webui
```

PowerShell 可用同等命令。

## 一、checkpoint 可访问性与恢复方案

回答：

```text
1. checkpoint tree 是否可访问？
2. git cat-file 返回类型是什么？
3. checkpoint 中是否包含 web/ 39 个基线文件？
4. checkpoint 中是否包含 api/README.md？
5. checkpoint 中是否包含 api/tests.py？
6. 推荐如何从 checkpoint 恢复指定路径？
7. 恢复前是否需要保存当前 T017-5 前端文件补丁？
8. 是否建议先生成 patch 文件而不是直接 checkout？
```

只输出命令建议，不执行。

建议给出两种安全方案：

### 方案 A：生成 patch 文件

```bash
git diff -- web/src/pages/DataPage.tsx web/src/pages/TaskDetailPage.tsx web/src/api/client.ts web/src/api/types.ts > /tmp/t017-5-frontend.patch
git diff -- web/src/utils/constants.ts web/vite.config.ts > /tmp/runtime-port-web.patch
```

### 方案 B：使用 git checkout tree -- path 恢复基线

```bash
git checkout aeaead1458c6187b42b9c62bd104e2fb7ff1d1b9 -- web/
```

注意：本轮不要执行。

## 二、web baseline manifest

基于 checkpoint，输出 web baseline 文件清单。

必须包含：

```text
package.json
package-lock.json
vite.config.ts
tsconfig*.json
tailwind/postcss 配置
index.html
public/
src/
```

必须排除：

```text
web/node_modules/
*.tsbuildinfo
```

回答：

```text
1. baseline 应提交哪些文件？
2. 当前 T017-5 前端改动如何保存并后续恢复？
3. 当前 runtime port 改动 constants/vite.config 如何保存并后续恢复？
4. web baseline commit 是否应包含 T017-5 前端改动？
5. 建议 commit message
```

目标 commit：

```text
feat(web): establish Vite frontend baseline
```

## 三、api/README.md manifest

回答：

```text
1. checkpoint 中是否有 api/README.md 前功能版本？
2. 是否建议先恢复并提交 api/README.md baseline？
3. 当前 api/README.md 中哪些内容属于 runtime port？
4. 当前 api/README.md 中哪些内容属于 content_asset？
5. 后续拆分 commit message 是什么？
```

建议 commit：

```text
docs(api): establish API usage guide baseline
docs(api): document content asset workflow
```

端口内容如单独提交：

```text
docs(api): align API port and CDP guidance
```

## 四、api/tests.py manifest

回答：

```text
1. checkpoint 中是否有 api/tests.py 前功能版本？
2. 当前 api/tests.py 新增 content_asset 测试有哪些函数？
3. 是否建议恢复 api/tests.py baseline？
4. 是否建议迁移 content_asset API 测试到 douyin_scraper/tests/？
5. 建议新测试文件名和测试函数清单
6. 迁移前是否阻断 Release-1？
```

建议目标文件：

```text
douyin_scraper/tests/test_content_asset_api.py
douyin_scraper/tests/test_task_result_selection.py
```

注意：本轮只列方案，不迁移。

## 五、前序 A-D patch manifest

为以下前序提交列出精确 hunk manifest。

```text
A. T016 search_result.csv 标准化与 workspace 输出
B. T017-2 comments_clean 输出
C. T017-3 search_title_clean 输出
D. T017-4 script_sources / script_raw / script_clean 输出
```

每组输出：

```markdown
### A. T016 search_result.csv 标准化与 workspace 输出

Commit:
feat(scraper): standardize search outputs in task workspaces

Files:
- ...

Hunks:
- core.py: ...
- routes.py: ...
- api/tasks.py: ...
- tests: ...

Suggested staging:
- whole file:
- git add -p:
- manual hunk edit required:

Validation:
- commands to run:
```

不要执行任何 staging。

## 六、runtime port patch manifest

因为 Isolation-3 发现端口仍有冲突：

```text
其他配置/文档使用 19222
douyin_scraper/config.py 默认仍是 9222
```

输出：

```text
1. 当前所有 9222 / 19222 残留位置
2. 哪些属于运行契约提交
3. 是否必须先修一致性再提交 runtime port
4. 建议 commit message
5. 本轮是否允许处理：不允许，只给方案
```

建议 commit：

```text
chore(runtime): align API web and CDP port contracts
```

## 七、T017-5 patch manifest

分四组：

```text
Builder
API
Frontend
Docs
```

### Builder

```text
douyin_scraper/content_asset.py
douyin_scraper/tests/test_content_asset.py
core.py build_content_asset()
core.py get_paths() content_asset 三项
routes.py MergeRequest task id 字段
routes.py merge task-id 分支
```

### API

```text
api/tasks.py merge selector
routes.py preview/result/export content_asset 相关 hunk
content_asset API tests，建议迁移后提交
```

### Frontend

```text
DataPage.tsx
TaskDetailPage.tsx
client.ts
types.ts
```

前提：

```text
web baseline 已提交
runtime port web 两文件已处理
```

### Docs

```text
docs/CONTENT_ASSET.md
docs/index.md
README Content Asset hunk
api/README Content Asset hunk
docs/tasks/T017-5-* 可选归档
```

每组输出：

```text
文件范围
是否整文件
是否 git add -p
依赖哪个前序 commit
建议 commit message
```

## 八、api/webui manifest

输出：

```text
1. 当前 api/webui 删除/新增/修改列表
2. 哪些删除需要恢复
3. 是否等待前端源码提交后重新 build
4. 是否需要保留 logo
5. 最终提交文件范围
6. 建议 commit message
```

建议：

```text
build(webui): rebuild static frontend bundle
```

但明确：

```text
api/webui 仍暂缓，不能在 Release-Isolation 阶段提交。
```

## 九、最终判断

回答：

```text
是否允许进入 T017-5-Release-Isolation-5？
是否允许进入 T017-5-Release-1？
```

建议：

```text
Isolation-5 可作为实际“patch 文件生成与恢复演练”阶段，但仍不提交。
Release-1 继续 NO-GO，直到：
- web baseline 已恢复并提交
- 前序 A-D 生产链路已提交
- API 测试已迁移或明确处理
- runtime port 契约一致
- api/webui 暂缓或干净重建策略明确
```

## 最终报告格式

```markdown
# T017-5-Release-Isolation-4 查询报告

## 1. 查询结论

## 2. checkpoint 可访问性与恢复方案

## 3. web baseline manifest

## 4. api/README.md manifest

## 5. api/tests.py manifest

## 6. 前序 A-D patch manifest

## 7. runtime port patch manifest

## 8. T017-5 patch manifest

## 9. api/webui manifest

## 10. 是否允许进入 Isolation-5 / Release-1
```

## 通过标准

```text
完成只读查询
确认 checkpoint 是否可访问
明确 web baseline 恢复方案
明确 api/README.md / api/tests.py 恢复或拆分方案
明确前序 A-D patch manifest
明确 runtime port 一致性问题
明确 T017-5 builder/API/frontend/docs manifest
明确 api/webui 暂缓方案
未修改文件
未暂存
未提交 commit
```
