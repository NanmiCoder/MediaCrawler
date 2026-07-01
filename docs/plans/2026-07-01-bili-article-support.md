# Bilibili Article Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add complete Bilibili article support, including article URL parsing, article detail crawling, first-level comments, optional second-level comments, and dedicated storage.

**Architecture:** Keep existing video public APIs compatible while extracting Bilibili comment crawling into a generic `type + oid` implementation. Article crawling is added as a first-class content flow with dedicated parsing, client methods, core orchestration, and storage models. The video comment pagination semantics have already been corrected: first-level comments are trimmed by `max_count` before saving and before second-level comment fetching, and retained first-level comments are always counted even when second-level comments are enabled.

**Tech Stack:** Python async/await, Playwright-backed Bilibili API client, SQLAlchemy models, existing MediaCrawler store abstractions, pytest.

---

## Context

Current Bilibili code is video-centered:

- `media_platform/bilibili/client.py` calls Bilibili comment APIs with `type=1`, which means video comments.
- Bilibili article comments require the same comment API family but with `type=12` and `oid=<article cvid>`.
- `media_platform/bilibili/help.py` only parses video BV URLs and creator URLs.
- `store/bilibili` and `database/models.py` only have video and video comment storage models.

Completed prerequisite: video comment crawling now trims first-level comments before fetching second-level comments and extends the local result in both modes. This behavior is covered by `tests/test_bilibili_client_comments.py`.

The implementation should preserve existing video methods such as `get_video_comments()` as compatibility wrappers. The new generic implementation should become the only place that knows how to page comments and second-level comments, while preserving the corrected video semantics above.

## External API Notes

Use Bilibili's common comment model:

- Video comments: `type=1`, `oid=<aid>`
- Article comments: `type=12`, `oid=<cvid>`
- First-level comments endpoint: `/x/v2/reply/wbi/main`
- Second-level comments endpoint: `/x/v2/reply/reply`

Before implementing article detail mapping, verify a real article detail response with one known `cv` article ID. Do not guess the final response shape for title/content/stat fields.

---

### Task 1: Add Bilibili Article URL Model And Parser

**Files:**
- Modify: `model/m_bilibili.py`
- Modify: `media_platform/bilibili/help.py`
- Test: `tests/media_platform/bilibili/test_help.py`

**Step 1: Write failing parser tests**

Create or extend `tests/media_platform/bilibili/test_help.py`:

```python
import pytest

from media_platform.bilibili.help import parse_article_info_from_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("cv123456", "123456"),
        ("123456", "123456"),
        ("https://www.bilibili.com/read/cv123456", "123456"),
        ("https://www.bilibili.com/read/cv123456?spm_id_from=333.999.0.0", "123456"),
    ],
)
def test_parse_article_info_from_url(raw, expected):
    article_info = parse_article_info_from_url(raw)
    assert article_info.article_id == expected
    assert article_info.article_type == "article"


def test_parse_article_info_from_url_invalid():
    with pytest.raises(ValueError):
        parse_article_info_from_url("https://www.bilibili.com/video/BV1d54y1g7db")
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/media_platform/bilibili/test_help.py -v
```

Expected: FAIL because `parse_article_info_from_url` and `ArticleUrlInfo` do not exist.

**Step 3: Add model and parser**

In `model/m_bilibili.py`, add:

```python
class ArticleUrlInfo(BaseModel):
    """Bilibili article URL information"""
    article_id: str = Field(title="article id (cv id without cv prefix)")
    article_type: str = Field(default="article", title="article type")
```

In `media_platform/bilibili/help.py`, import `ArticleUrlInfo` and add `parse_article_info_from_url(url: str) -> ArticleUrlInfo`.

Parsing rules:

- If input is digits, return it directly.
- If input starts with `cv` followed by digits, strip `cv`.
- If URL contains `/read/cv<digits>`, extract digits.
- Otherwise raise `ValueError`.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/media_platform/bilibili/test_help.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add model/m_bilibili.py media_platform/bilibili/help.py tests/media_platform/bilibili/test_help.py
git commit -m "feat: parse bilibili article urls"
```

---

### Task 2: Add Generic Bilibili Comment Type Support

**Files:**
- Modify: `media_platform/bilibili/field.py`
- Modify: `media_platform/bilibili/client.py`
- Test: `tests/media_platform/bilibili/test_client_comments.py`

**Step 1: Write failing client tests**

Create `tests/media_platform/bilibili/test_client_comments.py` with a minimal client fixture that bypasses network by monkeypatching `get`.

Test these cases:

```python
import pytest

