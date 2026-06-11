FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy shared packages first (they're mounted but need to exist at build)
COPY requirements-common.txt /app/requirements-common.txt
COPY shared/ /app/shared/
COPY service_registry/ /app/service_registry/

# Copy service requirements & install
COPY auth_service/requirements.txt /app/auth_service/requirements.txt
RUN pip install --no-cache-dir -r /app/auth_service/requirements.txt

# Copy service code
COPY auth_service/ /app/auth_service/

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

WORKDIR /app/auth_service

EXPOSE 8001

CMD ["gunicorn", "--bind", "0.0.0.0:8001", "--workers", "2", "--reload", "auth_config.wsgi:application"]
