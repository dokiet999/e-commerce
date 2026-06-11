FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-common.txt /app/requirements-common.txt
COPY shared/ /app/shared/
COPY service_registry/ /app/service_registry/

COPY payment_service/requirements.txt /app/payment_service/requirements.txt
RUN pip install --no-cache-dir -r /app/payment_service/requirements.txt

COPY payment_service/ /app/payment_service/

RUN adduser --disabled-password --gecos '' appuser
USER appuser

WORKDIR /app/payment_service

EXPOSE 8006

CMD ["gunicorn", "--bind", "0.0.0.0:8006", "--workers", "2", "--reload", "payment_config.wsgi:application"]
