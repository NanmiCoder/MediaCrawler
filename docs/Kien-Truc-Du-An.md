# Tài Liệu Kiến Trúc MediaCrawler

## 1. Tổng Quan Dự Án

### 1.1 Giới Thiệu Dự Án

MediaCrawler là một khung web scraper đa nền tảng dành cho truyền thông xã hội, được xây dựng bằng Python bất đồng bộ, hỗ trợ crawl nội dung, bình luận và thông tin nhà sáng tạo từ các nền tảng mạng xã hội chính.

### 1.2 Các Nền Tảng Được Hỗ Trợ

| Nền Tảng | Mã | Chức Năng Chính |
|----------|-----|-----------------|
| Xiaohongshu | `xhs` | Tìm kiếm note, chi tiết, nhà sáng tạo |
| Douyin (TikTok CN) | `dy` | Tìm kiếm video, chi tiết, nhà sáng tạo |
| Kuaishou | `ks` | Tìm kiếm video, chi tiết, nhà sáng tạo |
| Bilibili | `bili` | Tìm kiếm video, chi tiết, UP chủ |
| Weibo | `wb` | Tìm kiếm weibo, chi tiết, blogger |
| Baidu Tieba | `tieba` | Tìm kiếm bài viết, chi tiết |
| Zhihu | `zhihu` | Tìm kiếm hỏi đáp, chi tiết, trả lời viên |

### 1.3 Các Tính Năng Cốt Lõi

- **Hỗ trợ đa nền tảng**: Giao diện crawler thống nhất, hỗ trợ 7 nền tảng chính
- **Nhiều phương pháp đăng nhập**: Mã QR, số điện thoại, Cookie
- **Nhiều cách lưu trữ**: CSV, JSON, JSONL, SQLite, MySQL, MongoDB, Excel
- **Chống scrapy**: Chế độ CDP, pool proxy IP, ký hiệu yêu cầu
- **Bất đồng bộ hiệu suất cao**: Kiến trúc async dựa trên asyncio, crawl hiệu quả
- **Tạo word cloud**: Tự động tạo word cloud từ bình luận

---

## 2. Tổng Quan Kiến Trúc Hệ Thống

### 2.1 Sơ Đồ Kiến Trúc Tổng Thể

```
┌─────────────────────────────────────────────────────────┐
│                    ENTRY LAYER (Lớp Vào)               │
│  main.py (Lối vào) | config (Cấu hình) | cmd_arg      │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              CRAWLER CORE LAYER (Lớp Crawler Cốt Lõi)   │
│  CrawlerFactory (Công Nhân) → AbstractCrawler (Lớp Cơ)│
│  ├─ XiaoHongShuCrawler                                 │
│  ├─ DouYinCrawler                                      │
│  ├─ KuaishouCrawler                                    │
│  ├─ BilibiliCrawler                                    │
│  ├─ WeiboCrawler                                       │
│  ├─ TieBaCrawler                                       │
│  └─ ZhihuCrawler                                       │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              API CLIENT LAYER (Lớp Client API)          │
│  AbstractApiClient → Các Client Platform                │
│  (XiaoHongShuClient, DouYinClient, ...)                │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              STORAGE LAYER (Lớp Lưu Trữ)               │
│  StoreFactory → CSV/JSON/SQLite/MySQL/MongoDB/Excel   │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│        INFRASTRUCTURE LAYER (Lớp Cơ Sở Hạ Tầng)       │
│  Browser (Playwright/CDP) | Proxy Pool | Cache | Login │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Luồng Dữ Liệu

```
Dữ Liệu Vào → Xử Lý → Dữ Liệu Ra → Lưu Trữ
  ├─ Từ khóa        ├─ Khởi động browser    ├─ Nội dung
  ├─ ID             ├─ Xác thực đăng nhập   ├─ Bình luận
  └─ Cấu hình       ├─ Tìm kiếm/crawl       ├─ Nhà sáng tạo
                    ├─ Phân tích dữ liệu    ├─ Tệp media
                    └─ Lấy bình luận        │
                                            ↓
                            Lưu vào: File/DB/NoSQL
