

## Chương 2: Phát triển Hệ E-Commerce Microservices

### 2.1 Xác định yêu cầu

#### 2.1.1 Functional Requirements

- Quản lý sản phẩm (đa domain: book, electronics, fashion)
- Quản lý người dùng (admin, staff, customer)
- Giỏ hàng (cart)
- Đặt hàng (order)
- Thanh toán (payment)
- Giao hàng (shipping)
- Tìm kiếm và gợi ý sản phẩm

#### 2.1.2 Non-functional Requirements

- **Scalability:** scale từng service độc lập
- **High Availability:** hệ thống luôn sẵn sàng
- **Security:** JWT, authentication
- **Maintainability:** dễ bảo trì

---

### 2.2 Phân rã hệ thống theo DDD

#### 2.2.1 Bounded Context

- User Context → `user-service`
- Product Context → `product-service`
- Cart Context → `cart-service`
- Order Context → `order-service`
- Payment Context → `payment-service`
- Shipping Context → `shipping-service`

#### 2.2.2 Nguyên tắc

- Mỗi context = 1 database riêng
- Giao tiếp qua REST API

---

### 2.3 Thiết kế Product Service (Django)

#### 2.3.1 Phân loại sản phẩm

- **Book:** giáo trình, tiểu thuyết
- **Electronics:** mobile, laptop, tủ lạnh, điều hòa
- **Fashion:** áo, quần, giày

#### 2.3.2 Model tổng quát

```python
class Category(models.Model):
    name = models.CharField(max_length=100)

class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.FloatField()
    stock = models.IntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
```

#### 2.3.3 Chi tiết theo domain

**Book**

```python
class Book(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    author = models.CharField(max_length=255)
    publisher = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20)
```

**Electronics**

```python
class Electronics(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    brand = models.CharField(max_length=100)
    warranty = models.IntegerField()
```

**Fashion**

```python
class Fashion(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=50)
```

#### 2.3.4 API

```
GET  /products/
POST /products/
GET  /products/{id}
```

---

### 2.4 Thiết kế User Service (Django)

#### 2.4.1 Phân loại người dùng

- **Admin:** toàn quyền hệ thống
- **Staff:** xử lý đơn hàng, vận hành
- **Customer:** mua hàng

#### 2.4.2 Model

```python
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('customer', 'Customer'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
```

#### 2.4.3 Phân quyền (RBAC)

- **Admin:** CRUD toàn bộ
- **Staff:** xử lý order, shipping
- **Customer:** mua hàng, xem sản phẩm

#### 2.4.4 API

```
POST /auth/register
POST /auth/login
GET  /users/
```

---

### 2.5 Thiết kế Cart Service

#### 2.5.1 Model

```python
class Cart(models.Model):
    user_id = models.IntegerField()

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product_id = models.IntegerField()
    quantity = models.IntegerField()
```

#### 2.5.2 Logic

- Add product vào cart
- Update số lượng
- Remove item

#### 2.5.3 API

```
POST   /cart/add
GET    /cart/
DELETE /cart/remove
```

---

### 2.6 Thiết kế Order Service

#### 2.6.1 Model

```python
class Order(models.Model):
    user_id = models.IntegerField()
    total_price = models.FloatField()
    status = models.CharField(max_length=50)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product_id = models.IntegerField()
    quantity = models.IntegerField()
```

#### 2.6.2 Workflow

- Tạo order từ cart
- Gửi request sang payment-service
- Sau khi thanh toán → shipping

---

### 2.7 Thiết kế Payment Service

#### 2.7.1 Model

```python
class Payment(models.Model):
    order_id = models.IntegerField()
    amount = models.FloatField()
    status = models.CharField(max_length=50)
```

#### 2.7.2 Trạng thái

- Pending
- Success
- Failed

#### 2.7.3 API

```
POST /payment/pay
GET  /payment/status
```

---

### 2.8 Thiết kế Shipping Service

#### 2.8.1 Model

```python
class Shipment(models.Model):
    order_id = models.IntegerField()
    address = models.TextField()
    status = models.CharField(max_length=50)
```

