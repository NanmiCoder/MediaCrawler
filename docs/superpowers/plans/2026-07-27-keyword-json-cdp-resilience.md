# 关键词 JSON 队列与 Chrome 稳定连接实施计划

> **供智能体执行：** 必须使用 `subagent-driven-development`（推荐）或 `executing-plans`，逐任务实施并在每个任务后评审。所有步骤使用复选框跟踪。

**目标：** 让外部关键词工具读取任意数量的 JSON 关键词并独立断点续跑，同时让 MediaCrawler 复用专用 9222 Chrome，并为小红书验证码保留5分钟人工处理窗口。

**架构：** `D:\red_note_rich_search\keyword_crawl_runner` 只负责输入校验、API 编排、进度和 Chrome 启动脚本；`D:\red_note_rich_search\MediaCrawler` 保留爬虫实现，修改 CDP 连接顺序和小红书请求错误处理。两者继续通过现有本地 HTTP API 通信，不复制爬虫逻辑。

**技术栈：** Python 3.12 标准库、`unittest`、PowerShell 5+、MediaCrawler 现有 `pytest`/`pytest-asyncio`、Playwright、httpx、tenacity。

## 全局约束

- 关键词严格串行；每词最多20条；一级、二级评论关闭；保存格式为 JSON。
- JSON 关键词数量不限；去首尾空白、忽略空字符串、按首次出现顺序去重。
- 不新增第三方依赖，不实现三词并行、AI 粗筛、用户 ID、数据库或验证码自动化。
- 仅 `461/471` 进入人工等待；固定每10秒重试，最长5分钟。
- 保留 `pending/running/succeeded/failed/needs_review` 语义；`--retry-failed` 只重置明确失败项，不自动重跑不确定任务。
- 不修改或提交 `D:\red_note_rich_search\MediaCrawler\docs\公开账号索引研究模式改造方向.md`。
- 两个仓库分别提交；每个任务先看到失败测试，再写最小实现。

---

## 文件结构

### 外部工具仓库

- 修改 `D:\red_note_rich_search\keyword_crawl_runner\run_keywords.py`：JSON 输入、必填 `--source`、默认进度路径。
- 修改 `D:\red_note_rich_search\keyword_crawl_runner\test_run_keywords.py`：JSON 与路径回归测试。
- 创建 `D:\red_note_rich_search\keyword_crawl_runner\start_chrome.ps1`：专用 Chrome 启动器。
- 修改 `D:\red_note_rich_search\keyword_crawl_runner\.gitignore`：忽略输入、进度和 Chrome 数据。
- 修改 `D:\red_note_rich_search\keyword_crawl_runner\README.md`：新命令与启动顺序。

### MediaCrawler 仓库

- 修改 `D:\red_note_rich_search\MediaCrawler\tools\cdp_browser.py`：HTTP 发现优先、direct CDP 回退。
- 修改 `D:\red_note_rich_search\MediaCrawler\tests\test_cdp_browser.py`：连接顺序测试。
- 修改 `D:\red_note_rich_search\MediaCrawler\media_platform\xhs\exception.py`：验证码专用异常。
- 修改 `D:\red_note_rich_search\MediaCrawler\media_platform\xhs\client.py`：验证码分类和有界人工等待。
- 创建 `D:\red_note_rich_search\MediaCrawler\tests\test_xhs_captcha_wait.py`：可控时钟测试。

---

### Task 1：JSON 输入与独立进度文件

**文件：**

- 修改：`D:\red_note_rich_search\keyword_crawl_runner\run_keywords.py`
- 修改：`D:\red_note_rich_search\keyword_crawl_runner\test_run_keywords.py`
- 修改：`D:\red_note_rich_search\keyword_crawl_runner\.gitignore`
- 修改：`D:\red_note_rich_search\keyword_crawl_runner\README.md`

**接口：**

- 产出：`load_keywords(source: Path) -> list[str]`
- 产出：`default_progress_path(source: Path) -> Path`
- 产出：`parse_args(argv)` 中必填的 `--source` 和可空的 `--progress`
- 保持：`load_progress(path, source, keywords)`、`run_queue(...)` 及 API 请求体不变

- [ ] **Step 1：把解析测试改为 JSON 测试**

