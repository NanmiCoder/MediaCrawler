# XHS Creator ID Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture XHS author IDs during the initial keyword crawl, attach IDs only to strong/medium AI candidates, and optionally crawl those candidates with the existing creator mode.

**Architecture:** MediaCrawler gains an opt-in, local sidecar capture before anonymous storage. The keyword runner enables that option. Screening remains anonymous until all model responses are validated, then joins qualified author hashes to the local sidecar; an explicit flag submits each deduplicated ID to the existing creator API.

**Tech Stack:** Python 3.11, asyncio, Typer, FastAPI/Pydantic, standard-library JSON/urllib, pytest and unittest.

## Global Constraints

- `store/xhs/__init__.py` remains unchanged and ordinary content storage remains anonymous.
- Only `potential_customer` notes with `strong` or `medium` evidence and non-empty evidence quotes qualify.
- Raw IDs never enter AI prompts, screening cache, `cleaned_notes.jsonl`, or `screened_notes.jsonl`.
- ID capture is off by default and is enabled only by the keyword research runner.
- No new dependency, database, WebUI, contact extraction, cross-platform matching, or marketing automation.
- Creator comments and media downloads stay disabled; `--creator-max-notes` must be positive.
- Preserve unrelated changes in both repositories, especially `keyword_crawl_runner/docs/superpowers/plans/2026-07-29-xhs-ai-screening.md` and `keyword_crawl_runner/results/`.

---

### Task 1: Opt-in ID sidecar capture in MediaCrawler

**Files:**
- Create: `tools/xhs_creator_id_capture.py`
- Create: `tests/test_xhs_creator_id_capture.py`
- Modify: `config/base_config.py`
- Modify: `media_platform/xhs/core.py:170-174`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: raw XHS `note_detail` dictionaries returned by `get_note_detail_async_task()`.
- Produces: `build_capture_record(note_detail, captured_at=None) -> dict | None` and `capture_creator_id(note_detail) -> None`.
- Produces local files at `data/xhs/private/search_creator_ids_YYYY-MM-DD.json`; files contain only `note_id`, `creator_hash`, `public_user_id`, `profile_url`, and `captured_at`.

- [ ] **Step 1: Write failing unit tests for safe records and idempotent persistence**

```python
# tests/test_xhs_creator_id_capture.py
import json

import pytest

import config
from tools.xhs_creator_id_capture import build_capture_record, capture_creator_id


VALID_ID = "5eb8e1d400000000010075ae"


def test_build_capture_record_contains_only_allowed_fields():
    record = build_capture_record({
        "note_id": "note-1",
        "user": {
            "user_id": VALID_ID,
            "nickname": "不得保存",
            "avatar": "https://private.invalid/avatar",
        },
        "xsec_token": "secret-token",
    }, captured_at="2026-07-31T10:00:00+08:00")

    assert record == {
        "note_id": "note-1",
        "creator_hash": "fb9185b3a79e6291",
        "public_user_id": VALID_ID,
        "profile_url": f"https://www.xiaohongshu.com/user/profile/{VALID_ID}",
        "captured_at": "2026-07-31T10:00:00+08:00",
    }


@pytest.mark.asyncio
async def test_capture_is_disabled_by_default_and_idempotent_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ENABLE_XHS_CREATOR_ID_CAPTURE", False)
    monkeypatch.setattr(config, "XHS_CREATOR_ID_CAPTURE_DIR", str(tmp_path))
    detail = {"note_id": "note-1", "user": {"user_id": VALID_ID}}

    await capture_creator_id(detail)
    assert list(tmp_path.iterdir()) == []

    monkeypatch.setattr(config, "ENABLE_XHS_CREATOR_ID_CAPTURE", True)
    await capture_creator_id(detail)
    await capture_creator_id(detail)
    records = json.loads(next(tmp_path.iterdir()).read_text(encoding="utf-8"))
    assert len(records) == 1
    assert records[0]["public_user_id"] == VALID_ID


def test_invalid_user_id_is_not_captured():
    assert build_capture_record({"note_id": "note-1", "user": {"user_id": "short"}}) is None
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `uv run pytest tests/test_xhs_creator_id_capture.py -v`

Expected: collection fails with `ModuleNotFoundError: No module named 'tools.xhs_creator_id_capture'`.

- [ ] **Step 3: Add default-off configuration and minimal capture module**

Add to `config/base_config.py`:

```python
ENABLE_XHS_CREATOR_ID_CAPTURE = False
XHS_CREATOR_ID_CAPTURE_DIR = ""
```

Create `tools/xhs_creator_id_capture.py` with these concrete behaviors:

```python
import asyncio
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