#### 2.8.2 Trạng thái

- Processing
- Shipping
- Delivered

#### 2.8.3 API

```
POST /shipping/create
GET  /shipping/status
```

---

### 2.9 Luồng hệ thống tổng thể

1. User đăng nhập (user-service)
2. Xem sản phẩm (product-service)
3. Thêm vào giỏ hàng (cart-service)
4. Tạo đơn hàng (order-service)
5. Thanh toán (payment-service)
6. Giao hàng (shipping-service)

---

### 2.10 Hướng dẫn thực hành

#### 2.10.1 Mục tiêu

Sinh viên cần:

- Thiết kế Class Diagram bằng Visual Paradigm (VP)
- Xây dựng database cho từng microservice
- Mapping từ Class Diagram → Database

#### 2.10.2 Hướng dẫn vẽ Class Diagram bằng Visual Paradigm

**Bước 1: Xác định lớp (Classes)**

Product Service: `Product`, `Category`, `Book`, `Electronics`, `Fashion`

User Service: `User`, `Role`

Order Service: `Order`, `OrderItem`

**Bước 2: Xác định thuộc tính**

Ví dụ lớp Product:
- `id: int`
- `name: string`
- `price: float`
- `stock: int`

**Bước 3: Xác định quan hệ (Relationships)**

- Association: `Product → Category`
- Inheritance: `Book`, `Electronics`, `Fashion` kế thừa `Product`
- Composition: `Order` chứa `OrderItem`

**Ký hiệu UML**

- `1..*` (one-to-many)
- `1..1` (one-to-one)

**Yêu cầu bài nộp**

- Export sơ đồ từ VP (PNG/PDF)
- Có đầy đủ class + relationship

#### 2.10.3 Mapping Class Diagram sang Database

**Nguyên tắc**

- Class → Table
- Attribute → Column
- Relationship → Foreign Key

**Ví dụ**

```
Product(id, name, price)
Category(id, name)
=> Product.category_id (FK)
```

#### 2.10.4 Thiết kế Database cho từng Service

**Nguyên tắc Microservices**

- Mỗi service có database riêng với data model tương ứng với Biểu đồ lớp
- Không share database giữa các service

**1. Product Service Database (PostgreSQL)**

Lý do chọn PostgreSQL: hỗ trợ tốt JSON, phù hợp dữ liệu phức tạp.

```sql
CREATE TABLE category (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE product (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255),
    price       FLOAT,
    stock       INT,
    category_id INT REFERENCES category(id)
);

CREATE TABLE book (
    product_id INT PRIMARY KEY,
    author     VARCHAR(255),
    isbn       VARCHAR(20)
);
```

**2. User Service Database (MySQL)**

Lý do chọn MySQL: phổ biến, phù hợp authentication.

```sql
CREATE TABLE user (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100),
    password VARCHAR(255),
    role     VARCHAR(20)
);
```

**3. Cart Service**

```sql
CREATE TABLE cart (
    id      INT PRIMARY KEY,
    user_id INT
);

CREATE TABLE cart_item (
    id         INT PRIMARY KEY,
    cart_id    INT,
    product_id INT,
    quantity   INT
);
```

**4. Order Service**

```sql
CREATE TABLE orders (
    id          INT PRIMARY KEY,
    user_id     INT,
    total_price FLOAT,
    status      VARCHAR(50)
);

CREATE TABLE order_item (
    id         INT PRIMARY KEY,
    order_id   INT,
    product_id INT,
    quantity   INT
);
```

**5. Payment Service**

```sql
CREATE TABLE payment (
    id       INT PRIMARY KEY,
    order_id INT,
    amount   FLOAT,
    status   VARCHAR(50)
);
```

**6. Shipping Service**

```sql
CREATE TABLE shipment (
    id       INT PRIMARY KEY,
    order_id INT,
    address  TEXT,
    status   VARCHAR(50)
);
```

#### 2.10.5 So sánh MySQL vs PostgreSQL