from media_platform.bilibili.field import BilibiliCommentType, CommentOrderType


@pytest.mark.asyncio
async def test_get_comments_uses_comment_type(monkeypatch, bili_client):
    captured = {}

    async def fake_get(uri, params=None, enable_params_sign=True):
        captured["uri"] = uri
        captured["params"] = params
        return {}

    monkeypatch.setattr(bili_client, "get", fake_get)

    await bili_client.get_comments(
        oid="123456",
        comment_type=BilibiliCommentType.ARTICLE,
        order_mode=CommentOrderType.DEFAULT,
        next=0,
    )

    assert captured["uri"] == "/x/v2/reply/wbi/main"
    assert captured["params"]["oid"] == "123456"
    assert captured["params"]["type"] == 12
```

Also add a compatibility test:

```python
@pytest.mark.asyncio
async def test_get_video_comments_keeps_type_1(monkeypatch, bili_client):
    captured = {}

    async def fake_get(uri, params=None, enable_params_sign=True):
        captured["params"] = params
        return {}

    monkeypatch.setattr(bili_client, "get", fake_get)

    await bili_client.get_video_comments("998877")

    assert captured["params"]["oid"] == "998877"
    assert captured["params"]["type"] == 1
```

If there is no reusable `bili_client` fixture, create a local fixture with dummy headers, page, and cookies. Monkeypatched tests should not touch network or Playwright.

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/media_platform/bilibili/test_client_comments.py -v
```

Expected: FAIL because `BilibiliCommentType` and `get_comments()` do not exist.

**Step 3: Implement comment type enum and generic first-level method**

In `media_platform/bilibili/field.py`, add:

```python
class BilibiliCommentType(Enum):
    VIDEO = 1
    ARTICLE = 12
```

In `media_platform/bilibili/client.py`, add:

```python
async def get_comments(
    self,
    oid: str,
    comment_type: BilibiliCommentType,
    order_mode: CommentOrderType = CommentOrderType.DEFAULT,
    next: int = 0,
) -> Dict:
    uri = "/x/v2/reply/wbi/main"
    post_data = {
        "oid": oid,
        "mode": order_mode.value,
        "type": comment_type.value,
        "ps": 20,
        "next": next,
    }
    return await self.get(uri, post_data)
```

Change `get_video_comments()` to call `get_comments(..., BilibiliCommentType.VIDEO, ...)`.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/media_platform/bilibili/test_client_comments.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add media_platform/bilibili/field.py media_platform/bilibili/client.py tests/media_platform/bilibili/test_client_comments.py
git commit -m "feat: add generic bilibili comment type support"
```

---

### Task 3: Generalize Corrected Comment Pagination And Second-Level Comments

**Files:**
- Modify: `media_platform/bilibili/client.py`
- Test: `tests/media_platform/bilibili/test_client_comments.py`
- Existing regression: `tests/test_bilibili_client_comments.py`

**Step 1: Write failing pagination tests**

Add tests that monkeypatch first-level and second-level methods:

```python
@pytest.mark.asyncio
async def test_get_all_comments_limits_first_level_before_fetching_sub_comments(monkeypatch, bili_client):
    fetched_roots = []
    saved_batches = []

    async def fake_get_comments(oid, comment_type, order_mode, next):
        return {
            "cursor": {"is_end": True, "next": 0},
            "replies": [
                {"rpid": 1, "rcount": 1, "content": {"message": "a"}, "member": {"mid": 1, "uname": "u1"}},
                {"rpid": 2, "rcount": 1, "content": {"message": "b"}, "member": {"mid": 2, "uname": "u2"}},
            ],
        }

    async def fake_get_all_level_two_comments(oid, comment_type, level_one_comment_id, order_mode, ps, crawl_interval, callback):
        fetched_roots.append(level_one_comment_id)

    async def fake_callback(oid, comments):
        saved_batches.append(comments)

    monkeypatch.setattr(bili_client, "get_comments", fake_get_comments)
    monkeypatch.setattr(bili_client, "get_all_level_two_comments", fake_get_all_level_two_comments)

    await bili_client.get_all_comments(
        oid="123",
        comment_type=BilibiliCommentType.ARTICLE,
        crawl_interval=0,
        is_fetch_sub_comments=True,
        callback=fake_callback,
        max_count=1,
    )

    assert len(saved_batches[0]) == 1
    assert fetched_roots == [1]
