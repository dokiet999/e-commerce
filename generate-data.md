Hãy viết code Python để sinh file data_user500.csv với các yêu cầu sau:

- 500 user (user_id: U001 → U500)
- Mỗi user có 8 behaviors (hành vi)
- Tổng cộng file có 4000 dòng
- Các cột: user_id, product_id, action, timestamp, session_id, duration_seconds, device, category

Chi tiết từng cột:
- product_id: P001 → P100 (random)
- action: chọn ngẫu nhiên từ [view, click, add_to_cart, purchase, wishlist, review, share, compare]
- timestamp: từ 2024-01-01 đến 2024-12-31 (random, định dạng YYYY-MM-DD HH:MM:SS)
- session_id: chuỗi ngẫu nhiên dạng SESS_XXXXX
- duration_seconds: số giây từ 5 đến 600 (random)
- device: chọn từ [mobile, desktop, tablet]
- category: chọn từ [electronics, fashion, food, books, sports, beauty, home, toys]

Yêu cầu:
1. Dùng thư viện pandas, numpy, random, faker nếu cần
2. In ra 20 dòng đầu để kiểm tra
3. Lưu file thành data_user500.csv
4. In thống kê: số dòng, số cột, phân phối action, phân phối device