```

---

## 3. Cấu Trúc Thư Mục

```
MediaCrawler/
├── main.py                    # Điểm vào chương trình
├── var.py                     # Biến bối cảnh toàn cầu
├── pyproject.toml             # Cấu hình dự án
│
├── base/                      # Các lớp trừu tượng cơ bản
│   └── base_crawler.py        # Lớp cơ bản crawler, login, store, client
│
├── config/                    # Quản lý cấu hình
│   ├── base_config.py         # Cấu hình cốt lõi
│   ├── db_config.py           # Cấu hình cơ sở dữ liệu
│   └── {platform}_config.py   # Cấu hình platform cụ thể
│
├── media_platform/            # Triển khai crawler platform
│   ├── xhs/                   # Xiaohongshu
│   ├── douyin/                # Douyin
│   ├── kuaishou/              # Kuaishou
│   ├── bilibili/              # Bilibili
│   ├── weibo/                 # Weibo
│   ├── tieba/                 # Baidu Tieba
│   └── zhihu/                 # Zhihu
│
├── store/                     # Lưu trữ dữ liệu
│   ├── excel_store_base.py    # Lớp cơ bản Excel
│   └── {platform}/            # Triển khai lưu trữ platform
│
├── database/                  # Lớp cơ sở dữ liệu
│   ├── models.py              # Định nghĩa mô hình ORM
│   ├── db_session.py          # Quản lý phiên DB
│   └── mongodb_store_base.py  # Lớp cơ bản MongoDB
│
├── proxy/                     # Quản lý proxy
│   ├── proxy_ip_pool.py       # Quản lý pool IP
│   ├── proxy_mixin.py         # Mixin proxy
│   └── providers/             # Nhà cung cấp proxy
│
├── cache/                     # Hệ thống cache
│   ├── abs_cache.py           # Lớp trừu tượng cache
│   ├── local_cache.py         # Cache cục bộ
│   └── redis_cache.py         # Cache Redis
│
├── tools/                     # Module công cụ
│   ├── app_runner.py          # Quản lý chạy ứng dụng
│   ├── browser_launcher.py    # Khởi động trình duyệt
│   ├── cdp_browser.py         # Quản lý trình duyệt CDP
│   ├── crawler_util.py        # Công cụ crawler
│   └── async_file_writer.py   # Ghi file bất đồng bộ
│
├── model/                     # Mô hình dữ liệu
│   └── m_{platform}.py        # Mô hình Pydantic
│
├── libs/                      # Thư viện JS
│   └── stealth.min.js         # Script chống phát hiện
│
└── cmd_arg/                   # Tham số dòng lệnh
    └── arg.py                 # Định nghĩa tham số
