FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-common.txt /app/requirements-common.txt
COPY shared/ /app/shared/
COPY service_registry/ /app/service_registry/

COPY ai_service/requirements.txt /app/ai_service/requirements.txt
RUN pip install --no-cache-dir -r /app/ai_service/requirements.txt

COPY ai_service/ /app/ai_service/

RUN adduser --disabled-password --gecos '' appuser
RUN mkdir -p /app/ai_service/kb/chroma_db /app/ai_service/ml/saved_models && \
    chown -R appuser:appuser /app/ai_service/kb/chroma_db /app/ai_service/ml/saved_models
USER appuser

WORKDIR /app/ai_service

EXPOSE 8004

CMD ["gunicorn", "--bind", "0.0.0.0:8004", "--workers", "2", "--timeout", "300", "--reload", "ai_config.wsgi:application"]
