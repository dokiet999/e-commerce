FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev pkg-config && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-common.txt /app/requirements-common.txt
COPY shared/ /app/shared/
COPY service_registry/ /app/service_registry/

COPY shipping_service/requirements.txt /app/shipping_service/requirements.txt
RUN pip install --no-cache-dir -r /app/shipping_service/requirements.txt

COPY shipping_service/ /app/shipping_service/

RUN adduser --disabled-password --gecos '' appuser
USER appuser

WORKDIR /app/shipping_service

EXPOSE 8010

CMD ["gunicorn", "--bind", "0.0.0.0:8010", "--workers", "2", "--reload", "shipping_config.wsgi:application"]
