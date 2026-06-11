FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev pkg-config && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-common.txt /app/requirements-common.txt
COPY shared/ /app/shared/
COPY service_registry/ /app/service_registry/

COPY inventory_service/requirements.txt /app/inventory_service/requirements.txt
RUN pip install --no-cache-dir -r /app/inventory_service/requirements.txt

COPY inventory_service/ /app/inventory_service/

RUN adduser --disabled-password --gecos '' appuser
USER appuser

WORKDIR /app/inventory_service

EXPOSE 8007

CMD ["gunicorn", "--bind", "0.0.0.0:8007", "--workers", "2", "--reload", "inventory_config.wsgi:application"]
