# MediaCrawler - Hướng Dẫn Sử Dụng

## Tài Liệu Dự Án

- [Kiến Trúc Dự Án](Kien-Truc-Du-An.md) - Kiến trúc hệ thống, thiết kế module, luồng dữ liệu (bao gồm sơ đồ)

## Khuyến Nghị: Sử Dụng uv Quản Lý Phụ Thuộc

### 1. Phụ Thuộc Trước

- Cài đặt [uv](https://docs.astral.sh/uv/getting-started/installation), xác minh bằng `uv --version`.
- Phiên bản Python khuyên dùng **3.11** (phụ thuộc hiện tại dựa trên phiên bản này).
- Cài đặt Node.js (cần cho Douyin, Zhihu), phiên bản `>= 16.0.0`.

### 2. Đồng Bộ Phụ Thuộc Python

```bash
# Vào thư mục gốc dự án
cd MediaCrawler

# Sử dụng uv đảm bảo phiên bản Python và phụ thuộc nhất quán
uv sync
```

### 3. Cài Đặt Driver Trình Duyệt Playwright

```bash
uv run playwright install
```

> Dự án đã hỗ trợ kết nối Playwright với Chrome cục bộ. Nếu cần dùng CDP, có thể điều chỉnh cấu hình trong `config/base_config.py`.

### 4. Chạy Chương Trình Crawler

```bash
# Dự án mặc định không bật crawl bình luận. Nếu cần, sửa ENABLE_GET_COMMENTS trong config/base_config.py

# Tìm kiếm theo từ khóa và crawl bài viết & bình luận
uv run main.py --platform xhs --lt qrcode --type search

# Crawl danh sách ID bài viết cụ thể
uv run main.py --platform xhs --lt qrcode --type detail

# Lưu vào SQLite (khuyến nghị cho người dùng cá nhân)
uv run main.py --platform xhs --lt qrcode --type search --save_data_option sqlite

# Lưu vào MySQL
uv run main.py --platform xhs --lt qrcode --type search --save_data_option db

# Xem thêm ví dụ
uv run main.py --help
```

## Phương Pháp Thay Thế: Python venv (Không Khuyến Nghị)

> Nếu crawl Douyin hoặc Zhihu, cần cài Node.js trước, phiên bản `>= 16`.

```bash
# Vào thư mục gốc dự án
cd MediaCrawler

# Tạo môi trường ảo (Python 3.11)
python -m venv venv

# macOS & Linux - kích hoạt
source venv/bin/activate

# Windows - kích hoạt
venv\Scripts\activate
```

```bash
# Cài đặt phụ thuộc
pip install -r requirements.txt
playwright install
```

```bash
# Chạy crawler (venv)
python main.py --platform xhs --lt qrcode --type search
python main.py --platform xhs --lt qrcode --type detail
python main.py --platform xhs --lt qrcode --type search --save_data_option sqlite
python main.py --help
```

## 💾 Lưu Trữ Dữ Liệu

Hỗ trợ nhiều cách lưu trữ:
- **CSV**: Lưu vào CSV (thư mục `data/`)
- **JSON**: Lưu vào JSON (thư mục `data/`)
- **Database**
  - **SQLite**: Cơ sở dữ liệu nhẹ, không cần server (khuyến nghị)
  - **MySQL**: Hỗ trợ cơ sở dữ liệu quan hệ
  - **PostgreSQL**: Cơ sở dữ liệu PostgreSQL (khuyến nghị production)

## Tuyên Bố Từ Chối Trách Nhiệm

> **Tuyên Bố Từ Chối Trách Nhiệm:**
>
> Vui lòng sử dụng repository này cho mục đích học tập. Tham khảo [Các vụ kiện crawl bất hợp pháp](https://github.com/HiddenStrawberry/Crawler_Illegal_Cases_In_China)
>
> Toàn bộ nội dung của dự án này chỉ dành cho mục đích học tập và tham khảo, cấm sử dụng thương mại. Bất kỳ người hoặc tổ chức nào không được phép sử dụng nội dung của repository này cho mục đích bất hợp pháp hoặc xâm phạm quyền hợp pháp của người khác. Kỹ thuật crawl trong repository này chỉ dùng cho học tập và nghiên cứu, không được dùng để crawl quy mô lớn từ các nền tảng khác hoặc các hành động bất hợp pháp khác. Repository này không chịu trách nhiệm pháp lý nào phát sinh từ việc sử dụng nội dung của nó. Sử dụng nội dung của repository này đồng nghĩa với việc bạn đồng ý với toàn bộ các điều khoản và điều kiện của tuyên bố từ chối trách nhiệm này.

---