import config
from tools.user_hash import anonymize_user_id
from tools.utils import utils

_USER_ID = re.compile(r"^[0-9a-f]{24}$")
_LOCK = asyncio.Lock()


def build_capture_record(note_detail: dict, captured_at: str | None = None) -> dict | None:
    note_id = str(note_detail.get("note_id") or "").strip()
    user_id = str((note_detail.get("user") or {}).get("user_id") or "").strip()
    if not note_id or not _USER_ID.fullmatch(user_id):
        return None
    return {
        "note_id": note_id,
        "creator_hash": anonymize_user_id(user_id),
        "public_user_id": user_id,
        "profile_url": f"https://www.xiaohongshu.com/user/profile/{user_id}",
        "captured_at": captured_at or datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def _capture_path() -> Path:
    base = Path(config.XHS_CREATOR_ID_CAPTURE_DIR) if config.XHS_CREATOR_ID_CAPTURE_DIR else Path("data/xhs/private")
    return base / f"search_creator_ids_{utils.get_current_date()}.json"


def _write_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    keyed = {(item["note_id"], item["public_user_id"]): item for item in records}
    keyed[(record["note_id"], record["public_user_id"])] = record
    fd, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(list(keyed.values()), output, ensure_ascii=False, indent=2)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


async def capture_creator_id(note_detail: dict) -> None:
    if not config.ENABLE_XHS_CREATOR_ID_CAPTURE:
        return
    record = build_capture_record(note_detail)
    if record is None:
        return
    async with _LOCK:
        await asyncio.to_thread(_write_record, _capture_path(), record)
```

Add `/data/xhs/private/` to `.gitignore`.

- [ ] **Step 4: Hook capture before anonymous storage**

In `media_platform/xhs/core.py`, import `capture_creator_id`, then change the search result loop to:

```python
for note_detail in note_details:
    if note_detail:
        await capture_creator_id(note_detail)
        await xhs_store.update_xhs_note(note_detail)
        await self.get_notice_media(note_detail)
        note_ids.append(note_detail.get("note_id"))
        xsec_tokens.append(note_detail.get("xsec_token"))
```

- [ ] **Step 5: Run focused and anonymity tests**

Run: `uv run pytest tests/test_xhs_creator_id_capture.py tests/test_no_user_info.py -v`

Expected: all tests pass; no raw ID appears in ordinary XHS content storage.

- [ ] **Step 6: Commit Task 1 in the MediaCrawler repository**

```powershell
git add -- .gitignore config/base_config.py media_platform/xhs/core.py tools/xhs_creator_id_capture.py tests/test_xhs_creator_id_capture.py
git commit -m "feat: capture XHS creator ids during initial search"
```

### Task 2: Thread the capture switch through CLI, API, and keyword runner

**Files:**
- Modify: `cmd_arg/arg.py`
- Modify: `api/schemas/crawler.py`
- Modify: `api/services/crawler_manager.py`
- Modify: `tests/test_api_limits.py`
- Modify: `../keyword_crawl_runner/run_keywords.py`
- Modify: `../keyword_crawl_runner/test_run_keywords.py`

**Interfaces:**
- Consumes: API request field `capture_creator_ids: bool = False`.
- Produces: CLI option `--capture_creator_ids true|false`, assigned to `config.ENABLE_XHS_CREATOR_ID_CAPTURE`.
- Keyword runner search requests always set `capture_creator_ids` to `true`.

- [ ] **Step 1: Write failing MediaCrawler propagation tests**

Add to `tests/test_api_limits.py`:

```python
@pytest.mark.asyncio
async def test_capture_creator_ids_cli_defaults_off_and_can_be_enabled():
    original = config.ENABLE_XHS_CREATOR_ID_CAPTURE
    try:
        await parse_cmd(["--platform", "xhs", "--capture_creator_ids", "true"])
        assert config.ENABLE_XHS_CREATOR_ID_CAPTURE is True
    finally:
        config.ENABLE_XHS_CREATOR_ID_CAPTURE = original


def test_crawler_manager_only_passes_capture_switch_when_enabled():
    manager = CrawlerManager()
    disabled = manager._build_command(CrawlerStartRequest(platform=PlatformEnum.XHS))
    enabled = manager._build_command(CrawlerStartRequest(
        platform=PlatformEnum.XHS,
        capture_creator_ids=True,
    ))
    assert "--capture_creator_ids" not in disabled
    index = enabled.index("--capture_creator_ids")
    assert enabled[index + 1] == "true"
```

- [ ] **Step 2: Run MediaCrawler tests and verify RED**

Run: `uv run pytest tests/test_api_limits.py -v`

Expected: failures report the missing Pydantic field or missing CLI option.

- [ ] **Step 3: Implement the MediaCrawler propagation**

Add `capture_creator_ids: bool = False` to `CrawlerStartRequest`. Add a Typer string option named
`--capture_creator_ids`, normalize it with the existing `_to_bool()`, and assign the result to
`config.ENABLE_XHS_CREATOR_ID_CAPTURE`. In `CrawlerManager._build_command()` append:

```python
if config.capture_creator_ids:
    cmd.extend(["--capture_creator_ids", "true"])
```

- [ ] **Step 4: Verify MediaCrawler GREEN**

Run: `uv run pytest tests/test_api_limits.py tests/test_xhs_creator_id_capture.py -v`

Expected: all tests pass.

- [ ] **Step 5: Write the failing keyword-runner payload assertion**

In `../keyword_crawl_runner/test_run_keywords.py`, extend
`test_start_payload_disables_comments_and_limits_notes` with:

```python
self.assertTrue(payload["capture_creator_ids"])
```

- [ ] **Step 6: Run the keyword-runner test and verify RED**

Run from `D:\red_note_rich_search\keyword_crawl_runner`:
`python -m unittest test_run_keywords.HttpPayloadTests.test_start_payload_disables_comments_and_limits_notes -v`

Expected: failure with `KeyError: 'capture_creator_ids'`.

- [ ] **Step 7: Enable capture in keyword searches**

Add this field to `CrawlerApi.start()`'s POST payload in `run_keywords.py`:

```python
"capture_creator_ids": True,
```

- [ ] **Step 8: Verify and commit Task 2 in both repositories**

Run MediaCrawler: `uv run pytest tests/test_api_limits.py -v`

Run keyword runner: `python -m unittest test_run_keywords.HttpPayloadTests -v`

Commit MediaCrawler:

```powershell
git add -- cmd_arg/arg.py api/schemas/crawler.py api/services/crawler_manager.py tests/test_api_limits.py
git commit -m "feat: expose XHS creator id capture switch"
```

Commit keyword runner without staging unrelated files:

```powershell
git add -- run_keywords.py test_run_keywords.py
git commit -m "feat: capture creator ids in keyword crawls"
```

### Task 3: Keep only strong/medium candidates and attach captured IDs

**Files:**
- Modify: `../keyword_crawl_runner/screening/features.py`
- Create: `../keyword_crawl_runner/screening/creator_ids.py`
- Modify: `../keyword_crawl_runner/screen_data.py`
- Modify: `../keyword_crawl_runner/test_screening_features.py`
- Modify: `../keyword_crawl_runner/test_screen_data.py`

**Interfaces:**
- Consumes: sidecar JSON arrays matching `search_creator_ids_*.json`.
- Produces: `load_creator_id_records(path: Path) -> list[dict]` and
  `attach_creator_ids(authors: list[dict], records: list[dict]) -> tuple[list[dict], list[dict]]`.
- Produces: `candidate_creators.json` containing only qualified authors plus `public_user_id` and `profile_url`; `candidate_creator_errors.json` contains missing-map and hash-conflict records.

- [ ] **Step 1: Change aggregation expectations first**

Update `test_candidate_score_boundaries_are_assigned_to_tiers` to expect only authors `a` and `b`.
Replace provider-only, evidence-none, and weak-only tests with assertions that
`aggregate_authors(notes) == []`. These tests must fail because current aggregation emits C-tier authors.

- [ ] **Step 2: Run feature tests and verify RED**

Run from `keyword_crawl_runner`:
`python -m unittest test_screening_features.AggregateAuthorsTests -v`

Expected: three failures showing unqualified authors are still returned.

- [ ] **Step 3: Apply the minimal candidate filter**

In `aggregate_authors()`, skip groups immediately after computing `qualified_notes`:

```python
qualified_notes = [note for note in notes if _is_qualified_potential_customer(note)]
if not qualified_notes:
    continue
```

- [ ] **Step 4: Add failing ID join tests**

Add tests to `test_screen_data.py` that call the wished-for interface:

```python
from screening.creator_ids import attach_creator_ids


def test_attach_creator_ids_links_unique_hash_and_reports_missing_or_conflict():
    authors = [
        {"creator_hash": "ok"},
        {"creator_hash": "missing"},
        {"creator_hash": "conflict"},
    ]
    records = [
        {"creator_hash": "ok", "public_user_id": "5eb8e1d400000000010075ae"},
        {"creator_hash": "conflict", "public_user_id": "5eb8e1d400000000010075af"},
        {"creator_hash": "conflict", "public_user_id": "5eb8e1d400000000010075b0"},
    ]

    linked, errors = attach_creator_ids(authors, records)

    assert linked == [{
        "creator_hash": "ok",
        "public_user_id": "5eb8e1d400000000010075ae",
        "profile_url": "https://www.xiaohongshu.com/user/profile/5eb8e1d400000000010075ae",
    }]
    assert [item["error"] for item in errors] == ["missing_mapping", "hash_conflict"]
```

- [ ] **Step 5: Run the ID join test and verify RED**

Run: `python -m unittest test_screen_data -v`

Expected: import fails for missing `screening.creator_ids`.

- [ ] **Step 6: Implement sidecar loading and collision-safe join**

Create `screening/creator_ids.py` using only `json`, `re`, and `pathlib`. It must:

```python
def load_creator_id_records(path: Path) -> list[dict]:
    paths = [path] if path.is_file() else sorted(path.glob("search_creator_ids_*.json"))
    records = []
    for source in paths:
        value = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(value, list):
            raise ValueError(f"{source}: creator ID map must be an array")
        records.extend(item for item in value if isinstance(item, dict))
    return records


def attach_creator_ids(authors: list[dict], records: list[dict]) -> tuple[list[dict], list[dict]]:
    by_hash: dict[str, set[str]] = {}
    for record in records:
        creator_hash = record.get("creator_hash")
        user_id = record.get("public_user_id")
        if isinstance(creator_hash, str) and re.fullmatch(r"[0-9a-f]{24}", str(user_id)):
            by_hash.setdefault(creator_hash, set()).add(user_id)
    linked, errors = [], []
    for author in authors:
        ids = sorted(by_hash.get(author["creator_hash"], set()))
        if len(ids) != 1:
            errors.append({
                "creator_hash": author["creator_hash"],
                "error": "missing_mapping" if not ids else "hash_conflict",
            })
            continue
        user_id = ids[0]
        linked.append({
            **author,
            "public_user_id": user_id,
            "profile_url": f"https://www.xiaohongshu.com/user/profile/{user_id}",
        })
    return linked, errors
```

- [ ] **Step 7: Integrate the join after AI completion**

Add `--creator-id-map` to `screen_data.parse_args()`, defaulting to
`../MediaCrawler/data/xhs/private`. Add `"creator_errors": "candidate_creator_errors.json"` to
`OUTPUT_FILES`. After `aggregate_authors(evidence_notes)`, load the sidecar and call
`attach_creator_ids()`. Write linked authors to `candidate_creators.json` and errors to the new file.
Do not add either value to `featured_notes`, `results`, the AI call, or `ScreeningCache`.

Extend `_atomic_write()` with a keyword-only `sanitize: bool = True`. Keep the current sanitizer for
all existing outputs, but call it with `sanitize=False` only for `candidate_creators.json`,
`candidate_creator_errors.json`, and later `candidate_creator_crawl.json`. These three local files are
the intentional private research outputs; every value written to them must first be constructed by the
whitelisting functions in `screening.creator_ids.py` or the creator crawl status builder.

- [ ] **Step 8: Update integration expectations and verify**

Update `test_screen_data.py` fixtures to create a sidecar mapping for `author-1`; expect six output
files and assert raw IDs occur only in `candidate_creators.json`. Add one test where `screen_note()`
inspects its input and confirms `public_user_id` is absent.

Run:
`python -m unittest test_screening_features test_screen_data -v`

Expected: all tests pass.

- [ ] **Step 9: Commit Task 3 in keyword_crawl_runner**

```powershell
git add -- screening/features.py screening/creator_ids.py screen_data.py test_screening_features.py test_screen_data.py
git commit -m "feat: attach ids to strong and medium candidates"
```

### Task 4: Optional automatic creator crawl

**Files:**
- Modify: `../keyword_crawl_runner/run_keywords.py`
- Modify: `../keyword_crawl_runner/screen_data.py`
- Modify: `../keyword_crawl_runner/test_run_keywords.py`
- Modify: `../keyword_crawl_runner/test_screen_data.py`
- Modify: `../keyword_crawl_runner/README.md`

**Interfaces:**
- Produces: `CrawlerApi.start_creator(user_id: str, max_notes_count: int) -> str`.
- Consumes: `--crawl-creators`, `--crawler-api-base`, and `--creator-max-notes`.
- Produces: `candidate_creator_crawl.json` with one status record per deduplicated candidate ID.

- [ ] **Step 1: Write failing creator API payload test**

Add to `test_run_keywords.HttpPayloadTests`:

```python
def test_start_creator_disables_comments_and_uses_one_public_id(self):
    api = CrawlerApi("http://127.0.0.1:8080/api")
    with patch.object(api, "_request", return_value={"task_id": "creator-task"}) as request_call:
        task_id = api.start_creator("5eb8e1d400000000010075ae", 50)
    assert task_id == "creator-task"
    payload = request_call.call_args.args[2]
    assert payload["crawler_type"] == "creator"
    assert payload["creator_ids"] == "5eb8e1d400000000010075ae"
    assert payload["max_notes_count"] == 50
    assert payload["enable_comments"] is False
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m unittest test_run_keywords.HttpPayloadTests.test_start_creator_disables_comments_and_uses_one_public_id -v`

Expected: failure with missing `start_creator`.

- [ ] **Step 3: Implement `start_creator` with the existing `_request` helper**

```python
def start_creator(self, user_id: str, max_notes_count: int) -> str:
    response = self._request("POST", "/crawler/start", {
        "platform": "xhs",
        "login_type": "qrcode",
        "crawler_type": "creator",
        "creator_ids": user_id,
        "enable_comments": False,
        "enable_sub_comments": False,
        "save_option": "json",
        "cookies": "",
        "headless": False,
        "max_notes_count": max_notes_count,
    })
    task_id = response.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        raise ApiError("启动响应缺少 task_id")
    return task_id
```

- [ ] **Step 4: Write failing orchestration tests**

Add tests to `test_screen_data.py` for a helper with this interface:

```python
from screen_data import crawl_candidate_creators


def test_crawl_candidate_creators_deduplicates_and_continues_after_failure():
    creators = [
        {"public_user_id": "5eb8e1d400000000010075ae"},
        {"public_user_id": "5eb8e1d400000000010075ae"},
        {"public_user_id": "5eb8e1d400000000010075af"},
    ]
    api = FakeCreatorApi(fail_ids={"5eb8e1d400000000010075ae"})
    statuses = crawl_candidate_creators(creators, api, 50, sleep=lambda _: None)
    assert api.started == [
        "5eb8e1d400000000010075ae",
        "5eb8e1d400000000010075af",
    ]
    assert [item["status"] for item in statuses] == ["failed", "succeeded"]
```

Also assert `run_screening()` never constructs `CrawlerApi` without `--crawl-creators`.

- [ ] **Step 5: Run orchestration tests and verify RED**

Run: `python -m unittest test_screen_data -v`

Expected: import fails for missing `crawl_candidate_creators`.

- [ ] **Step 6: Implement explicit creator crawling**

Add CLI options:

```python
parser.add_argument("--crawl-creators", action="store_true")
parser.add_argument("--crawler-api-base", default="http://127.0.0.1:8080/api")
parser.add_argument("--creator-max-notes", type=int, default=50)
```

Reject `creator_max_notes < 1`. Implement `crawl_candidate_creators()` to preserve input order,
deduplicate IDs, call `start_creator()` once per author, poll `api.status()` until the matching task is
idle, and catch `ApiError` per author. Return only:

```python
{
    "public_user_id": user_id,
    "task_id": task_id_or_none,
    "status": "succeeded" | "failed" | "needs_review",
    "error": safe_short_error_or_none,
}
```

When `args.crawl_creators` is true, call the helper only after all screening files are successfully
written, then atomically write `candidate_creator_crawl.json`. When false, do not create this file and
do not contact the crawler API.

- [ ] **Step 7: Update README with the exact two-stage commands**

Document:

```powershell
python screen_data.py `
  --input ..\MediaCrawler\data\xhs\json `
  --output results\first_pass_20260731 `
  --creator-id-map ..\MediaCrawler\data\xhs\private `
  --crawl-creators `
  --creator-max-notes 50

python screen_data.py `
  --input ..\MediaCrawler\data\xhs\json `
  --pattern "creator_contents_*.json" `
  --output results\second_pass_20260731
```

- [ ] **Step 8: Run keyword-runner regression tests**

Run: `python -m unittest discover -v`

Expected: all tests pass with no network calls from tests.

- [ ] **Step 9: Commit Task 4 in keyword_crawl_runner**

```powershell
git add -- run_keywords.py screen_data.py test_run_keywords.py test_screen_data.py README.md
git commit -m "feat: crawl qualified XHS creator candidates"
```

### Task 5: Cross-repository verification

**Files:**
- Verify only; no new production files.

**Interfaces:**
- Confirms the API contract and sidecar schema match across both repositories.

- [ ] **Step 1: Run MediaCrawler focused regression**

Run from `D:\red_note_rich_search\MediaCrawler`:

```powershell
uv run pytest tests/test_xhs_creator_id_capture.py tests/test_api_limits.py tests/test_no_user_info.py tests/test_crawler_task_status.py -v
```

Expected: all selected tests pass.

- [ ] **Step 2: Run keyword runner full suite**

Run from `D:\red_note_rich_search\keyword_crawl_runner`:

```powershell
python -m unittest discover -v
```

Expected: all tests pass.

- [ ] **Step 3: Run static and diff checks**

Run in each repository:

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors; only the user's pre-existing unrelated changes remain unstaged.

- [ ] **Step 4: Perform one controlled manual smoke test**

Start the existing MediaCrawler API, run one keyword through `run_keywords.py`, and verify:

1. A new `data/xhs/private/search_creator_ids_YYYY-MM-DD.json` exists.
2. Ordinary search content still contains `creator_hash` and no raw `user_id`.
3. AI request inspection shows no raw ID.
4. `candidate_creators.json` contains IDs only for strong/medium candidates.
5. With `--crawl-creators`, creator notes are saved without requesting comments or media.

Do not commit generated data or smoke-test results.
