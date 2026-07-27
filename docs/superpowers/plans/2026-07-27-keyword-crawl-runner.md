# 关键词自动采集队列实施计划

> **供自动化执行代理使用：** 必须使用 `subagent-driven-development`（推荐）或 `executing-plans`，按任务逐项实施本计划。步骤使用复选框（`- [ ]`）跟踪进度。

**目标：** 构建一个可断点续跑的本地队列，读取已确认的20个关键词，逐词调用 MediaCrawler API，并避免重复执行已成功任务。

**架构：** 为 MediaCrawler 增加最小任务标识与状态字段（`task_id`、`last_exit_code`、`finished_at`）。同级目录中的独立 Python 程序只使用标准库，负责解析 Markdown、原子保存 JSON 进度、逐个提交 API 任务，并依据任务 ID 恢复中断任务。

**技术栈：** Python 3.11、FastAPI/Pydantic、pytest/pytest-asyncio，以及 Python 标准库（`argparse`、`hashlib`、`json`、`urllib.request`、`unittest`）。

## 全局约束

- 只解析 `## 建议首先执行的20个词`，并要求恰好得到20个唯一关键词。
- 每次只提交一个关键词，设置 `max_notes_count=20`，并关闭两级评论采集。
- 使用 MediaCrawler 现有 API `http://127.0.0.1:8080/api`，不自动操作 WebUI 输入框。
- 每次状态变化都原子保存；绝不自动重复执行 `succeeded` 或 `needs_review` 项。
- 明确失败后继续下一个关键词；只有指定 `--retry-failed` 时才重试失败项。
- 队列程序不增加任何第三方依赖。
- 保持 MediaCrawler 当前匿名存储行为，不改动用户现有的未跟踪讨论文档。
- 仅用于个人、非商业研究和公开笔记。

---

## 文件结构

### MediaCrawler 仓库（`D:\red_note_rich_search\MediaCrawler`）

- 修改 `api/schemas/crawler.py`：公开任务标识和完成字段。
- 修改 `api/services/crawler_manager.py`：创建任务 ID 并保留退出元数据。
- 修改 `api/routers/crawler.py`：返回创建的任务 ID。
- 修改 `tests/test_api_limits.py`：使现有启动接口模拟响应适配新接口。
- 创建 `tests/test_crawler_task_status.py`：验证任务生命周期和 API 序列化。

### 独立队列程序仓库（`D:\red_note_rich_search\keyword_crawl_runner`）

- 创建 `.gitignore`：排除运行进度和 Python 缓存。
- 创建 `run_keywords.py`：实现 Markdown 解析、进度持久化、HTTP 客户端、恢复和命令行入口。
- 创建 `test_run_keywords.py`：使用模拟 API 客户端编写标准库单元测试。
- 创建 `README.md`：记录准确的启动、续跑和重试命令。

---

### 任务1：为 MediaCrawler API 增加可追踪的任务标识

**文件：**
- 修改：`api/schemas/crawler.py:81-87`
- 修改：`api/services/crawler_manager.py:19-285`
- 修改：`api/routers/crawler.py:27-37`
- 修改：`tests/test_api_limits.py:64-107`
- 创建：`tests/test_crawler_task_status.py`

**接口：**
- 产出：`CrawlerManager.start(config) -> Optional[str]`，成功时返回 UUID 字符串，未启动进程时返回 `None`。
- 产出：`CrawlerManager.get_status() -> dict`，包含 `task_id`、`last_exit_code` 和 `finished_at`。
- 产出：`POST /api/crawler/start` 响应包含 `task_id`。

- [ ] **步骤1：编写失败的响应结构与生命周期测试**

创建 `tests/test_crawler_task_status.py`：

