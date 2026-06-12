# Phan ra he thong eCommerceStore theo DDD

Tai lieu nay phan ra he thong hien tai theo Domain-Driven Design, bam theo source code trong repo `eCommerceStore`. He thong dang duoc to chuc theo microservices, moi service tuong ung gan nhu mot Bounded Context rieng.

## 1. Core Domain, Supporting Domain, Generic Domain

| Nhom domain | Bounded Context | Ly do |
|---|---|---|
| Core Domain | Product Catalog | Quan ly hang hoa, danh muc, bien the san pham. Day la trung tam cua e-commerce. |
| Core Domain | Order | Tao don, giu lich su mua hang, trang thai don. Day la dong tien nghiep vu chinh. |
| Core Domain | AI / Recommendation / Consultation | Tao loi the khac biet bang goi y, phan tich hanh vi va tu van san pham. |
| Supporting Domain | Cart | Ho tro qua trinh mua hang truoc khi tao order. |
| Supporting Domain | Inventory | Dam bao ton kho, reserve/release/deduct hang. |
| Supporting Domain | Payment | Xu ly thanh toan va dong bo trang thai voi order. |
| Supporting Domain | Shipping | Quan ly giao hang, tracking, chi phi van chuyen. |
| Supporting Domain | Coupon | Quan ly khuyen mai va ma giam gia. |
| Supporting Domain | Review | Danh gia san pham, verified purchase. |
| Generic Domain | Auth / Identity | Dang ky, dang nhap, JWT, profile nguoi dung. |
| Generic Domain | API Gateway | Routing, proxy, RBAC, identity translation. |
| Generic Domain | Service Registry | Service discovery qua Redis. |
| Generic Domain | Frontend | Presentation layer, khong nen chua domain logic cot loi. |

## 2. Bounded Context va Ubiquitous Language

| Bounded Context | Microservice | Ubiquitous Language | Trach nhiem chinh |
|---|---|---|---|
| API Gateway Context | `api_gateway` | Route, Public Path, Admin Path, Service Token, Session Id, Proxy | Entry point, decode JWT, enforce RBAC, forward identity headers. |
| Auth Context | `auth_service` | User, Profile, Credential, Access Token, Refresh Token, Role | Dang ky, dang nhap, phat JWT, quan ly profile. |
| Product Catalog Context | `product_service` | Product, Category, SubCategory, Computer, Mobile, Clothes, Price, Stock | Quan ly catalog va thong tin san pham. |
| Cart Context | `cart_service` | Cart, CartItem, Guest Cart, User Cart, Merge Cart, Price At Add | Luu gio hang user/guest va snapshot gia luc them vao gio. |
| Order Context | `order_service` | Order, OrderItem, Pending, Confirmed, Delivered, Cancelled, Refunded | Tao don tu cart, luu snapshot san pham, quan ly trang thai don. |
| Inventory Context | `inventory_service` | InventoryItem, Quantity Available, Quantity Reserved, StockMovement, Reserve, Release, Deduct | Quan ly so luong ton kho va lich su thay doi stock. |
| Payment Context | `payment_service` | Payment, Method, Transaction, Refund, Completed, Failed | Tao payment, xu ly refund, cap nhat order khi thanh toan thanh cong. |
| Shipping Context | `shipping_service` | ShippingMethod, Shipment, TrackingNumber, TrackingEvent, Carrier | Tinh phi ship, tao shipment, cap nhat tracking. |
| Coupon Context | `coupon_service` | Coupon, Discount Type, Discount Value, Usage Limit, CouponUsage | Validate/apply coupon, ghi nhan lich su su dung. |
| Review Context | `review_service` | Review, Rating, Comment, Verified Purchase, Approval | Tao va quan ly review, xac minh nguoi dung da mua hang. |
| AI Context | `ai_service` | BehaviorEvent, UserBehaviorProfile, Recommendation, Similarity, ChatSession, RAG, Knowledge Graph | Ghi nhan hanh vi, goi y san pham, tu van bang LLM/RAG/Graph QA. |
| Service Registry Context | `service_registry` | Register, Discover, Heartbeat, TTL, Service URL | Dang ky va tim endpoint cua service. |

### 2.1 Port va database cua tung microservice

