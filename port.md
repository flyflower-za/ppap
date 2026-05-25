# PPAP 端口配置

> 更新日期: 2026-05-25

---

## 端口总览

| 服务 | 端口 | 外部访问 | 说明 |
|------|------|----------|------|
| **后端 API** | 31234 | ✅ | FastAPI (Swagger: `/docs`) |
| **前端 (Nginx)** | 80 | ✅ | 生产环境静态服务 + 反向代理 |
| **前端 (Vite Dev)** | 5173 | — | 开发环境，代理 `/api` → `localhost:31234` |
| **PostgreSQL** | 5435 → 5432 | ✅ | 外部映射 5435，容器内 5432 |
| **Redis** | 6379 | ✅ | — |
| **MinIO API** | 9000 | ✅ | 对象存储接口 |
| **MinIO Console** | 9001 | ✅ | 管理界面 |
| **SSH** | 22 | ✅ | 服务器远程访问 |
| **HTTPS** | 443 | ✅ | 预留 (防火墙已开放) |

---

## 详细配置

### 后端 API (31234)

**配置文件:** `deploy/docker-compose.yml`

```yaml
ports:
  - "31234:31234"
command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "31234"]
environment:
  PORT: "31234"
```

- Swagger 文档: `http://<host>:31234/docs`
- Redoc 文档: `http://<host>:31234/redoc`

**前端开发代理:** `frontend/vite.config.ts`

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:31234',
    changeOrigin: true,
    ws: true,
  },
}
```

---

### 前端 (Nginx, 80)

**配置文件:** `deploy/nginx.conf`

```nginx
server {
    listen 80;
    server_name localhost;

    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://backend:31234;
    }

    # MinIO presigned URL
    location /ppap-files/ {
        proxy_pass http://minio:9000/ppap-files/;
    }
}
```

---

### PostgreSQL (5435 → 5432)

```yaml
ports:
  - "5435:5432"
```

连接 URL: `postgresql+asyncpg://ppap:ppap123@localhost:5435/ppap`

---

### Redis (6379)

```yaml
ports:
  - "6379:6379"
```

连接 URL: `redis://localhost:6379/0`

---

### MinIO (9000 / 9001)

```yaml
ports:
  - "9000:9000"   # API
  - "9001:9001"   # Console
```

- API: `http://<host>:9000`
- Console: `http://<host>:9001`
- 默认凭据: `minioadmin` / `minioadmin`

---

## 防火墙规则

**脚本:** `setup_firewall.sh`

使用 UFW (Ubuntu) 管理端口:

```bash
sudo bash setup_firewall.sh
```

| 端口 | 规则 | 用途 |
|------|------|------|
| 22/tcp | ALLOW | SSH |
| 80/tcp | ALLOW | HTTP (前端) |
| 443/tcp | ALLOW | HTTPS (预留) |
| 31234/tcp | ALLOW | 后端 API |
| 9000/tcp | ALLOW | MinIO API |
| 9001/tcp | ALLOW | MinIO Console |

查看状态: `sudo ufw status`

---

## 变更历史

| 日期 | 变更 | 说明 |
|------|------|------|
| 2026-05-25 | 后端 8000 → 31234 | 解决端口冲突 |
| 2026-05-25 | 新增防火墙脚本 | UFW 管理端口访问 |