| Tiêu chí           | MySQL    | PostgreSQL |
|--------------------|----------|------------|
| Hiệu năng          | Tốt      | Tốt        |
| JSON               | Trung bình | Mạnh     |
| Quan hệ phức tạp   | Trung bình | Tốt      |

#### 2.10.6 Bài tập

- Vẽ Class Diagram cho toàn bộ hệ thống bằng VP
- Mapping sang database schema
- Triển khai database bằng MySQL/PostgreSQL

#### 2.10.7 Checklist đánh giá

- [ ] Có sơ đồ class đúng UML
- [ ] Có mapping rõ ràng sang database
- [ ] Database tách riêng từng service
- [ ] Có sử dụng cả MySQL và PostgreSQL

---

### 2.11 Kết luận

- Kiến trúc microservices giúp hệ thống linh hoạt
- Django phù hợp xây dựng nhanh
- DDD giúp thiết kế đúng ngay từ đầu

---

## Chương 3: AI Service cho tư vấn sản phẩm

### 3.1 Mục tiêu

Xây dựng hệ thống AI gợi ý sản phẩm dựa trên:

- Hành vi người dùng (click, search, add-to-cart)
- Quan hệ sản phẩm (similarity)
- Ngữ cảnh truy vấn (chatbot)

**Output:**

- Danh sách sản phẩm đề xuất
- Chatbot tư vấn

---

### 3.2 Kiến trúc AI Service

AI Service được thiết kế như một microservice độc lập:

- **Input:** user behavior, query
- **Processing:** LSTM model, Knowledge Graph, RAG
- **Output:** recommendation / chatbot response

---

### 3.3 Thu thập dữ liệu

#### 3.3.1 User Behavior Data

- `user_id`
- `product_id`
- `action` (view, click, add_to_cart)
- `timestamp`

#### 3.3.2 Ví dụ dataset

```
user_id, product_id, action, time
1, 101, view, t1
1, 102, add_to_cart, t2
```

---

### 3.4 Mô hình LSTM (Sequence Modeling)

#### 3.4.1 Ý tưởng

Dự đoán sản phẩm tiếp theo dựa trên chuỗi hành vi.

#### 3.4.2 Model chi tiết

```python
import torch
import torch.nn as nn

class LSTMModel(nn.Module):
    def __init__(self, input_dim=10, hidden_dim=64, output_dim=100):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        return self.fc(out)
```

#### 3.4.3 Training

```python
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters())

for epoch in range(epochs):
    output = model(x)
    loss = criterion(output, y)
    loss.backward()
    optimizer.step()
```

---

### 3.5 Knowledge Graph với Neo4j

#### 3.5.1 Mô hình đồ thị

- **Node:** User, Product
- **Edge:** BUY, VIEW, SIMILAR

#### 3.5.2 Ví dụ Cypher

```cypher
CREATE (u:User {id: 1})
CREATE (p:Product {id: 101})
CREATE (u)-[:BUY]->(p)
```

#### 3.5.3 Truy vấn gợi ý

```cypher
MATCH (u:User {id: 1})-[:BUY]->(p)-[:SIMILAR]->(rec)
RETURN rec
```

---

### 3.6 RAG (Retrieval-Augmented Generation)

#### 3.6.1 Pipeline

- **Retrieve:** Tìm sản phẩm liên quan từ DB / vector DB
- **Generate:** Sinh câu trả lời bằng LLM

#### 3.6.2 Vector Database

- FAISS / ChromaDB
- Embedding từ mô tả sản phẩm

#### 3.6.3 Ví dụ

```python
query = "laptop gaming"
results = vector_db.search(query)
response = LLM.generate(results)
```

---

### 3.7 Kết hợp Hybrid Model

- **LSTM:** dự đoán hành vi
- **Graph:** quan hệ sản phẩm
- **RAG:** hiểu ngữ nghĩa

**Final Recommendation:**

```python
final_score = w1 * lstm + w2 * graph + w3 * rag
```

---

### 3.8 Hai dạng AI Service

#### 3.8.1 Recommendation List

**Use cases**

