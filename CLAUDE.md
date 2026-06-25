# MediaCrawler — TikTok Vietnam Extension

## Mục tiêu dự án

Fork [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) và thêm platform `tiktok` hỗ trợ **TikTok quốc tế** (`tiktok.com`), tương đương với platform `douyin` hiện có.

**Dữ liệu cần crawl:**
- Video + metadata (views, likes, shares, description, hashtags)
- Bình luận + replies (nested comments)
- Profile creator / KOL (follower count, video list, bio)
- Hashtag trending (video list theo hashtag)

---

## Kiến trúc tổng quan

```
MediaCrawler/
├── media_platform/
│   ├── douyin/          ← REFERENCE: copy cấu trúc này
│   └── tiktok/          ← TẠO MỚI
├── store/
│   ├── douyin/          ← REFERENCE
│   └── tiktok/          ← TẠO MỚI
├── model/
│   ├── m_douyin.py      ← REFERENCE
│   └── m_tiktok.py      ← TẠO MỚI
├── config/
│   └── tiktok_config.py ← TẠO MỚI
├── constant/
│   └── tiktok_constant.py ← TẠO MỚI
├── libs/
│   └── tiktok_sign.js   ← TẠO MỚI (phần khó nhất)
├── cmd_arg/arg.py        ← SỬA: thêm "tiktok"
└── main.py               ← SỬA: thêm case "tiktok"
```

**Nguyên tắc:** Luôn đọc file tương đương của `douyin/` trước khi tạo file mới.

---

## Phase 1 — Setup & Foundation

### Bước 1.1 — Fork và khảo sát codebase

```bash
git clone https://github.com/NanmiCoder/MediaCrawler.git
cd MediaCrawler
git checkout -b feature/tiktok-platform
uv sync
uv run playwright install chromium
```

**Đọc các file sau trước khi code:**

```bash
cat base/base_crawler.py
cat media_platform/douyin/core.py
cat media_platform/douyin/client.py
cat media_platform/douyin/login.py
cat media_platform/douyin/field.py
cat cmd_arg/arg.py
cat main.py
```

### Bước 1.2 — Tạo cấu trúc thư mục

```bash
mkdir -p media_platform/tiktok
mkdir -p store/tiktok
```

---

## Phase 2 — Config & Constants

### File: `config/tiktok_config.py`

```python
TIKTOK_KEYWORD_LIST: list = ["AI tools", "review sản phẩm"]
TIKTOK_VIDEO_ID_LIST: list = []
TIKTOK_CREATOR_ID_LIST: list = []
TIKTOK_HASHTAG_LIST: list = []
TIKTOK_MAX_COMMENTS_PER_VIDEO: int = 100
TIKTOK_MAX_CONCURRENCY: int = 3
```

### File: `constant/tiktok_constant.py`

```python
TIKTOK_BASE_URL = "https://www.tiktok.com"

# API endpoints — verify bằng DevTools > Network > XHR khi dùng TikTok
SEARCH_VIDEO_URL = "/api/search/general/full/"
VIDEO_DETAIL_URL = "/api/item/detail/"
COMMENT_LIST_URL = "/api/comment/list/"
COMMENT_REPLY_URL = "/api/comment/reply/list/"
CREATOR_PROFILE_URL = "/api/user/detail/"
CREATOR_VIDEO_LIST_URL = "/api/post/item_list/"
HASHTAG_DETAIL_URL = "/api/challenge/detail/"
HASHTAG_VIDEO_URL = "/api/challenge/item_list/"

COMMON_PARAMS = {
    "aid": "1988",
    "app_language": "en",
    "app_name": "tiktok_web",
    "browser_language": "en-US",
    "browser_platform": "Win32",
    "channel": "tiktok_web",
    "device_platform": "web_pc",
    "os": "windows",
    "region": "VN",
    "tz_name": "Asia/Ho_Chi_Minh",
}
```

---

## Phase 3 — Data Models