在 `test_run_keywords.py` 中删除 Markdown 构造器和固定20词断言，导入 `load_keywords`、`default_progress_path`，加入：

```python
class ParsingTests(unittest.TestCase):
    def write_json(self, directory, value):
        path = Path(directory) / "batch.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def test_loads_any_number_and_deduplicates_in_order(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.write_json(
                directory,
                {"keywords": [" 词一 ", "", "词二", "词一", "词三"]},
            )
            self.assertEqual(load_keywords(source), ["词一", "词二", "词三"])

    def test_rejects_invalid_keyword_documents(self):
        invalid_values = [
            [], {}, {"keywords": "词一"},
            {"keywords": ["词一", 2]}, {"keywords": [" ", ""]},
        ]
        for value in invalid_values:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                source = self.write_json(directory, value)
                with self.assertRaises(ValueError):
                    load_keywords(source)

    def test_default_progress_uses_source_stem(self):
        path = default_progress_path(Path("inputs/重庆客户.json"))
        self.assertEqual(path.name, "重庆客户.progress.json")
        self.assertEqual(path.parent.name, "progress")
```

补充 CLI 测试，确认缺少 `--source` 返回 argparse 的退出码2；将现有缺失源文件名改为 `.json`。

- [ ] **Step 2：运行失败测试**

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
python -m unittest -v test_run_keywords.ParsingTests test_run_keywords.CliTests
```

预期：导入 `load_keywords` 或 `default_progress_path` 失败。

- [ ] **Step 3：实现最小 JSON 解析和路径选择**

在 `run_keywords.py` 中删除 `SECTION`、`DEFAULT_SOURCE`、`DEFAULT_PROGRESS` 和 `extract_keywords`，加入：

```python
TOOL_ROOT = Path(__file__).resolve().parent
DEFAULT_PROGRESS_DIR = TOOL_ROOT / "progress"


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="逐词调用 MediaCrawler API")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--api-base", default="http://127.0.0.1:8080/api")
    parser.add_argument("--progress", type=Path)
    parser.add_argument("--retry-failed", action="store_true")
    return parser.parse_args(argv)


def load_keywords(source: Path) -> list[str]:
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"关键词 JSON 无法解析: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("keywords"), list):
        raise ValueError("关键词 JSON 必须包含 keywords 数组")
    raw_keywords = value["keywords"]
    if any(not isinstance(keyword, str) for keyword in raw_keywords):
        raise ValueError("keywords 数组元素必须全部为字符串")
    keywords = list(dict.fromkeys(
        keyword.strip() for keyword in raw_keywords if keyword.strip()
    ))
    if not keywords:
        raise ValueError("keywords 数组没有有效关键词")
    return keywords


def default_progress_path(source: Path) -> Path:
    return DEFAULT_PROGRESS_DIR / f"{source.stem}.progress.json"
```

在 `main` 中统一使用：

```python
keywords = load_keywords(args.source)
progress_path = args.progress or default_progress_path(args.source)
state = load_progress(progress_path, args.source, keywords)
result = run_queue(
    state,
    api,
    lambda value: atomic_write_json(progress_path, value),
    args.retry_failed,
)
```

`.gitignore` 增加：

```gitignore
/inputs/
/progress/
/chrome_crawler_profile/
```

README 加入以下输入说明，并删除旧 Markdown 示例：

````markdown
## 关键词 JSON

创建 `inputs\keywords.json`：

```json
{
  "keywords": ["重庆企业主资产配置", "重庆公私资产隔离"]
}
```

运行：

```powershell
uv run python run_keywords.py --source .\inputs\keywords.json
```

程序按输入文件名保存 `progress\keywords.progress.json`。同名 JSON 的关键词内容发生变化时，程序拒绝混用旧进度；请更换输入文件名，或用 `--progress` 指定新文件。
````

- [ ] **Step 4：运行 runner 全套测试**

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
python -m unittest -v
```

预期：全部通过且无失败；现有 `running` 恢复、`failed` 重试和 `needs_review` 防重复测试继续通过。

- [ ] **Step 5：提交 Task 1**

```powershell
git add -- run_keywords.py test_run_keywords.py .gitignore README.md
git commit -m "feat: accept JSON keyword batches"
```

