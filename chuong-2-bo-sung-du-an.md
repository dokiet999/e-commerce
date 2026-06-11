# Bo sung Chương 2 - Can chinh theo du an eCommerceStore hien tai

Tai lieu Chương 2 trong PDF mo ta dung y tuong tong quat ve he thong e-commerce microservices, nhung can bo sung va chinh lai cac diem duoi day de khop voi source code hien tai cua du an `eCommerceStore`.

## 2.2 Bo sung Service Mapping thuc te

He thong hien tai khong chi co 7 service nhu ban mo ta ban dau, ma gom cac bounded context/service sau:

| Bounded Context | Microservice | Port | Chuc nang chinh | Database/Cong nghe |
|---|---:|---:|---|---|
| API Gateway Context | api-gateway | 8000 | Entry point, proxy request, JWT middleware, RBAC, session forwarding | Khong dung database |
| Auth Context | auth-service | 8001 | Dang ky, dang nhap, refresh token, profile nguoi dung | PostgreSQL |
| Product Context | product-service | 8002 | Quan ly danh muc, san pham, may tinh, dien thoai, quan ao | PostgreSQL |
| Cart Context | cart-service | 8003 | Gio hang user/guest, cart item, merge cart | MySQL |
| AI Context | ai-service | 8004 | Recommendation, behavior tracking, consultation/chat, RAG/Graph QA | PostgreSQL, Neo4j, ChromaDB |
| Order Context | order-service | 8005 | Tao don hang tu gio hang, quan ly trang thai don | PostgreSQL |
| Payment Context | payment-service | 8006 | Tao thanh toan, refund, cap nhat trang thai order | PostgreSQL |
| Inventory Context | inventory-service | 8007 | Ton kho, reserve/release/deduct stock, stock movement | MySQL |
| Review Context | review-service | 8009 | Danh gia san pham, verified purchase | PostgreSQL |
| Shipping Context | shipping-service | 8010 | Phuong thuc giao hang, shipment, tracking event | MySQL |
| Coupon Context | coupon-service | 8011 | Ma giam gia, dieu kien ap dung, lich su su dung | PostgreSQL |

Ghi chu: `docker-compose.yml` co khai bao `notification-service` port 8008, nhung trong source code hien tai chua co thu muc `notification_service`. Vi vay neu trinh bay trong bao cao, can ghi day la thanh phan du kien hoac can bo sung source code rieng.

## 2.3 Cap nhat Product Service theo source code

Product Service hien tai khong trien khai cac lop `Book`, `Electronics`, `Fashion` nhu ban mo ta cu. Source code dang co:

- `Category`: danh muc cha.
- `SubCategory`: danh muc con, thuoc mot `Category`.
- `Product`: san pham tong quat, co `name`, `description`, `price`, `stock`, `category`, `subcategory`, `image_url`, `is_active`.
- `ComputerProduct`: thong tin rieng cho laptop/may tinh, gom `brand`, `ram`, `storage`, `cpu`, `screen_size`.
- `MobileProduct`: thong tin rieng cho dien thoai, gom `brand`, `screen_size`, `battery`, `operating_system`.
- `ClothesProduct`: thong tin rieng cho thoi trang, gom `size`, `color`, `material`, `gender`.

API thuc te:

```text
GET/POST   /api/products/
GET/PUT/DELETE /api/products/{id}/
GET/POST   /api/products/computers/
GET/PUT/DELETE /api/products/computers/{id}/
GET/POST   /api/products/mobiles/
GET/PUT/DELETE /api/products/mobiles/{id}/
GET/POST   /api/products/clothes/
GET/PUT/DELETE /api/products/clothes/{id}/
GET/POST   /api/products/categories/
GET/POST   /api/products/subcategories/
GET/PUT/DELETE /api/products/subcategories/{id}/
```

Quyen ghi du lieu Product duoc bao ve o API Gateway: `POST`, `PUT`, `DELETE` voi `/api/products/` yeu cau admin.

## 2.4 Cap nhat Auth/User Service va RBAC

Trong source code, service quan ly nguoi dung ten la `auth-service`, khong phai `user-service`.

Model nguoi dung hien tai la `CustomUser`, ke thua `AbstractUser`, gom:

- `email`: unique, dung lam truong dang nhap chinh.
- `phone`: so dien thoai.
- `address`: dia chi.

He thong chua co field `role` truc tiep trong model user. RBAC hien tai duoc xu ly bang:

- JWT payload: `user_id`, `role`, `is_staff`, `is_superuser`.
- `shared/jwt_utils.py`: decode JWT va lay token tu Authorization header.
- `shared/rbac.py`: tao `AuthContext`, kiem tra `is_authenticated`, `is_admin`, `is_service_request`.
- `api_gateway/proxy/middleware.py`: enforce public/user/admin/service policy truoc khi proxy request.

