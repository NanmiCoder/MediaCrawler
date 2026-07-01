T017-5-Release-API-1：Content Asset API result / preview / export 实际拆分与提交。

本轮允许实际暂存并提交 Content Asset API 接入内容，但只允许提交 result selector、preview、GET export、POST export、字段映射和对应 API 测试。禁止混入 Builder、Web、Docs、runtime、api/webui、CDP、ASR。

## 当前状态

```text
A-D 前序成果已提交
Builder 已提交
Builder commit: 55199ea5 feat(content-asset): add content asset builder
暂存区为空
未 push
```

## 目标 commit

```text
feat(api): expose content asset result preview and export
```

## 允许范围

只允许包含：

```text
api/tasks.py 中 merge/content_asset result selector
api/routes.py 中 content_asset preview 相关 hunk
api/routes.py 中 GET /scrape/data/export?task_id=... 原始主结果下载
api/routes.py 中 POST export 对 content_asset 的旧七字段映射
api/routes.py 中 _normalize_row 的 content_asset 字段别名映射
Content Asset API 测试
```

建议将 API 测试迁移或提交到独立测试文件：

```text
douyin_scraper/tests/test_content_asset_api.py
douyin_scraper/tests/test_task_result_selection.py 中 merge/content_asset selector 部分
```

## 禁止范围

```text
禁止提交 Builder 代码
禁止提交 douyin_scraper/content_asset.py
禁止提交 douyin_scraper/tests/test_content_asset.py
禁止提交 Web
禁止提交 Docs
禁止提交 api/webui
禁止提交 runtime port
禁止提交 crawl_comments_v2.py
禁止提交 pyproject.toml
禁止处理 CDP
禁止处理真实 ASR/Whisper
禁止 git add .
禁止整文件暂存 routes.py
禁止混入 A-D 已提交内容
```

## 执行前检查

```powershell
git status --short
git diff --cached --name-status
git diff --check
python -m py_compile api\routes.py api\tasks.py
python -m pytest douyin_scraper\tests\test_content_asset_api.py -q
python -m pytest douyin_scraper\tests\test_task_result_selection.py -q
```

如果 `test_content_asset_api.py` 尚不存在，请先从混杂的 `api/tests.py` 中迁移 Content Asset API 相关测试到该文件，再执行测试。

## 暂存方式

`api/tasks.py` 可以只暂存 merge/content_asset selector hunk：

```powershell
git add -p api/tasks.py
```

`api/routes.py` 必须 patch 暂存：

```powershell
git add -p api/routes.py
```

只选择 API hunk：

```text
_normalize_row 的 content_asset 字段别名
preview_data 对 content_asset 的主结果选择
GET export 原始主结果下载
POST export 对 content_asset 的旧七字段映射
```

测试文件如已拆清，可整文件暂存：

```powershell
git add douyin_scraper/tests/test_content_asset_api.py
git add -p douyin_scraper/tests/test_task_result_selection.py
```

## 暂存后检查

```powershell
git diff --cached --stat
git diff --cached --name-status
git diff --cached --check
git diff --cached -- api/routes.py api/tasks.py
```

必须确认 staged diff 不包含：

```text
Builder
Web
Docs
runtime port
api/webui
CDP
ASR
pyproject.toml
```

## 测试

```powershell
python -m py_compile api\routes.py api\tasks.py
python -m pytest douyin_scraper\tests\test_content_asset_api.py -q
python -m pytest douyin_scraper\tests\test_task_result_selection.py -q
python -m pytest douyin_scraper\tests\test_content_asset.py -q
```

## 提交

只有 staged diff 和测试均通过后，执行：

```powershell
git commit -m "feat(api): expose content asset result preview and export"
```

## 提交后验证

```powershell
git status --short
git log --oneline -8
python -m pytest douyin_scraper\tests\test_content_asset_api.py -q
python -m pytest douyin_scraper\tests\test_task_result_selection.py -q
```

## 最终报告

输出：

```markdown
# T017-5-Release-API-1 报告

## 1. 执行结论

## 2. Commit hash

## 3. 暂存文件范围

## 4. staged diff 检查结果

## 5. 测试结果

## 6. 剩余工作区状态

## 7. 是否允许进入 Web 三组提交阶段
```

## 通过标准

```text
只提交 Content Asset API
不包含 Builder/Web/Docs/runtime/api-webui
Content Asset API 测试 PASS
task result selector 测试 PASS
py_compile PASS
commit 创建成功
暂存区最终为空
未 push
```
