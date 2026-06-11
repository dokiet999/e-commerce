FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev pkg-config && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-common.txt /app/requirements-common.txt
COPY shared/ /app/shared/
COPY service_registry/ /app/service_registry/

COPY cart_service/requirements.txt /app/cart_service/requirements.txt
RUN pip install --no-cache-dir -r /app/cart_service/requirements.txt

COPY cart_service/ /app/cart_service/

RUN adduser --disabled-password --gecos '' appuser
USER appuser

WORKDIR /app/cart_service

EXPOSE 8003

CMD ["gunicorn", "--bind", "0.0.0.0:8003", "--workers", "2", "--reload", "cart_config.wsgi:application"]