| Bounded Context | Microservice / Container | App port | Database / Storage | Database name / endpoint | Ghi chu |
|---|---|---:|---|---|---|
| API Gateway Context | `api-gateway` | 8000 | Khong dung database rieng | N/A | Proxy request, RBAC, service discovery qua Redis. |
| Auth Context | `auth-service` | 8001 | PostgreSQL | `ecommerce_auth` | Cau hinh qua `AUTH_DB_NAME`. |
| Product Catalog Context | `product-service` | 8002 | PostgreSQL | `ecommerce_products` | Cau hinh qua `PRODUCT_DB_NAME`. |
| Cart Context | `cart-service` | 8003 | MySQL | `ecommerce_cart` | Cau hinh qua `CART_DB_NAME`. |
| AI Context | `ai-service` | 8004 | PostgreSQL, Neo4j, ChromaDB | `ecommerce_ai`; Neo4j `bolt://neo4j:7687`; ChromaDB `ai_service/kb/chroma_db` | PostgreSQL luu behavior/recommendation/chat; Neo4j va ChromaDB phuc vu RAG/Graph QA. |
| Order Context | `order-service` | 8005 | PostgreSQL | `ecommerce_orders` | Cau hinh qua `ORDER_DB_NAME`. |
| Payment Context | `payment-service` | 8006 | PostgreSQL | `ecommerce_payments` | Cau hinh qua `PAYMENT_DB_NAME`. |
| Inventory Context | `inventory-service` | 8007 | MySQL | `ecommerce_inventory` | Cau hinh qua `INVENTORY_DB_NAME`. |
| Notification Context | `notification-service` | 8008 | Chua co source trong repo | `ecommerce_notifications` trong `.env.example` | Co khai bao trong `docker-compose.yml` va env, nhung chua co thu muc `notification_service`. |
| Review Context | `review-service` | 8009 | PostgreSQL | `ecommerce_reviews` | Cau hinh qua `REVIEW_DB_NAME`. |
| Shipping Context | `shipping-service` | 8010 | MySQL | `ecommerce_shipping` | Cau hinh qua `SHIPPING_DB_NAME`. |
| Coupon Context | `coupon-service` | 8011 | PostgreSQL | `ecommerce_coupons` | Cau hinh qua `COUPON_DB_NAME`. |
| Frontend Context | `frontend` | 8080 | Khong dung database rieng | N/A | Django frontend/presentation layer, goi API Gateway. |
| Service Registry Context | `redis` / `service_registry` | 6379 | Redis | `redis:6379` | Luu service registration/heartbeat TTL. |
| Knowledge Graph | `neo4j` | 7474, 7687 | Neo4j | `neo4j:7474` UI, `neo4j:7687` Bolt | External storage cho AI Context. |

Ghi chu chung: cac service Django doc bien moi truong tu `.env`. PostgreSQL dang dung `POSTGRES_PORT`, MySQL dung `MYSQL_PORT`, va host database dung `DB_HOST` khi chay trong Docker/local.

## 3. Aggregate, Entity va Value Object

### 3.1 Auth Context

| Loai | Thanh phan | Ghi chu |
|---|---|---|
| Aggregate Root | `CustomUser` | Dai dien tai khoan nguoi dung. |
| Entity | Profile fields | `email`, `phone`, `address` dang nam trong `CustomUser`. |
| Value Object | JWT Claims | `user_id`, `role`, `is_staff`, `is_superuser`, thoi han token. |
| Domain Service | Token issuing / authentication | Dang nam trong serializer/view cua Django SimpleJWT. |

### 3.2 Product Catalog Context

| Loai | Thanh phan | Ghi chu |
|---|---|---|
| Aggregate Root | `Product` | San pham la doi tuong trung tam cua catalog. |
| Entity | `Category`, `SubCategory` | Phan loai san pham, co rang buoc subcategory thuoc category. |
| Entity mo rong | `ComputerProduct`, `MobileProduct`, `ClothesProduct` | Chi tiet theo loai san pham, quan he one-to-one voi `Product`. |
| Value Object | Price, Stock, Slug, ImageUrl | Hien tai la field trong model, co the tach thanh VO neu domain phuc tap hon. |
| Invariant | Subcategory phai thuoc Category da chon | Duoc enforce trong `Product.clean()`. |

### 3.3 Cart Context

