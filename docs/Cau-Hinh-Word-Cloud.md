# Cấu Hình Word Cloud

Word Cloud là một hình ảnh trực quan hóa từ từ các bình luận được crawl.

## Bật Word Cloud

Cấu hình trong `config/base_config.py`:

```python
ENABLE_GET_WORDCLOUD = True        # Bật tính năng word cloud
ENABLE_GET_COMMENTS = True         # Phải bật crawl bình luận
```

## Thêm Từ Dừng (Stopwords)

1. Mở file `docs/hit_stopwords.txt`
2. Thêm các từ cần loại bỏ (mỗi từ một dòng)

Ví dụ:
```
thế
này
là
của
và
```

## Thêm Từ Tùy Chỉnh

Trong `config/base_config.py`:

```python
CUSTOM_WORDS = [
    "lập trình",
    "Python",
    "web scraping"
]
```

## Cách Sử Dụng

1. Crawl dữ liệu với word cloud được bật
2. Chương trình tự động tạo file ảnh word cloud
3. File ảnh lưu trong thư mục `data/{platform}/`

---
