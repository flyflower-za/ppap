# PPAP 部署流程文档

> 本文档详细描述 PPAP 平台的完整部署流程，包括环境准备、服务启动顺序和初始化步骤。

---

## 目录

- [前置条件](#前置条件)
- [部署流程概述](#部署流程概述)
- [详细启动步骤](#详细启动步骤)
- [服务健康检查](#服务健康检查)
- [首次登录](#首次登录)
- [故障排查](#故障排查)

---

## 前置条件

### 系统要求

- **操作系统**: Linux / macOS / Windows (with Docker Desktop)
- **Docker**: ≥ 20.10.0
- **Docker Compose**: v2.x (`docker compose`) 或 v1.x (`docker-compose`)
- **Python**: 3.x (用于生成 bcrypt 密码 hash)
- **OpenSSL**: 用于生成随机密钥（可选，脚本会检测）

### 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| Frontend (Nginx) | 80/443 | Web UI 访问 |
| Backend API | 31234 | 后端 API 服务 |
| PostgreSQL | 5432 (容器内部) | 数据库，不对外暴露 |
| Redis | 6379 (容器内部) | 缓存/消息队列，不对外暴露 |
| MinIO | 9000 | 对象存储，通过 Nginx 代理 |
| MinIO Console | 9001 | MinIO 管理界面 |

---

## 部署流程概述

```
deploy.sh
    │
    ├─ 检查前置条件 (docker / docker-compose / daemon)
    │
    ├─ 设置环境变量 (.env)
    │   ├─ 首次部署: 生成强密码 (openssl)
    │   ├─ 生成 ADMIN_PASSWORD_HASH (bcrypt)
    │   └─ 导出给 docker-compose
    │
    ├─ docker compose up -d --build
    │   └─ 按依赖顺序启动容器:
    │       ├─ postgres (健康检查)
    │       ├─ redis (健康检查)
    │       ├─ minio (健康检查)
    │       ├─ db-init (run once, 依赖 postgres)
    │       ├─ minio-init (run once, 依赖 minio)
    │       ├─ backend (依赖 postgres/redis/minio/db-init)
    │       ├─ celery-worker (依赖 backend 镜像)
    │       └─ frontend (依赖 backend)
    │
    ├─ 等待服务就绪 (健康检查)
    │
    └─ 输出访问信息 + 默认管理员账号
```

---

## 详细启动步骤

### 第一步：环境变量设置

`deploy.sh` 进入 `deploy/` 目录并执行以下操作：

#### 1.1 同步 `.env.example` → `.env`

如果存在 `sync-env.sh` 和 `.env.example`，运行同步脚本。

#### 1.2 首次部署：生成强密码

检测 `.env` 是否存在，不存在则：

```bash
# 生成随机密钥
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -base64 16 | tr -d '/+==' | head -c 20)
MINIO_ROOT_PASSWORD=$(openssl rand -base64 16 | tr -d '/+==' | head -c 20)
REDIS_PASSWORD=$(openssl rand -base64 12 | tr -d '/+==' | head -c 16)
GENERATED_ADMIN_PASS=$(openssl rand -base64 10 | tr -d '/+==' | head -c 12)

# 写入 .env
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" .env
sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${POSTGRES_PASSWORD}/" .env
# ... 其他环境变量
```

#### 1.3 生成管理员密码 hash

```bash
# Python bcrypt 生成 hash
ADMIN_HASH=$(python3 -c "
import bcrypt
print(bcrypt.hashpw(b'${GENERATED_ADMIN_PASS}', bcrypt.gensalt()).decode())
")

# 写入 .env (db-init 和 bootstrap_users.py 会读取)
echo "ADMIN_PASSWORD_HASH=${ADMIN_HASH}" >> .env
export ADMIN_PASSWORD_HASH="${ADMIN_HASH}"
```

#### 1.4 存量部署：补充 `ADMIN_PASSWORD_HASH`

如果 `.env` 已存在但缺少 `ADMIN_PASSWORD_HASH`：

```bash
# 检查是否存在
if ! grep -q "ADMIN_PASSWORD_HASH" .env; then
    # 使用默认密码 admin123 生成 hash
    ADMIN_HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode())")
    echo "ADMIN_PASSWORD_HASH=${ADMIN_HASH}" >> .env
fi
```

---

### 第二步：启动 Docker Compose 服务

```bash
docker compose up -d --build --remove-orphans
```

服务启动顺序：

```
1. postgres (15-alpine)
   └─ 健康检查: pg_isready

2. redis
   └─ 健康检查: redis-cli ping

3. minio
   └─ 健康检查: curl /minio/health/live

4. db-init (postgres:15-alpine, run once)
   ├─ 等待 postgres 健康检查通过
   ├─ 检查 users 表是否存在
   ├─ 不存在 → init-db.sql 建表 + 插 admin 用户
   │          password_hash 使用 $ADMIN_PASSWORD_HASH 环境变量
   ├─ 存在 → db_migrations.sql 迁移
   └─ 退出: condition: service_completed_successfully

5. minio-init (minio/mc:latest, run once)
   ├─ 等待 minio 健康检查通过
   ├─ mc alias set ppapminio http://minio:9000 ...
   ├─ mc mb ppapminio/ppap-files --ignore-existing
   ├─ mc anonymous set download ppapminio/ppap-files
   └─ 退出: condition: service_completed_successfully

6. backend (ppap-backend:latest)
   ├─ depends_on: postgres, redis, minio, db-init (completed)
   ├─ 启动容器 → start.sh 执行:
   │   ├─ python scripts/bootstrap_users.py
   │   │   ├─ 连接数据库 (asyncpg + DATABASE_URL)
   │   │   ├─ 检查用户数量
   │   │   ├─ 零用户 → 创建 admin@example.com
   │   │   │             password_hash = $ADMIN_PASSWORD_HASH or hash(admin123)
   │   │   ├─ password_hash NULL 用户 → 设置 fallback 密码
   │   │   └─ 无 admin → 提升第一个用户为 admin
   │   └─ uvicorn app.main:app --host 0.0.0.0 --port 31234 --workers 2
   └─ 健康检查: curl http://localhost:31234/health

7. celery-worker (ppap-backend:latest)
   └─ celery -A app.tasks.celery_app worker --loglevel=info --concurrency=3

8. frontend (ppap-frontend:latest)
   └─ Nginx 反向代理 → backend / minio
```

---

### 第三步：数据库初始化详情

#### 3.1 `db-init` 容器执行逻辑

使用 `postgres:15-alpine` 镜像，执行以下 Shell 脚本：

```bash
#!/bin/sh
# 睡眠等待 postgres 启动
sleep 5

# 检查 users 表是否已存在
if ! psql -h postgres -U ppap -d ppap -c 'SELECT 1 FROM users' > /dev/null 2>&1; then
  # 首次部署：执行 init-db.sql
  psql -h postgres -U ppap -d ppap < /docker-entrypoint-initdb.d/init-db.sql
else
  # 存量部署：仅执行迁移脚本
  psql -h postgres -U ppap -d ppap < /docker-entrypoint-initdb.d/db_migrations.sql || true
fi

# 如果设置了 ADMIN_PASSWORD_HASH 环境变量，更新 admin 密码
if [ -n "$ADMIN_PASSWORD_HASH" ]; then
  psql -h postgres -U ppap -d ppap -c "
    UPDATE users
    SET password_hash = '$ADMIN_PASSWORD_HASH'
    WHERE email = 'admin@example.com';
  "
fi
```

#### 3.2 `init-db.sql` 关键操作

- 创建所有表结构 (`users`, `files`, `tasks`, `notifications`, `settings`, ...)
- 插入默认 admin 用户：

```sql
INSERT INTO users (id, username, email, full_name, is_active, is_admin, role, password_hash)
VALUES (
    '01234567-0123-0123-0123-0123456789ab',
    'admin',
    'admin@example.com',
    'System Administrator',
    true, true, 'ADMIN',
    '$2b$12$...'  -- 被 $ADMIN_PASSWORD_HASH 替换
) ON CONFLICT (email) DO NOTHING;
```

#### 3.3 `db_migrations.sql` 关键操作

- 添加 `moduletype.online_verification` 枚举值
- 添加 `password_hash` 列到 `users` 表
- 添加 `module_id` 列到 `verification_rules` 表
- 添加 `severity.reference` 枚举值
- 添加 `username` 列到 `users` 表（包含冲突解决逻辑）
- 添加 `author_name` 列到 `notes` 表

---

### 第四步：Bootstrap 用户脚本

`backend/scripts/bootstrap_users.py` 在 backend 启动前运行：

#### 4.1 连接数据库

```python
import asyncpg

DATABASE_URL = os.environ.get("DATABASE_URL")
conn = await asyncpg.connect(DATABASE_URL)
```

#### 4.2 检查用户数量

```python
count = await conn.fetchval("SELECT COUNT(*) FROM users")
```

#### 4.3 场景处理

| 场景 | 操作 |
|------|------|
| **零用户** | 创建 `admin@example.com`，使用 `$ADMIN_PASSWORD_HASH` 或 hash `admin123` |
| **用户 password_hash = NULL** | 批量更新 `UPDATE users SET password_hash = ... WHERE password_hash IS NULL` |
| **无管理员** | 提升最早创建的用户为 admin：`UPDATE users SET is_admin = TRUE, role = 'ADMIN' WHERE id = (SELECT id FROM users ORDER BY created_at ASC LIMIT 1)` |

---

### 第五步：服务健康检查

#### 5.1 等待 `db-init` 完成

```bash
RETRIES=30
while [ $RETRIES -gt 0 ]; do
  STATUS=$(docker inspect ppap-db-init --format='{{.State.Status}}')
  EXITCODE=$(docker inspect ppap-db-init --format='{{.State.ExitCode}}')

  if [ "$STATUS" = "exited" ] && [ "$EXITCODE" = "0" ]; then
    echo "[+] Database initialization completed"
    break
  fi

  RETRIES=$((RETRIES - 1))
  sleep 2
done
```

#### 5.2 等待各服务健康检查通过

| 服务 | 健康检查命令 |
|------|-------------|
| PostgreSQL | `docker compose exec -T postgres pg_isready -U ppap` |
| Redis | `docker compose exec -T redis redis-cli ping` |
| MinIO | `curl -sf http://localhost:9000/minio/health/live` |
| Backend | `curl -sf http://localhost:31234/docs` |
| MinIO bucket init | 等待 `ppap-minio-init` 容器退出且 exitcode=0 |

---

### 第六步：输出访问信息

```bash
echo "=== Deployment Completed Successfully ==="
echo ""
echo "Access the services at:"
echo "  🌐 Frontend UI:   http://localhost"
echo "  🔧 Backend API:   http://localhost:31234/docs"
echo "  📁 MinIO Console: http://localhost:9001 (minioadmin / minioadmin)"
echo ""
echo "Default Admin Account:"
echo "  📧 Email:    admin@example.com"
echo "  🔑 Password: ${GENERATED_ADMIN_PASS:-admin123}"
```

---

## 首次登录

### 1. 访问前端

打开浏览器访问 `http://localhost`（或配置的 `API_HOST`）

### 2. 使用管理员账号登录

```
Email: admin@example.com
Password: <生成的密码> (默认 admin123)
```

### 3. 配置系统（可选）

- **SSO/LDAP**: 进入 `Settings` → `SSO 配置` 或 `LDAP 配置`
- **SMTP**: 配置邮件通知服务器
- **AI 模型**: 配置 LLM/VLM API 密钥（用于印章检测等 AI 功能）

### 4. 测试文件上传

- 进入 `任务中心`
- 拖拽上传 PDF 文件
- 查看实时校验进度

---

## 故障排查

### 问题：db-init 容器启动失败

**症状**: `docker compose logs db-init` 显示错误

**排查**:
```bash
# 查看 db-init 日志
docker compose logs db-init

# 手动进入 postgres 容器检查
docker compose exec postgres psql -U ppap -d ppap -c 'SELECT 1 FROM users;'
```

**常见原因**:
- PostgreSQL 未启动 → 等待健康检查通过
- `init-db.sql` 语法错误 → 检查 SQL 语法
- 权限问题 → 确保 `ppap` 用户有 CREATE TABLE 权限

---

### 问题：backend 启动后无法登录

**症状**: 登录返回 401 Unauthorized

**排查**:
```bash
# 进入 backend 容器检查 bootstrap 日志
docker compose logs backend | grep bootstrap

# 进入数据库检查用户
docker compose exec postgres psql -U ppap -d ppap -c "
SELECT email, password_hash IS NULL AS missing_pwd
FROM users;
"
```

**常见原因**:
- 存量用户 `password_hash` 为 NULL → `bootstrap_users.py` 应自动修复
- Admin 用户被禁用 (`is_active = false`) → `UPDATE users SET is_active = true WHERE email = 'admin@example.com';`
- 首次部署未创建用户 → 检查 `bootstrap_users.py` 输出

---

### 问题：MinIO bucket 未创建

**症状**: 文件上传失败，日志显示 "bucket not found"

**排查**:
```bash
# 查看 minio-init 日志
docker compose logs minio-init

# 手动创建 bucket
docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker compose exec minio mc mb local/ppap-files
docker compose exec minio mc anonymous set download local/ppap-files
```

---

### 问题：Celery worker 任务不执行

**症状**: 文件上传后状态一直为 `pending`

**排查**:
```bash
# 检查 celery-worker 状态
docker compose exec celery-worker celery -A app.tasks.celery_app inspect ping

# 查看日志
docker compose logs celery-worker

# 检查 Redis 连接
docker compose exec redis redis-cli ping
```

**常见原因**:
- Redis 未启动 → 检查 Redis 健康状态
- Celery 无法连接 Backend API → 检查 `DATABASE_URL` / `MINIO_ENDPOINT` 环境变量

---

## 高级部署选项

### 自定义管理员账号

修改 `.env` 中的环境变量：

```bash
ADMIN_EMAIL=myadmin@company.com
ADMIN_PASSWORD=my-secure-password
```

`deploy.sh` 会自动生成 `ADMIN_PASSWORD_HASH` 并写入 `.env`。

### 强制重建所有容器

```bash
./deploy.sh --clean
# 或
docker compose build --no-cache
docker compose up -d
```

### 单独重启服务

```bash
# 重启 backend (会重新运行 bootstrap_users.py)
docker compose restart backend

# 重启所有服务
docker compose restart
```

---

## 附录：环境变量清单

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SECRET_KEY` | `change-this-in-production` | JWT 签名密钥 |
| `POSTGRES_PASSWORD` | `ppap123` | PostgreSQL 数据库密码 |
| `MINIO_ROOT_USER` | `minioadmin` | MinIO 管理员用户名 |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO 管理员密码 |
| `REDIS_PASSWORD` | `redis-secret-pass` | Redis 密码 |
| `ADMIN_EMAIL` | `admin@example.com` | 默认管理员邮箱 |
| `ADMIN_PASSWORD` | `admin123` | 默认管理员密码（用于生成 hash） |
| `ADMIN_PASSWORD_HASH` | *(自动生成)* | bcrypt hash，优先于 `ADMIN_PASSWORD` |
| `DATABASE_URL` | `postgresql+asyncpg://...` | SQLAlchemy 数据库连接 |
| `REDIS_URL` | `redis://:password@host:6379/0` | Celery broker URL |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO API 端点（容器内部） |
| `TZ` | `Asia/Shanghai` | 时区配置 |

---

*文档版本: v1.0.0*
*最后更新: 2026-06-26*
