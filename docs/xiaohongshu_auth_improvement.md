# Xiaohongshu (小红书) Authentication Improvement

## Overview

The authentication system for Xiaohongshu has been improved to avoid repeated QR code scanning on every run. The system now automatically saves and reuses cookies from successful login sessions.

## Features

### 1. Automatic Cookie Management
- **Auto-save**: After a successful QR code or phone login, cookies are automatically saved to `cookies/xhs_cookies.json`
- **Auto-load**: On subsequent runs, saved cookies are automatically loaded and validated
- **Smart fallback**: If saved cookies are invalid or expired, the system falls back to the configured login method

### 2. Cookie Validation
- Cookies are validated using the `pong()` check before being used
- Invalid or expired cookies trigger a new login flow
- Cookie age warning (30+ days old)

### 3. Multiple Login Methods
The system supports three login methods:
- **QR Code Login** (default): Scan QR code with Xiaohongshu mobile app
- **Phone Login**: SMS verification code
- **Cookie Login**: Use saved or manually provided cookies

## Configuration

### Enable/Disable Auto Cookie Management

In `config/base_config.py`:

```python
# Enable automatic cookie saving and usage (recommended)
AUTO_SAVE_AND_USE_COOKIES = True  # Set to False to disable

# Choose login method (qrcode, phone, or cookie)
LOGIN_TYPE = "qrcode"

# Optional: Manually provide cookies (if AUTO_SAVE_AND_USE_COOKIES is False)
COOKIES = ""
```

### Configuration Options

| Option | Values | Description |
|--------|--------|-------------|
| `AUTO_SAVE_AND_USE_COOKIES` | `True`/`False` | Enable automatic cookie management |
| `LOGIN_TYPE` | `"qrcode"`/`"phone"`/`"cookie"` | Primary login method |
| `SAVE_LOGIN_STATE` | `True`/`False` | Save browser session state |
| `COOKIES` | String | Manually provided cookies (optional) |

## How It Works

### First Run (No Saved Cookies)

1. System checks for saved cookies in `cookies/xhs_cookies.json`
2. No cookies found → Prompt for QR code or phone login
3. After successful login → Automatically save cookies
4. Crawling begins

### Subsequent Runs (With Saved Cookies)

1. System loads cookies from `cookies/xhs_cookies.json`
2. Validates cookies with `pong()` check
3. **If valid** → Use cookies directly, no QR code needed ✅
4. **If invalid** → Fall back to configured login method
5. Crawling begins

### Login Flow Diagram

```
Start
  ↓
Check AUTO_SAVE_AND_USE_COOKIES
  ↓
[Enabled] → Load saved cookies → Validate with pong()
  ↓                                      ↓
[Valid] ✅                        [Invalid] ❌
  ↓                                      ↓
Use cookies                     Try configured login method
  ↓                                      ↓
Skip QR code scan!              QR/Phone login → Save cookies
  ↓                                      ↓
Start crawling ←──────────────────────────┘
```

## File Structure

```
MediaCrawler/
├── cookies/                           # Cookie storage (gitignored)
│   └── xhs_cookies.json              # Saved Xiaohongshu cookies
├── media_platform/xhs/
│   ├── cookie_manager.py             # Cookie management utility
│   ├── login.py                      # Enhanced login logic
│   └── core.py                       # Updated authentication flow
└── config/
    └── base_config.py                # Configuration options
```

## Cookie File Format

The `cookies/xhs_cookies.json` file contains:

```json
{
  "cookies": [
    {
      "name": "web_session",
      "value": "...",
      "domain": ".xiaohongshu.com",
      "path": "/",
      ...
    },
    ...
  ],
  "saved_at": 1234567890.123,
  "saved_time": "2025-01-15 10:30:45"
}
```

## Security Considerations

### ⚠️ Important
- **Never commit** `cookies/xhs_cookies.json` to version control
- The `cookies/` directory is automatically ignored in `.gitignore`
- Cookies contain sensitive authentication data
- Treat cookies like passwords

### Cookie Expiration
- Cookies typically expire after 30 days of inactivity
- The system warns about old cookies (30+ days)
- Expired cookies trigger automatic re-authentication

## Usage Examples

### Example 1: Default Setup (Recommended)

```python
# config/base_config.py
PLATFORM = "xhs"
LOGIN_TYPE = "qrcode"
AUTO_SAVE_AND_USE_COOKIES = True  # Enable auto cookie management
```

**First run**: Scan QR code once → Cookies saved automatically
**Future runs**: No QR code needed! Cookies loaded automatically ✅

