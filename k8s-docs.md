# 4.8 Triển khai Kubernetes (Optional)

Dù môi trường phát triển local sử dụng Docker Compose, hệ thống đã chuẩn bị đầy đủ
cấu hình Kubernetes cho môi trường production. Toàn bộ 13 service đều có file
Deployment và Service riêng trong thư mục `k8s/`, được sinh tự động từ script
`generate_k8s.py`. Các Docker image được public trên DockerHub với prefix
`<your-dockerhub-username>/ecommerce-<service-name>:latest`.

```
k8s/
├── namespace.yaml          # Namespace: ecommerce
├── configmap.yaml          # Biến môi trường không nhạy cảm
├── secret.yaml             # Biến môi trường nhạy cảm (JWT key, DB password)
├── redis.yaml              # StatefulSet + Service
├── neo4j.yaml              # StatefulSet + Service + PVC 5Gi
├── api-gateway.yaml        # Deployment (x2) + Service LoadBalancer :8000
├── frontend.yaml           # Deployment (x2) + Service LoadBalancer :80→8080
├── auth-service.yaml       # Deployment (x2) + Service ClusterIP :8001
├── product-service.yaml    # Deployment (x2) + Service ClusterIP :8002
├── cart-service.yaml       # Deployment (x2) + Service ClusterIP :8003
├── order-service.yaml      # Deployment (x2) + Service ClusterIP :8005
├── payment-service.yaml    # Deployment (x2) + Service ClusterIP :8006
├── inventory-service.yaml  # Deployment (x2) + Service ClusterIP :8007
├── notification-service.yaml # Deployment (x1) + Service ClusterIP :8008
├── review-service.yaml     # Deployment (x2) + Service ClusterIP :8009
├── shipping-service.yaml   # Deployment (x1) + Service ClusterIP :8010
├── coupon-service.yaml     # Deployment (x1) + Service ClusterIP :8011
├── ai-service.yaml         # Deployment (x1) + Service ClusterIP :8004
└── ingress.yaml            # Nginx Ingress: / → frontend, /api/ → api-gateway
```

## 4.8.1 Namespace và cấu hình chung

Toàn bộ hệ thống chạy trong namespace `ecommerce` để cô lập với các ứng dụng khác
trong cùng cluster. Biến môi trường được quản lý qua hai tầng: `ConfigMap` cho các giá
trị không nhạy cảm (host, port, URL nội bộ) và `Secret` cho các giá trị nhạy cảm (JWT
key, mật khẩu database):

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ecommerce
```

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ecommerce-secret
  namespace: ecommerce
type: Opaque
stringData:
  JWT_SECRET_KEY: "change-me"
  SERVICE_AUTH_TOKEN: "change-me"
  POSTGRES_USER: "postgres"
  POSTGRES_PASSWORD: "change-me"
  NEO4J_PASSWORD: "change-me"
```

## 4.8.2 Deployment

Mỗi service có một file Deployment định nghĩa Pod template, resource limits, và health
probe. Ví dụ với **API Gateway** (entry point của toàn hệ thống):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: ecommerce
  labels:
    app: api-gateway
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: <your-dockerhub-username>/ecommerce-api-gateway:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: ecommerce-config
        - secretRef:
            name: ecommerce-secret
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 15
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
```

AI Service được cấp tài nguyên cao hơn (`memory: 2Gi`, `cpu: 1000m`) và có thời gian
`initialDelaySeconds: 60` vì cần load model TF/Keras và kết nối Neo4j khi khởi động.

Redis và Neo4j sử dụng **StatefulSet** thay vì Deployment để đảm bảo stable network
identity và persistent storage:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: neo4j
  namespace: ecommerce
spec:
  serviceName: neo4j
  replicas: 1
  ...
  volumeClaimTemplates:
  - metadata:
      name: neo4j-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 5Gi
```

## 4.8.3 Service

Các internal service sử dụng kiểu **ClusterIP** để giao tiếp nội bộ trong cluster. Chỉ
`frontend` và `api-gateway` được expose ra ngoài qua kiểu **LoadBalancer**:

```yaml
# Internal service — ClusterIP (ví dụ: auth-service)
apiVersion: v1
kind: Service
metadata:
  name: auth-service
  namespace: ecommerce
spec:
  type: ClusterIP
  selector:
    app: auth-service
  ports:
  - port: 8001
    targetPort: 8001
    protocol: TCP
```

```yaml
# External service — LoadBalancer (frontend)
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: ecommerce
spec:
  type: LoadBalancer
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
```

## 4.8.4 Ingress

Nginx Ingress Controller định tuyến traffic từ một địa chỉ IP public duy nhất: path `/`
chuyển đến `frontend` (Django template), path `/api/` chuyển đến `api-gateway`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ecommerce-ingress
  namespace: ecommerce
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 80
      - path: /api/
        pathType: Prefix
        backend:
          service:
            name: api-gateway
            port:
              number: 8000
