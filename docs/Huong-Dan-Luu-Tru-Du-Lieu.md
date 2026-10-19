# Hướng Dẫn Lưu Trữ Dữ Liệu

### 💾 Lưu Trữ Dữ Liệu

MediaCrawler hỗ trợ nhiều cách lưu trữ dữ liệu, bạn có thể chọn phương pháp phù hợp nhất với nhu cầu:

#### Các Phương Pháp Lưu Trữ

- **File CSV**: Lưu vào CSV (thư mục `data/`)
- **File JSON**: Lưu vào JSON (thư mục `data/`)
- **File JSONL**: Lưu vào JSONL (thư mục `data/`) — Định dạng mặc định, mỗi dòng một JSON object, hiệu suất ghi append tốt
- **File Excel**: Lưu vào file Excel được định dạng (thư mục `data/`) ✨ Tính năng mới
  - Hỗ trợ nhiều sheet (nội dung, bình luận, nhà sáng tạo)
  - Định dạng chuyên nghiệp (kiểu tiêu đề, tự động điều chỉnh cột, viền)
  - Dễ phân tích và chia sẻ
- **Lưu Trữ Cơ Sở Dữ Liệu**
  - Sử dụng tham số `--init_db` để khởi tạo cơ sở dữ liệu (khi dùng `--init_db` không cần tham số tùy chọn khác)
  - **SQLite**: Cơ sở dữ liệu nhẹ, không cần server, phù hợp cho người dùng cá nhân (khuyến nghị)
    1. Khởi tạo: `--init_db sqlite`
    2. Lưu dữ liệu: `--save_data_option sqlite`
  - **MySQL**: Hỗ trợ lưu vào cơ sở dữ liệu quan hệ MySQL (cần tạo DB trước)
    1. Khởi tạo: `--init_db mysql`
    2. Lưu dữ liệu: `--save_data_option db` (tham số db được giữ lại để tương thích)
  - **PostgreSQL**: Hỗ trợ lưu vào cơ sở dữ liệu PostgreSQL cao cấp (khuyến nghị cho production)
    1. Khởi tạo: `--init_db postgres`
    2. Lưu dữ liệu: `--save_data_option postgres`

#### Ví Dụ Sử Dụng

```bash
# Lưu vào Excel (khuyến nghị cho phân tích dữ liệu) ✨ Tính năng mới
uv run main.py --platform xhs --lt qrcode --type search --save_data_option excel

# Khởi tạo SQLite
uv run main.py --init_db sqlite
# Lưu dữ liệu vào SQLite
uv run main.py --platform xhs --lt qrcode --type search --save_data_option sqlite
```

```bash
# Khởi tạo MySQL
uv run main.py --init_db mysql
# Lưu dữ liệu vào MySQL
uv run main.py --platform xhs --lt qrcode --type search --save_data_option db
```

```bash
# Khởi tạo PostgreSQL
uv run main.py --init_db postgres
# Lưu dữ liệu vào PostgreSQL
uv run main.py --platform xhs --lt qrcode --type search --save_data_option postgres
```

```bash
# Lưu vào CSV
uv run main.py --platform xhs --lt qrcode --type search --save_data_option csv

# Lưu vào JSON
uv run main.py --platform xhs --lt qrcode --type search --save_data_option json

# Lưu vào JSONL (định dạng mặc định, không cần chỉ định)
uv run main.py --platform xhs --lt qrcode --type search --save_data_option jsonl
```

#### Tài Liệu Chi Tiết

- **Hướng Dẫn Xuất Excel**: Xem [Hướng Dẫn Xuất Excel](Huong-Dan-Xuat-Excel.md)
- **Cấu Hình Cơ Sở Dữ Liệu**: Tham khảo [FAQ](FAQ-VietNam.md)

---