### File: `model/m_tiktok.py`

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TikTokVideo:
    video_id: str
    desc: str
    create_time: int
    author_id: str
    author_unique_id: str
    author_nickname: str
    video_play_url: str
    video_cover_url: str
    liked_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    play_count: int = 0
    collect_count: int = 0
    duration: int = 0
    hashtags: List[str] = field(default_factory=list)
    source_keyword: str = ""

@dataclass
class TikTokComment:
    comment_id: str
    video_id: str
    content: str
    user_id: str
    user_unique_id: str
    nickname: str
    create_time: int
    like_count: int = 0
    reply_count: int = 0
    parent_comment_id: Optional[str] = None

@dataclass
class TikTokCreator:
    user_id: str
    unique_id: str
    nickname: str
    bio: str
    avatar_url: str
    follower_count: int = 0
    following_count: int = 0
    video_count: int = 0
    heart_count: int = 0
    verified: bool = False
    region: str = ""
```

---

## Phase 4 — Core Implementation

### File: `media_platform/tiktok/exception.py`

```python
class DataFetchError(Exception):
    pass

class IPBlockError(Exception):
    pass
```

### File: `media_platform/tiktok/field.py`

```python
class SearchField:
    VIDEO_LIST = "data"
    CURSOR = "cursor"
    HAS_MORE = "has_more"

class VideoField:
    VIDEO_ID = "id"
    DESC = "desc"
    CREATE_TIME = "createTime"
    AUTHOR = "author"
    STATS = "stats"

class CommentField:
    COMMENT_ID = "cid"
    TEXT = "text"
    USER = "user"
    CREATE_TIME = "create_time"
    LIKE_COUNT = "digg_count"
    REPLY_TOTAL = "reply_comment_total"

class CreatorField:
    USER_INFO = "userInfo"
    USER = "user"
    STATS = "stats"
```

### File: `media_platform/tiktok/help.py`

```python
import re
from typing import Optional

