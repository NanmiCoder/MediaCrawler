# Xiaohongshu URL Crawler - Standalone Module

A standalone Python module for crawling Xiaohongshu (Little Red Book) note details from a given URL without database storage.

## Features

- ✅ Simple API for crawling individual Xiaohongshu notes
- ✅ **Automatic cookie management** - Login once, use forever! ⭐ NEW
- ✅ Multiple authentication methods (QR code, cookies, auto-login)
- ✅ No database dependencies
- ✅ Automatic signature generation
- ✅ Fallback to HTML parsing if API fails
- ✅ Proxy support
- ✅ Cookie persistence and validation

## What's New

### Automatic Cookie Persistence

The module now includes automatic cookie management! No more scanning QR codes every time:

- **First run**: Login once with QR code
- **Auto-save**: Cookies automatically saved to file
- **Next runs**: Auto-login using saved cookies - done in seconds! 🎉

**Before**: Scan QR code every single run ❌
**After**: Scan QR code only once, then automatic authentication ✅

## Requirements

```bash
pip install playwright httpx pydantic tenacity xhshow humps
playwright install chromium
```

## Quick Start

### Basic Usage (with Auto-Login) ⭐ RECOMMENDED

```python
import asyncio
from xhs_url_crawler import XhsUrlCrawler

async def main():
    # Create crawler instance (auto_save_cookies is True by default)
    crawler = XhsUrlCrawler(headless=False)

    try:
        # Try auto-login first (uses saved cookies)
        login_success = await crawler.auto_login()

        if not login_success:
            # First time: login with QR code
            # Cookies will be automatically saved for future use
            print("\nAuto-login failed. Please scan QR code:")
            await crawler.login_by_qrcode()

        # Crawl a note
        note_url = "https://www.xiaohongshu.com/explore/YOUR_NOTE_ID?xsec_token=xxx&xsec_source=pc_search"
        note_data = await crawler.crawl_note(note_url)

        if note_data:
            print("Note title:", note_data.get('title'))
            print("Note description:", note_data.get('desc'))
            print("Author:", note_data.get('user', {}).get('nickname'))

    finally:
        await crawler.close()

if __name__ == "__main__":
    asyncio.run(main())
```

**Result:**
- **First run**: Scan QR code once, cookies automatically saved to `cookies/xhs_cookies.json`
- **Subsequent runs**: Auto-login using saved cookies - no QR code needed! 🎉

### Manual Cookie Login

```python
async def main():
    crawler = XhsUrlCrawler(headless=True)

    try:
        # Option 1: Login with cookie string
        cookie_str = "web_session=your_session_value_here; a1=xxx"
        await crawler.login_by_cookie(cookie_str)

        # Option 2: Login with saved cookies (no argument)
        # await crawler.login_by_cookie()  # Loads from cookies/xhs_cookies.json

        # Crawl note
        note_data = await crawler.crawl_note(note_url)

    finally:
        await crawler.close()
```

### Advanced Configuration

```python
# With proxy
crawler = XhsUrlCrawler(
    headless=True,
    proxy="http://proxy.example.com:8080"
)

# Disable auto-save cookies
crawler = XhsUrlCrawler(
    auto_save_cookies=False  # Won't save cookies after login
)

# Custom cookie directory
crawler = XhsUrlCrawler(
    cookie_dir="my_cookies"  # Save cookies to my_cookies/xhs_cookies.json
)
```

## API Reference

### `XhsUrlCrawler`

Main crawler class for Xiaohongshu notes.

#### Constructor

```python
XhsUrlCrawler(
    headless: bool = True,
    proxy: Optional[str] = None,
    auto_save_cookies: bool = True,
    cookie_dir: str = "cookies"
)
```

- `headless`: Run browser in headless mode (default: True)
- `proxy`: HTTP proxy URL (optional)
- `auto_save_cookies`: Automatically save and load cookies (default: True) ⭐ NEW
- `cookie_dir`: Directory to store cookies (default: "cookies") ⭐ NEW

#### Methods

##### `auto_login() -> bool` ⭐ NEW

Attempt to login automatically using saved cookies. Returns True if successful.

```python
success = await crawler.auto_login()
if not success:
    # Fallback to manual login
    await crawler.login_by_qrcode()
```

##### `login_by_qrcode(save_cookies: Optional[bool] = None)`

Login using QR code. The browser will open and display a QR code. Scan it with your Xiaohongshu mobile app.

```python
# Auto-saves if auto_save_cookies=True
await crawler.login_by_qrcode()

# Override auto-save setting
await crawler.login_by_qrcode(save_cookies=False)  # Don't save this time
```

##### `login_by_cookie(cookie_str: str = "")`

Login using cookie string or saved cookies file.

```python
# Load from saved cookies file
await crawler.login_by_cookie()

# Or use cookie string (all cookies, not just web_session)
await crawler.login_by_cookie("web_session=xxx; a1=yyy; other=zzz")
```

##### `crawl_note(note_url: str) -> Optional[Dict]`

