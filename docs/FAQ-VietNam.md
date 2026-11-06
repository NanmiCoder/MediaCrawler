# Các Câu Hỏi Thường Gặp - FAQ

## Vấn Đề Do Thiếu Môi Trường Node.js

**Q: Crawl Douyin và Zhihu báo lỗi: `execjs._exceptions.ProgramError: SyntaxError: thiếu ';'`**

A: Lỗi này do thiếu môi trường Node.js. Cài đặt Node.js phiên bản >= v16 để giải quyết.

**Q: Dùng Cookie để crawl Douyin báo lỗi: execjs._exceptions.ProgramError: TypeError: Cannot read property 'JS_MD5_NO_COMMON_JS' of null**

A: Trên Windows, tải về Node.js từ `https://nodejs.org/en/blog/release/v16.8.0` (phiên bản Windows 64-bit Installer), rồi cài đặt theo hướng dẫn.

---

## Vấn Đề Xác Thực Slider Khi Đăng Nhập Xiaohongshu

**Q: Xiaohongshu quét mã QR thành công nhưng trình duyệt liên tục xác thực slider, không thể đăng nhập?**

A: Xiaohongshu có cơ chế chống bot rất nghiêm ngặt. **Khuyến khích sử dụng CDP mode kết nối trình duyệt thật của bạn** (cấu hình mặc định), không nên dùng trình duyệt vô danh hay chế độ Playwright chuẩn. Kết nối trình duyệt thật giúp bạn tái sử dụng Cookie, trạng thái đăng nhập và lịch sử duyệt web có sẵn, giảm đáng kể rủi ro bị phát hiện chống bot. Nếu vẫn gặp vấn đề slider, hãy thử xóa thư mục `brower_data` trong thư mục dự án và tái đăng nhập.

---

## Cách Chỉ Định Từ Khóa

**Q: Có thể chỉ định từ khóa để crawl không?**

A: Có, trong file `config/base_config.py`, tham số `KEYWORDS` được dùng để kiểm soát các từ khóa cần crawl.

---

## Cách Chỉ Định Bài Viết

**Q: Có thể chỉ định bài viết để crawl không?**

A: Có, trong file `config/base_config.py`, tham số `XHS_SPECIFIED_ID_LIST` được dùng để kiểm soát danh sách ID bài viết cần crawl.

---

## Crawl Bất Ngờ Dừng Hoạt Động

**Q: Ban đầu có thể crawl dữ liệu, nhưng sau một thời gian thì dừng hoạt động?**

A: Tình huống này thường xảy ra do tài khoản của bạn đã kích hoạt cơ chế chống bot của nền tảng. ❗️❗️Vui lòng không crawl quy mô lớn từ nền tảng, điều này ảnh hưởng đến hoạt động của nền tảng.

---

## Cách Thay Đổi Tài Khoản Đăng Nhập

**Q: Cách thay đổi tài khoản đăng nhập?**

A: Xóa thư mục `brower_data` ở thư mục gốc của dự án.

---

## Vấn Đề Timeout của Playwright

**Q: Báo lỗi `playwright._impl._api_types.TimeoutError: Timeout 30000ms exceeded.`**

A: Kiểm tra xem bạn có sử dụng VPN không.

---

## Cách Xác Thực Manual Slider Cho Playwright

**Q: Xiaohongshu quét mã QR thành công, làm cách nào xác thực slider manually?**

A: Mở file `config/base_config.py`, tìm cấu hình `HEADLESS`, đặt nó thành `False`. Sau đó khởi động lại dự án, trong trình duyệt hãy thực hiện xác thực slider manually.

---

## Tạo Word Cloud

**Q: Cách cấu hình tạo word cloud?**

A: Mở file `config/base_config.py`, tìm hai cấu hình `ENABLE_GET_WORDCLOUD` và `ENABLE_GET_COMMENTS`, đặt cả hai thành `True` để sử dụng tính năng này.

---

## Thêm Từ Dừng và Từ Tùy Chỉnh Cho Word Cloud

**Q: Cách thêm từ dừng (stopwords) và từ tùy chỉnh vào word cloud?**

A: Mở `docs/hit_stopwords.txt` và nhập các từ dừng (lưu ý mỗi từ một dòng). Mở file `config/base_config.py`, tìm `CUSTOM_WORDS` và thêm từ tùy chỉnh theo định dạng được hướng dẫn.

---

## Các Vấn Đề Liên Quan Đến Kết Nối CDP

**Q: Sau khi chạy crawler, nhận được thông báo không thể kết nối tới trình duyệt, báo lỗi `Cannot connect to existing browser on port 9222`?**

A: Vui lòng kiểm tra các điểm sau:

1. Đảm bảo trình duyệt Chrome đã mở và đang chạy
2. Nhập `chrome://inspect/#remote-debugging` vào địa chỉ Chrome, đảm bảo đã tích chọn **"Allow remote debugging for this browser instance"**
3. Trang nên hiển thị `Server running at: 127.0.0.1:9222`, nếu không có nghĩa là remote debugging chưa bật thành công
4. Đảm bảo phiên bản Chrome >= 144, phiên bản cũ không hỗ trợ, nhập `chrome://version` vào địa chỉ để kiểm tra phiên bản

**Q: Sau khi chạy crawler, trình duyệt bật lên hộp thoại xác nhận, cần phải làm gì?**

A: Đây là hành vi bình thường. Chrome sẽ bật hộp thoại xác nhận khi kết nối tới trình duyệt đã có, hãy nhấp vào "Chấp nhận". Chương trình sẽ chờ xác nhận từ người dùng, thời gian timeout mặc định là 60 giây, hãy nhấp vào xác nhận trong khoảng thời gian này.

**Q: Không muốn kết nối tới trình duyệt đã có, muốn chương trình tự động khởi động một trình duyệt mới?**

A: Trong `config/base_config.py`, đặt `CDP_CONNECT_EXISTING = False`, chương trình sẽ tự động phát hiện và khởi động một instance Chrome/Edge mới.

**Q: Tại sao khuyến khích kết nối tới trình duyệt đã có thay vì khởi động trình duyệt mới?**

A: Kết nối tới trình duyệt đã có cho phép bạn trực tiếp tái sử dụng Cookie thật, trạng thái đăng nhập, plugin mở rộng và lịch sử duyệt web của chính bạn. Nền tảng rất khó phân biệt đây là hoạt động tự động hay hành vi người dùng thật, **giảm đáng kể rủi ro bị phát hiện chống bot**. Còn khởi động trình duyệt mới là một môi trường "sạch", dễ bị nền tảng nhận dạng là bot.

