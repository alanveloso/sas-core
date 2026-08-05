# SAS production foundation: FastAPI gateway + Celery worker (same image).
# Base image pinned by digest for reproducible builds (P0-003).
FROM python:3.11-slim-bookworm@sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/sas_mvp_core

WORKDIR /app/sas_mvp_core

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock.txt ./requirements.lock.txt
# Keep pip itself reproducible for lock installs (P0-003 review).
RUN pip install --upgrade 'pip==25.2' \
    && pip install -r requirements.lock.txt

COPY . .

EXPOSE 9000 9001

CMD ["python", "main.py"]