### Example 2: Manual Cookie Management

```python
# config/base_config.py
PLATFORM = "xhs"
LOGIN_TYPE = "cookie"
AUTO_SAVE_AND_USE_COOKIES = False  # Disable auto management
COOKIES = "web_session=xxx; a1=yyy; ..."  # Manually provide cookies
```

### Example 3: Phone Login with Auto-Save

```python
# config/base_config.py
PLATFORM = "xhs"
LOGIN_TYPE = "phone"
AUTO_SAVE_AND_USE_COOKIES = True
```

**First run**: Enter phone number and SMS code → Cookies saved
**Future runs**: No SMS code needed! Cookies loaded automatically ✅

## Troubleshooting

### Issue: Cookies Not Being Saved

**Possible causes:**
1. `AUTO_SAVE_AND_USE_COOKIES = False` in config
2. Login failed before cookie saving
3. File permission issues

**Solution:**
- Check config: `AUTO_SAVE_AND_USE_COOKIES = True`
- Ensure login completes successfully
- Check write permissions for `cookies/` directory

### Issue: Cookies Expired or Invalid

**Symptoms:**
- Log message: "Saved cookies are invalid or expired"
- System falls back to QR code login

**Solution:**
- This is normal behavior after long inactivity
- Simply login again with QR code
- New cookies will be saved automatically

### Issue: "Cookie file not found" on First Run

**This is normal!**
- First run has no saved cookies
- Complete QR code or phone login
- Cookies will be saved for future use

## Benefits

### Before This Improvement ❌
- Scan QR code **every single time**
- Manual cookie management required
- Tedious repeated authentication

### After This Improvement ✅
- Scan QR code **only once**
- Automatic cookie persistence
- Seamless authentication on subsequent runs
- No manual intervention needed

## API Reference

### CookieManager Class

Located in `media_platform/xhs/cookie_manager.py`

#### Methods

##### `save_cookies(cookies: List[Dict]) -> bool`
Save cookies to file with timestamp

##### `load_cookies() -> Optional[List[Dict]]`
Load cookies from file, returns None if not found

##### `clear_cookies() -> bool`
Delete saved cookie file

##### `get_cookie_info() -> Optional[Dict]`
Get metadata about saved cookies (count, age, etc.)

### XiaoHongShuLogin Class Enhancements

#### New Method: `save_cookies_to_file() -> bool`
Automatically called after successful login when `AUTO_SAVE_AND_USE_COOKIES = True`

#### Enhanced Method: `login_by_cookies()`
Now supports both:
- Loading from saved cookie file (if `cookie_str` is empty)
- Using manually provided `cookie_str`
- Imports **all** cookies, not just `web_session`

## Migration Guide

### Upgrading from Previous Version

No migration needed! The improvement is backward compatible:

1. Update your code
2. Set `AUTO_SAVE_AND_USE_COOKIES = True` in config
3. On first run, login as usual
4. Subsequent runs will use saved cookies automatically

### Disabling the Feature

If you prefer the old behavior:

```python
# config/base_config.py
AUTO_SAVE_AND_USE_COOKIES = False
```

## Technical Details

### Cookie Storage Location
- Default: `cookies/xhs_cookies.json`
- Configurable via `CookieManager(cookie_dir="custom_path")`

### Cookie Validation Process
1. Load cookies from file
2. Add cookies to browser context
3. Call `xhs_client.pong()` to test validity
4. Search for keyword "小红书" as validation test
5. Return success/failure

### Important Cookies
The system saves all cookies, but these are most critical:
- `web_session`: Main session identifier
- `a1`: Authentication token
- `webId`: Device identifier
- `gid`: User group identifier

## FAQ

**Q: How long do cookies last?**
A: Typically 30 days from last use, but can vary.

**Q: Can I use cookies from multiple accounts?**
A: No, only one account at a time. To switch accounts, delete `cookies/xhs_cookies.json` and login with a different account.

**Q: Are cookies safe to store?**
A: Cookies are stored locally and gitignored by default. Never share or commit them.

**Q: What happens if I delete the cookie file?**
A: Next run will require login again. New cookies will be saved.

**Q: Can I copy cookies between machines?**
A: Technically yes, but not recommended due to IP/device fingerprinting.

## Contributing

To extend cookie management to other platforms (Douyin, Bilibili, etc.), use the `CookieManager` class as a reference implementation.

## License

This enhancement follows the project's NON-COMMERCIAL LEARNING LICENSE 1.1.

---

**Last Updated**: 2025-11-20
**Version**: 1.0.0
