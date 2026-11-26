# MediaCrawler - Project Overview

## 📋 Project Summary

**MediaCrawler** là một công cụ web scraping mạnh mẽ dùng để thu thập dữ liệu công khai từ các nền tảng truyền thông xã hội (Social Media) phổ biến của Trung Quốc.

### Mục đích chính
Hỗ trợ lập trình viên trong việc học tập, nghiên cứu và phân tích dữ liệu từ các nền tảng đa phương tiện. **Chỉ dành cho mục đích học tập, không sử dụng thương mại**.

## 🎯 Nền tảng được hỗ trợ

| Nền tảng | Tìm kiếm từ khóa | Lấy post theo ID | Bình luận cấp 2 | Trang cá nhân | Cache đăng nhập | Proxy | Word Cloud |
|---------|-----------------|-----------------|-----------------|---------------|-----------------|-------|-----------|
| 小红书 (Xiaohongshu) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 抖音 (Douyin/TikTok CN) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 快手 (Kuaishou) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| B站 (Bilibili) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 微博 (Weibo) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 贴吧 (Tieba/Baidu) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 知乎 (Zhihu) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## 🏗️ Cấu trúc dự án

### Các thư mục chính:

```
media-crawler/
├── api/                    # FastAPI endpoints cho WebUI
├── base/                   # Lớp cơ sở cho các crawler (AbstractCrawler)
├── cache/                  # Quản lý cache (Redis, Memory cache)
├── cmd_arg/                # Xử lý tham số dòng lệnh (CLI arguments)
├── config/                 # Cấu hình chung (config.py, toml files)
├── constant/               # Hằng số, enum cho các nền tảng
├── database/               # ORM, migration, quản lý DB (SQLAlchemy, Alembic)
├── docs/                   # Tài liệu (tiếng Trung, Anh, Tây Ban Nha)
├── libs/                   # Thư viện tiện ích
├── media_platform/         # Các crawler riêng cho từng nền tảng
│   ├── bilibili.py
│   ├── douyin.py
│   ├── kuaishou.py
│   ├── tieba.py
│   ├── weibo.py
│   ├── xhs.py             # Xiaohongshu
│   └── zhihu.py
├── model/                  # Pydantic models, schemas
├── proxy/                  # Quản lý proxy pool
├── store/                  # Lưu trữ dữ liệu (JSON, JSONL, Excel, DB)
├── test/                   # Unit tests
├── tools/                  # Công cụ tiện ích (wordcloud, file writer)
├── webui/                  # Web UI (Vue.js, build artifacts)
└── main.py                 # Entry point chính
```

## 🔧 Tech Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI (API), Typer (CLI)
- **Browser Automation**: Playwright (v1.61+)
- **Database**: SQLAlchemy + Alembic (migration), Redis cache
- **Async**: asyncio, aiofiles, asyncmy, asyncpg

### Storage
- **Database Options**: SQLite, MySQL, PostgreSQL, MongoDB
- **File Formats**: JSON, JSONL, Excel (openpyxl)
- **Serialization**: Pydantic v2+

### Frontend
- **WebUI**: Vue.js (src/ trong webui/)
- **API Server**: Uvicorn + FastAPI

### Utilities
- **Word Cloud**: matplotlib, wordcloud, PIL
- **Text Processing**: jieba (Chinese tokenizer), parsel (HTML parsing)
- **HTTP**: httpx, requests
- **Crypto**: cryptography, pyexecjs (JS signature execution)

## 🚀 Cách hoạt động

### Kiến trúc chính:

1. **CrawlerFactory Pattern** - Tạo crawler dựa trên loại nền tảng
2. **CDP Mode** (Chrome DevTools Protocol) - Kết nối tới Chrome browser đang chạy
3. **Login State Caching** - Lưu trữ session, cookie, state giữa các lần chạy
4. **Proxy Support** - Hỗ trợ rotation proxy để tránh IP ban
5. **Async Architecture** - Xử lý concurrent requests

### Workflow cơ bản:
```
CLI Args → Config Loading → Crawler Init → Browser Connect → 
Login (hoặc load cached state) → Data Crawl → Parse Data → 
Store (DB/File) → Generate WordCloud → Exit
```

## 📦 Dependencies chính

```
playwright>=1.61.0          # Browser automation
fastapi==0.110.2            # Web framework
sqlalchemy>=2.0.43          # ORM
pydantic>=2.13.4            # Data validation
redis~=4.6.0                # Caching
httpx==0.28.1               # HTTP client
typer>=0.12.3               # CLI framework
wordcloud>=1.9.6            # Word cloud generation
```

## 🔗 Điểm vào chính

- **main.py**: Entry point CLI chính - khởi tạo crawler, run công việc crawl
- **api/**: FastAPI app cho WebUI server
- **media_platform/**: Từng platform crawler có logic riêng
- **config/**: Tập trung tất cả cấu hình (env variables, settings)

## 📝 Lưu ý quan trọng

### Legal & Disclaimer ⚠️
- **Chỉ dùng cho học tập** - không sử dụng thương mại
- **Tuân thủ ToS** - tuân thủ điều khoản dịch vụ của từng nền tảng
- **Hợp pháp** - tham khảo danh sách [crawler illegal cases in China](https://github.com/HiddenStrawberry/Crawler_Illegal_Cases_In_China)

### Best Practices
- Sử dụng CDP mode (Chrome browser sẵn có) thay vì Playwright mode để tái sử dụng login state
- Bật remote debugging: `chrome://inspect/#remote-debugging`
- Kiểm soát tần suất request (rate limiting)
- Sử dụng proxy pool để tránh IP ban
- Backup cookie/session cache để tránh tái login

## 🎯 Hướng phát triển gần đây

### Commits gần nhất:
- **3bde9e2**: docs: update sponsors
- **04da7f3**: Update Readme
- **84907f0**: docs: 新增 Bloome 赞助商
- **076dcba**: fix: 修复 WebUI 源码缺失、环境检测路径
- **65ddaa8**: refactor: 将 WebUI 源码纳入仓库

### Features dự tính (Pro version)
- Self-media content decomposition Agent
- Breakpoint resume crawling
- Multi-account + IP proxy pool
- Remove Playwright dependency
- Full Linux support
- AI Agent Skills (OpenClaw, Claude Code, Cursor)

## 💡 Sử dụng cơ bản

```bash
# Install dependencies
uv sync

# Install browser drivers (optional, chỉ cho Playwright mode)
uv run playwright install

# Run crawler
python main.py --platform xhs --keywords "咖啡"

# Access WebUI
# Mở http://localhost:8000 (nếu API server chạy)
```

## 📚 Tài liệu chính

- **README.md**: Tổng quan chính (tiếng Trung)
- **docs/**: Tài liệu chi tiết (tiếng Trung)
  - `项目代码结构.md` - Cấu trúc code
  - `项目架构文档.md` - Kiến trúc hệ thống
  - `常见问题.md` - FAQ
  - `原生环境管理文档.md` - Quản lý môi trường

## 🔐 Configuration

Xem `.env.example` để hiểu các biến môi trường:
```
PLAYWRIGHT_BROWSER_PATH=...  # Đường dẫn Chrome
PROXY_POOL=...                # Cấu hình proxy
DATABASE_URL=...              # Connection string DB
REDIS_URL=...                 # Redis connection
```

---

**Last updated**: 2026-07-14  
**Project License**: NON-COMMERCIAL LEARNING LICENSE 1.1  
**Author**: 程序员阿江 (Relakkes)