```

## 4.8.5 Quy trình deploy lên Kubernetes

**Bước 1 — (Tùy chọn) Sinh lại YAML từ script:**

```bash
python generate_k8s.py --dockerhub-user <your-dockerhub-username>
```

**Bước 2 — Build và push image lên DockerHub:**

```bash
docker compose build

# Tag và push từng service
docker tag ecommercestore-api-gateway <your-dockerhub-username>/ecommerce-api-gateway:latest
docker push <your-dockerhub-username>/ecommerce-api-gateway:latest

docker tag ecommercestore-frontend <your-dockerhub-username>/ecommerce-frontend:latest
docker push <your-dockerhub-username>/ecommerce-frontend:latest

docker tag ecommercestore-auth-service <your-dockerhub-username>/ecommerce-auth-service:latest
docker push <your-dockerhub-username>/ecommerce-auth-service:latest

docker tag ecommercestore-product-service <your-dockerhub-username>/ecommerce-product-service:latest
docker push <your-dockerhub-username>/ecommerce-product-service:latest

docker tag ecommercestore-cart-service <your-dockerhub-username>/ecommerce-cart-service:latest
docker push <your-dockerhub-username>/ecommerce-cart-service:latest

docker tag ecommercestore-order-service <your-dockerhub-username>/ecommerce-order-service:latest
docker push <your-dockerhub-username>/ecommerce-order-service:latest

docker tag ecommercestore-payment-service <your-dockerhub-username>/ecommerce-payment-service:latest
docker push <your-dockerhub-username>/ecommerce-payment-service:latest

docker tag ecommercestore-inventory-service <your-dockerhub-username>/ecommerce-inventory-service:latest
docker push <your-dockerhub-username>/ecommerce-inventory-service:latest

docker tag ecommercestore-notification-service <your-dockerhub-username>/ecommerce-notification-service:latest
docker push <your-dockerhub-username>/ecommerce-notification-service:latest

docker tag ecommercestore-review-service <your-dockerhub-username>/ecommerce-review-service:latest
docker push <your-dockerhub-username>/ecommerce-review-service:latest

docker tag ecommercestore-shipping-service <your-dockerhub-username>/ecommerce-shipping-service:latest
docker push <your-dockerhub-username>/ecommerce-shipping-service:latest

docker tag ecommercestore-coupon-service <your-dockerhub-username>/ecommerce-coupon-service:latest
docker push <your-dockerhub-username>/ecommerce-coupon-service:latest

docker tag ecommercestore-ai-service <your-dockerhub-username>/ecommerce-ai-service:latest
docker push <your-dockerhub-username>/ecommerce-ai-service:latest
```

**Bước 3 — Apply toàn bộ cấu hình Kubernetes:**

```bash
kubectl apply -f k8s/
kubectl get pods -n ecommerce
kubectl get services -n ecommerce
```

**Bước 4 — Lấy địa chỉ IP public:**

```bash
kubectl get ingress -n ecommerce
# Hoặc lấy EXTERNAL-IP của LoadBalancer
kubectl get svc frontend -n ecommerce
```

Sau khi deploy thành công, URL của trang web không còn là `localhost` mà là địa chỉ IP
public được cấp bởi cloud provider (ví dụ: `http://203.0.113.42`), mọi người đều có
thể truy cập mà không cần cài đặt gì thêm.

---

# 4.9 Logging và Monitoring

Hệ thống sử dụng Docker Compose Profile `monitoring` để đóng gói toàn bộ stack giám
sát — chỉ khởi động khi cần thiết, không ảnh hưởng đến hiệu năng môi trường phát triển
thông thường.

## 4.9.1 Logging — ELK Stack

Elasticsearch đảm nhận lưu trữ và index toàn bộ log từ các service, trong khi Kibana
cung cấp giao diện trực quan hóa và tìm kiếm log theo thời gian thực:

```yaml
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.1
  profiles: ["monitoring"]
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
  ports:
    - "9200:9200"

kibana:
  image: docker.elastic.co/kibana/kibana:8.11.1
  profiles: ["monitoring"]
  ports:
    - "5601:5601"
  environment:
    - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
```

## 4.9.2 Monitoring — Prometheus + Grafana + cAdvisor

cAdvisor thu thập metrics từng container theo thời gian thực, Prometheus scrape và lưu
trữ time-series metrics, Grafana trực quan hóa CPU, RAM và network của từng service
qua dashboard:

```yaml
prometheus:
  image: prom/prometheus:v2.45.0
  profiles: ["monitoring"]
  ports:
    - "9090:9090"
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana:10.0.3
  profiles: ["monitoring"]
  ports:
    - "3000:3000"

cadvisor:
  image: gcr.io/cadvisor/cadvisor:v0.47.0
  profiles: ["monitoring"]
  ports:
    - "8090:8080"   # tránh conflict với frontend :8080
```