- Khi search
- Khi add-to-cart

**API**

```
GET /recommend?user_id=1
```

**Output**

```json
[101, 102, 205]
```

#### 3.8.2 Chatbot tư vấn

**Input**

```
"tôi cần laptop giá rẻ"
```

**Pipeline**

- NLP hiểu intent
- Retrieve sản phẩm
- Generate response

**API**

```
POST /chatbot
```

**Output**

```
"Bạn có thể tham khảo Laptop XYZ giá 10 triệu..."
```

---

### 3.9 Triển khai AI Service

#### 3.9.1 Tech stack

- TensorFlow / PyTorch (LSTM)
- Neo4j (Graph)
- FAISS (Vector DB)
- FastAPI (service)

#### 3.9.2 Kiến trúc

- AI service độc lập
- Giao tiếp với các service khác qua API

---

### 3.10 Bài tập

- Xây dựng model LSTM đơn giản
- Tạo graph trong Neo4j
- Implement API recommendation
- Xây dựng chatbot cơ bản

### 3.11 Checklist đánh giá

- [ ] Có pipeline AI rõ ràng
- [ ] Có model (LSTM)
- [ ] Có Graph và RAG
- [ ] Có API hoạt động

### 3.12 Kết luận

- AI giúp cá nhân hóa trải nghiệm
- Kết hợp nhiều mô hình cho hiệu quả cao
- Phù hợp hệ e-commerce hiện đại

---

## Chương 4: Xây dựng hệ thống hoàn chỉnh

### 4.1 Kiến trúc tổng thể

#### 4.1.1 Mô hình hệ thống

Hệ thống được xây dựng theo kiến trúc microservices, mỗi service là một Django project độc lập.

- API Gateway (Nginx)
- `user-service` (Django)
- `product-service` (Django)
- `cart-service` (Django)
- `order-service` (Django)
- `payment-service` (Django)
- `shipping-service` (Django)
- `ai-service` (FastAPI/Python)

#### 4.1.2 Nguyên tắc

- Mỗi service có database riêng
- Giao tiếp qua REST API
- Không truy cập DB của service khác

---

### 4.2 System Architecture

#### 4.2.1 Overview

The proposed system, named **ecom-final**, is designed as a fully distributed microservice-based e-commerce platform. The architecture follows modern enterprise design principles, ensuring scalability, maintainability, and fault isolation.

Each core business domain is implemented as an independent Django REST microservice, while an API Gateway is employed to manage request routing, authentication, and system-wide policies.

#### 4.2.2 Microservice Architecture

The system consists of the following core services:

- **User Service:** Handles authentication, authorization, and user management.
- **Product Service:** Manages product catalog, categories, and inventory.
- **Order Service:** Processes customer orders and order lifecycle.
- **Payment Service:** Handles payment transactions and billing.
- **Notification Service:** Sends asynchronous notifications (email, SMS).

Each service is independently deployable and maintains its own database, following the principle of **database-per-service**.

#### 4.2.3 API Gateway

An API Gateway layer is introduced as the single entry point for all client requests. The gateway is responsible for:

- Routing incoming requests to appropriate microservices
- Handling authentication using JSON Web Tokens (JWT)
- Enforcing rate limiting and security policies
- Logging and monitoring API usage

In this system, the API Gateway is implemented using **NGINX** as a reverse proxy.

#### 4.2.4 Service Communication

The system adopts a hybrid communication strategy:

- **Synchronous communication:** RESTful APIs over HTTP for real-time operations (e.g., order validation).
- **Asynchronous communication:** Message queues (e.g., Redis, RabbitMQ) for event-driven workflows.

For example, when an order is created, an event is published and consumed by the payment and notification services.

#### 4.2.5 Containerization and Deployment

All services are containerized using **Docker** to ensure consistency across environments. The system is orchestrated using **Docker Compose** for development and can be extended to **Kubernetes** for production deployment.

#### 4.2.6 System Structure

