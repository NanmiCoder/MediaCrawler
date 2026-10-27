# Hướng Dẫn Xuất Excel

## Tổng Quan

MediaCrawler hiện hỗ trợ xuất dữ liệu crawled sang file Excel được định dạng (.xlsx) với kiểu dáng chuyên nghiệp và nhiều sheet cho nội dung, bình luận và nhà sáng tạo.

## Các Tính Năng

- **Workbook đa sheet**: Sheet riêng cho Nội Dung, Bình Luận và Nhà Sáng Tạo
- **Định dạng chuyên nghiệp**:
  - Tiêu đề được định kiểu với nền xanh và chữ trắng
  - Tự động điều chỉnh độ rộng cột
  - Viền cell và bao phủ văn bản
  - Bố cục sạch và dễ đọc
- **Xuất thông minh**: Sheet trống được xóa tự động
- **Lưu trữ có tổ chức**: File lưu tại thư mục `data/{platform}/` với timestamp

## Cài Đặt

Xuất Excel yêu cầu thư viện `openpyxl`:

```bash
# Sử dụng uv (khuyến nghị)
uv sync

# Hoặc dùng pip
pip install openpyxl
```

## Sử Dụng

### Sử Dụng Cơ Bản

1. **Cấu hình xuất Excel** trong `config/base_config.py`:

```python
SAVE_DATA_OPTION = "excel"  # Đổi từ jsonl/json/csv/db thành excel
```

2. **Chạy crawler**:

```bash
# Ví dụ Xiaohongshu
uv run main.py --platform xhs --lt qrcode --type search

# Ví dụ Douyin
uv run main.py --platform dy --lt qrcode --type search

# Ví dụ Bilibili
uv run main.py --platform bili --lt qrcode --type search
```

3. **Tìm file Excel** trong thư mục `data/{platform}/`:
   - Định dạng tên: `{platform}_{crawler_type}_{timestamp}.xlsx`
   - Ví dụ: `xhs_search_20250128_143025.xlsx`

### Ví Dụ Dòng Lệnh

```bash
# Tìm kiếm theo từ khóa và xuất Excel
uv run main.py --platform xhs --lt qrcode --type search --save_data_option excel

# Crawl bài viết cụ thể và xuất Excel
uv run main.py --platform xhs --lt qrcode --type detail --save_data_option excel

# Crawl hồ sơ nhà sáng tạo và xuất Excel
uv run main.py --platform xhs --lt qrcode --type creator --save_data_option excel
```

## Cấu Trúc File Excel

### Sheet Nội Dung
Chứa thông tin bài viết/video:
- `note_id`: Định danh bài viết duy nhất
- `title`: Tiêu đề bài viết
- `desc`: Mô tả bài viết
- `user_id`: ID tác giả
- `nickname`: Biệt danh tác giả
- `liked_count`: Số lượt thích
- `comment_count`: Số bình luận
- `share_count`: Số chia sẻ
- Và thêm các trường khác...

### Sheet Bình Luận
Chứa thông tin bình luận:
- `comment_id`: Định danh bình luận duy nhất
- `note_id`: ID bài viết liên quan
- `content`: Nội dung bình luận
- `user_id`: ID người bình luận
- `nickname`: Biệt danh người bình luận
- `like_count`: Số lượt thích bình luận
- Và thêm các trường khác...

### Sheet Nhà Sáng Tạo
Chứa thông tin nhà sáng tạo/tác giả:
- `user_id`: Định danh người dùng duy nhất
- `nickname`: Tên hiển thị
- `avatar`: URL ảnh hồ sơ
- `desc`: Tiểu sử/mô tả
- `fans`: Số người theo dõi
- Và thêm các trường khác...

## Ưu Điểm So Với Các Định Dạng Khác

### So Với CSV
- Nhiều sheet trong một file
- Định dạng chuyên nghiệp
- Xử lý ký tự đặc biệt tốt hơn
- Không có vấn đề mã hóa

### So Với JSON
- Định dạng bảng dễ đọc
- Dễ mở trong Excel/Google Sheets
- Phù hợp cho phân tích dữ liệu
- Chia sẻ dễ dàng

### So Với Database
- Không cần thiết lập database
- Định dạng file đơn lẻ
- Dễ chia sẻ và lưu trữ
- Hoạt động ngoại tuyến

## Mẹo & Thực Hành Tốt

1. **Tập dữ liệu lớn**: Với crawl rất lớn (>10,000 hàng), cân nhắc sử dụng database
2. **Phân tích dữ liệu**: File Excel hoạt động tốt với Python pandas:
   ```python
   import pandas as pd
   df = pd.read_excel('file.xlsx', sheet_name='Contents')
   ```

---