Crawl a single Xiaohongshu note from URL.

```python
note_data = await crawler.crawl_note(
    "https://www.xiaohongshu.com/explore/66fad51c000000001b0224b8?xsec_token=xxx&xsec_source=pc_search"
)
```

Returns a dictionary containing:
- `note_id`: Note ID
- `title`: Note title
- `desc`: Note description
- `user`: Author information (nickname, user_id, avatar, etc.)
- `image_list`: List of images
- `video`: Video information (if applicable)
- `liked_count`: Number of likes
- `collected_count`: Number of collections
- `comment_count`: Number of comments
- `share_count`: Number of shares
- And more...

##### `close()`

Close browser and cleanup resources.

```python
await crawler.close()
```

## Cookie Management ⭐ NEW

The module now includes automatic cookie persistence, so you only need to login once!

### How It Works

1. **First Run**: Login with QR code or cookie string
2. **Auto-Save**: Cookies are automatically saved to `cookies/xhs_cookies.json`
3. **Next Runs**: Just call `auto_login()` - no QR code needed!

### Cookie Manager API

Access the cookie manager for advanced control:

```python
# Check cookie info
info = crawler.cookie_manager.get_cookie_info()
if info:
    print(f"Saved at: {info['saved_time']}")
    print(f"Cookie count: {info['cookie_count']}")
    print(f"File path: {info['file_path']}")

# Clear saved cookies (force re-login)
crawler.cookie_manager.clear_cookies()
```

### Cookie File Format

Cookies are saved in JSON format with metadata:

```json
{
  "cookies": [
    {
      "name": "web_session",
      "value": "xxx",
      "domain": ".xiaohongshu.com",
      "path": "/"
    },
    ...
  ],
  "saved_at": 1698765432.0,
  "saved_time": "2024-11-21 10:30:32"
}
```

### Security Notes

- Cookie files are saved locally in the `cookies/` directory
- **Add `cookies/` to your `.gitignore`** to avoid committing sensitive data
- Cookies are checked for age (warns if >30 days old)
- All cookies are saved, not just `web_session`

## Note Data Structure

The `crawl_note()` method returns a dictionary with the following structure:

```json
{
  "note_id": "66fad51c000000001b0224b8",
  "title": "Note title",
  "desc": "Note description",
  "type": "normal",  // or "video"
  "user": {
    "user_id": "xxx",
    "nickname": "Author name",
    "avatar": "https://...",
  },
  "image_list": [
    {
      "url": "https://...",
      "url_default": "https://...",
      "width": 1080,
      "height": 1440
    }
  ],
  "video": {
    "url": "https://...",
    "duration": 15000
  },
  "liked_count": "1234",
  "collected_count": "567",
  "comment_count": "89",
  "share_count": "12",
  "time": 1698765432,
  "last_update_time": 1698765432,
  "xsec_token": "xxx",
  "xsec_source": "pc_search"
}
```

## Important Notes

⚠️ **Legal and Ethical Use**

This code is for educational and research purposes only. Please:

1. ❌ Do NOT use for commercial purposes
2. ✅ Respect the target platform's Terms of Service and robots.txt
3. ✅ Do NOT perform large-scale crawling or cause operational interference
4. ✅ Control request frequency reasonably
5. ❌ Do NOT use for illegal or improper purposes

## Troubleshooting

### Issue: "stealth.min.js not found"

Make sure the `libs/stealth.min.js` file exists in your project directory. This file helps avoid detection by the website.

### Issue: "Captcha detected"

If you encounter captcha challenges:
- Try using cookies from a valid session
- Reduce crawling frequency
- Use a proxy
- Complete the captcha manually in the browser

### Issue: "Login timeout"

For QR code login:
- Make sure the browser window is visible (set `headless=False`)
- Scan the QR code within 600 seconds
- Ensure your Xiaohongshu app is up to date

### Issue: "Auto-login failed" ⭐ NEW

If auto-login keeps failing:
- Clear old cookies: `crawler.cookie_manager.clear_cookies()`
- Login manually with QR code: `await crawler.login_by_qrcode()`
- Cookies will be automatically saved for next time
- Check if cookies are too old (>30 days) - the system will warn you
- Verify the cookie file exists: `cookies/xhs_cookies.json`

## License

Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

See the LICENSE file in the project root for details.

## Related Projects

This module is extracted from [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) - a comprehensive social media crawler supporting multiple platforms.

## Changelog

### v2.0 (Latest) ⭐
- **NEW**: Automatic cookie persistence and management
- **NEW**: `auto_login()` method for seamless re-authentication
- **NEW**: `CookieManager` class for advanced cookie control
- **IMPROVED**: `login_by_cookie()` now loads from file if no argument provided
- **IMPROVED**: `login_by_qrcode()` now auto-saves cookies by default
- **IMPROVED**: All cookies are saved, not just `web_session`
- **IMPROVED**: Cookie age validation with warnings for old cookies

### v1.0
- Initial release
- Basic URL crawling functionality
- QR code and cookie string authentication