---

### Task 2：专用 Chrome 一键启动脚本

**文件：**

- 创建：`D:\red_note_rich_search\keyword_crawl_runner\start_chrome.ps1`
- 修改：`D:\red_note_rich_search\keyword_crawl_runner\README.md`

**接口：**

- 产出：`start_chrome.ps1 [-ProfileDir D:\red_note_rich_search\chrome_crawler_profile] [-Port 9222]`
- 依赖：Chrome `/json/version` 返回非空 `webSocketDebuggerUrl`

- [ ] **Step 1：创建无第三方依赖的启动脚本**

```powershell
param(
    [string]$ProfileDir = 'D:\red_note_rich_search\chrome_crawler_profile',
    [int]$Port = 9222
)

$ErrorActionPreference = 'Stop'
$versionUri = "http://127.0.0.1:$Port/json/version"

function Test-CrawlerChrome {
    try {
        $version = Invoke-RestMethod -Uri $versionUri -TimeoutSec 2
        return [bool]$version.webSocketDebuggerUrl
    } catch {
        return $false
    }
}

if (Test-CrawlerChrome) {
    Write-Host "专用 Chrome 已在 $Port 端口运行。"
    exit 0
}

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    throw "端口 $Port 已被占用，但不是可用的 Chrome 调试接口。"
}

$candidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$chrome = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $chrome) { throw '找不到 chrome.exe，请先安装 Google Chrome。' }

New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null
Start-Process -FilePath $chrome -ArgumentList @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$ProfileDir",
    'https://www.xiaohongshu.com/explore'
)

for ($attempt = 0; $attempt -lt 30; $attempt++) {
    if (Test-CrawlerChrome) {
        Write-Host "专用 Chrome 已启动。首次使用请在浏览器中登录小红书。"
        exit 0
    }
    Start-Sleep -Milliseconds 500
}
throw "Chrome 已启动，但 $versionUri 在15秒内不可用。"
```

- [ ] **Step 2：执行 PowerShell 语法检查**

```powershell
$tokens = $null
$errors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile(
  'D:\red_note_rich_search\keyword_crawl_runner\start_chrome.ps1',
  [ref]$tokens,
  [ref]$errors
)
if ($errors.Count) { $errors | Format-List; exit 1 }
```

预期：退出码0且无语法错误。

- [ ] **Step 3：更新 README 的运行顺序**

README 加入以下运行顺序：

````markdown
## 完整运行顺序

```powershell
.\start_chrome.ps1
```

首次使用时，在打开的专用 Chrome 中登录小红书。脚本不会关闭普通 Chrome；如果 9222 已经是可用的 Chrome 调试接口，脚本只提示已运行。

另开终端启动 API：

```powershell
cd D:\red_note_rich_search\MediaCrawler
uv run uvicorn api.main:app --port 8080
```

再开一个终端运行队列：

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
uv run python run_keywords.py --source .\inputs\keywords.json
```
````

- [ ] **Step 4：人工验证幂等启动**

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
.\start_chrome.ps1
.\start_chrome.ps1
Invoke-RestMethod http://127.0.0.1:9222/json/version | Select-Object webSocketDebuggerUrl
```

预期：第一次打开专用 Chrome；第二次仅提示已运行；最后输出非空 WebSocket URL。

- [ ] **Step 5：提交 Task 2**

```powershell
git add -- start_chrome.ps1 README.md
git commit -m "feat: add dedicated Chrome launcher"
```

---

### Task 3：MediaCrawler 优先连接 `/json/version`

**文件：**

- 修改：`D:\red_note_rich_search\MediaCrawler\tests\test_cdp_browser.py`
- 修改：`D:\red_note_rich_search\MediaCrawler\tools\cdp_browser.py`

**接口：**

- 消费：`CDPBrowserManager._get_browser_websocket_url(debug_port: int) -> str`
- 保持：`CDPBrowserManager._connect_via_cdp(playwright)` 的调用方不变
- 产出：已有浏览器模式先使用发现 URL，发现失败才使用默认的 `ws://localhost:9222/devtools/browser`（端口取运行时配置）

- [ ] **Step 1：把现有连接顺序测试改为新规则**

