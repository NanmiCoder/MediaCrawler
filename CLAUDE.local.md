# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MediaCrawler is a multi-platform social media data collection tool supporting platforms like Xiaohongshu (Little Red Book), Douyin (TikTok), Kuaishou, Bilibili, Weibo, Tieba, and Zhihu. The project uses Playwright for browser automation and maintains login states to crawl public information without needing JS reverse engineering.

## Development Environment Setup

### Prerequisites
- **Python**: >= 3.9 (verified with 3.9.6)
- **Node.js**: >= 16.0.0 (required for Douyin and Zhihu crawlers)
- **uv**: Modern Python package manager (recommended)

### Installation Commands
```bash
# Using uv (recommended)
uv sync
uv run playwright install

# Using traditional pip (fallback)
pip install -r requirements.txt
playwright install
```

### Running the Application
```bash
# Basic crawling command
uv run main.py --platform xhs --lt qrcode --type search

# View all available options
uv run main.py --help

# Using traditional Python
python main.py --platform xhs --lt qrcode --type search
```

## Architecture Overview

### Core Components

1. **Platform Crawlers** (`media_platform/`):
   - Each platform has its own crawler implementation
   - Follows abstract base class pattern (`base/base_crawler.py`)
   - Platforms: `xhs`, `dy`, `ks`, `bili`, `wb`, `tieba`, `zhihu`

2. **Configuration System** (`config/`):
   - `base_config.py`: Main configuration file with extensive options
   - `db_config.py`: Database configuration
   - Key settings: login types, proxy settings, CDP mode, data storage options

3. **Data Storage** (`store/`):
   - Multiple storage backends: CSV, JSON, MySQL
   - Platform-specific storage implementations
   - Image download capabilities

4. **Caching System** (`cache/`):
   - Local cache and Redis cache implementations
   - Factory pattern for cache selection

5. **Proxy Support** (`proxy/`):
   - IP proxy pool management
   - Multiple proxy provider support (Kuaidaili, Jishu)

6. **Browser Automation** (`tools/`):
   - Playwright browser launcher
   - CDP (Chrome DevTools Protocol) support
   - Slider validation utilities

### Key Configuration Options

- `PLATFORM`: Target platform (xhs, dy, ks, bili, wb, tieba, zhihu)
- `KEYWORDS`: Search keywords (comma-separated)
- `CRAWLER_TYPE`: Type of crawling (search, detail, creator)
- `ENABLE_CDP_MODE`: Use Chrome DevTools Protocol for better anti-detection
- `SAVE_DATA_OPTION`: Data storage format (csv, db, json)
- `ENABLE_GET_COMMENTS`: Enable comment crawling
- `ENABLE_IP_PROXY`: Enable proxy IP rotation

## Testing

### Available Test Commands
```bash
# Run all tests
python -m unittest discover test

# Run specific test files
python -m unittest test.test_expiring_local_cache
python -m unittest test.test_proxy_ip_pool
python -m unittest test.test_redis_cache
python -m unittest test.test_utils

# Install and use pytest (enhanced testing)
uv add pytest
uv run pytest test/
```

### Test Coverage
- Cache functionality tests
- Proxy IP pool tests
- Utility function tests
- Redis cache tests (requires Redis server)

## Database Setup

### MySQL Database Initialization
```bash
# Initialize database tables (first time only)
python db.py

# Or with uv
uv run db.py
```

### Supported Storage Options
- **MySQL**: Full relational database with deduplication
- **CSV**: Simple file-based storage in `data/` directory
- **JSON**: Structured file-based storage in `data/` directory

## Common Development Tasks

### Adding New Platform Support
1. Create new directory in `media_platform/`
2. Implement crawler class inheriting from `AbstractCrawler`
3. Add platform-specific client, core, field, and login modules
4. Update `CrawlerFactory` in `main.py`
5. Add storage implementation in `store/`

### Debugging CDP Mode
- Set `ENABLE_CDP_MODE = True` in config
- Use `CDP_HEADLESS = False` for visual debugging
- Check browser console for CDP connection issues

### Managing Login States
- Login states are cached in `browser_data/` directory
- Platform-specific user data directories maintain session cookies
- Set `SAVE_LOGIN_STATE = True` to preserve login across runs

## Platform-Specific Notes

### Xiaohongshu (XHS)
- Supports search, detail, and creator crawling
- Requires `xsec_token` and `xsec_source` parameters for specific note URLs
- Custom User-Agent configuration available

### Douyin (DY)
- Requires Node.js environment
- Supports publish time filtering
- Has specific creator ID format (sec_id)

### Bilibili (BILI)
- Supports date range filtering with `START_DAY` and `END_DAY`
- Can crawl creator fans/following lists
- Uses BV video ID format

## Legal and Usage Notes

This project is for educational and research purposes only. Users must:
- Comply with platform terms of service
- Follow robots.txt rules
- Control request frequency appropriately
- Not use for commercial purposes
- Respect platform rate limits

The project includes comprehensive legal disclaimers and usage guidelines in the README.md file.