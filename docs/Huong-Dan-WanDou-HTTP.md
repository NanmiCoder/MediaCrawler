# Hướng Dẫn Sử Dụng WanDou HTTP (豌豆HTTP)

WanDou HTTP là một nhà cung cấp proxy HTTP cho web scraping.

## Các Bước Cơ Bản

1. Đăng ký tài khoản tại [WanDou HTTP](https://www.wandouip.com/)
2. Lấy API key từ dashboard
3. Cấu hình trong `config/base_config.py`:

```python
ENABLE_IP_PROXY = True
IP_PROXY_PROVIDER = "wandou"
IP_PROXY_POOL_COUNT = 5
```

4. Chạy crawler:

```bash
uv run main.py --platform xhs --lt qrcode --type search
```

## Ưu Điểm

- Proxy tốc độ cao
- Hỗ trợ nhiều giao thức
- Dải IP đa dạng
- Giá cơ bản

---
