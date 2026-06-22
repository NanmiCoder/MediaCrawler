T017-5-Release-Builder-API-0：Content Asset Builder / API / Web / Docs 剩余差异重新审查。

本轮只做查询和分组判断，不提交 commit。目标是在 A-D 四个前序 commit 已完成后，重新审查剩余工作区，确认 T017-5 Builder、API、Web、Docs 的提交边界。

## 当前状态

```text
A-D 前序成果已实际提交
分支 ahead 4
暂存区为空
未 push
T017-5 Release-1 尚未开启
```

已完成 commit：

```text
be8fbcec387328ef7e754c90290ad646c853e245 feat(scraper): standardize search outputs in task workspaces
00a4946cc5dbe31a163b78d4bfa3f85ba5885ee0 feat(scraper): add raw and cleaned comment outputs
8bee152f028c48a301be8d4f2cbd4d2bddc17a98 feat(scraper): add cleaned search title outputs
2d7afaf8b61ea43977858560ef1745ca5aad5f09 feat(scraper): add script source raw and clean outputs
```

## 本轮目标

重新审查剩余 diff，拆分后续提交：

```text
1. Content Asset Builder
2. Content Asset API result / preview / export
3. Web baseline
4. Runtime web port patch
5. T017-5 frontend UX
6. Docs
7. api/webui build 产物
8. 暂缓项
```

## 禁止

```text
禁止 git commit
禁止 git add .
禁止 git add web/
禁止 push
禁止处理真实 CDP
禁止处理真实 Whisper/ASR
禁止接 AI/LLM
禁止提交 api/webui
禁止提交 crawl_comments_v2.py
禁止提交 pyproject.toml
禁止混入 runtime port 全局契约
```

## 允许

```text
允许 git status / git diff 查询
允许 git diff --cached 查询
允许临时 git add -p 演练并 reset
允许运行测试
禁止 commit
```

## 一、执行前检查

```powershell
git status --short
git diff --cached --name-status
git diff --stat
git log --oneline -8
git diff --check
```

要求：

```text
暂存区为空
A-D commit 已在 log 中
git diff --check PASS
```

## 二、剩余工作区分类

请输出剩余文件分组：

### 1. T017-5 Builder

候选范围：

```text
douyin_scraper/content_asset.py
douyin_scraper/tests/test_content_asset.py
douyin_scraper/core.py 中 build_content_asset()
douyin_scraper/core.py get_paths() content_asset_jsonl/content_asset_csv/content_asset_stats
api/routes.py MergeRequest 三个 task-id 字段
api/routes.py merge task-id content_asset 分支
```

判断：

```text
是否可形成独立 commit？
是否仍依赖 A-D？
是否有越界内容？
建议 commit message？
```

建议 message：

```text
feat(content-asset): add content asset builder
```

### 2. T017-5 API

候选范围：

```text
api/tasks.py merge/content_asset selector
api/routes.py preview_data content_asset
api/routes.py GET export
api/routes.py POST export content_asset 映射
Content Asset API 测试
```

判断：

```text
是否应先迁移 API 测试到 douyin_scraper/tests/test_content_asset_api.py？
是否可独立提交？
是否与 Builder 分开？
```

建议 message：

```text
feat(api): expose content asset result preview and export
```

### 3. Web baseline

候选范围：

```text
39 个 checkpoint web baseline 文件
```

判断：

```text
是否仍可按 Isolation-8 的三组顺序提交？
是否仍需要先恢复 baseline？
是否有 web/node_modules / tsbuildinfo 混入？
```

建议 message：

```text
feat(web): establish Vite frontend baseline
```

### 4. Runtime web port patch

候选范围：

```text
web/src/utils/constants.ts
web/vite.config.ts
```

建议 message：

```text
chore(web): align frontend API and dev ports
```

### 5. T017-5 frontend

候选范围：

```text
web/src/api/client.ts
web/src/api/types.ts
web/src/pages/DataPage.tsx
web/src/pages/TaskDetailPage.tsx
```

建议 message：

```text
feat(web): add content asset preview and download UX
```

### 6. Docs

候选范围：

```text
docs/CONTENT_ASSET.md
docs/index.md
README.md Content Asset hunk
api/README.md Content Asset hunk
docs/tasks/T017-5-* 可选归档
```

建议拆成：

```text
docs(content-asset): document schema workflow and acceptance
docs(tasks): archive T017-5 implementation notes
```

### 7. api/webui

当前只审查，不提交。

判断：

```text
已跟踪文件是否干净？
未跟踪新 bundle 是否仍存在？
是否继续暂缓到最后 build(webui)?
```

### 8. 暂缓项

明确列出：

```text
crawl_comments_v2.py
pyproject.toml
CDP 真实采集
真实 Whisper/ASR
全局 runtime port 契约
api/webui build 产物
未
```
