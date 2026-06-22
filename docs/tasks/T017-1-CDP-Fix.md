T017-1-CDP-Fix：真实评论 CDP 采集修复与隔离提交。

当前 T017-5 已封版，T018-1 runtime/部署已提交，T018-2 api/webui 构建产物已提交。现在进入 CDP/真实评论采集阶段。本轮只处理 CDP、登录、浏览器连接、真实评论采集链路，以及必要的 `crawl_comments_v2.py` 接入。

## 当前状态

```text
T017-5 Release：CLOSED
T018-1 Runtime/Deploy：PASS
T018-2 api/webui：PASS
当前分支 ahead 2
暂存区为空
剩余工作区约 46 项
未 push
```

## 本轮允许范围

只允许审查和处理：

```text
config/dy_config.py
media_platform/douyin/core.py
media_platform/douyin/login.py
tools/cdp_browser.py
crawl_comments_v2.py
crawl_comments.py 仅允许在 v2 验收后删除
douyin_scraper/core.py 中直接引用 crawl_comments_v2.py 的必要 hunk
README.md / api/README.md 中 CDP 真实评论采集相关 hunk，如确有必要
docs/CDP模式使用指南.md 中 CDP 使用说明，如确有必要
```

## 禁止范围

```text
禁止提交 ASR/Whisper
禁止提交 pyproject.toml
禁止提交 extract_scripts.py / extract_scripts_v2.py
禁止提交测试工具旧 CLI
禁止提交 api/webui
禁止提交 runtime/部署剩余 hunk
禁止提交架构文档
禁止提交 docs/tasks
禁止 git add .
禁止 push
```

## 固定端口契约

CDP 端口必须使用：

```text
Chrome/CDP 宿主端口：19222
```

禁止重新引入：

```text
9222
```

除非仅作为“不要使用默认 9222”的说明出现。

## 第一步：只读审查

```powershell
git status --short
git diff --cached --name-status
git diff --check -- . ':!api/webui'
git diff --name-status
```

重点查看 CDP 相关差异：

```powershell
git diff -- config/dy_config.py media_platform/douyin/core.py media_platform/douyin/login.py tools/cdp_browser.py crawl_comments_v2.py crawl_comments.py douyin_scraper/core.py
```

## 第二步：污染项处理判断

重点检查 `config/dy_config.py`：

```powershell
git diff -- config/dy_config.py
```

如果其中包含本地真实视频 ID、临时采集目标、个人采集样本，必须恢复或排除，不得提交。

建议：

```text
config/dy_config.py 中真实视频 ID 污染：恢复或 patch 排除
CDP 端口/浏览器连接配置：可保留
```

## 第三步：确认 crawl_comments_v2.py 是否为正式脚本

检查引用关系：

```powershell
Select-String -Path douyin_scraper/core.py,media_platform/douyin/core.py,api/routes.py,api/tasks.py -Pattern "crawl_comments_v2|crawl_comments"
```

判断：

```text
1. crawl_comments_v2.py 是否已经被正式链路引用
2. crawl_comments.py 是否仍被引用
3. 如果 v2 已替代 v1，crawl_comments.py 是否可以删除
4. 是否存在路径、端口、profile 目录硬编码风险
```

## 第四步：CDP 端口与浏览器连接检查

```powershell
Select-String -Path config/dy_config.py,media_platform/douyin/core.py,media_platform/douyin/login.py,tools/cdp_browser.py,crawl_comments_v2.py,douyin_scraper/core.py -Pattern "9222|19222|remote-debugging-port|CDP|chrome|browser"
```

要求：

```text
推荐端口统一为 19222
不得把 9222 作为默认运行端口
如出现 9222，只能作为禁止/兼容说明，并需注明项目默认使用 19222
```

## 第五步：必要修复

仅允许做 CDP/真实评论采集相关修复：

```text
CDP WebSocket 获取
Chrome remote debugging 连接
Douyin 登录状态复用
真实评论采集入口
crawl_comments_v2.py 正式化
core.py 对 v2 的必要调用
评论采集失败时的清晰 fallback / pending_cdp 状态
```

禁止顺手改：

```text
ASR
script extraction
pyproject
Docker
api/webui
Web
通用测试框架
旧 CLI
架构文档
```

## 第六步：暂存方式

混合文件必须 patch 暂存：

```powershell
git add -p config/dy_config.py
git add -p media_platform/douyin/core.py
git add -p media_platform/douyin/login.py
git add -p tools/cdp_browser.py
git add -p douyin_scraper/core.py
```

新正式脚本可整文件暂存：

```powershell
git add crawl_comments_v2.py
```

如确认 `crawl_comments.py` 已被 v2 替代且不再引用，可删除并暂存删除：

```powershell
git rm crawl_comments.py
```

但如果无法确认，不要删除，先保留。

文档如有必要，只 patch 暂存 CDP hunk：

```powershell
git add -p docs/CDP模式使用指南.md
git add -p README.md
git add -p api/README.md
```

## 第七步：暂存后检查

```powershell
git diff --cached --stat
git diff --cached --name-status
git diff --cached --check
git diff --cached
```

必须确认 staged diff：

```text
只包含 CDP / 登录 / 真实评论采集
不包含 ASR/Whisper
不包含 pyproject.toml
不包含 api/webui
不包含 runtime/部署
不包含测试工具旧 CLI
不包含架构文档
不包含真实视频 ID 污染
```

端口扫描：

```powershell
git diff --cached | Select-String -Pattern "9222|19222|localhost:8000|:3000"
```

要求：

```text
不能新增默认 9222
不能新增宿主 localhost:8000
不能新增 Web 3000
CDP 默认必须为 19222
```

## 第八步：验证

基础编译：

```powershell
python -m py_compile config\dy_config.py media_platform\douyin\core.py media_platform\douyin\login.py tools\cdp_browser.py douyin_scraper\core.py crawl_comments_v2.py
```

引用检查：

```powershell
python -c "import tools.cdp_browser; import media_platform.douyin.core; import media_platform.douyin.login; import douyin_scraper.core; print('CDP imports OK')"
```

如果本机没有可用 Chrome/CDP，不强行要求真实采集 PASS，但必须输出：

```text
1. 是否检测到 CDP 端口
2. 是否能连接 ws endpoint
3. 如果不能连接，失败原因是否清晰
4. 系统是否能回退为 pending_cdp 而不是崩溃
```

如可以运行真实评论采集 smoke，则执行最小 smoke，不要扩大采集范围：

```powershell
python crawl_comments_v2.py --help
```

如已有项目命令，运行一个最小 dry-run / help / config check，而不是批量真实采集。

## 第九步：提交

检查通过后提交：

```powershell
git commit -m "fix(douyin): stabilize CDP comment collection"
```

## 第十步：提交后验证

```powershell
git status --short
git log --oneline -8
git diff --check -- . ':!api/webui'
```

## 最终报告

输出：

```markdown
# T017-1-CDP-Fix 报告

## 1. 执行结论
## 2. Commit hash
## 3. 暂存文件范围
## 4. CDP 端口契约
## 5. 真实视频 ID 污染处理
## 6. crawl_comments_v2.py 处理结论
## 7. staged diff 检查结果
## 8. 验证结果
## 9. 剩余工作区状态
## 10. 是否允许进入 T017-4-ASR-Dependency
```

## 通过标准

```text
只提交 CDP / 登录 / 真实评论采集相关内容
CDP 默认端口统一为 19222
不提交真实视频 ID 污染
不提交 ASR/Whisper/pyproject
不提交 api/webui/runtime/测试/工具/旧 CLI
编译和导入检查 PASS
暂存区最终为空
未 push
```