```

---

## 4. Chi Tiết Các Module Cốt Lõi

### 4.1 Hệ Thống Lớp Cơ Bản

- **AbstractCrawler**: Lớp cơ bản cho crawler
  - `start()`: Khởi động crawler
  - `search()`: Tính năng tìm kiếm
  - `launch_browser()`: Khởi động trình duyệt

- **AbstractLogin**: Lớp cơ bản cho đăng nhập
  - `login_by_qrcode()`: Đăng nhập bằng mã QR
  - `login_by_mobile()`: Đăng nhập bằng số điện thoại
  - `login_by_cookies()`: Đăng nhập bằng Cookie

- **AbstractStore**: Lớp cơ bản cho lưu trữ
  - `store_content()`: Lưu nội dung
  - `store_comment()`: Lưu bình luận
  - `store_creator()`: Lưu thông tin nhà sáng tạo

### 4.2 Chu Kỳ Sống Crawler

1. Khởi tạo CrawlerFactory
2. Tạo instance crawler cụ thể
3. Khởi động trình duyệt (Playwright hoặc CDP)
4. Xác thực đăng nhập (nếu cần)
5. Thực hiện tìm kiếm hoặc lấy chi tiết
6. Phân tích dữ liệu
7. Lưu trữ dữ liệu
8. Đóng kết nối

### 4.3 Ba Chế Độ Crawl

| Chế Độ | Giá Trị Config | Mô Tả | Trường Hợp Sử Dụng |
|--------|---------|---------|-----------------|
| Search (Tìm Kiếm) | `search` | Tìm kiếm theo từ khóa | Lấy nội dung chủ đề cụ thể |
| Detail (Chi Tiết) | `detail` | Lấy chi tiết ID cụ thể | Lấy nội dung đã biết |
| Creator (Nhà Sáng Tạo) | `creator` | Lấy tất cả nội dung nhà sáng tạo | Theo dõi blogger cụ thể |

---

## 5. Lớp Lưu Trữ

### 5.1 Các Phương Pháp Lưu Trữ

| Phương Pháp | Giá Trị Config | Ưu Điểm | Trường Hợp Sử Dụng |
|-------------|---------|--------|-----------------|
| CSV | `csv` | Đơn giản, phổ quát | Dữ liệu nhỏ, xem nhanh |
| JSON | `json` | Cấu trúc hoàn chỉnh, dễ phân tích | Tương tác API, trao đổi dữ liệu |
| JSONL | `jsonl` | Ghi append, hiệu suất tốt | Dữ liệu lớn, crawl tăng dần (mặc định) |
| SQLite | `sqlite` | Nhẹ, không cần server | Dev cục bộ, dự án nhỏ |
| MySQL | `db` | Hiệu suất tốt, hỗ trợ đồng thời | Môi trường production |
| MongoDB | `mongodb` | Linh hoạt, dễ mở rộng | Dữ liệu không cấu trúc |
| Excel | `excel` | Trực quan, dễ chia sẻ | Báo cáo, phân tích dữ liệu |

---

## 6. Lớp Cơ Sở Hạ Tầng

### 6.1 Hệ Thống Proxy

- **Các Nhà Cung Cấp Proxy**:
  - KuaiDaiLi (快代理)
  - WanDouHttp (万代理)
  - JiShuHttp (技术IP)

- **Quản Lý Pool**:
  - Tải proxy từ nhà cung cấp
  - Xác thực proxy hợp lệ
  - Tự động làm mới khi hết hạn

### 6.2 Luồng Đăng Nhập

1. **Mã QR**: Hiển thị QR → Chờ quét → Lưu Cookie
2. **Số Điện Thoại**: Nhập số → Gửi OTP → Xác thực → Lưu Cookie
3. **Cookie**: Tải Cookie đã lưu → Xác thực → Sử dụng

### 6.3 Quản Lý Trình Duyệt

- **Chế độ Playwright**: Khởi động trình duyệt mới (môi trường sạch)
- **Chế độ CDP**: Kết nối tới Chrome đang chạy (tái sử dụng state)

---

## 7. Mô Hình Dữ Liệu

### 7.1 Bảng Dữ Liệu (Ví Dụ Douyin)

- **DouyinAweme**: Bài viết/video
- **DouyinAwemeComment**: Bình luận bài viết
- **DyCreator**: Thông tin nhà sáng tạo

### 7.2 Các Bảng Theo Platform

| Platform | Bảng Nội Dung | Bảng Bình Luận | Bảng Nhà Sáng Tạo |
|----------|--------|----------|------------|
| Douyin | DouyinAweme | DouyinAwemeComment | DyCreator |
| Xiaohongshu | XHSNote | XHSNoteComment | XHSCreator |
| Kuaishou | KuaishouVideo | KuaishouVideoComment | KsCreator |
| Bilibili | BilibiliVideo | BilibiliVideoComment | BilibiliUpInfo |
| Weibo | WeiboNote | WeiboNoteComment | WeiboCreator |
| Zhihu | ZhihuContent | ZhihuContentComment | ZhihuCreator |

---

## 8. Hệ Thống Cấu Hình

### 8.1 Các Tham Số Cấu Hình Chính

**config/base_config.py:**
```python
PLATFORM = "xhs"                    # Nền tảng (xhs, dy, ks, bili, wb, tieba, zhihu)
LOGIN_TYPE = "qrcode"              # Kiểu đăng nhập (qrcode, phone, cookie)
CRAWLER_TYPE = "search"            # Loại crawl (search, detail, creator)
KEYWORDS = "lập trình,副业"         # Từ khóa tìm kiếm
ENABLE_GET_COMMENTS = True         # Lấy bình luận
ENABLE_GET_SUB_COMMENTS = False    # Lấy bình luận cấp 2
HEADLESS = False                   # Chế độ headless (không GUI)
ENABLE_CDP_MODE = True             # Dùng CDP mode
SAVE_DATA_OPTION = "jsonl"         # Định dạng lưu (csv, json, jsonl, sqlite, db, mongodb, excel)
```

### 8.2 Cấu Hình Cơ Sở Dữ Liệu

**config/db_config.py:**
```python
MYSQL_DB_HOST = "localhost"
MYSQL_DB_PORT = 3306
MYSQL_DB_NAME = "media_crawler"