```python
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.schemas import CrawlerStartRequest, PlatformEnum
from api.services.crawler_manager import CrawlerManager


def request() -> CrawlerStartRequest:
    return CrawlerStartRequest(platform=PlatformEnum.XHS, keywords="重庆企业主资产配置")


@pytest.mark.asyncio
async def test_start_returns_task_id_and_clears_completion_state():
    manager = CrawlerManager()
    manager.last_exit_code = 1
    manager.finished_at = datetime.now()
    process = MagicMock()
    process.poll.return_value = None

    with patch("api.services.crawler_manager.subprocess.Popen", return_value=process):
        with patch("api.services.crawler_manager.asyncio.create_task"):
            task_id = await manager.start(request())

    assert isinstance(task_id, str)
    assert task_id == manager.task_id
    assert manager.last_exit_code is None
    assert manager.finished_at is None
    assert manager.status == "running"


@pytest.mark.asyncio
async def test_read_output_records_exit_metadata():
    manager = CrawlerManager()
    manager.status = "running"
    manager.current_config = request()
    manager.task_id = "task-123"
    process = MagicMock()
    process.poll.side_effect = [0, 0]
    process.returncode = 0
    process.stdout.readline.return_value = ""
    process.stdout.read.return_value = ""
    manager.process = process

    await manager._read_output()

    status = manager.get_status()
    assert status["status"] == "idle"
    assert status["task_id"] == "task-123"
    assert status["last_exit_code"] == 0
    assert status["finished_at"] is not None
    assert status["platform"] is None


def test_start_endpoint_returns_task_id():
    client = TestClient(app)
    with patch(
        "api.routers.crawler.crawler_manager.start",
        new_callable=AsyncMock,
        return_value="task-123",
    ):
        response = client.post(
            "/api/crawler/start",
            json={"platform": "xhs", "keywords": "重庆企业主资产配置"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "message": "Crawler started successfully",
        "task_id": "task-123",
    }


def test_status_endpoint_serializes_completion_fields():
    client = TestClient(app)
    status = {
        "status": "idle",
        "platform": None,
        "crawler_type": None,
        "started_at": "2026-07-27T10:00:00+08:00",
        "error_message": None,
        "task_id": "task-123",
        "last_exit_code": 0,
        "finished_at": "2026-07-27T10:02:00+08:00",
    }
    with patch("api.routers.crawler.crawler_manager.get_status", return_value=status):
        response = client.get("/api/crawler/status")

    assert response.status_code == 200
    assert response.json() == status
```

- [ ] **步骤2：更新现有 API 模拟值，并运行测试确认失败**

在 `tests/test_api_limits.py` 的两个启动接口测试中，将：

```python
mock_start.return_value = True
```

替换为：

```python
mock_start.return_value = "task-123"
```

将精确响应断言更新为：

```python
assert response.json() == {
    "status": "ok",
    "message": "Crawler started successfully",
    "task_id": "task-123",
}
```

运行：

```powershell
uv run pytest tests/test_crawler_task_status.py tests/test_api_limits.py -q
```

预期：失败，因为 `CrawlerStatusResponse` 尚无完成字段，且 `start()` 仍返回 `bool`。

- [ ] **步骤3：扩展状态响应结构**

将 `api/schemas/crawler.py` 中的 `CrawlerStatusResponse` 替换为：

```python
class CrawlerStatusResponse(BaseModel):
    """Crawler status response"""
    status: Literal["idle", "running", "stopping", "error"]
    platform: Optional[str] = None
    crawler_type: Optional[str] = None
    started_at: Optional[str] = None
    error_message: Optional[str] = None
    task_id: Optional[str] = None
    last_exit_code: Optional[int] = None
    finished_at: Optional[str] = None
```

- [ ] **步骤4：在任务管理器中实现生命周期元数据**

增加导入：

```python
from uuid import uuid4
```

在 `CrawlerManager.__init__` 中增加字段：

```python
self.task_id: Optional[str] = None
self.last_exit_code: Optional[int] = None
self.finished_at: Optional[datetime] = None
```