| Loai | Thanh phan | Ghi chu |
|---|---|---|
| Aggregate Root | `Cart` | Gio hang cua user da dang nhap hoac guest session. |
| Entity | `CartItem` | Item trong gio, tham chieu product bang `product_id`. |
| Value Object | `price_at_add` | Snapshot gia luc them vao gio, bao ve Cart khoi thay doi gia live cua Product. |
| Domain Service | Merge Cart | Hop nhat guest cart vao user cart sau khi dang nhap. |
| Invariant | Mot cart phai thuoc user hoac session | Can duoc giu o application/domain service. |

### 3.4 Order Context

| Loai | Thanh phan | Ghi chu |
|---|---|---|
| Aggregate Root | `Order` | Quan ly lifecycle cua don hang. |
| Entity | `OrderItem` | Dung snapshot `product_name`, `unit_price`, `subtotal`. |
| Value Object | OrderStatus, Address, Money | Hien tai la field; nen coi la VO trong thiet ke DDD. |
| Domain Service | Create Order From Cart | Lay cart, lay product name, tinh total, tao order items, clear cart. |
| Invariant | Total amount bang tong subtotal cua order items | Can enforce khi tao/cap nhat order. |

### 3.5 Inventory Context

| Loai | Thanh phan | Ghi chu |
|---|---|---|
| Aggregate Root | `InventoryItem` | Ton kho theo tung `product_id`. |
| Entity | `StockMovement` | Lich su restock/reserve/release/deduct/adjustment. |
| Value Object | Quantity, MovementType, ReferenceId | Dien giai thay doi ton kho. |
| Domain Service | Reserve, Release, Deduct | Dam bao khong reserve qua so luong co san. |
| Invariant | `quantity_available` va `quantity_reserved` khong duoc am | Nen enforce trong service layer/model method. |

### 3.6 Payment Context

| Loai | Thanh phan | Ghi chu |
|---|---|---|
| Aggregate Root | `Payment` | Thanh toan cho mot `order_id`. |
| Value Object | PaymentStatus, PaymentMethod, Money, TransactionId | Cac field domain cua payment. |
| Domain Service | Process Payment, Refund Payment | Gia lap xu ly thanh toan, cap nhat status, goi Order Service. |
| Invariant | Payment completed moi cap nhat Order thanh confirmed | Hien tai dang goi sync sang Order. |

### 3.7 Shipping Context

| Loai | Thanh phan | Ghi chu |
|---|---|---|
| Aggregate Root | `Shipment` | Dai dien mot lan giao hang cho order. |
| Entity | `ShippingMethod`, `TrackingEvent` | Phuong thuc giao hang va lich su tracking. |
| Value Object | TrackingNumber, ShippingStatus, Address, Weight, Cost | Mo ta van chuyen. |
| Domain Service | Calculate Shipping Cost, Update Shipment Status | Tinh phi va cap nhat tracking. |

### 3.8 Coupon Context

| Loai | Thanh phan | Ghi chu |
|---|---|---|
| Aggregate Root | `Coupon` | Quan ly dieu kien va trang thai ma giam gia. |
| Entity | `CouponUsage` | Lich su dung coupon theo user/order. |
| Value Object | DiscountType, DiscountValue, ValidPeriod, ApplicableScope | Dieu kien ap dung coupon. |
| Domain Service | Validate Coupon, Apply Coupon | Kiem tra hieu luc, usage limit, min order amount, product/category scope. |
| Invariant | Mot coupon khong duoc dung trung cho cung user/order | Dang co `unique_together`. |

### 3.9 Review Context

| Loai | Thanh phan | Ghi chu |
|---|---|---|
| Aggregate Root | `Review` | Danh gia cua user cho product. |
| Value Object | Rating, ReviewStatus, VerifiedPurchase | Rating tu 1 den 5, approved/verified flags. |
| Domain Service | Check Verified Purchase | Goi Order Service va convert ket qua thanh boolean. |
| Invariant | Review hop le can co product_id, user_id, rating hop le | Nen enforce trong serializer/model validation. |

### 3.10 AI Context

| Subdomain | Aggregate Root / Entity | Ghi chu |
|---|---|---|
| Behavior | `BehaviorEvent`, `UserBehaviorProfile` | Ghi nhan hanh vi va suy luan intent/purchase likelihood. |
| Recommendation | `ProductSimilarity`, `ProductCoOccurrence`, `RecommendationLog` | Read model va log cho goi y san pham. |
| Consultation | `ChatSession`, `ChatMessage` | Luu hoi thoai tu van san pham. |
| Knowledge Base | ChromaDB, Neo4j | External read model cho RAG va Graph QA. |