```
ecom-final/
├── gateway/
│   └── nginx.conf          # THỂ HIỆN QUAN TRỌNG
├── user-service/           # staff, admin, customer
├── product-service/        # 10 nhóm loại sản phẩm
├── cart-service/
├── order-service/
├── payment-service/
├── ai-service/
└── infrastructure/
    └── docker-compose.yml
```

#### 4.2.7 Design Principles

The proposed architecture adheres to the following principles:

- **Loose Coupling:** Services interact only through APIs or messaging systems.
- **High Cohesion:** Each service encapsulates a single business domain.
- **Scalability:** Services can be scaled independently.
- **Fault Isolation:** Failure in one service does not affect others.

#### 4.2.8 Security Considerations

Security is enforced through:

- JWT-based authentication
- API Gateway validation
- Role-based access control (RBAC)

#### 4.2.9 Discussion

Compared to monolithic architectures, the proposed microservice design significantly improves system flexibility and scalability. However, it introduces additional complexity in deployment and service coordination, which is mitigated through containerization and standardized communication protocols.

---

### 4.3 API Gateway (Nginx)

#### 4.3.1 Vai trò

- Entry point cho toàn hệ thống
- Routing request đến đúng service
- Xử lý authentication

#### 4.3.2 Cấu hình mẫu

```nginx
location /users/ {
    proxy_pass http://user-service:8000;
}

location /products/ {
    proxy_pass http://product-service:8001;
}
```

---

### 4.4 Authentication (JWT)

#### 4.4.1 Cài đặt

```bash
pip install djangorestframework-simplejwt
```

#### 4.4.2 Cấu hình

```python
from rest_framework_simplejwt.views import TokenObtainPairView
```

#### 4.4.3 Luồng

- User login → nhận token
- Gửi token trong header
- Các service verify token

---

### 4.5 Giao tiếp giữa các Service

#### 4.5.1 REST API call

```python
import requests

response = requests.get(
    "http://product-service:8001/products/"
)
```

#### 4.5.2 Best Practice

- Timeout
- Retry
- Circuit breaker (advanced)

---

### 4.6 Docker hóa hệ thống

#### 4.6.1 Dockerfile (Django)

```dockerfile
FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

#### 4.6.2 docker-compose.yml

```yaml
version: '3'
services:
  user-service:
    build: ./user-service
    ports:
      - "8000:8000"

  product-service:
    build: ./product-service
    ports:
      - "8001:8001"
```

---

### 4.7 Luồng hệ thống (End-to-End)

#### 4.7.1 Use case: Mua hàng

1. User login (user-service)
2. Xem sản phẩm (product-service)
3. Add to cart (cart-service)
4. Tạo order (order-service)
5. Thanh toán (payment-service)
6. Giao hàng (shipping-service)

#### 4.7.2 Sequence logic

- `order-service` gọi `payment-service`
- payment success → gọi `shipping-service`

---

### 4.8 Triển khai Kubernetes (Optional)

#### 4.8.1 Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
```

#### 4.8.2 Service

```yaml
kind: Service
spec:
  type: ClusterIP
```

---

### 4.9 Logging và Monitoring

- **Logging:** ELK stack
- **Monitoring:** Prometheus + Grafana

---

### 4.10 Đánh giá hệ thống

#### 4.10.1 Hiệu năng

- Response time
- Throughput

#### 4.10.2 Khả năng mở rộng

- Scale từng service
- Load balancing

#### 4.10.3 Ưu điểm

- Linh hoạt
- Dễ mở rộng

#### 4.10.4 Nhược điểm

- Phức tạp triển khai
- Debug khó

---

### 4.11 Bài tập thực hành

- Triển khai các service bằng Django
- Kết nối qua API
- Docker hóa hệ thống
- Test full flow mua hàng + kết quả tư vấn

### 4.12 Checklist đánh giá

- [ ] Có API Gateway
- [ ] Có JWT Auth
- [ ] Có Docker chạy được
- [ ] Có flow order → payment → shipping

---

## Kết luận

- Microservices phù hợp hệ thống lớn
- DDD giúp thiết kế rõ ràng
- AI nâng cao trải nghiệm người dùng