API thuc te:

```text
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/refresh/
GET  /api/auth/profile/
GET  /api/auth/health/
```

## 2.5 Cap nhat Cart Service

Cart Service hien tai ho tro ca nguoi dung da dang nhap va guest user.

Model:

- `Cart.user_id`: id nguoi dung neu da dang nhap.
- `Cart.session_id`: id phien cho guest cart.
- `CartItem.product_id`: id san pham tu Product Service.
- `CartItem.quantity`: so luong.
- `CartItem.price_at_add`: snapshot gia tai thoi diem them vao gio.

Diem can bo sung vao bao cao: Cart Service dung Anti-Corruption Layer voi Product Service bang cach luu `price_at_add`, giup gio hang khong bi thay doi khi gia san pham tren Product Service thay doi.

API thuc te:

```text
GET    /api/cart/
POST   /api/cart/items/
PUT    /api/cart/items/{item_id}/
DELETE /api/cart/items/{item_id}/remove/
DELETE /api/cart/clear/
POST   /api/cart/merge/
```

## 2.6 Cap nhat Order Service

Order Service hien tai tao don hang tu Cart Service, sau do clear cart. Khi tao OrderItem, service lay thong tin Product de snapshot:

- `product_name`
- `unit_price`
- `subtotal`

Model `Order` gom:

- `user_id`
- `status`: `pending`, `confirmed`, `processing`, `shipped`, `delivered`, `cancelled`, `refunded`
- `total_amount`
- `shipping_address`
- `billing_address`
- `payment_id`
- `shipping_id`
- `notes`

API thuc te:

```text
GET/POST /api/orders/
GET      /api/orders/{order_id}/
PUT      /api/orders/{order_id}/status/
POST     /api/orders/{order_id}/cancel/
```

Luu y can sua trong bao cao: Order Service hien tai chua tu dong goi Payment Service va Shipping Service trong cung workflow. Thuc te:

1. User tao order tu cart.
2. Order Service tao order va order items.
3. Order Service clear cart.
4. User hoac frontend goi Payment Service de tao payment.
5. Payment Service cap nhat Order sang `confirmed`.

## 2.7 Cap nhat Payment Service

Payment Service hien tai co cac trang thai:

- `pending`
- `processing`
- `completed`
- `failed`
- `refunded`
- `partially_refunded`

Model `Payment` gom:

- `order_id`
- `user_id`
- `amount`
- `currency`
- `method`
- `status`
- `transaction_id`
- `payment_details`

API thuc te:

```text
GET/POST /api/payments/
GET      /api/payments/{payment_id}/
POST     /api/payments/{payment_id}/refund/
```

Khi tao payment, service gia lap xu ly thanh toan, chuyen status sang `completed`, sau do goi Order Service de cap nhat order thanh `confirmed`.

## 2.8 Cap nhat Shipping Service

Shipping Service hien tai chi tiet hon ban mo ta cu. Model gom:

- `ShippingMethod`: ten phuong thuc, carrier, base cost, cost per kg, estimated days.
- `Shipment`: order id, method, tracking number, status, shipping address, weight, cost.
- `TrackingEvent`: lich su trang thai van chuyen.

Trang thai shipment:

- `pending`
- `picked_up`
- `in_transit`
- `out_for_delivery`
- `delivered`
- `returned`
- `failed`

API thuc te:

```text
GET/POST /api/shipping/methods/
POST     /api/shipping/calculate/
POST     /api/shipping/
GET      /api/shipping/{tracking_number}/track/
PUT      /api/shipping/{shipment_id}/status/
```

## 2.9 Bo sung Inventory Service

Inventory Service la service con thieu trong Chương 2 ban dau. Service nay quan ly ton kho doc lap voi Product Service.

Model:

- `InventoryItem`: `product_id`, `quantity_available`, `quantity_reserved`, `low_stock_threshold`.
- `StockMovement`: ghi nhan lich su thay doi ton kho voi cac loai `restock`, `reserve`, `release`, `deduct`, `adjustment`.

Vai tro:

- Kiem tra so luong ton kho.
- Reserve hang khi tao don.
- Release hang khi huy don.
- Deduct hang khi don hang thanh cong.

API can trinh bay:

```text
GET      /api/inventory/{product_id}/
POST     /api/inventory/restock/
POST     /api/inventory/reserve/
POST     /api/inventory/release/
POST     /api/inventory/deduct/
GET      /api/inventory/low-stock/
```

## 2.10 Bo sung Coupon Service

Coupon Service la bounded context rieng cho khuyen mai/giam gia.

Model:

- `Coupon`: ma coupon, loai giam gia `percentage` hoac `fixed`, gia tri giam, dieu kien don toi thieu, thoi gian hieu luc, so luot su dung.
- `CouponUsage`: lich su nguoi dung su dung coupon theo order.

