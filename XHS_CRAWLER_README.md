# Xiaohongshu URL Crawler - Standalone Module

A standalone Python module for crawling Xiaohongshu (Little Red Book) note details from a given URL without database storage.

## Features

- ✅ Simple API for crawling individual Xiaohongshu notes
- ✅ Multiple authentication methods (QR code, cookies)
- ✅ No database dependencies
- ✅ Automatic signature generation
- ✅ Fallback to HTML parsing if API fails
- ✅ Proxy support

## Requirements

```bash
pip install playwright httpx pydantic tenacity xhshow humps
playwright install chromium
```

## Quick Start

### Basic Usage

```python
import asyncio
from xhs_url_crawler import XhsUrlCrawler

async def main():
    # Create crawler instance
    crawler = XhsUrlCrawler(headless=False)  # Set headless=True to hide browser

    try:
        # Login using QR code
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

### Login with Cookies

```python
async def main():
    crawler = XhsUrlCrawler(headless=True)

    try:
        # Login with cookie string
        cookie_str = "web_session=your_session_value_here"
        await crawler.login_by_cookie(cookie_str)

        # Crawl note
        note_data = await crawler.crawl_note(note_url)

    finally:
        await crawler.close()
```

### With Proxy

```python
crawler = XhsUrlCrawler(
    headless=True,
    proxy="http://proxy.example.com:8080"
)
```

## API Reference

### `XhsUrlCrawler`

Main crawler class for Xiaohongshu notes.

#### Constructor

```python
XhsUrlCrawler(headless: bool = True, proxy: Optional[str] = None)
```

- `headless`: Run browser in headless mode (default: True)
- `proxy`: HTTP proxy URL (optional)

#### Methods

##### `login_by_qrcode()`

Login using QR code. The browser will open and display a QR code. Scan it with your Xiaohongshu mobile app.

```python
await crawler.login_by_qrcode()
```

##### `login_by_cookie(cookie_str: str)`

Login using cookie string containing `web_session` value.

```python
await crawler.login_by_cookie("web_session=xxx; other_cookie=yyy")
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

## License

Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

See the LICENSE file in the project root for details.

## Related Projects

This module is extracted from [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) - a comprehensive social media crawler supporting multiple platforms.
