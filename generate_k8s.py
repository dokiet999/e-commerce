#!/usr/bin/env python3
"""
generate_k8s.py — Auto-generate Kubernetes Deployment + Service YAML files
for all eCommerce microservices.

Usage:
    python generate_k8s.py
    python generate_k8s.py --dockerhub-user myusername
    python generate_k8s.py --output-dir ./k8s
"""
import argparse
import os

SERVICES = [
    # (name, port, replicas, memory_limit, cpu_limit, service_type)
    ("api-gateway",         8000, 2, "512Mi", "500m",  "LoadBalancer"),
    ("frontend",            8080, 2, "512Mi", "500m",  "LoadBalancer"),
    ("auth-service",        8001, 2, "512Mi", "500m",  "ClusterIP"),
    ("product-service",     8002, 2, "512Mi", "500m",  "ClusterIP"),
    ("cart-service",        8003, 2, "512Mi", "500m",  "ClusterIP"),
    ("order-service",       8005, 2, "512Mi", "500m",  "ClusterIP"),
    ("payment-service",     8006, 2, "512Mi", "500m",  "ClusterIP"),
    ("inventory-service",   8007, 2, "512Mi", "500m",  "ClusterIP"),
    ("notification-service",8008, 1, "512Mi", "500m",  "ClusterIP"),
    ("review-service",      8009, 2, "512Mi", "500m",  "ClusterIP"),
    ("shipping-service",    8010, 1, "512Mi", "500m",  "ClusterIP"),
    ("coupon-service",      8011, 1, "512Mi", "500m",  "ClusterIP"),
    ("ai-service",          8004, 1, "2Gi",   "1000m", "ClusterIP"),
]

DEPLOYMENT_TEMPLATE = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: ecommerce
  labels:
    app: {name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
      - name: {name}
        image: {dockerhub_user}/ecommerce-{name}:latest
        ports:
        - containerPort: {port}
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
            memory: "{memory_limit}"
            cpu: "{cpu_limit}"
        livenessProbe:
          httpGet:
            path: /health/
            port: {port}
          initialDelaySeconds: {liveness_delay}
          periodSeconds: {liveness_period}
        readinessProbe:
          httpGet:
            path: /health/
            port: {port}
          initialDelaySeconds: {readiness_delay}
          periodSeconds: 10
"""

SERVICE_TEMPLATE = """\
---
apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: ecommerce
spec:
  type: {service_type}
  selector:
    app: {name}
  ports:
  - port: {external_port}
    targetPort: {port}
    protocol: TCP
"""


def generate(dockerhub_user: str, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    for name, port, replicas, memory_limit, cpu_limit, service_type in SERVICES:
        is_ai = name == "ai-service"
        liveness_delay  = 60 if is_ai else 30
        liveness_period = 30 if is_ai else 15
        readiness_delay = 30 if is_ai else 10

        # frontend exposes on port 80 externally but listens on 8080 internally
        external_port = 80 if name == "frontend" else port

        deployment = DEPLOYMENT_TEMPLATE.format(
            name=name,
            port=port,
            replicas=replicas,
            dockerhub_user=dockerhub_user,
            memory_limit=memory_limit,
            cpu_limit=cpu_limit,
            liveness_delay=liveness_delay,
            liveness_period=liveness_period,
            readiness_delay=readiness_delay,
        )
        service = SERVICE_TEMPLATE.format(
            name=name,
            port=port,
            external_port=external_port,
            service_type=service_type,
        )

        file_path = os.path.join(output_dir, f"{name}.yaml")
        with open(file_path, "w") as f:
            f.write(deployment + service)

        print(f"  [OK] {file_path}  ({service_type}  port {external_port}->{port}  x{replicas})")

    print(f"\nDone. Apply with:  kubectl apply -f {output_dir}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Kubernetes YAML for eCommerce services.")
    parser.add_argument(
        "--dockerhub-user",
        default="<your-dockerhub-username>",
        help="DockerHub username (default: <your-dockerhub-username>)",
    )
    parser.add_argument(
        "--output-dir",
        default="k8s",
        help="Output directory for generated YAML files (default: k8s)",
    )
    args = parser.parse_args()

    print(f"Generating k8s YAML → {args.output_dir}/  (image prefix: {args.dockerhub_user}/)")
    generate(args.dockerhub_user, args.output_dir)


if __name__ == "__main__":
    main()