## 4. Context Map

### 4.1 Shared Kernel

| Shared Kernel | File | Context dung chung |
|---|---|---|
| JWT utils | `shared/jwt_utils.py` | Gateway va cac service can decode token. |
| RBAC helpers | `shared/rbac.py` | Gateway, Product, Order, Inventory, Payment, Shipping, Coupon, Review, AI. |
| Service discovery | `service_registry/` | Gateway va cac service goi cheo nhau. |

Luu y DDD: Shared Kernel hien tai kha nhay cam vi thay doi JWT/RBAC co the anh huong nhieu context. Neu he thong lon hon, nen thu hep shared kernel va bien Auth thanh upstream identity provider ro rang.

### 4.2 Customer-Supplier

| Upstream | Downstream | Hop dong / API | Y nghia DDD |
|---|---|---|---|
| Product Catalog | Cart | Lay product va gia hien tai | Cart phu thuoc Product de validate item. |
| Product Catalog | Order | Lay ten/gia san pham | Order snapshot product info de bao toan lich su. |
| Product Catalog | AI | Lay product detail/list | AI enrich ket qua goi y. |
| Cart | Order | Lay cart items, clear cart | Order tao tu gio hang. |
| Order | Payment | Cap nhat order status | Payment bao thanh toan thanh cong/refund. |
| Order | Review | Kiem tra lich su mua hang | Review xac minh verified purchase. |
| Inventory | Order | Reserve/release/deduct stock | Nen tich hop chat hon vao workflow dat hang. |
| Shipping | Order | Shipment id/tracking | Shipping quan ly giao hang cho order. |

### 4.3 Anti-Corruption Layer

| ACL | Vi tri | Chuyen doi model |
|---|---|---|
| Gateway Identity ACL | `api_gateway/proxy/middleware.py`, `api_gateway/proxy/views.py` | JWT/cookie/service token -> `X-User-Id`, `X-Role`, `X-Session-Id`, `X-Service-Token`. |
| Cart-Product ACL | `cart_service/carts/views.py` | Product price -> `CartItem.price_at_add`. |
| Order-Product ACL | `order_service/orders/views.py` | Product name/price -> `OrderItem.product_name`, `OrderItem.unit_price`. |
| Review-Order ACL | `review_service/reviews/views.py` | Order history -> `Review.is_verified_purchase`. |
| AI-Product ACL | `ai_service/recommendations/*`, `ai_service/kb/indexer.py` | Product API response -> recommendation/read model/knowledge base. |

## 5. De xuat module layer theo Tactical DDD

Moi bounded context hien tai dang theo style Django app truyen thong. Neu muon tach DDD ro hon, co the chuan hoa moi service theo cau truc:

```text
<service>/
  <context>/
    domain/
      entities.py
      value_objects.py
      services.py
      events.py
      repositories.py
    application/
      commands.py
      handlers.py
      queries.py
      dto.py
    infrastructure/
      django_models.py
      repositories.py
      http_clients.py
    interfaces/
      serializers.py
      views.py
      urls.py
```

Mapping de refactor dan:

| Context | Nen dua vao `domain` | Nen dua vao `application` | Nen dua vao `infrastructure` |
|---|---|---|---|
| Product | Product, Category, ProductDetail, Price rules | Create/update product, category management | Django ORM, serializers, views. |
| Cart | Cart, CartItem, PriceAtAdd, merge rule | Add/update/remove/merge cart | Product HTTP client, Django ORM. |
| Order | Order, OrderItem, OrderStatus transition | Create order from cart, cancel order, update status | Cart/Product/Inventory clients, Django ORM. |
| Inventory | InventoryItem, StockMovement, stock invariants | Reserve/release/deduct/restock commands | Django ORM. |
| Payment | Payment, PaymentStatus, refund rules | Process payment, refund payment | Payment provider client, Order client. |
| Shipping | Shipment, TrackingEvent, cost policy | Calculate shipping, create shipment, update tracking | Carrier APIs, Django ORM. |
| Coupon | Coupon, CouponUsage, discount policy | Validate/apply coupon | Django ORM. |
| Review | Review, Rating, verified purchase policy | Create review, approve review | Order client, Django ORM. |
| AI | Behavior profile, recommendation policies, chat session | Track behavior, recommend, chat | ChromaDB, Neo4j, LLM providers, Product client. |