```python
@pytest.mark.asyncio
async def test_existing_browser_prefers_discovered_websocket_url(monkeypatch):
    monkeypatch.setattr(config, "CDP_CONNECT_EXISTING", True)
    monkeypatch.setattr(config, "BROWSER_LAUNCH_TIMEOUT", 60)
    manager = CDPBrowserManager()
    manager.debug_port = 9222
    manager._get_browser_websocket_url = AsyncMock(
        return_value="ws://localhost:9222/devtools/browser/generated-id"
    )
    browser = MagicMock()
    browser.is_connected.return_value = True
    browser.contexts = []
    playwright = MagicMock()
    playwright.chromium.connect_over_cdp = AsyncMock(return_value=browser)

    await manager._connect_via_cdp(playwright)

    manager._get_browser_websocket_url.assert_awaited_once_with(9222)
    playwright.chromium.connect_over_cdp.assert_awaited_once_with(
        "ws://localhost:9222/devtools/browser/generated-id", timeout=60000
    )


@pytest.mark.asyncio
async def test_existing_browser_falls_back_to_direct_when_discovery_fails(monkeypatch):
    monkeypatch.setattr(config, "CDP_CONNECT_EXISTING", True)
    monkeypatch.setattr(config, "BROWSER_LAUNCH_TIMEOUT", 60)
    manager = CDPBrowserManager()
    manager.debug_port = 9222
    manager._get_browser_websocket_url = AsyncMock(side_effect=RuntimeError("no endpoint"))
    browser = MagicMock()
    browser.is_connected.return_value = True
    browser.contexts = []
    playwright = MagicMock()
    playwright.chromium.connect_over_cdp = AsyncMock(return_value=browser)

    await manager._connect_via_cdp(playwright)

    playwright.chromium.connect_over_cdp.assert_awaited_once_with(
        "ws://localhost:9222/devtools/browser", timeout=60000
    )
```

- [ ] **Step 2：运行失败测试**

```powershell
cd D:\red_note_rich_search\MediaCrawler
uv run pytest tests/test_cdp_browser.py -q
```

预期：第一个测试失败，因为当前实现先 direct；第二个测试失败，因为当前 discovery 调用发生在 direct 失败之后。

- [ ] **Step 3：最小调整 `_connect_via_cdp`**

```python
if config.CDP_CONNECT_EXISTING:
    try:
        ws_url = await self._get_browser_websocket_url(self.debug_port)
        utils.logger.info(
            f"[CDPBrowserManager] Connecting via discovered CDP URL: {ws_url}"
        )
    except Exception as discovery_error:
        ws_url = f"ws://localhost:{self.debug_port}/devtools/browser"
        utils.logger.warning(
            "[CDPBrowserManager] /json/version unavailable; falling back to "
            "Chrome 136+ direct CDP mode, which may require browser approval: "
            f"{discovery_error}"
        )
    self.browser = await playwright.chromium.connect_over_cdp(
        ws_url, timeout=config.BROWSER_LAUNCH_TIMEOUT * 1000
    )
```

不要改变 `CDP_CONNECT_EXISTING = False` 的自动启动浏览器分支。

- [ ] **Step 4：运行 CDP 与 API 聚焦测试**

```powershell
uv run pytest tests/test_cdp_browser.py tests/test_crawler_task_status.py tests/test_api_limits.py -q
```

预期：全部通过。

- [ ] **Step 5：提交 Task 3**

```powershell
git add -- tests/test_cdp_browser.py tools/cdp_browser.py
git commit -m "fix: prefer discovered CDP websocket"
```

---

### Task 4：小红书验证码5分钟人工等待

**文件：**

- 修改：`D:\red_note_rich_search\MediaCrawler\media_platform\xhs\exception.py`
- 修改：`D:\red_note_rich_search\MediaCrawler\media_platform\xhs\client.py`
- 创建：`D:\red_note_rich_search\MediaCrawler\tests\test_xhs_captcha_wait.py`

**接口：**

- 产出：`CaptchaRequiredError`
- 产出：`raise_for_captcha(response) -> None`
- 产出：`wait_for_captcha(operation, sleep=asyncio.sleep, monotonic=time.monotonic)`
- 保持：`XiaoHongShuClient.request(method, url, **kwargs)` 的公开签名和返回值不变