REDIS_DB_HOST = "127.0.0.1"
REDIS_DB_PORT = 6379

MONGODB_HOST = "localhost"
MONGODB_PORT = 27017

SQLITE_DB_PATH = "database/sqlite_tables.db"
```

---

## 9. Module Công Cụ

| Module | File | Chức Năng Chính |
|--------|------|-----------------|
| App Runner | `app_runner.py` | Xử lý signal, thoát graceful |
| Browser Launcher | `browser_launcher.py` | Phát hiện đường dẫn, khởi động browser |
| CDP Browser | `cdp_browser.py` | Kết nối CDP, quản lý context |
| Crawler Utils | `crawler_util.py` | Nhận dạng QR, xử lý captcha |
| File Writer | `async_file_writer.py` | Ghi bất đồng bộ CSV/JSON |
| Time Utils | `time_util.py` | Chuyển đổi timestamp, xử lý date |

---

## 10. Hướng Dẫn Mở Rộng

### 10.1 Thêm Platform Mới

1. Tạo thư mục trong `media_platform/`
2. Triển khai: `core.py`, `client.py`, `login.py`, `field.py`
3. Tạo thư mục lưu trữ trong `store/`
4. Đăng ký trong `main.py` `CrawlerFactory`

### 10.2 Thêm Phương Pháp Lưu Trữ Mới

1. Tạo lớp implement trong `store/`
2. Kế thừa `AbstractStore`
3. Triển khai các phương thức: `store_content`, `store_comment`, `store_creator`
4. Đăng ký trong `StoreFactory` của các platform

### 10.3 Thêm Nhà Cung Cấp Proxy Mới

1. Tạo lớp trong `proxy/providers/`
2. Kế thừa `BaseProxy`
3. Triển khai phương thức `get_proxy()`
4. Đăng ký trong cấu hình

---

## 11. Tham Khảo Nhanh

### Các Lệnh Phổ Biến

```bash
# Khởi động crawler
python main.py

# Chỉ định platform
python main.py --platform xhs

# Chỉ định loại đăng nhập
python main.py --lt qrcode

# Chỉ định loại crawl
python main.py --type search
```

### Đường Dẫn File Quan Trọng

| Mục Đích | Đường Dẫn |
|---------|---------|
| Lối vào chương trình | `main.py` |
| Cấu hình cốt lõi | `config/base_config.py` |
| Cấu hình DB | `config/db_config.py` |
| Lớp cơ bản crawler | `base/base_crawler.py` |
| Mô hình ORM | `database/models.py` |
| Pool Proxy | `proxy/proxy_ip_pool.py` |
| Trình duyệt CDP | `tools/cdp_browser.py` |

---

*Được cập nhật: 2025-12-18*
