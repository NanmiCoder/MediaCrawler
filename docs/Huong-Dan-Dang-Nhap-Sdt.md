# Hướng Dẫn Đăng Nhập Bằng Số Điện Thoại

Đăng nhập bằng số điện thoại là một phương pháp thay thế khi đăng nhập bằng mã QR gặp khó khăn.

## Các Bước

1. Cấu hình loại đăng nhập trong `config/base_config.py`:

```python
LOGIN_TYPE = "phone"  # Đổi từ qrcode thành phone
```

2. Chạy crawler:

```bash
uv run main.py --platform xhs --lt phone --type search
```

3. Làm theo hướng dẫn trên giao diện:
   - Nhập số điện thoại
   - Nhân mã xác minh từ SMS
   - Hoàn thành xác thực slider (nếu cần)

## Lưu Ý

- Có thể chậm hơn so với mã QR
- Một số nền tảng yêu cầu xác thực slider
- Hãy chắc chắn bạn có quyền truy cập SMS của số điện thoại

---
