Dùng file data_user500.csv, hãy xây dựng Knowledge Base Graph với Neo4j.

**Bước 1 - Cài đặt và kết nối:**
- Dùng thư viện: neo4j, py2neo hoặc neo4j-driver
- Kết nối tới Neo4j local: bolt://localhost:7687, user: neo4j, password: [để placeholder]

**Bước 2 - Thiết kế schema đồ thị:**
Các Node:
- User {user_id}
- Product {product_id, category}
- Action {action_type}
- Device {device_name}
- Session {session_id, timestamp, duration_seconds}

Các Relationship:
- (User)-[:HAS_SESSION]->(Session)
- (Session)-[:PERFORMED]->(Action)
- (Action)-[:ON_PRODUCT]->(Product)
- (Session)-[:USED_DEVICE]->(Device)
- (User)-[:INTERESTED_IN]->(Product) — nếu action là view hoặc click
- (User)-[:PURCHASED]->(Product) — nếu action là purchase

**Bước 3 - Import data:**
- Đọc data_user500.csv
- Tạo tất cả nodes và relationships bằng Cypher query (MERGE để tránh trùng)
- Xử lý theo batch 100 dòng một lần

**Bước 4 - Truy vấn minh họa:**
Viết 5 Cypher query mẫu:
1. Top 10 sản phẩm được xem nhiều nhất
2. User nào có nhiều hành vi nhất
3. Tỉ lệ purchase theo category
4. Sản phẩm nào được add_to_cart nhưng chưa purchase
5. User dùng mobile hay mua hàng nhiều hơn desktop không?

**Bước 5 - Visualize:**
- Dùng matplotlib hoặc networkx để vẽ subgraph (lấy 20 dòng đầu)
- Vẽ đồ thị với màu sắc khác nhau cho từng loại node
- Node size tỉ lệ với số kết nối (degree)