- [ ] **Step 1：写验证码分类和等待的失败测试**

```python
from unittest.mock import AsyncMock

import httpx
import pytest

from media_platform.xhs.client import raise_for_captcha, wait_for_captcha
from media_platform.xhs.exception import CaptchaRequiredError


async def record_sleep(values, seconds):
    values.append(seconds)


@pytest.mark.parametrize("status", [461, 471])
def test_captcha_status_raises_specific_error(status):
    response = httpx.Response(
        status,
        headers={"Verifytype": "slider", "Verifyuuid": "uuid-1"},
        request=httpx.Request("GET", "https://example.test"),
    )
    with pytest.raises(CaptchaRequiredError, match="slider"):
        raise_for_captcha(response)


@pytest.mark.asyncio
async def test_wait_for_captcha_continues_after_manual_verification():
    operation = AsyncMock(
        side_effect=[CaptchaRequiredError("verify"), {"notes": []}]
    )
    sleeps = []
    times = iter([0.0, 1.0])
    result = await wait_for_captcha(
        operation,
        sleep=lambda seconds: record_sleep(sleeps, seconds),
        monotonic=lambda: next(times),
    )
    assert result == {"notes": []}
    assert sleeps == [10]


@pytest.mark.asyncio
async def test_wait_for_captcha_stops_after_five_minutes():
    operation = AsyncMock(side_effect=CaptchaRequiredError("verify"))
    times = iter([0.0, 300.0])
    with pytest.raises(CaptchaRequiredError):
        await wait_for_captcha(
            operation, sleep=AsyncMock(), monotonic=lambda: next(times)
        )


@pytest.mark.asyncio
async def test_wait_for_captcha_does_not_retry_other_errors():
    operation = AsyncMock(side_effect=RuntimeError("network"))
    sleep = AsyncMock()
    with pytest.raises(RuntimeError, match="network"):
        await wait_for_captcha(operation, sleep=sleep)
    sleep.assert_not_awaited()
```

- [ ] **Step 2：运行失败测试**

```powershell
cd D:\red_note_rich_search\MediaCrawler
uv run pytest tests/test_xhs_captcha_wait.py -q
```

预期：导入新增异常或函数失败。

- [ ] **Step 3：实现专用异常和纯辅助函数**

在 `exception.py` 增加：

```python
class CaptchaRequiredError(RuntimeError):
    """Xiaohongshu requires the user to complete CAPTCHA manually."""
```

在 `client.py` 导入 `time`、`Awaitable`、`CaptchaRequiredError`，加入：

```python
CAPTCHA_RETRY_SECONDS = 10
CAPTCHA_MAX_WAIT_SECONDS = 300


def raise_for_captcha(response: httpx.Response) -> None:
    if response.status_code not in {461, 471}:
        return
    verify_type = response.headers.get("Verifytype", "unknown")
    verify_uuid = response.headers.get("Verifyuuid", "unknown")
    raise CaptchaRequiredError(
        "CAPTCHA appeared; please verify manually in Chrome. "
        f"Verifytype: {verify_type}, Verifyuuid: {verify_uuid}"
    )


async def wait_for_captcha(
    operation: Callable[[], Awaitable[Any]],
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> Any:
    deadline = monotonic() + CAPTCHA_MAX_WAIT_SECONDS
    while True:
        try:
            return await operation()
        except CaptchaRequiredError:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise
            utils.logger.warning(
                "[XiaoHongShuClient] CAPTCHA appeared; complete verification "
                "in Chrome within 5 minutes."
            )
            await sleep(min(CAPTCHA_RETRY_SECONDS, remaining))
```

- [ ] **Step 4：把现有短重试包在验证码等待内部**

将当前 `request` 的实际请求和响应解析移动到私有 `_request_with_short_retry`，保留原三次短重试，但排除验证码：

