# Quản Lý Môi Trường Native

## Phương Pháp Khuyến Nghị: Sử Dụng uv Quản Lý Phụ Thuộc

### 1. Phụ Thuộc Trước

- Cài đặt [uv](https://docs.astral.sh/uv/getting-started/installation), xác minh bằng `uv --version`.
- Phiên bản Python khuyên dùng **3.11** (các phụ thuộc hiện tại được xây dựng dựa trên phiên bản này).
- Cài đặt Node.js (cần cho các platform như Douyin, Zhihu), phiên bản `>= 16.0.0`.

### 2. Đồng Bộ Phụ Thuộc Python

```bash
# Nhập vào thư mục gốc dự án
cd MediaCrawler

# Sử dụng uv đảm bảo phiên bản Python và phụ thuộc nhất quán
uv sync
```

### 3. Cài Đặt Driver Trình Duyệt Playwright

```bash
uv run playwright install
```

> Dự án đã hỗ trợ kết nối Playwright với Chrome cục bộ. Nếu cần dùng phương pháp CDP, có thể điều chỉnh cấu hình `xhs` và `dy` trong `config/base_config.py`.

### 4. Chạy Chương Trình Crawler

```bash
# Dự án mặc định không bật crawl bình luận. Nếu cần bình luận, hãy sửa ENABLE_GET_COMMENTS trong config/base_config.py
# Các chức năng khác cũng có thể tùy chỉnh trong config/base_config.py với chú thích tiếng Trung

# Đọc từ config, tìm kiếm theo từ khóa và crawl bài viết & bình luận
uv run main.py --platform xhs --lt qrcode --type search

# Đọc từ config, lấy danh sách ID bài viết cụ thể và crawl bài viết & bình luận
uv run main.py --platform xhs --lt qrcode --type detail

# Xem ví dụ cho các platform khác
uv run main.py --help
```

---

## Phương Pháp Thay Thế: Python Native venv (Không Khuyến Nghị)

### Tạo Và Kích Hoạt Môi Trường Ảo

> Nếu crawl Douyin hoặc Zhihu, cần cài đặt Node.js trước, phiên bản `>= 16`.

```bash
# Nhập vào thư mục gốc dự án
cd MediaCrawler

# Tạo môi trường ảo (ví dụ phiên bản Python: 3.11, requirements dựa trên phiên bản này)
python -m venv venv

# macOS & Linux - kích hoạt môi trường ảo
source venv/bin/activate

# Windows - kích hoạt môi trường ảo
venv\Scripts\activate
```

### Cài Đặt Phụ Thuộc Và Driver

```bash
pip install -r requirements.txt
playwright install
```

### Chạy Chương Trình Crawler (Môi Trường venv)

```bash
# Đọc từ config, tìm kiếm theo từ khóa và crawl bài viết & bình luận
python main.py --platform xhs --lt qrcode --type search

# Đọc từ config, lấy danh sách ID bài viết cụ thể và crawl bài viết & bình luận
python main.py --platform xhs --lt qrcode --type detail

# Xem thêm ví dụ
python main.py --help
```

---

## Các Ghi Chú Quan Trọng

### uv vs venv

**Ưu điểm uv:**
- Cài đặt nhanh hơn
- Quản lý phiên bản Python tự động
- Đảm bảo phụ thuộc nhất quán giữa các máy

**Ưu điểm venv:**
- Phương pháp chuẩn Python
- Không cần cài đặt công cụ bổ sung

### Troubleshooting

Nếu gặp vấn đề, hãy kiểm tra:
1. Phiên bản Python là 3.11+
2. Node.js đã cài (cho Douyin/Zhihu)
3. Chạy `uv sync` hoặc `pip install -r requirements.txt` lại
4. Xóa cache: `rm -rf ~/.cache/uv/`