修改方法签名及失败返回值：

```python
async def start(self, config: CrawlerStartRequest) -> Optional[str]:
    """Start crawler process and return its task id."""
```

`subprocess.Popen` 调用成功后立即设置：

```python
self.task_id = str(uuid4())
self.last_exit_code = None
self.finished_at = None
self.status = "running"
self.started_at = datetime.now()
self.current_config = config
```

成功时返回 `self.task_id` 而不是 `True`；两个失败分支返回 `None` 而不是 `False`。

在 `_read_output` 中，将进程结束处理代码替换为：

```python
if self.status == "running":
    exit_code = self.process.returncode if self.process else -1
    self.last_exit_code = exit_code
    self.finished_at = datetime.now()
    if exit_code == 0:
        entry = self._create_log_entry("Crawler completed successfully", "success")
    else:
        entry = self._create_log_entry(
            f"Crawler exited with code: {exit_code}", "warning"
        )
    await self._push_log(entry)
    self.status = "idle"
    self.current_config = None
```

扩展 `get_status()`：

```python
return {
    "status": self.status,
    "platform": self.current_config.platform.value if self.current_config else None,
    "crawler_type": self.current_config.crawler_type.value if self.current_config else None,
    "started_at": self.started_at.isoformat() if self.started_at else None,
    "error_message": None,
    "task_id": self.task_id,
    "last_exit_code": self.last_exit_code,
    "finished_at": self.finished_at.isoformat() if self.finished_at else None,
}
```

`stop()` 完成进程终止后设置：

```python
self.last_exit_code = self.process.poll()
self.finished_at = datetime.now()
```

- [ ] **步骤5：由路由返回任务 ID**

将 `api/routers/crawler.py` 中启动处理函数的函数体替换为：

```python
task_id = await crawler_manager.start(request)
if not task_id:
    if crawler_manager.process and crawler_manager.process.poll() is None:
        raise HTTPException(status_code=400, detail="Crawler is already running")
    raise HTTPException(status_code=500, detail="Failed to start crawler")

return {
    "status": "ok",
    "message": "Crawler started successfully",
    "task_id": task_id,
}
```

- [ ] **步骤6：运行聚焦测试和回归测试**

运行：

```powershell
uv run pytest tests/test_crawler_task_status.py tests/test_api_limits.py -q
uv run pytest tests -q
```

预期：两条命令均通过；第一条覆盖新增生命周期测试，第二条无回归失败。

- [ ] **步骤7：提交 API 增强**

```powershell
git add api/schemas/crawler.py api/services/crawler_manager.py api/routers/crawler.py tests/test_api_limits.py tests/test_crawler_task_status.py
git commit -m "feat: expose crawler task completion status"
```

---

### 任务2：实现 Markdown 解析和进度原子保存

**文件：**
- 创建：`D:\red_note_rich_search\keyword_crawl_runner\.gitignore`
- 创建：`D:\red_note_rich_search\keyword_crawl_runner\run_keywords.py`
- 创建：`D:\red_note_rich_search\keyword_crawl_runner\test_run_keywords.py`

**接口：**
- 产出：`extract_keywords(markdown: str) -> list[str]`。
- 产出：`keyword_digest(keywords: list[str]) -> str`。
- 产出：`new_progress(source: Path, keywords: list[str]) -> dict`。
- 产出：`atomic_write_json(path: Path, value: dict) -> None`。
- 产出：`load_progress(path: Path, source: Path, keywords: list[str]) -> dict`。

- [ ] **步骤1：创建并初始化独立仓库**

```powershell
New-Item -ItemType Directory -Force -Path D:\red_note_rich_search\keyword_crawl_runner
git -C D:\red_note_rich_search\keyword_crawl_runner init
```

创建 `.gitignore`：

```gitignore
__pycache__/
*.pyc
crawl_progress.json
crawl_progress.json.tmp
```