```python
async def request(self, method, url, **kwargs) -> Union[str, Any]:
    return_response = kwargs.pop("return_response", False)

    async def operation():
        return await self._request_with_short_retry(
            method, url, return_response=return_response, **kwargs
        )

    return await wait_for_captcha(operation)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry=retry_if_not_exception_type((NoteNotFoundError, CaptchaRequiredError)),
    reraise=True,
)
async def _request_with_short_retry(
    self, method, url, *, return_response=False, **kwargs
) -> Union[str, Any]:
    await self._refresh_proxy_if_expired()
    async with make_async_client(proxy=self.proxy) as client:
        response = await client.request(method, url, timeout=self.timeout, **kwargs)
    raise_for_captcha(response)
    if return_response:
        return response.text
    data: Dict = response.json()
    if data["success"]:
        return data.get("data", data.get("success", {}))
    if data["code"] == self.IP_ERROR_CODE:
        raise IPBlockError(self.IP_ERROR_STR)
    if data["code"] in (self.NOTE_NOT_FOUND_CODE, self.NOTE_ABNORMAL_CODE):
        raise NoteNotFoundError(
            f"Note not found or abnormal, code: {data['code']}"
        )
    err_msg = data.get("msg", None) or response.text
    raise DataFetchError(err_msg)
```

删除旧的裸 `raise Exception(msg)`；除移动到私有方法外，不改变上述数据分支。

- [ ] **Step 5：运行验证码与小红书聚焦测试**

```powershell
uv run pytest tests/test_xhs_captcha_wait.py tests/test_no_user_info.py -q
```

预期：全部通过，测试过程不真实等待。

- [ ] **Step 6：提交 Task 4**

```powershell
git add -- media_platform/xhs/exception.py media_platform/xhs/client.py tests/test_xhs_captcha_wait.py
git commit -m "fix: wait for manual XHS CAPTCHA"
```

---

### Task 5：双仓库回归、人工冒烟与发布准备

**文件：** 验证 Task 1–4 的全部改动，不新增生产接口。

- [ ] **Step 1：运行外部工具完整测试和差异检查**

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
python -m unittest -v
git diff --check HEAD~2..HEAD
git status -sb
```

预期：全部测试通过，差异检查退出码0。

- [ ] **Step 2：运行 MediaCrawler 聚焦测试**

```powershell
cd D:\red_note_rich_search\MediaCrawler
uv run pytest tests/test_cdp_browser.py tests/test_xhs_captcha_wait.py tests/test_crawler_task_status.py tests/test_api_limits.py tests/test_no_user_info.py -q
git diff --check HEAD~2..HEAD
```

预期：全部通过；不得把既有 Windows `grep` 兼容失败混入该聚焦结果。

- [ ] **Step 3：创建被忽略的最小人工验收输入**

文件 `D:\red_note_rich_search\keyword_crawl_runner\inputs\smoke.json`：

```json
{
  "keywords": [
    "重庆企业主资产配置",
    "重庆公私资产隔离"
  ]
}
```

- [ ] **Step 4：执行真实本地冒烟**

终端一：

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
.\start_chrome.ps1
```

终端二：

```powershell
cd D:\red_note_rich_search\MediaCrawler
uv run uvicorn api.main:app --port 8080
```

终端三：

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
uv run python run_keywords.py --source .\inputs\smoke.json
```

预期：两个关键词串行完成；第二个子进程不再要求 Chrome CDP 授权；生成 `progress\smoke.progress.json`；输出仍位于 `MediaCrawler\data\xhs\json`。

- [ ] **Step 5：验证断点与进度隔离**

再次运行同一命令，确认成功词不重新提交。复制输入为 `inputs\smoke-copy.json` 后运行，确认使用 `progress\smoke-copy.progress.json`。修改原 `smoke.json` 后运行，确认程序拒绝复用 `smoke.progress.json`。

- [ ] **Step 6：确认两个仓库提交范围**

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
git status -sb
git log -3 --oneline

cd D:\red_note_rich_search\MediaCrawler
git status -sb
git log -4 --oneline
```

预期：实现均已提交；MediaCrawler 中用户未跟踪的研究文档仍未加入；不提交 Chrome profile、关键词输入、进度或采集结果。

- [ ] **Step 7：进入完成分支流程**

使用 `finishing-a-development-branch` 检查测试证据和提交范围。外部工具远程为 `yukikojo/mediaClawerTooler`，只有在用户确认发布后才推送。MediaCrawler 本地 `main` 与上游存在分歧，不执行强制推送或历史重写。