def extract_video_id_from_url(url: str) -> Optional[str]:
    patterns = [
        r'tiktok\.com/@[^/]+/video/(\d+)',
        r'tiktok\.com/video/(\d+)',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def extract_creator_id_from_url(url: str) -> Optional[str]:
    m = re.search(r'tiktok\.com/@([^/?]+)', url)
    return m.group(1) if m else None
```

### File: `media_platform/tiktok/login.py`

```python
"""
3 phương thức login:
1. qrcode  — quét QR bằng TikTok mobile app
2. phone   — số điện thoại + OTP
3. cookie  — load cookie đã save

NOTE: TikTok international dùng Arkose Labs captcha,
khuyến nghị dùng cookie mode sau lần đầu login thủ công.
"""

from playwright.async_api import BrowserContext, Page
from base.base_crawler import AbstractLogin


class TikTokLogin(AbstractLogin):
    def __init__(self, login_type: str, browser_context: BrowserContext,
                 playwright_page=None, cookie_str: str = ""):
        self.login_type = login_type
        self.browser_context = browser_context
        self.playwright_page = playwright_page
        self.cookie_str = cookie_str

    async def begin(self):
        if self.login_type == "qrcode":
            await self.login_by_qrcode()
        elif self.login_type == "cookie":
            await self.login_by_cookies()

    async def login_by_qrcode(self):
        page = await self.browser_context.new_page()
        await page.goto("https://www.tiktok.com/login/phone-or-email/email")
        # TODO: click "Use QR code", screenshot, polling check login state

    async def login_by_cookies(self):
        # TODO: parse cookie_str và add vào browser_context
        pass

    async def check_login_state(self, page: Page) -> bool:
        try:
            await page.wait_for_selector('[data-e2e="profile-icon"]', timeout=5000)
            return True
        except:
            return False
```

### File: `libs/tiktok_sign.js` ⚠️ PHẦN KHÓ NHẤT

```javascript
/**
 * TikTok Web Signature Generator
 *
 * TikTok dùng X-Bogus + msToken để validate request.
 *
 * CHIẾN LƯỢC KHUYẾN NGHỊ:
 * Dùng Playwright để gọi signing function có sẵn trong
 * window context của TikTok (same approach với douyin.js).
 *
 * Bước debug:
 * 1. Mở tiktok.com trong browser
 * 2. DevTools > Console > gõ: Object.keys(window).filter(k => k.includes('sign'))
 * 3. Tìm function liên quan đến X-Bogus
 * 4. Test: window.TIKTOK_SIGN_URL("https://www.tiktok.com/api/test?a=1")
 */

async function sign(url) {
    // Placeholder — cần inspect window object trên tiktok.com để tìm đúng function name
    throw new Error("NOT IMPLEMENTED — inspect window object trên tiktok.com");
}

module.exports = { sign };
```

### File: `media_platform/tiktok/client.py`

```python
import httpx
from typing import Optional
from .exception import DataFetchError
from constant.tiktok_constant import TIKTOK_BASE_URL, COMMON_PARAMS


class TikTokClient:
    def __init__(self, proxies=None, timeout=10, headers=None,
                 playwright_page=None, cookie_dict=None):
        self.proxies = proxies
        self.timeout = timeout
        self.headers = headers or {}
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict or {}

    async def _sign_url(self, url: str) -> str:
        """Inject JS để sign URL với X-Bogus qua Playwright"""
        # Cần verify đúng function name bằng cách inspect window object
        signed = await self.playwright_page.evaluate(
            f'() => window.TIKTOK_SIGN_URL("{url}")'
        )
        return signed

    async def get(self, uri: str, params: dict = None) -> dict:
        full_url = f"{TIKTOK_BASE_URL}{uri}"
        merged = {**COMMON_PARAMS, **(params or {})}
        query = "&".join(f"{k}={v}" for k, v in merged.items())
        url_with_params = f"{full_url}?{query}"

        signed_url = await self._sign_url(url_with_params)
        cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookie_dict.items())

        async with httpx.AsyncClient(proxies=self.proxies) as client:
            resp = await client.get(
                signed_url,
                headers={**self.headers, "Cookie": cookie_str,
                         "Referer": "https://www.tiktok.com/"},
                timeout=self.timeout
            )
            data = resp.json()
            if data.get("statusCode") not in (0, None):
                raise DataFetchError(f"TikTok API error: {data}")
            return data

    async def search_video_by_keyword(self, keyword: str, offset=0, count=20):
        return await self.get("/api/search/general/full/", {
            "keyword": keyword, "offset": offset, "count": count
        })

    async def get_video_detail(self, video_id: str):
        return await self.get("/api/item/detail/", {"itemId": video_id})

    async def get_video_comments(self, video_id: str, cursor=0, count=20):
        return await self.get("/api/comment/list/", {
            "aweme_id": video_id, "cursor": cursor, "count": count
        })

    async def get_comment_replies(self, video_id: str, comment_id: str, cursor=0, count=20):
        return await self.get("/api/comment/reply/list/", {
            "item_id": video_id, "comment_id": comment_id, "cursor": cursor, "count": count
        })

    async def get_creator_profile(self, unique_id: str):
        return await self.get("/api/user/detail/", {"uniqueId": unique_id})

    async def get_creator_videos(self, user_id: str, cursor=0, count=20):
        return await self.get("/api/post/item_list/", {
            "userId": user_id, "cursor": cursor, "count": count
        })

    async def get_hashtag_detail(self, hashtag: str):
        return await self.get("/api/challenge/detail/", {"challengeName": hashtag})

    async def get_hashtag_videos(self, hashtag_id: str, cursor=0, count=20):
        return await self.get("/api/challenge/item_list/", {
            "challengeID": hashtag_id, "cursor": cursor, "count": count
        })
```

### File: `media_platform/tiktok/core.py`

```python
"""
TikTokCrawler — main crawler class
Mirror cấu trúc của media_platform/douyin/core.py
"""

import asyncio
from typing import Optional
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

from base.base_crawler import AbstractCrawler
from config import tiktok_config, base_config
from .client import TikTokClient
from .login import TikTokLogin
from model.m_tiktok import TikTokVideo, TikTokComment, TikTokCreator