- [ ] **步骤2：编写失败的解析和持久化测试**

创建 `test_run_keywords.py`：

```python
import json
import tempfile
import unittest
from pathlib import Path

from run_keywords import (
    atomic_write_json,
    extract_keywords,
    keyword_digest,
    load_progress,
    new_progress,
)


KEYWORDS = [f"关键词{i:02d}" for i in range(1, 21)]


def markdown(words=KEYWORDS):
    body = "\n".join(words)
    return f"""# 词表

## 第一批
```text
不应读取
```

## 建议首先执行的20个词
```text
{body}
```

## 建议配置的排除方向
```text
广告
```
"""


class ParsingTests(unittest.TestCase):
    def test_extracts_only_approved_twenty(self):
        self.assertEqual(extract_keywords(markdown()), KEYWORDS)

    def test_rejects_wrong_count_after_deduplication(self):
        with self.assertRaisesRegex(ValueError, "恰好包含20个"):
            extract_keywords(markdown(KEYWORDS[:-1] + [KEYWORDS[0]]))

    def test_digest_changes_when_order_changes(self):
        self.assertNotEqual(keyword_digest(KEYWORDS), keyword_digest(KEYWORDS[::-1]))


class ProgressTests(unittest.TestCase):
    def test_new_progress_starts_pending(self):
        state = new_progress(Path("words.md"), KEYWORDS)
        self.assertTrue(all(item["status"] == "pending" for item in state["keywords"]))
        self.assertEqual(state["keywords_sha256"], keyword_digest(KEYWORDS))

    def test_atomic_write_produces_valid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            atomic_write_json(path, {"ok": True})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"ok": True})
            self.assertFalse(path.with_suffix(path.suffix + ".tmp").exists())

    def test_load_rejects_changed_keyword_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            atomic_write_json(path, new_progress(Path("words.md"), KEYWORDS))
            with self.assertRaisesRegex(ValueError, "词表已变化"):
                load_progress(path, Path("words.md"), KEYWORDS[::-1])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤3：运行测试确认失败**

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
python -m unittest -v test_run_keywords.py
```

预期：报错 `ModuleNotFoundError: No module named 'run_keywords'`。

- [ ] **步骤4：实现解析和进度函数**

创建 `run_keywords.py`，包含以下导入和函数：

```python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib import error, request


SECTION = "## 建议首先执行的20个词"
VALID_STATUSES = {"pending", "running", "succeeded", "failed", "needs_review"}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def extract_keywords(markdown: str) -> list[str]:
    lines = markdown.splitlines()
    try:
        section_index = next(i for i, line in enumerate(lines) if line.strip() == SECTION)
        fence_start = next(
            i for i in range(section_index + 1, len(lines))
            if lines[i].strip() == "```text"
        )
        fence_end = next(
            i for i in range(fence_start + 1, len(lines))
            if lines[i].strip() == "```"
        )
    except StopIteration as exc:
        raise ValueError("找不到建议首先执行的20个词代码块") from exc

    keywords = list(dict.fromkeys(
        line.strip() for line in lines[fence_start + 1:fence_end] if line.strip()
    ))
    if len(keywords) != 20:
        raise ValueError(f"建议词代码块去重后必须恰好包含20个关键词，实际为{len(keywords)}个")
    return keywords


def keyword_digest(keywords: list[str]) -> str:
    return hashlib.sha256("\n".join(keywords).encode("utf-8")).hexdigest()


def new_progress(source: Path, keywords: list[str]) -> dict:
    timestamp = now_iso()
    return {
        "source_file": str(source.resolve()),
        "keywords_sha256": keyword_digest(keywords),
        "created_at": timestamp,
        "updated_at": timestamp,
        "keywords": [
            {
                "keyword": keyword,
                "status": "pending",
                "attempts": 0,
                "task_id": None,
                "started_at": None,
                "finished_at": None,
                "exit_code": None,
                "error": None,
            }
            for keyword in keywords
        ],
    }