Vai tro:

- Tao va quan ly ma giam gia.
- Validate coupon theo gia tri don hang, user, san pham/danh muc ap dung.
- Ghi nhan coupon da duoc su dung.

API can trinh bay:

```text
GET/POST /api/coupons/
POST     /api/coupons/validate/
POST     /api/coupons/apply/
```

## 2.11 Bo sung Review Service

Review Service quan ly danh gia san pham va co lien ket voi Order Service de xac minh nguoi dung da mua hang.

Model `Review`:

- `product_id`
- `user_id`
- `rating` tu 1 den 5
- `title`
- `comment`
- `is_verified_purchase`
- `is_approved`

Diem can trinh bay theo DDD: Review Service khong dung truc tiep model Order. Thay vao do, service goi Order Service de kiem tra lich su mua hang va chuyen doi ket qua thanh boolean `is_verified_purchase`. Day la mot Anti-Corruption Layer giua Review Context va Order Context.

API thuc te:

```text
GET/POST /api/reviews/
GET/PUT/DELETE /api/reviews/{review_id}/
GET      /api/reviews/product/{product_id}/
GET      /api/reviews/product/{product_id}/summary/
```

## 2.12 Bo sung AI Service trong Chương 2

Chương 2 co the gioi thieu ngan gon AI Context, sau do Chương 3 trinh bay chi tiet.

AI Service hien tai gom cac module:

- Behavior: ghi nhan hanh vi nguoi dung.
- Recommendations: goi y san pham bang content-based, collaborative, trending va ML.
- Consultation: tu van/chat voi RAG, Knowledge Graph, LLM.
- Knowledge Base: ChromaDB vector store, Neo4j graph store.

API AI duoc proxy qua:

```text
/api/ai/...
```

Gateway dat timeout dai hon cho AI Service vi cac request LLM/RAG co the mat nhieu thoi gian hon request CRUD thong thuong.

## 2.13 Cap nhat luong tong the dung voi source code

Luong mua hang nen sua thanh:

1. User dang ky/dang nhap qua Auth Service va nhan JWT.
2. Client goi API Gateway; Gateway decode JWT va forward `X-User-Id`, `X-Role`, `X-Session-Id`.
3. User xem danh sach san pham qua Product Service.
4. User them san pham vao gio hang qua Cart Service; Cart snapshot `price_at_add`.
5. User tao order; Order Service lay cart, lay ten san pham tu Product Service, tao Order/OrderItem va clear cart.
6. User thanh toan qua Payment Service; Payment tao transaction, mark `completed`, cap nhat Order sang `confirmed`.
7. Shipping Service tao shipment va tracking khi co yeu cau giao hang.
8. Review Service cho phep user danh gia san pham, co kiem tra verified purchase tu Order Service.
9. Coupon Service xu ly ma giam gia neu user ap dung coupon.
10. AI Service ghi nhan hanh vi, goi y san pham va ho tro tu van san pham.

## 2.14 Cac quan he DDD can bo sung

### Shared Kernel

- `shared/jwt_utils.py`: decode JWT, lay user id tu token, lay bearer token tu header.
- `shared/rbac.py`: `AuthContext`, `is_admin`, `is_authenticated`, `is_service_request`.
- `service_registry/`: dang ky va discover service qua Redis.

### Customer-Supplier

- Product Service -> Cart Service: Cart can validate product va lay gia hien tai.
- Product Service -> Order Service: Order lay ten san pham de snapshot vao OrderItem.
- Cart Service -> Order Service: Order lay danh sach item trong cart.
- Order Service -> Payment Service: Payment cap nhat trang thai order sau thanh toan.
- Order Service -> Review Service: Review kiem tra verified purchase.
- Product Service -> AI Service: AI can enrich ket qua goi y bang thong tin san pham.

### Anti-Corruption Layer

- Cart snapshot `price_at_add` tu Product.
- Order snapshot `product_name`, `unit_price` tu Product.
- API Gateway chuyen JWT thanh cac header noi bo `X-User-Id`, `X-Role`, `X-Session-Id`.
- Review chuyen lich su Order thanh boolean `is_verified_purchase`.

## 2.15 Cac diem can ghi ro la chua hoan thien

De bao cao trung thuc voi source code hien tai, nen ghi ro:

- Chua co source code `notification_service`, du `docker-compose.yml` co khai bao.
- Chua co message broker nhu Kafka/RabbitMQ; cac service dang giao tiep chu yeu bang REST dong bo.
- Order Service chua tu dong orchestrate Payment va Shipping trong mot Saga hoan chinh.
- Inventory Service da co model reserve/release/deduct, nhung can kiem tra them muc do tich hop vao luong Order/Payment thuc te.
- Bao cao cu ghi AI Service dung FAISS, nhung source hien tai co ChromaDB va Neo4j.
