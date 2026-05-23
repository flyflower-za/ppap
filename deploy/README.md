# Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

## Quick Start

### 1. Clone repository

```bash
git clone <repository-url>
cd ppap
```

### 2. Configure environment

```bash
cp deploy/.env.example deploy/.env
# Edit deploy/.env with your settings
```

### 3. Start services

```bash
cd deploy
docker-compose up -d
```

### 4. Initialize database

```bash
# Wait for PostgreSQL to be ready
docker-compose exec postgres psql -U ppap -d ppap -f /docker-entrypoint-initdb.d/init.sql
```

### 5. Create MinIO bucket

```bash
# Access MinIO console at http://localhost:9001
# Login with minioadmin/minioadmin
# Create bucket named 'ppap-files'
```

### 6. Access application

- Frontend: http://localhost
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 80 | Nginx serving Vue 3 app |
| Backend | 8000 | FastAPI application |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache & queue |
| MinIO | 9000 | Object storage |
| MinIO Console | 9001 | MinIO web UI |

## Production Deployment

### Environment Variables

Edit `deploy/.env`:

```bash
# Security
SECRET_KEY=<your-secret-key>

# Database
POSTGRES_PASSWORD=<strong-password>

# MinIO
MINIO_ROOT_USER=<username>
MINIO_ROOT_PASSWORD=<strong-password>

# Aliyun
ALIYUN_ACCESS_KEY_ID=<your-key>
ALIYUN_ACCESS_KEY_SECRET=<your-secret>
```

### SSL/TLS

1. Use reverse proxy (nginx/traefik)
2. Configure certificates

```nginx
server {
    listen 443 ssl http2;
    server_name ppap.brose.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://frontend;
    }

    location /api/ {
        proxy_pass http://backend;
    }
}
```

### Backup

```bash
# Database backup
docker-compose exec postgres pg_dump -U ppap ppap > backup.sql

# MinIO backup
docker-compose exec minio mc mirror /data /backup/minio
```

### Monitoring

Consider adding:
- Prometheus + Grafana for metrics
- ELK stack for logs
- Health check endpoint

## Troubleshooting

### Check logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

### Restart service

```bash
docker-compose restart backend
```

### Rebuild after code changes

```bash
docker-compose up -d --build backend frontend
```

### Reset everything

```bash
docker-compose down -v
docker-compose up -d
```