def atomic_write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def load_progress(path: Path, source: Path, keywords: list[str]) -> dict:
    if not path.exists():
        state = new_progress(source, keywords)
        atomic_write_json(path, state)
        return state

    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"进度文件无法读取: {exc}") from exc
    if state.get("keywords_sha256") != keyword_digest(keywords):
        raise ValueError("词表已变化，不能复用现有进度文件")
    items = state.get("keywords")
    if not isinstance(items, list) or any(
        not isinstance(item, dict) or item.get("status") not in VALID_STATUSES
        for item in items
    ):
        raise ValueError("进度文件结构无效")
    return state
```

- [ ] **步骤5：运行解析和持久化测试**

```powershell
python -m unittest -v test_run_keywords.py
```

预期：6项测试全部通过。

- [ ] **步骤6：提交独立程序基础功能**

```powershell
git add .gitignore run_keywords.py test_run_keywords.py
git commit -m "feat: parse keyword plan and persist progress"
```

---

### 任务3：实现 API 编排和中断恢复

**文件：**
- 修改：`D:\red_note_rich_search\keyword_crawl_runner\run_keywords.py`
- 修改：`D:\red_note_rich_search\keyword_crawl_runner\test_run_keywords.py`

**接口：**
- 产出：`CrawlerApi.status() -> dict` 和 `CrawlerApi.start(keyword: str) -> str`。
- 产出：`reconcile_running(state, api, save, sleep) -> bool`。
- 产出：`run_queue(state, api, save, retry_failed, sleep) -> int`。
- 依赖：任务1的 API 字段和任务2的进度函数。

- [ ] **步骤1：编写失败的队列行为测试**

追加到 `test_run_keywords.py`：

```python
from run_keywords import run_queue


class FakeApi:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.started = []
        self.current = None

    def status(self):
        if self.current is None:
            return {
                "status": "idle",
                "task_id": None,
                "last_exit_code": None,
                "finished_at": None,
            }
        task_id, exit_code = self.current
        return {
            "status": "idle",
            "task_id": task_id,
            "last_exit_code": exit_code,
            "finished_at": "2026-07-27T10:02:00+08:00",
        }

    def start(self, keyword):
        self.started.append(keyword)
        exit_code = self.outcomes.pop(0)
        task_id = f"task-{len(self.started)}"
        self.current = (task_id, exit_code)
        return task_id


class QueueTests(unittest.TestCase):
    def state(self):
        return new_progress(Path("words.md"), KEYWORDS)

    def test_skips_success_and_continues_after_failure(self):
        state = self.state()
        state["keywords"][0]["status"] = "succeeded"
        api = FakeApi([1] + [0] * 18)
        saves = []
        result = run_queue(state, api, saves.append, False, lambda _: None)
        self.assertEqual(result, 1)
        self.assertNotIn(KEYWORDS[0], api.started)
        self.assertEqual(state["keywords"][1]["status"], "failed")
        self.assertEqual(state["keywords"][2]["status"], "succeeded")
        self.assertGreater(len(saves), 20)

    def test_retry_failed_only_resets_failed(self):
        state = self.state()
        for item in state["keywords"]:
            item["status"] = "succeeded"
        state["keywords"][3]["status"] = "failed"
        state["keywords"][4]["status"] = "needs_review"
        api = FakeApi([0])
        run_queue(state, api, lambda _: None, True, lambda _: None)
        self.assertEqual(api.started, [KEYWORDS[3]])
        self.assertEqual(state["keywords"][4]["status"], "needs_review")

    def test_mismatched_running_task_needs_review(self):
        state = self.state()
        item = state["keywords"][0]
        item.update({"status": "running", "task_id": "old-task"})
        api = FakeApi([])
        api.current = ("other-task", 0)
        result = run_queue(state, api, lambda _: None, False, lambda _: None)
        self.assertEqual(result, 2)
        self.assertEqual(item["status"], "needs_review")
        self.assertEqual(api.started, [])
