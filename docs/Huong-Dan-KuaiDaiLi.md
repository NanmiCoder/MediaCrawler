# Hướng Dẫn Sử Dụng KuaiDaiLi (快代理)

KuaiDaiLi là một nhà cung cấp proxy IP hàng đầu cho web scraping.

## Các Bước Cơ Bản

1. Đăng ký tài khoản tại [KuaiDaiLi](https://www.kuaidaili.com/)
2. Lấy API key từ dashboard
3. Cấu hình trong `config/base_config.py`:

```python
ENABLE_IP_PROXY = True
IP_PROXY_PROVIDER = "kuaidaili"
IP_PROXY_POOL_COUNT = 5  # Số lượng proxy
```

4. Chạy crawler:

```bash
uv run main.py --platform xhs --lt qrcode --type search
```

## Ưu Điểm

- Dải IP rộng
- Tốc độ ổn định
- Hỗ trợ tiếng Trung tốt
- Giá cả cạnh tranh

---
