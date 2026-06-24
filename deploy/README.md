# 部署指南

## 环境要求

- Docker 20.10+
- Docker Compose 2.0+

## 快速开始

### 1. 克隆仓库

```bash
git clone <repository-url>
cd ppap
```

### 2. 部署

使用部署脚本自动完成环境配置、密钥生成和服务启动：

**Linux / macOS:**
```bash
bash deploy.sh
```

**Windows (PowerShell):**
```powershell
.\deploy.ps1
```

脚本会自动：
- 检查 Docker 环境
- 生成 `.env` 文件（首次运行时自动生成强密钥）
- 构建并启动所有服务
- 初始化数据库和 MinIO bucket

### 3. 访问应用

- **前端**: http://localhost
- **后端 API**: http://localhost:31234
- **API 文档**: http://localhost:31234/docs
- **MinIO 控制台**: http://localhost:9001

## 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Frontend | 80 | Nginx 静态文件 + API 反向代理 |
| Backend | 31234 | FastAPI 应用 |
| MinIO API | 9000 | 对象存储 API |
| MinIO Console | 9001 | MinIO Web 管理界面 |

> PostgreSQL、Redis 仅通过 Docker 内部网络访问，不暴露到宿主机。

## 环境变量

编辑 `deploy/.env`（由部署脚本自动生成）：

```bash
# 安全
SECRET_KEY=<自动生成>
ACCESS_TOKEN_EXPIRE_MINUTES=120

# 数据库
POSTGRES_PASSWORD=<自动生成>

# Redis
REDIS_PASSWORD=<自动生成>

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<自动生成>

# 应用
APP_BASE_URL=http://your-server-ip  # 生产环境必须修改

# Aliyun AI（可选）
ALIYUN_ACCESS_KEY_ID=<your-key>
ALIYUN_ACCESS_KEY_SECRET=<your-secret>
```

## 生产部署

### 修改 APP_BASE_URL

生产环境务必修改为实际域名或公网 IP：

```bash
APP_BASE_URL=http://your-domain.com
```

### 防火墙

```bash
bash setup_firewall.sh
```

### SSL/TLS

建议使用反向代理（Nginx/Traefik）配置 HTTPS。

### 备份

```bash
# 数据库备份
docker compose exec postgres pg_dump -U ppap ppap > backup.sql

# MinIO 备份
docker compose exec minio mc mirror /data /backup/minio
```

## 常见问题

### 查看日志

```bash
docker compose logs -f backend
docker compose logs -f celery-worker
```

### 重启服务

```bash
docker compose restart backend
```

### 代码更新后重新构建

```bash
docker compose up -d --build backend frontend celery-worker
```

### 完全重置

```bash
docker compose down -v
bash deploy.sh
```
