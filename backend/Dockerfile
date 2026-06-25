# ---- Stage 1: Builder (install all deps including dev) ----
FROM python:3.11-slim AS builder

WORKDIR /build

# Use Chinese apt mirror for faster downloads
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; \
    sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null; \
    true

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install ALL dependencies (including dev) to build wheels
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com -r requirements.txt

# ---- Stage 2: Production (runtime only) ----
FROM python:3.11-slim

WORKDIR /app

# Use Chinese apt mirror
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; \
    sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null; \
    true

# Runtime system dependencies only (no gcc/build tools)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy only production Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /usr/local/bin/celery /usr/local/bin/celery

# Install production requirements to ensure entry points are consistent
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com -r requirements-prod.txt

# Copy application code (only runtime-needed files)
COPY app/ app/
COPY scripts/ scripts/
COPY migrations/ migrations/
COPY alembic.ini .
COPY start.sh .
COPY start_celery.sh .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

RUN chmod +x start.sh start_celery.sh

EXPOSE 8000

CMD ["./start.sh"]
