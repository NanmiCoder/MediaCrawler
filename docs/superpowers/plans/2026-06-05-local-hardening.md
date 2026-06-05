# Local Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the local MediaCrawler checkout by making WebUI/CDP loopback-only by default and preventing cookie values from appearing in crawler start logs.

**Architecture:** Keep the real subprocess command unchanged, and add a small display-only redaction helper inside `CrawlerManager`. Add a testable WebUI server launch wrapper, and change the browser launcher CDP argument at the existing launch point.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, pytest, pytest-asyncio, unittest.mock.

---

## File Structure

- Modify `tests/test_api_limits.py`: add focused tests for command redaction, WebUI loopback launch, and browser CDP loopback launch.
- Modify `api/services/crawler_manager.py`: add display-only command redaction helpers and use them for the start log entry.
- Modify `api/main.py`: add `run_api_server()` and use `127.0.0.1` for direct module execution.
- Modify `tools/browser_launcher.py`: replace the remote debugging address argument with loopback.

---

### Task 0: Baseline Check

**Files:**
- Read: `tests/test_api_limits.py`

- [ ] **Step 1: Run the existing focused tests**

Run:

```powershell
uv run pytest tests/test_api_limits.py -q
```

Expected: exit code `0`, with `10 passed` before new tests are added. If this fails because dependencies are not installed, run `uv sync` and repeat the same pytest command.

---

### Task 1: Safe Crawler Command Logging

**Files:**
- Modify: `tests/test_api_limits.py`
- Modify: `api/services/crawler_manager.py:117`
- Modify: `api/services/crawler_manager.py:205`

- [ ] **Step 1: Write failing tests for redaction and subprocess command preservation**

Add these tests to `tests/test_api_limits.py` after `test_crawler_manager_build_command()`:

```python
def test_crawler_manager_redacts_cookies_in_logged_command():
    cm = CrawlerManager()
    cmd = [
        "uv",
        "run",
        "python",
        "main.py",
        "--platform",
        "xhs",
        "--cookies",
        "web_session=secret; a=b",
        "--headless",
        "false",
    ]

    redacted = cm._redact_command_for_log(cmd)

    assert redacted == [
        "uv",
        "run",
        "python",
        "main.py",
        "--platform",
        "xhs",
        "--cookies",
        "[REDACTED]",
        "--headless",
        "false",
    ]
    assert cmd[cmd.index("--cookies") + 1] == "web_session=secret; a=b"


def test_crawler_manager_format_start_log_redacts_cookie_value():
    cm = CrawlerManager()
    cmd = [
        "uv",
        "run",
        "python",
        "main.py",
        "--cookies",
        "web_session=secret; a=b",
        "--headless",
        "false",
    ]

    message = cm._format_start_command_log(cmd)

    assert message == "Starting crawler: uv run python main.py --cookies [REDACTED] --headless false"
    assert "web_session=secret" not in message


def test_crawler_manager_build_command_keeps_cookie_value_for_subprocess():
    cm = CrawlerManager()
    req = CrawlerStartRequest(
        platform=PlatformEnum.XHS,
        login_type=LoginTypeEnum.COOKIE,
        crawler_type=CrawlerTypeEnum.SEARCH,
        keywords="test",
        cookies="web_session=secret; a=b",
    )

    cmd = cm._build_command(req)

    cookies_index = cmd.index("--cookies")
    assert cmd[cookies_index + 1] == "web_session=secret; a=b"
```

- [ ] **Step 2: Run the new redaction tests and verify they fail for the expected reason**

Run:

```powershell
uv run pytest tests/test_api_limits.py::test_crawler_manager_redacts_cookies_in_logged_command tests/test_api_limits.py::test_crawler_manager_format_start_log_redacts_cookie_value tests/test_api_limits.py::test_crawler_manager_build_command_keeps_cookie_value_for_subprocess -q
```

Expected: the first two tests fail because `CrawlerManager` does not yet define `_redact_command_for_log()` and `_format_start_command_log()`. The third test should pass because `_build_command()` already passes cookies to the subprocess command.

- [ ] **Step 3: Add the minimal redaction helpers**

Add these methods in `api/services/crawler_manager.py` before `async def start(...)`:

```python
    @staticmethod
    def _redact_command_for_log(cmd: list) -> list:
        """Return a display-safe command copy with cookie values hidden."""
        redacted_cmd = list(cmd)
        for index, arg in enumerate(redacted_cmd):
            if arg == "--cookies" and index + 1 < len(redacted_cmd):
                redacted_cmd[index + 1] = "[REDACTED]"
        return redacted_cmd

    def _format_start_command_log(self, cmd: list) -> str:
        """Format the crawler start message without exposing secrets."""
        redacted_cmd = self._redact_command_for_log(cmd)
        return f"Starting crawler: {' '.join(redacted_cmd)}"
```

Replace the existing start-log line in `api/services/crawler_manager.py`:

```python
            entry = self._create_log_entry(f"Starting crawler: {' '.join(cmd)}", "info")
```

with:

```python
            entry = self._create_log_entry(self._format_start_command_log(cmd), "info")
```

- [ ] **Step 4: Run the redaction tests and verify they pass**

Run:

```powershell
uv run pytest tests/test_api_limits.py::test_crawler_manager_redacts_cookies_in_logged_command tests/test_api_limits.py::test_crawler_manager_format_start_log_redacts_cookie_value tests/test_api_limits.py::test_crawler_manager_build_command_keeps_cookie_value_for_subprocess -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit the logging change**

Run:

```powershell
git add tests/test_api_limits.py api/services/crawler_manager.py
git commit -m "fix: redact cookies in crawler start logs"
```

---

### Task 2: WebUI Direct Launch Loopback Binding

**Files:**
- Modify: `tests/test_api_limits.py`
- Modify: `api/main.py:199`

- [ ] **Step 1: Write the failing WebUI launch test**

Add this import near the other imports in `tests/test_api_limits.py`:

```python
import api.main as api_main
```

Add this test near the API tests:

```python
def test_run_api_server_binds_to_loopback():
    with patch("api.main.uvicorn.run") as mock_run:
        api_main.run_api_server()

    mock_run.assert_called_once_with(api_main.app, host="127.0.0.1", port=8080)
```

- [ ] **Step 2: Run the WebUI launch test and verify it fails for the expected reason**

Run:

```powershell
uv run pytest tests/test_api_limits.py::test_run_api_server_binds_to_loopback -q
```

Expected: failure because `api.main` does not yet define `run_api_server()`.

- [ ] **Step 3: Add the testable loopback launch wrapper**

Replace the bottom of `api/main.py`:

```python
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

with:

```python
def run_api_server():
    uvicorn.run(app, host="127.0.0.1", port=8080)


if __name__ == "__main__":
    run_api_server()
```

- [ ] **Step 4: Run the WebUI launch test and verify it passes**

Run:

```powershell
uv run pytest tests/test_api_limits.py::test_run_api_server_binds_to_loopback -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit the WebUI binding change**

Run:

```powershell
git add tests/test_api_limits.py api/main.py
git commit -m "fix: bind webui direct launch to loopback"
```

---

### Task 3: Browser CDP Loopback Binding

**Files:**
- Modify: `tests/test_api_limits.py`
- Modify: `tools/browser_launcher.py:128`

- [ ] **Step 1: Write the failing browser launcher test**

Add this import near the other imports in `tests/test_api_limits.py`:

```python
from tools.browser_launcher import BrowserLauncher
```

Add this test near the crawler manager tests:

```python
def test_browser_launcher_binds_remote_debugging_to_loopback():
    launcher = BrowserLauncher()

    with patch("tools.browser_launcher.subprocess.Popen") as mock_popen:
        launcher.launch_browser(r"C:\Browser\browser.exe", 9222)

    args = mock_popen.call_args.args[0]
    assert "--remote-debugging-address=127.0.0.1" in args
    assert "--remote-debugging-address=0.0.0.0" not in args
```

- [ ] **Step 2: Run the browser launcher test and verify it fails for the expected reason**

Run:

```powershell
uv run pytest tests/test_api_limits.py::test_browser_launcher_binds_remote_debugging_to_loopback -q
```

Expected: failure because the launch arguments still contain `--remote-debugging-address=0.0.0.0`.

- [ ] **Step 3: Change the CDP address argument**

Replace this argument in `tools/browser_launcher.py`:

```python
            "--remote-debugging-address=0.0.0.0",  # Allow remote access
```

with:

```python
            "--remote-debugging-address=127.0.0.1",  # Restrict CDP to local access
```

- [ ] **Step 4: Run the browser launcher test and verify it passes**

Run:

```powershell
uv run pytest tests/test_api_limits.py::test_browser_launcher_binds_remote_debugging_to_loopback -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit the browser binding change**

Run:

```powershell
git add tests/test_api_limits.py tools/browser_launcher.py
git commit -m "fix: bind browser cdp to loopback"
```

---

### Task 4: Final Verification

**Files:**
- Verify: `api/main.py`
- Verify: `api/services/crawler_manager.py`
- Verify: `tools/browser_launcher.py`
- Verify: `tests/test_api_limits.py`

- [ ] **Step 1: Run the focused test file**

Run:

```powershell
uv run pytest tests/test_api_limits.py -q
```

Expected: exit code `0`, with `15 passed`.

- [ ] **Step 2: Scan the hardened files for old exposure patterns**

Run:

```powershell
rg -n "0\\.0\\.0\\.0|Starting crawler:.*join\\(cmd\\)" api\\main.py tools\\browser_launcher.py api\\services\\crawler_manager.py
```

Expected: no matches and exit code `1`.

- [ ] **Step 3: Check patch whitespace**

Run:

```powershell
git diff --check
```

Expected: exit code `0` and no output.

- [ ] **Step 4: Inspect final branch status**

Run:

```powershell
git status --short --branch
```

Expected: branch `codex/harden-local-defaults` with no uncommitted changes after the task commits.