```

Also add or preserve a video-wrapper regression equivalent to `tests/test_bilibili_client_comments.py`:

- `get_video_all_comments(..., is_fetch_sub_comments=True, max_count=1)` saves and returns only one retained first-level comment.
- Second-level comments are fetched only for that retained first-level comment.
- This regression should continue to pass after video methods delegate to generic methods.

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/media_platform/bilibili/test_client_comments.py -v
```

Expected: FAIL because `get_all_comments()` and generic second-level methods do not exist yet. The existing video-specific regression should already pass before this task and must continue to pass after the refactor.

**Step 3: Implement generic pagination**

In `media_platform/bilibili/client.py`, add:

- `get_all_comments(oid, comment_type, crawl_interval, is_fetch_sub_comments, callback, max_count)`
- `get_all_level_two_comments(oid, comment_type, level_one_comment_id, order_mode, ps, crawl_interval, callback)`
- `get_level_two_comments(oid, comment_type, level_one_comment_id, pn, ps, order_mode)`

Required behavior:

1. Fetch a page of first-level comments.
2. Validate `cursor.is_end` and `cursor.next`.
3. Trim `comment_list` before saving and before fetching sub-comments.
4. Save first-level comments with `callback(oid, comment_list)`.
5. If `is_fetch_sub_comments` is true, fetch second-level comments only for retained first-level comments where `rcount > 0`.
6. Always extend the local result with retained first-level comments so `max_count` works in both modes.

Important: `max_count` limits retained first-level comments. It does not impose a global cap on second-level comments; second-level pagination remains controlled by the second-level API loop for each retained first-level comment.

Update old video methods as wrappers:

- `get_video_all_comments()` calls `get_all_comments(..., BilibiliCommentType.VIDEO, ...)`.
- `get_video_all_level_two_comments()` calls generic second-level method with `VIDEO`.
- `get_video_level_two_comments()` calls generic method with `VIDEO`.

**Step 4: Run tests**

Run:

```bash
pytest tests/media_platform/bilibili/test_client_comments.py tests/test_bilibili_client_comments.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add media_platform/bilibili/client.py tests/media_platform/bilibili/test_client_comments.py
git commit -m "refactor: generalize bilibili comment pagination"
```

---

### Task 4: Verify And Implement Article Detail Client

**Files:**
- Modify: `media_platform/bilibili/client.py`
- Test: `tests/media_platform/bilibili/test_client_article.py`

**Step 1: Manually verify article detail endpoint**

Use one known public article ID and run a small script or interactive call through existing client authentication if needed. Candidate API endpoints to verify include Bilibili article/read APIs. Record the response fields used for:

- article ID
- title
- summary or content
- creator ID and name
- publish timestamp
- stats: likes, favorites, shares, comments

Do not commit captured personal cookies or full response dumps.

**Step 2: Write failing mapping test**

Create `tests/media_platform/bilibili/test_client_article.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_get_article_info_calls_expected_endpoint(monkeypatch, bili_client):
    captured = {}

    async def fake_get(uri, params=None, enable_params_sign=True):
        captured["uri"] = uri
        captured["params"] = params
        return {"id": 123456, "title": "article title"}

    monkeypatch.setattr(bili_client, "get", fake_get)

    result = await bili_client.get_article_info("123456")

    assert captured["params"]
    assert result["title"] == "article title"
```

Adjust exact assertions after endpoint verification.

**Step 3: Run test to verify it fails**

Run:

```bash
pytest tests/media_platform/bilibili/test_client_article.py -v
```

Expected: FAIL because `get_article_info()` does not exist.

**Step 4: Implement `get_article_info()`**

Add a method to `BilibiliClient` that accepts article ID without the `cv` prefix and returns raw article detail data.

Keep response normalization out of the client unless existing project style clearly normalizes in client. Current Bilibili video code stores raw-ish API detail and maps it in store layer, so follow that pattern.

**Step 5: Run tests**

Run:

```bash
pytest tests/media_platform/bilibili/test_client_article.py tests/media_platform/bilibili/test_client_comments.py -v
```

Expected: PASS.

**Step 6: Commit**

```bash
git add media_platform/bilibili/client.py tests/media_platform/bilibili/test_client_article.py
git commit -m "feat: add bilibili article detail client"
```

---

### Task 5: Add Article Database Models

**Files:**
- Modify: `database/models.py`
- Test: `tests/database/test_bilibili_article_models.py`

**Step 1: Write model metadata test**

Create `tests/database/test_bilibili_article_models.py`:

```python
from database.models import BilibiliArticle, BilibiliArticleComment


def test_bilibili_article_table_name():
    assert BilibiliArticle.__tablename__ == "bilibili_article"


def test_bilibili_article_comment_table_name():
    assert BilibiliArticleComment.__tablename__ == "bilibili_article_comment"
```

Add assertions for key columns if existing database model tests follow that style.

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/database/test_bilibili_article_models.py -v
```

Expected: FAIL because models do not exist.

**Step 3: Add models**

In `database/models.py`, add:

`BilibiliArticle` fields:

- `id`
- `article_id`
- `article_url`
- `title`
- `desc`
- `content`
- `creator_hash`
- `nickname`
- `liked_count`
- `favorite_count`
- `share_count`
- `comment_count`
- `create_time`
- `source_keyword`
- `add_ts`
- `last_modify_ts`

`BilibiliArticleComment` fields:

- `id`
- `creator_hash`
- `nickname`
- `add_ts`
- `last_modify_ts`
- `comment_id`
- `article_id`
- `content`
- `create_time`
- `sub_comment_count`
- `parent_comment_id`
- `like_count`

Follow existing type choices from `BilibiliVideo` and `BilibiliVideoComment`.

**Step 4: Run test**

Run:

```bash
pytest tests/database/test_bilibili_article_models.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add database/models.py tests/database/test_bilibili_article_models.py
git commit -m "feat: add bilibili article database models"
```

---

### Task 6: Add Article Store Methods

**Files:**
- Modify: `store/bilibili/__init__.py`
- Modify: `store/bilibili/_store_impl.py`
- Test: `tests/store/bilibili/test_article_store.py`

**Step 1: Write failing store mapping tests**

Create `tests/store/bilibili/test_article_store.py`.

Use monkeypatching to avoid filesystem and database writes:

```python
import pytest

from store import bilibili as bilibili_store


@pytest.mark.asyncio
async def test_update_bilibili_article_maps_article_fields(monkeypatch):
    saved = {}

    class FakeStore:
        async def store_content(self, content_item):
            saved.update(content_item)

    monkeypatch.setattr(bilibili_store.BiliStoreFactory, "create_store", lambda: FakeStore())

    await bilibili_store.update_bilibili_article({
        "id": 123456,
        "title": "title",
        "summary": "summary",
        "content": "content",
        "publish_time": 1710000000,
        "author": {"mid": 100, "name": "author"},
        "stats": {"like": 1, "favorite": 2, "share": 3, "reply": 4},
    })

    assert saved["article_id"] == "123456"
    assert saved["article_url"] == "https://www.bilibili.com/read/cv123456"
    assert saved["title"] == "title"