```

- [ ] **步骤2：运行队列测试确认失败**

```powershell
python -m unittest -v test_run_keywords.py
```

预期：报错，因为 `run_queue` 尚未定义。

- [ ] **步骤3：实现 HTTP 客户端**

追加到 `run_keywords.py`：

```python
class ApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class CrawlerApi:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ApiError(detail or str(exc), exc.code) from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ApiError(str(exc)) from exc

    def status(self) -> dict:
        return self._request("GET", "/crawler/status")

    def start(self, keyword: str) -> str:
        response = self._request(
            "POST",
            "/crawler/start",
            {
                "platform": "xhs",
                "login_type": "qrcode",
                "crawler_type": "search",
                "keywords": keyword,
                "start_page": 1,
                "enable_comments": False,
                "enable_sub_comments": False,
                "save_option": "json",
                "cookies": "",
                "headless": False,
                "max_notes_count": 20,
            },
        )
        task_id = response.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise ApiError("启动响应缺少 task_id")
        return task_id
```

- [ ] **步骤4：实现任务核对和串行队列**

追加到 `run_keywords.py`：

```python
def save_state(state: dict, save: Callable[[dict], None]) -> None:
    state["updated_at"] = now_iso()
    save(state)


def finish_item(item: dict, status: dict) -> None:
    exit_code = status.get("last_exit_code")
    item["finished_at"] = status.get("finished_at") or now_iso()
    item["exit_code"] = exit_code
    if exit_code == 0:
        item["status"] = "succeeded"
        item["error"] = None
    else:
        item["status"] = "failed"
        item["error"] = f"crawler exited with code {exit_code}"


def wait_for_task(item, api, save_state_callback, sleep):
    while True:
        try:
            status = api.status()
        except ApiError as exc:
            item["status"] = "needs_review"
            item["error"] = f"无法确认 API 任务结果: {exc}"
            save_state_callback()
            return False
        if status.get("task_id") != item.get("task_id"):
            item["status"] = "needs_review"
            item["error"] = "API task_id 与进度文件不匹配"
            save_state_callback()
            return False
        if status.get("status") in {"running", "stopping"}:
            sleep(2)
            continue
        if status.get("status") == "idle" and status.get("last_exit_code") is not None:
            finish_item(item, status)
            save_state_callback()
            return True
        item["status"] = "needs_review"
        item["error"] = "API 未返回可确认的任务结果"
        save_state_callback()
        return False