class TikTokCrawler(AbstractCrawler):

    def __init__(self):
        self.browser_context: Optional[BrowserContext] = None
        self.context_page: Optional[Page] = None
        self.tiktok_client: Optional[TikTokClient] = None

    async def start(self):
        async with async_playwright() as playwright:
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium, None, headless=base_config.HEADLESS
            )
            await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto("https://www.tiktok.com")

            login_obj = TikTokLogin(
                login_type=base_config.LOGIN_TYPE,
                browser_context=self.browser_context,
                playwright_page=self.context_page,
                cookie_str=getattr(tiktok_config, "COOKIES", ""),
            )
            await login_obj.begin()

            cookie_dict = {c["name"]: c["value"]
                          for c in await self.browser_context.cookies()}
            self.tiktok_client = TikTokClient(
                playwright_page=self.context_page,
                cookie_dict=cookie_dict,
            )

            crawl_type = base_config.CRAWLER_TYPE
            if crawl_type == "search":
                await self.search()
            elif crawl_type == "detail":
                await self.get_specified_videos()
            elif crawl_type == "creator":
                await self.get_creators_and_videos()
            elif crawl_type == "hashtag":
                await self.get_hashtag_videos()

    async def search(self):
        for keyword in tiktok_config.TIKTOK_KEYWORD_LIST:
            offset = 0
            while True:
                resp = await self.tiktok_client.search_video_by_keyword(
                    keyword=keyword, offset=offset
                )
                videos = resp.get("data", [])
                if not videos:
                    break
                await self._process_video_list(videos, source_keyword=keyword)
                offset += len(videos)
                if not resp.get("has_more"):
                    break
                await asyncio.sleep(1)

    async def get_specified_videos(self):
        for video_id in tiktok_config.TIKTOK_VIDEO_ID_LIST:
            resp = await self.tiktok_client.get_video_detail(video_id)
            item = resp.get("itemInfo", {}).get("itemStruct", {})
            if item:
                await self._save_video(item)
                if base_config.ENABLE_GET_COMMENTS:
                    await self._crawl_comments(video_id)

    async def get_creators_and_videos(self):
        for creator_id in tiktok_config.TIKTOK_CREATOR_ID_LIST:
            profile = await self.tiktok_client.get_creator_profile(creator_id)
            user_info = profile.get("userInfo", {})
            await self._save_creator(user_info)
            user_id = user_info.get("user", {}).get("id")
            if user_id:
                await self._crawl_creator_videos(user_id)

    async def get_hashtag_videos(self):
        for hashtag in tiktok_config.TIKTOK_HASHTAG_LIST:
            detail = await self.tiktok_client.get_hashtag_detail(hashtag)
            hashtag_id = detail.get("challengeInfo", {}).get("challenge", {}).get("id")
            if not hashtag_id:
                continue
            cursor = 0
            while True:
                resp = await self.tiktok_client.get_hashtag_videos(hashtag_id, cursor=cursor)
                videos = resp.get("itemList", [])
                if not videos:
                    break
                await self._process_video_list(videos)
                cursor = resp.get("cursor", 0)
                if not resp.get("hasMore"):
                    break
                await asyncio.sleep(1)

    async def _process_video_list(self, videos: list, source_keyword: str = ""):
        for item in videos:
            await self._save_video(item, source_keyword)
            video_id = item.get("id")
            if video_id and base_config.ENABLE_GET_COMMENTS:
                await self._crawl_comments(video_id)

    async def _crawl_comments(self, video_id: str):
        cursor = 0
        while True:
            resp = await self.tiktok_client.get_video_comments(video_id, cursor=cursor)
            comments = resp.get("comments", [])
            if not comments:
                break
            for comment in comments:
                await self._save_comment(comment, video_id)
                if comment.get("reply_comment_total", 0) > 0:
                    await self._crawl_replies(video_id, comment["cid"])
            cursor = resp.get("cursor", 0)
            if not resp.get("has_more"):
                break
            await asyncio.sleep(0.5)

    async def _crawl_replies(self, video_id: str, comment_id: str):
        cursor = 0
        while True:
            resp = await self.tiktok_client.get_comment_replies(
                video_id, comment_id, cursor=cursor
            )
            replies = resp.get("comments", [])
            if not replies:
                break
            for reply in replies:
                await self._save_comment(reply, video_id, parent_comment_id=comment_id)
            cursor = resp.get("cursor", 0)
            if not resp.get("has_more"):
                break
            await asyncio.sleep(0.3)

    async def _crawl_creator_videos(self, user_id: str):
        cursor = 0
        while True:
            resp = await self.tiktok_client.get_creator_videos(user_id, cursor=cursor)
            videos = resp.get("items", [])
            if not videos:
                break
            await self._process_video_list(videos)
            cursor = resp.get("cursor", 0)
            if not resp.get("hasMore"):
                break
            await asyncio.sleep(0.5)

    async def _save_video(self, item: dict, source_keyword: str = ""):
        from store.tiktok import store_video
        video = TikTokVideo(
            video_id=item.get("id", ""),
            desc=item.get("desc", ""),
            create_time=item.get("createTime", 0),
            author_id=item.get("author", {}).get("id", ""),
            author_unique_id=item.get("author", {}).get("uniqueId", ""),
            author_nickname=item.get("author", {}).get("nickname", ""),
            video_play_url=item.get("video", {}).get("playAddr", ""),
            video_cover_url=item.get("video", {}).get("cover", ""),
            liked_count=item.get("stats", {}).get("diggCount", 0),
            comment_count=item.get("stats", {}).get("commentCount", 0),
            share_count=item.get("stats", {}).get("shareCount", 0),
            play_count=item.get("stats", {}).get("playCount", 0),
            hashtags=[c.get("hashtagName", "") for c in item.get("challenges", [])],
            source_keyword=source_keyword,
        )
        await store_video.save(video)

    async def _save_comment(self, comment: dict, video_id: str, parent_comment_id=None):
        from store.tiktok import store_comment
        c = TikTokComment(
            comment_id=comment.get("cid", ""),
            video_id=video_id,
            content=comment.get("text", ""),
            user_id=comment.get("user", {}).get("uid", ""),
            user_unique_id=comment.get("user", {}).get("unique_id", ""),
            nickname=comment.get("user", {}).get("nickname", ""),
            create_time=comment.get("create_time", 0),
            like_count=comment.get("digg_count", 0),
            reply_count=comment.get("reply_comment_total", 0),
            parent_comment_id=parent_comment_id,
        )
        await store_comment.save(c)

    async def _save_creator(self, user_info: dict):
        from store.tiktok import store_creator
        user = user_info.get("user", {})
        stats = user_info.get("stats", {})
        creator = TikTokCreator(
            user_id=user.get("id", ""),
            unique_id=user.get("uniqueId", ""),
            nickname=user.get("nickname", ""),
            bio=user.get("signature", ""),
            avatar_url=user.get("avatarLarger", ""),
            follower_count=stats.get("followerCount", 0),
            following_count=stats.get("followingCount", 0),
            video_count=stats.get("videoCount", 0),
            heart_count=stats.get("heartCount", 0),
            verified=user.get("verified", False),
            region=user.get("region", ""),
        )
        await store_creator.save(creator)

    async def launch_browser(self, chromium, proxy, headless: bool):
        if base_config.SAVE_LOGIN_STATE:
            return await chromium.launch_persistent_context(
                user_data_dir=base_config.USER_DATA_DIR,
                headless=headless,
                proxy=proxy,
            )
        return await (await chromium.launch(headless=headless, proxy=proxy)).new_context()

    async def close(self):
        await self.browser_context.close()
