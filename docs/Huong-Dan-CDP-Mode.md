# Hướng Dẫn Sử Dụng Chế Độ CDP

## Tổng Quan

Chế độ CDP (Chrome DevTools Protocol) là một kỹ thuật chống phát hiện nâu cao, điều khiển trình duyệt Chrome/Edge hiện có của người dùng để crawl web. So với Playwright tự động hóa truyền thống, chế độ CDP có các ưu điểm:

### 🎯 Các Ưu Điểm Chính

1. **Môi trường trình duyệt thật**: Dùng trình duyệt thực tế của người dùng, bao gồm tất cả extension và cài đặt
2. **Khả năng chống phát hiện tốt hơn**: Dấu vân tay trình duyệt thực tế, khó bị phát hiện là công cụ tự động
3. **Giữ trạng thái người dùng**: Tự động kế thừa trạng thái đăng nhập, Cookie và lịch sử duyệt
4. **Hỗ trợ Extension**: Có thể sử dụng ad blocker, proxy extension của người dùng
5. **Hành vi tự nhiên hơn**: Mô hình hành vi gần hơn với người dùng thật

### 📌 Hai Chế Độ CDP

| Chế Độ | Mô Tả | Trường Hợp Sử Dụng |
|--------|--------|-----------------|
| **Kết nối trình duyệt hiện có** (mặc định khuyến nghị) | Kết nối Chrome đang sử dụng, tái sử dụng Cookie, extension thật | Yêu cầu chống phát hiện cao |
| **Khởi động trình duyệt mới** | Tự động phát hiện và khởi động Chrome/Edge mới | Khi không cần tái sử dụng trạng thái |

## Bắt Đầu Nhanh

### Phương Pháp 1: Kết Nối Trình Duyệt Hiện Có (Khuyến Nghị Mặc Định)

Đây là **cách mặc định và khuyến nghị**, trực tiếp kết nối Chrome đang sử dụng, hiệu suất chống phát hiện tốt nhất.

#### Bước 1: Đảm Bảo Phiên Bản Chrome

Cần Chrome **144 trở lên**. Nhập `chrome://version` trong address bar để kiểm tra.

#### Bước 2: Bật Remote Debugging

1. Nhập `chrome://inspect/#remote-debugging` trong address bar
2. Tích chọn **"Allow remote debugging for this browser instance"**
3. Trang sẽ hiển thị `Server running at: 127.0.0.1:9222`

#### Bước 3: Chạy Crawler

```bash
uv run main.py --platform xhs --lt qrcode --type search
```

Chrome sẽ **bật hộp thoại xác nhận**, nhấp "Chấp nhận". Chương trình chờ xác nhận (timeout 60s mặc định).

#### Cấu Hình

`config/base_config.py`:

```python
ENABLE_CDP_MODE = True
CDP_CONNECT_EXISTING = True  # Mặc định bật
CDP_DEBUG_PORT = 9222
```

### Phương Pháp 2: Khởi Động Trình Duyệt Mới

```python
ENABLE_CDP_MODE = True
CDP_CONNECT_EXISTING = False  # Đóng, khởi động mới
```

---