def run_queue(
    state: dict,
    api,
    save: Callable[[dict], None],
    retry_failed: bool,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    def persist():
        save_state(state, save)

    if retry_failed:
        for item in state["keywords"]:
            if item["status"] == "failed":
                item.update({
                    "status": "pending",
                    "task_id": None,
                    "started_at": None,
                    "finished_at": None,
                    "exit_code": None,
                    "error": None,
                })
        persist()

    running = next((item for item in state["keywords"] if item["status"] == "running"), None)
    if running and not wait_for_task(running, api, persist, sleep):
        return 2

    status = api.status()
    if status.get("status") in {"running", "stopping"}:
        raise RuntimeError("API 已有其他爬虫任务运行")

    pending = [item for item in state["keywords"] if item["status"] == "pending"]
    total = len(state["keywords"])
    for item in pending:
        position = state["keywords"].index(item) + 1
        print(f"[{position}/{total}] 开始：{item['keyword']}")
        item["status"] = "running"
        item["attempts"] += 1
        item["started_at"] = now_iso()
        item["task_id"] = None
        persist()
        try:
            item["task_id"] = api.start(item["keyword"])
            persist()
            if not wait_for_task(item, api, persist, sleep):
                return 2
        except ApiError as exc:
            if exc.status_code == 400:
                item["status"] = "needs_review"
                item["error"] = str(exc)
                persist()
                return 2
            item["status"] = "failed"
            item["finished_at"] = now_iso()
            item["error"] = str(exc)
            persist()
        print(f"[{position}/{total}] {item['status']}：{item['keyword']}")
        sleep(5)

    failed = sum(item["status"] == "failed" for item in state["keywords"])
    review = sum(item["status"] == "needs_review" for item in state["keywords"])
    return 2 if review else (1 if failed else 0)
```

- [ ] **步骤5：运行队列测试，仅修复测试证实的问题**

```powershell
python -m unittest -v test_run_keywords.py
```

预期：解析、持久化和队列测试全部通过。

- [ ] **步骤6：提交队列编排功能**

```powershell
git add run_keywords.py test_run_keywords.py
git commit -m "feat: run resumable keyword crawl queue"
```

---

### 任务4：增加命令行入口、操作文档和端到端验证

**文件：**
- 修改：`D:\red_note_rich_search\keyword_crawl_runner\run_keywords.py`
- 修改：`D:\red_note_rich_search\keyword_crawl_runner\test_run_keywords.py`
- 创建：`D:\red_note_rich_search\keyword_crawl_runner\README.md`

**接口：**
- 产出：`main(argv: list[str] | None = None) -> int`。
- 依赖：任务2和任务3的全部函数。

- [ ] **步骤1：编写命令行请求参数测试**

追加到 `test_run_keywords.py`：

```python
from unittest.mock import patch
from run_keywords import CrawlerApi


class HttpPayloadTests(unittest.TestCase):
    def test_start_payload_disables_comments_and_limits_notes(self):
        api = CrawlerApi("http://127.0.0.1:8080/api")
        with patch.object(api, "_request", return_value={"task_id": "task-123"}) as call:
            self.assertEqual(api.start("重庆企业主资产配置"), "task-123")

        method, path, payload = call.call_args.args
        self.assertEqual((method, path), ("POST", "/crawler/start"))
        self.assertEqual(payload["keywords"], "重庆企业主资产配置")
        self.assertEqual(payload["max_notes_count"], 20)
        self.assertFalse(payload["enable_comments"])
        self.assertFalse(payload["enable_sub_comments"])
        self.assertEqual(payload["save_option"], "json")
```

运行：

```powershell
python -m unittest -v test_run_keywords.py
```

预期：请求参数测试及此前所有测试均通过。该测试在接入命令行前锁定已确认的采集限制。

- [ ] **步骤2：实现命令行解析和 `main`**

追加到 `run_keywords.py`：

```python
DEFAULT_SOURCE = Path(
    r"C:\Users\15377\Documents\民生银行课题\首批可立即使用的搜索词.md"
)
DEFAULT_PROGRESS = Path(__file__).with_name("crawl_progress.json")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="逐词调用 MediaCrawler API")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--api-base", default="http://127.0.0.1:8080/api")
    parser.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--retry-failed", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        source_text = args.source.read_text(encoding="utf-8")
        keywords = extract_keywords(source_text)
        state = load_progress(args.progress, args.source, keywords)
        api = CrawlerApi(args.api_base)
        initial = api.status()
        running = next(
            (item for item in state["keywords"] if item["status"] == "running"),
            None,
        )
        if initial.get("status") in {"running", "stopping"} and not running:
            raise RuntimeError("API 已有其他爬虫任务运行")
        result = run_queue(
            state,
            api,
            lambda value: atomic_write_json(args.progress, value),
            args.retry_failed,
        )
    except (OSError, ValueError, ApiError, RuntimeError) as exc:
        print(f"错误：{exc}")
        return 2

    counts = {
        status: sum(item["status"] == status for item in state["keywords"])
        for status in VALID_STATUSES
    }
    print(
        f"成功 {counts['succeeded']}，失败 {counts['failed']}，"
        f"待处理 {counts['pending']}，需要人工确认 {counts['needs_review']}"
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **步骤3：编写操作文档**

创建 `README.md`：

```markdown
# 关键词自动采集队列

逐个读取课题词表中“建议首先执行的20个词”，调用本机 MediaCrawler API，关闭评论并保存断点进度。

## 前置条件

1. Chrome 已开启远程调试，`127.0.0.1:9222` 可用。
2. MediaCrawler API 已启动：

   ```powershell
   cd D:\red_note_rich_search\MediaCrawler
   uv run uvicorn api.main:app --port 8080
   ```

3. 确认当前没有其他爬虫任务。

## 首次运行或继续未完成任务

```powershell
cd D:\red_note_rich_search\MediaCrawler
uv run python ..\keyword_crawl_runner\run_keywords.py
```

程序自动读取：

```text
C:\Users\15377\Documents\民生银行课题\首批可立即使用的搜索词.md
```

进度保存在 `crawl_progress.json`。再次执行会跳过已经成功的关键词。

## 重试明确失败项

```powershell
uv run python ..\keyword_crawl_runner\run_keywords.py --retry-failed
```

`needs_review` 不会自动重跑。先检查 MediaCrawler 输出和进度文件，再手工决定改为 `succeeded` 或 `failed`。

## 输出

笔记仍由 MediaCrawler 写入：

```text
D:\red_note_rich_search\MediaCrawler\data\xhs\json
```

后续分析按 `(note_id, source_keyword)` 去重。
```

- [ ] **步骤4：运行全部自动化验证**

独立队列程序仓库：

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
python -m unittest -v
```

预期：不连接 MediaCrawler 或小红书，队列程序测试全部通过。

MediaCrawler 仓库：

```powershell
cd D:\red_note_rich_search\MediaCrawler
uv run pytest tests/test_crawler_task_status.py tests/test_api_limits.py -q
uv run pytest tests -q
```

预期：聚焦测试及完整测试套件全部通过。

- [ ] **步骤5：执行受控的两关键词冒烟测试**

使用真实的20关键词词表和专用冒烟测试进度文件。运行：

```powershell
cd D:\red_note_rich_search\MediaCrawler
uv run uvicorn api.main:app --port 8080
```

在第二个终端中：

```powershell
uv run python ..\keyword_crawl_runner\run_keywords.py --progress D:\red_note_rich_search\keyword_crawl_runner\smoke_progress.json
```

第一个关键词成功后的5秒间隔内按 `Ctrl+C`。再次运行相同命令，程序必须跳过第一个关键词并开始第二个；第二个关键词成功后的间隔内再次按 `Ctrl+C`。

验证：

- Two keywords reach terminal states.
- 两次 API 请求均关闭评论，并设置 `max_notes_count=20`。
- 重启队列程序后跳过第一个已完成关键词。
- MediaCrawler 输出记录包含匹配的 `source_keyword`。

验证后，可以保留被忽略的 `smoke_progress.json`，或仅删除该冒烟测试进度文件；不要改动真实的 `crawl_progress.json`。

- [ ] **步骤6：提交队列程序命令行和文档**

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
git add run_keywords.py test_run_keywords.py README.md
git commit -m "docs: add keyword runner operating guide"
```

- [ ] **步骤7：记录两个仓库的最终状态**

```powershell
git -C D:\red_note_rich_search\MediaCrawler status --short
git -C D:\red_note_rich_search\MediaCrawler log -2 --oneline
git -C D:\red_note_rich_search\keyword_crawl_runner status --short
git -C D:\red_note_rich_search\keyword_crawl_runner log -2 --oneline
```

预期：

- MediaCrawler 仅显示用户原有的未跟踪讨论文档。
- 队列程序仓库状态干净，`crawl_progress.json` 仍被忽略。
- 两个仓库都显示本计划对应的任务提交。