```

---

## Phase 5 — Store Layer

### `store/tiktok/__init__.py`

```python
from . import store_video, store_comment, store_creator
```

### `store/tiktok/store_video.py` (mirror douyin store)

```python
"""Mirror cấu trúc store/douyin/store_dy_video.py"""
from config import base_config
from model.m_tiktok import TikTokVideo

async def save(video: TikTokVideo):
    save_option = base_config.SAVE_DATA_OPTION
    if save_option == "csv":
        await _save_csv(video)
    elif save_option == "json":
        await _save_json(video)
    elif save_option == "sqlite":
        await _save_db(video)

async def _save_csv(video: TikTokVideo):
    # TODO: implement CSV save — đọc store/douyin/store_dy_video.py để làm theo
    pass
```

---

## Phase 6 — Wiring vào main.py

### Sửa `cmd_arg/arg.py`

Tìm dòng có `choices=[...]` và thêm `"tiktok"`:

```python
choices=["xhs", "dy", "ks", "bili", "wb", "tieba", "zh", "tiktok"]
```

### Sửa `main.py`

Thêm case mới:

```python
elif platform == "tiktok":
    from media_platform.tiktok import TikTokCrawler
    crawler = TikTokCrawler()
```

---

## ⚠️ Challenge lớn nhất: TikTok Signature

| | Douyin | TikTok International |
|---|---|---|
| Captcha | Ít | Arkose Labs / FunCaptcha |
| Signature | X-Bogus từ JS bundle | X-Bogus + thêm check |
| Rate limit | Moderate | Aggressive hơn |

**Option A — Playwright mode (Khuyến nghị):**
- Route tất cả request qua browser thật
- Không cần reverse engineer signature
- Chậm hơn nhưng ổn định, TikTok không phân biệt được

**Option B — Semi-reverse:**
- Inspect Network tab trong DevTools
- Tìm X-Bogus generation function trong JS bundle
- Port sang Node.js
- Rủi ro: TikTok update thường → break

**Debug signature:**
```
1. Mở tiktok.com trong browser
2. DevTools > Console > Object.keys(window).filter(k => k.includes('sign'))
3. Tìm function liên quan đến X-Bogus
4. Test thử với URL thật
```

---

## Thứ tự implement

```
1.  config/tiktok_config.py                          ← 5 phút
2.  constant/tiktok_constant.py                      ← 10 phút
3.  model/m_tiktok.py                                ← 10 phút
4.  media_platform/tiktok/exception.py               ← 5 phút
5.  media_platform/tiktok/field.py                   ← 5 phút
6.  media_platform/tiktok/help.py                    ← 10 phút
7.  store/tiktok/ (CSV only trước)                   ← 20 phút
8.  media_platform/tiktok/login.py                   ← 45 phút
9.  media_platform/tiktok/client.py                  ← 60 phút
10. media_platform/tiktok/core.py                    ← 60 phút
11. cmd_arg/arg.py + main.py (wiring)                ← 10 phút
12. Testing từng phần                                ← ongoing
```

---

## Cách chạy

```bash
# Search theo keyword
uv run main.py --platform tiktok --lt cookie --type search --keywords "review mỹ phẩm"

# Crawl video cụ thể
uv run main.py --platform tiktok --lt cookie --type detail

# Crawl creator
uv run main.py --platform tiktok --lt cookie --type creator

# Lưu vào SQLite
uv run main.py --platform tiktok --lt cookie --type search --save_data_option sqlite

# Debug mode (không headless)
# Trong config/base_config.py: HEADLESS = False
```

---

## Notes cho Claude Code / AI Agent

- Luôn `Read media_platform/douyin/` trước khi tạo file tương đương trong `tiktok/`
- Các abstract method trong `base/base_crawler.py` là bắt buộc implement
- Lỗi 403/401 = vấn đề signature hoặc cookie expired
- Test `client.py` riêng với 1 video ID cố định trước khi test toàn bộ `core.py`
- Dùng `HEADLESS = False` khi debug để thấy browser thực tế
- Bước khó nhất là `tiktok_sign.js` — nên dành thời gian inspect window object kỹ

---

*Dự án này chỉ dành cho mục đích học tập và nghiên cứu kỹ thuật.*
