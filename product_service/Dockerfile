FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-common.txt /app/requirements-common.txt
COPY shared/ /app/shared/
COPY service_registry/ /app/service_registry/

COPY product_service/requirements.txt /app/product_service/requirements.txt
RUN pip install --no-cache-dir -r /app/product_service/requirements.txt

COPY product_service/ /app/product_service/

RUN adduser --disabled-password --gecos '' appuser
USER appuser

WORKDIR /app/product_service

EXPOSE 8002

CMD ["gunicorn", "--bind", "0.0.0.0:8002", "--workers", "2", "--reload", "product_config.wsgi:application"]
