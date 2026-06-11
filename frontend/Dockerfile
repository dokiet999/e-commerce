FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-common.txt /app/requirements-common.txt
COPY shared/ /app/shared/
COPY service_registry/ /app/service_registry/

COPY frontend/requirements.txt /app/frontend/requirements.txt
RUN pip install --no-cache-dir -r /app/frontend/requirements.txt

COPY frontend/ /app/frontend/

# Collect static files for whitenoise
RUN cd /app/frontend && python manage.py collectstatic --noinput

RUN adduser --disabled-password --gecos '' appuser
USER appuser

WORKDIR /app/frontend

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--reload", "frontend_config.wsgi:application"]
