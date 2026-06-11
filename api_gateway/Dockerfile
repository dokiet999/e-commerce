FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-common.txt /app/requirements-common.txt
COPY shared/ /app/shared/
COPY service_registry/ /app/service_registry/

COPY api_gateway/requirements.txt /app/api_gateway/requirements.txt
RUN pip install --no-cache-dir -r /app/api_gateway/requirements.txt

COPY api_gateway/ /app/api_gateway/

RUN adduser --disabled-password --gecos '' appuser
USER appuser

WORKDIR /app/api_gateway

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "300", "--reload", "gateway.wsgi:application"]