```

Adjust raw field names after Task 4 endpoint verification.

Add a comment mapping test:

```python
@pytest.mark.asyncio
async def test_update_bilibili_article_comment_maps_common_reply_fields(monkeypatch):
    saved = {}

    class FakeStore:
        async def store_article_comment(self, comment_item):
            saved.update(comment_item)

    monkeypatch.setattr(bilibili_store.BiliStoreFactory, "create_store", lambda: FakeStore())

    await bilibili_store.update_bilibili_article_comment("123456", {
        "rpid": 9,
        "parent": 0,
        "ctime": 1710000000,
        "content": {"message": "hello"},
        "member": {"mid": 10, "uname": "user"},
        "like": 5,
        "rcount": 1,
    })

    assert saved["article_id"] == "123456"
    assert saved["comment_id"] == "9"
    assert saved["content"] == "hello"
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/store/bilibili/test_article_store.py -v
```

Expected: FAIL because article store methods do not exist.

**Step 3: Add public store functions**

In `store/bilibili/__init__.py`, add:

- `update_bilibili_article(article_item: Dict)`
- `batch_update_bilibili_article_comments(article_id: str, comments: List[Dict])`
- `update_bilibili_article_comment(article_id: str, comment_item: Dict)`

Use `anonymize_user_id()` and `mask_nickname()` consistently with video storage.

**Step 4: Add store implementation methods**

In `store/bilibili/_store_impl.py`:

- Import `BilibiliArticle` and `BilibiliArticleComment`.
- Add `store_article_comment()` to store classes that need a separate comment collection/table.
- For file-based stores, write article content with `item_type="articles"` and article comments with `item_type="article_comments"`.
- For DB store, upsert `BilibiliArticle` by `article_id` and `BilibiliArticleComment` by `comment_id`.
- For Mongo store, use collection suffixes `articles` and `article_comments`.

If changing the abstract store interface would affect every platform, avoid adding abstract methods. Use Bilibili store implementation methods directly where needed, or fall back to existing `store_comment()` only if the implementation can route by `item_type`.

**Step 5: Run tests**

Run:

```bash
pytest tests/store/bilibili/test_article_store.py tests/database/test_bilibili_article_models.py -v
```

Expected: PASS.

**Step 6: Commit**

```bash
git add store/bilibili/__init__.py store/bilibili/_store_impl.py tests/store/bilibili/test_article_store.py
git commit -m "feat: add bilibili article storage"
```

---

### Task 7: Wire Article Detail Flow Into Bilibili Core

**Files:**
- Modify: `media_platform/bilibili/core.py`
- Modify: `config/bilibili_config.py`
- Test: `tests/media_platform/bilibili/test_core_article_flow.py`

**Step 1: Write failing orchestration tests**

Create `tests/media_platform/bilibili/test_core_article_flow.py`.

Test that article inputs are parsed and passed to article detail/comment methods. Use a `BilibiliCrawler` instance with monkeypatched `bili_client` and store functions.

Important cases:

- `get_specified_articles(["cv123456"])` fetches article detail for `123456`.
- If comments are enabled, article comments are fetched.
- Existing `get_specified_videos()` remains unchanged.

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/media_platform/bilibili/test_core_article_flow.py -v
```

Expected: FAIL because article core methods do not exist.

**Step 3: Add config documentation**

In `config/bilibili_config.py`, update `BILI_SPECIFIED_ID_LIST` comments to say it supports:

- Bilibili video URL
- BV number
- Bilibili article URL
- `cv` article ID
- numeric article ID, when treated as article ID in article-specific config

Prefer adding `BILI_SPECIFIED_ARTICLE_ID_LIST = []` if mixed numeric IDs would be ambiguous. A pure numeric input could be a creator ID or article ID depending on context, so article-specific config is safer.

Recommended approach:

- Keep `BILI_SPECIFIED_ID_LIST` for videos.
- Add `BILI_SPECIFIED_ARTICLE_ID_LIST` for articles.
- In `detail` mode, crawl both lists.

**Step 4: Add core methods**

In `media_platform/bilibili/core.py`, add:

- `get_specified_articles(article_url_list: List[str])`
- `batch_get_article_comments(article_id_list: List[str])`
- `get_article_comments(article_id: str, semaphore: asyncio.Semaphore)`

Behavior:

1. Parse article IDs.
2. Fetch article detail with `self.bili_client.get_article_info(article_id)`.
3. Store with `bilibili_store.update_bilibili_article(article_detail)`.
4. If `ENABLE_GET_COMMENTS`, fetch article comments with:
   - `self.bili_client.get_all_comments(...)`
   - `comment_type=BilibiliCommentType.ARTICLE`
   - `callback=bilibili_store.batch_update_bilibili_article_comments`
   - `max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES`

In `start()`, under `CRAWLER_TYPE == "detail"`, call both:

- `get_specified_videos(config.BILI_SPECIFIED_ID_LIST)`
- `get_specified_articles(config.BILI_SPECIFIED_ARTICLE_ID_LIST)`

Only call article flow if the list exists and is non-empty.

**Step 5: Run tests**

Run:

```bash
pytest tests/media_platform/bilibili/test_core_article_flow.py tests/media_platform/bilibili/test_client_comments.py -v
```

Expected: PASS.

**Step 6: Commit**

