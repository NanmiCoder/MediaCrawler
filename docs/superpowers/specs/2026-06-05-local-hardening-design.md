# Local Hardening Design

## Goal

Make the local MediaCrawler checkout safer for personal XHS/Douyin keyword crawling by reducing accidental exposure of WebUI control endpoints, Chrome DevTools Protocol access, and cookie values in runtime logs.

## Scope

This change is limited to the minimal hardening path approved as option A:

- Bind the WebUI API server to `127.0.0.1` by default when started with `python -m api.main`.
- Bind launched browser CDP access to `127.0.0.1` instead of all interfaces.
- Redact cookie values when `CrawlerManager` logs the generated crawler command.
- Add focused tests for cookie redaction and keep the existing command-building behavior intact.

## Non-Goals

- Do not add WebUI authentication or token middleware in this pass.
- Do not upgrade dependency versions in this pass.
- Do not change crawler platform behavior, scraping limits, storage formats, or cookie passing to the subprocess.
- Do not remove WebUI cookie-login support; only prevent cookie disclosure in logs.

## Architecture

The WebUI server already centralizes process launch in `api/services/crawler_manager.py`, so cookie redaction should live near command construction and logging. `_build_command()` remains the source of the real subprocess command; a separate helper returns a redacted copy for display/logging only.

The bind-address hardening is a default change at the launch points:

- `api/main.py` changes the direct module entrypoint to `host="127.0.0.1"`.
- `tools/browser_launcher.py` changes Chrome/Edge launch arguments to `--remote-debugging-address=127.0.0.1`.

## Data Flow

WebUI request data still flows into `CrawlerStartRequest`, then into `_build_command()`, then into `subprocess.Popen()`. Cookie values are still present in the actual `cmd` list when provided, because the crawler subprocess needs them. Only the message passed to `_create_log_entry()` uses the redacted copy.

## Error Handling

No new external failure mode is introduced. If subprocess launch fails, the existing `Failed to start crawler: ...` path remains unchanged. Redaction should be defensive: if a command list contains `--cookies` without a following value, the helper leaves the flag intact and does not raise.

## Testing

Add tests in `tests/test_api_limits.py` or a nearby existing API service test file:

- A command with `--cookies <value>` is rendered with the cookie value replaced by a constant redaction marker.
- The original command list is not mutated by redaction.
- A request with cookies still passes the real cookie value into `_build_command()`.

Run the focused pytest target first, then a broader existing test target if dependencies are available.

## Risks

Users who intentionally exposed WebUI or CDP to other hosts will need to pass their own host/launch configuration manually. That is acceptable for this local checkout because the approved objective is safer personal use.