## 6. Domain Events nen co

Hien tai he thong chu yeu giao tiep REST dong bo. Theo DDD/microservices, cac su kien sau nen duoc them neu bo sung message broker:

| Event | Publisher | Subscriber |
|---|---|---|
| `cart.item_added` | Cart | AI Behavior, Recommendation |
| `order.created` | Order | Inventory, Payment, Notification, AI |
| `inventory.reserved` | Inventory | Order |
| `inventory.reserve_failed` | Inventory | Order |
| `payment.completed` | Payment | Order, Notification, Shipping |
| `payment.refunded` | Payment | Order, Notification, Inventory |
| `shipment.created` | Shipping | Order, Notification |
| `shipment.delivered` | Shipping | Order, Notification, Review |
| `review.created` | Review | Product/AI Recommendation |
| `coupon.applied` | Coupon | Order, AI Behavior |

## 7. Luong nghiep vu chinh theo DDD

### 7.1 Browse va add to cart

1. Client goi API Gateway.
2. Gateway dich JWT/session thanh identity header.
3. Product Context tra danh sach san pham.
4. Cart Context nhan lenh add item.
5. Cart goi Product de validate product va lay price.
6. Cart luu `CartItem.price_at_add` lam snapshot.
7. AI Context co the ghi nhan `product_view` hoac `add_to_cart`.

### 7.2 Checkout va tao order

1. User gui request tao order.
2. Order Context lay cart tu Cart Context.
3. Order Context lay product detail tu Product Context.
4. Order tao `Order` va `OrderItem` voi snapshot ten/gia.
5. Order clear cart.
6. Theo thiet ke nen co tiep: Order publish `order.created`, Inventory reserve stock, Payment xu ly thanh toan.

### 7.3 Payment

1. Payment Context tao `Payment` cho `order_id`.
2. Payment xu ly transaction va chuyen status thanh `completed`.
3. Payment goi Order Context de cap nhat order thanh `confirmed`.
4. Theo thiet ke nen publish `payment.completed` de Shipping/Notification/Inventory phan ung bat dong bo.

### 7.4 Review verified purchase

1. User tao review cho product.
2. Review Context goi Order Context de kiem tra user da mua product chua.
3. Review Context khong nhan Order model truc tiep, chi nhan ket qua boolean.
4. Review luu `is_verified_purchase`.

## 8. Diem can hoan thien de dung DDD hon

| Van de hien tai | Tac dong | Huong cai thien |
|---|---|---|
| Domain logic con nam nhieu trong Django views | Kho test, kho tai su dung, domain bi tron voi HTTP | Tach application service va domain service. |
| Nhieu field dang la primitive | De sai logic voi money/status/quantity | Tao Value Object cho Money, Quantity, Status, Address. |
| Giao tiep giua service chu yeu la REST sync | Coupling thoi gian, loi lan truyen khi service down | Them domain events va message broker. |
| Shared Kernel JWT/RBAC kha rong | Thay doi shared code gay anh huong toan he thong | Thu hep shared kernel, chuan hoa contract Auth. |
| Inventory chua la buoc bat buoc trong checkout | Co nguy co oversell | Order workflow nen reserve stock truoc khi confirm order. |
| Notification service duoc khai bao nhung source chua co | Context map co thanh phan chua hien thuc | Bo sung service hoac ghi ro la future context. |
| AI phu thuoc Product API runtime | Recommendation co the cham khi Product cham | Dung read model/cache product trong AI Context. |

## 9. Tom tat phan ra DDD

He thong co 11 bounded context da co source code chinh: API Gateway, Auth, Product, Cart, AI, Order, Payment, Inventory, Review, Shipping, Coupon. `notification-service` dang xuat hien trong cau hinh nhung chua co source rieng.

Phan thiet ke hien tai da co nen tang DDD kha ro: moi bounded context co database/model rieng, cac context giao tiep qua API, Cart/Order/Review da co ACL de tranh phu thuoc truc tiep vao model ben ngoai. De tien gan DDD hon, buoc quan trong nhat la tach domain logic ra khoi views, them value objects/invariants, va chuyen cac luong Order-Payment-Inventory-Shipping sang domain events/Saga.