```bash
git add media_platform/bilibili/core.py config/bilibili_config.py tests/media_platform/bilibili/test_core_article_flow.py
git commit -m "feat: wire bilibili article detail crawling"
```

---

### Task 8: Add Article Comment Wrapper Methods

**Files:**
- Modify: `media_platform/bilibili/client.py`
- Test: `tests/media_platform/bilibili/test_client_comments.py`

**Step 1: Write failing wrapper tests**

Add tests:

```python
@pytest.mark.asyncio
async def test_get_article_comments_uses_type_12(monkeypatch, bili_client):
    captured = {}

    async def fake_get_comments(oid, comment_type, order_mode, next):
        captured["oid"] = oid
        captured["type"] = comment_type.value
        return {}

    monkeypatch.setattr(bili_client, "get_comments", fake_get_comments)

    await bili_client.get_article_comments("123456")

    assert captured == {"oid": "123456", "type": 12}
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/media_platform/bilibili/test_client_comments.py -v
```

Expected: FAIL because article wrappers do not exist.

**Step 3: Add wrappers**

Add:

- `get_article_comments(article_id, order_mode=CommentOrderType.DEFAULT, next=0)`
- `get_article_all_comments(article_id, crawl_interval=1.0, is_fetch_sub_comments=False, callback=None, max_count=10)`

Both should delegate to generic comment methods with `BilibiliCommentType.ARTICLE`.

**Step 4: Run tests**

Run:

```bash
pytest tests/media_platform/bilibili/test_client_comments.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add media_platform/bilibili/client.py tests/media_platform/bilibili/test_client_comments.py
git commit -m "feat: add bilibili article comment wrappers"
```

---

### Task 9: Documentation And User Configuration

**Files:**
- Modify: `README.md`
- Modify: `docs/index.md`
- Modify: `docs/项目架构文档.md`

**Step 1: Update user-facing docs**

Document Bilibili article support:

- `BILI_SPECIFIED_ARTICLE_ID_LIST`
- Supported formats:
  - `https://www.bilibili.com/read/cv123456`
  - `cv123456`
  - `123456`
- Comment flags:
  - `ENABLE_GET_COMMENTS`
  - `ENABLE_GET_SUB_COMMENTS`
  - `CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES`
- Data outputs:
  - `articles`
  - `article_comments`

**Step 2: Run docs grep**

Run:

```bash
rg -n "BILI_SPECIFIED_ARTICLE_ID_LIST|article_comments|专栏" README.md docs config/bilibili_config.py
```

Expected: New config and docs are discoverable.

**Step 3: Commit**

```bash
git add README.md docs/index.md docs/项目架构文档.md
git commit -m "docs: document bilibili article crawling"
```

---

### Task 10: End-To-End Verification

**Files:**
- No code changes expected unless verification finds defects.

**Step 1: Run focused tests**

Run:

```bash
pytest tests/media_platform/bilibili tests/store/bilibili tests/database/test_bilibili_article_models.py -v
```

Expected: PASS.

**Step 2: Run broader test suite**

Run:

```bash
pytest tests -v
```

Expected: PASS, or document unrelated existing failures with exact failing tests.

**Step 3: Run a dry manual detail crawl**

Set a local config or command-line args for:

- `PLATFORM=bili`
- `CRAWLER_TYPE=detail`
- one valid `BILI_SPECIFIED_ARTICLE_ID_LIST`
- `ENABLE_GET_COMMENTS=True`
- `ENABLE_GET_SUB_COMMENTS=False`
- `CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES=2`
- `SAVE_DATA_OPTION=jsonl`

Run the crawler and verify:

- Article detail output exists.
- Article comment output exists.
- No video output is created unless video IDs are configured.

**Step 4: Run optional second-level comment verification**

Repeat with:

- `ENABLE_GET_SUB_COMMENTS=True`
- `CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES=1`

Verify:

- For both video and article flows, only retained first-level comments trigger second-level comment fetching.
- Saved second-level comments have non-zero `parent_comment_id`.

**Step 5: Final status**

Run:

```bash
git status --short --branch
```

Expected: clean working tree after final commit.

---

## Non-Goals For This Plan

- Bilibili article search by keyword.
- Crawling all articles from a creator homepage.
- Downloading images embedded in article content.
- Changing comment crawling behavior for non-Bilibili platforms.

These can be added later once the specified-article flow is stable.