Prometheus được cấu hình scrape metrics từ cAdvisor mỗi 15 giây:

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

## 4.9.3 Khởi động và kiểm tra

Toàn bộ monitoring stack được khởi động bằng lệnh:

```bash
docker compose --profile monitoring up -d
```

Grafana được truy cập tại `http://localhost:3000` với tài khoản mặc định `admin/admin`.
Sau khi cấu hình Prometheus làm data source tại URL `http://prometheus:9090`, dashboard
**Docker & System Monitoring** (ID: 193) cung cấp toàn bộ metrics CPU, RAM và network
của từng container. Kibana được truy cập tại `http://localhost:5601` để tìm kiếm và phân
tích log từ toàn bộ hệ thống.

---

# 4.10 Đánh giá hệ thống

## 4.10.1 Hiệu năng

Hệ thống được đánh giá theo hai tiêu chí hiệu năng chính. **Response time** được theo
dõi qua API Gateway access log và Grafana dashboard, phản ánh thời gian xử lý thực tế
của từng request xuyên qua các service. **Throughput** được đánh giá thông qua số lượng
request mà hệ thống có thể xử lý đồng thời, đặc biệt trong các tình huống tải cao khi
nhiều service hoạt động song song.

API Gateway được cấu hình timeout riêng biệt: **300 giây** cho AI Service (do phải
load model và thực hiện inference) và **10 giây** cho tất cả các service còn lại — giúp
cân bằng giữa tính năng AI nặng và các API thương mại thông thường.

## 4.10.2 Khả năng mở rộng

Kiến trúc microservices cho phép mở rộng từng service độc lập theo nhu cầu thực tế.
Trong giai đoạn cao điểm, `product-service` và `order-service` (Core Domain) có thể
được scale out riêng lẻ mà không cần mở rộng toàn bộ hệ thống:

```bash
# Tăng số replica của product-service lên 5
kubectl scale deployment product-service --replicas=5 -n ecommerce

# Hoặc bật Horizontal Pod Autoscaler
kubectl autoscale deployment product-service \
  --cpu-percent=70 --min=2 --max=10 -n ecommerce
```

Service Registry (Redis-based, 30s TTL heartbeat) đảm bảo API Gateway tự động phát
hiện các instance mới mà không cần restart hay cấu hình lại.

## 4.10.3 Ưu điểm

Hệ thống thể hiện rõ những ưu điểm nổi bật của kiến trúc Microservices trong thực tế:

- **Tính linh hoạt cao:** Từng service được cập nhật, thay thế hoặc mở rộng độc lập mà
  không ảnh hưởng đến phần còn lại.
- **Khả năng cô lập lỗi:** Cơ chế `try-except` cho REST calls đảm bảo hệ thống tiếp
  tục hoạt động ngay cả khi một service gặp sự cố (graceful degradation).
- **Anti-Corruption Layer (ACL):** Bốn lớp ACL (Review←Order, Cart←Product,
  Order←Product, Gateway←Auth) ngăn model của một bounded context "nhiễm" sang
  context khác, giữ cho từng service có domain model sạch và tự chủ.
- **Sẵn sàng production:** Toàn bộ 13 service có cấu hình Kubernetes (Deployment,
  Service, liveness/readiness probe, resource limits) và script `generate_k8s.py` để
  tái sinh YAML khi cần thay đổi hàng loạt.

## 4.10.4 Nhược điểm

Bên cạnh ưu điểm, kiến trúc này đặt ra một số thách thức trong thực tế:

- **Độ phức tạp triển khai tăng cao:** Phải quản lý đồng thời 13 service với các
  database (PostgreSQL, MySQL, Redis, Neo4j, ChromaDB), cấu hình và phiên bản thư
  viện khác nhau — đòi hỏi quy trình CI/CD chặt chẽ.
- **Không có message broker:** Luồng `Order → Clear Cart` và `Payment → Update Order`
  hiện là synchronous HTTP call. Nếu Cart Service hoặc Order Service tạm thời down,
  dữ liệu có thể rơi vào trạng thái không nhất quán. Giải pháp dài hạn là thêm async
  event queue (`order.created` → Cart consumer).
- **Inventory chưa tích hợp Order:** Chưa có quy trình `reserve stock` trước khi tạo
  Order, dẫn đến nguy cơ oversell khi nhiều người cùng đặt hàng sản phẩm cuối cùng.
- **Debug khó hơn:** Lỗi trong luồng multi-service đòi hỏi distributed tracing và
  logging tập trung (ELK stack) để theo dõi toàn bộ hành trình của một request xuyên
  qua nhiều service — phức tạp hơn so với monolith.
- **Shared Kernel rủi ro:** Thay đổi `JWT_SECRET_KEY` buộc phải redeploy đồng thời
  toàn bộ 13 service. Giải pháp lý tưởng là chuyển sang asymmetric JWT (public/private
  key), các service chỉ cần public key để verify.
