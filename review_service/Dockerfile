FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-common.txt /app/requirements-common.txt
COPY shared/ /app/shared/
COPY service_registry/ /app/service_registry/

COPY review_service/requirements.txt /app/review_service/requirements.txt
RUN pip install --no-cache-dir -r /app/review_service/requirements.txt

COPY review_service/ /app/review_service/

RUN adduser --disabled-password --gecos '' appuser
USER appuser

WORKDIR /app/review_service

EXPOSE 8009

CMD ["gunicorn", "--bind", "0.0.0.0:8009", "--workers", "2", "--reload", "review_config.wsgi:application"]
