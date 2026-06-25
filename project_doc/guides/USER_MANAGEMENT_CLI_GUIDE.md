# PPAP 用户管理 CLI 工具使用指南

> 本工具提供命令行界面管理 PPAP 平台用户，通过 Docker 容器执行，无需直接连接数据库。

---

## 功能特性

- ✅ 列出所有用户（显示密码状态、角色、活跃状态等）
- ✅ 创建新用户（可选择是否设置密码）
- ✅ 重置用户密码
- ✅ 激活/停用用户账号
- ✅ 提升为管理员/降级为普通用户
- ✅ 检查特定用户详情

---

## 前置条件

### Docker 环境

工具通过 Docker 容器执行，需要：

- Docker 和 Docker Compose 已安装
- PPAP 服务正在运行（至少 backend 容器需要运行）

### 快速开始

```bash
# 确保服务正在运行
docker compose -f deploy/docker-compose.yml ps

# 如果未运行，启动服务
docker compose -f deploy/docker-compose.yml up -d
```

---

## 基本用法

### 推荐方式：使用 Wrapper 脚本

项目根目录提供了 `manage_users.sh` wrapper 脚本，简化执行流程：

```bash
# 添加执行权限（首次使用）
chmod +x manage_users.sh

# 列出所有用户
./manage_users.sh list

# 查看帮助
./manage_users.sh --help
```

### 方式 2：通过 Docker Compose 直接执行

如果不使用 wrapper 脚本，可以直接通过 Docker Compose 在 backend 容器内执行用户管理命令。

#### 基本语法

```bash
docker compose -f deploy/docker-compose.yml exec backend python scripts/user_cli.py [命令] [参数]
```

#### 完整示例

```bash
# 列出所有用户
docker compose -f deploy/docker-compose.yml exec backend python scripts/user_cli.py list

# 创建新用户
docker compose -f deploy/docker-compose.yml exec backend python scripts/user_cli.py create \
  --email john@example.com \
  --full-name "John Doe" \
  --password secret123 \
  --role USER

# 重置密码
docker compose -f deploy/docker-compose.yml exec backend python scripts/user_cli.py reset-password \
  --email user@example.com \
  --password newpass

# 查看帮助
docker compose -f deploy/docker-compose.yml exec backend python scripts/user_cli.py --help
```

#### 使用场景

这种方式适合以下情况：

- **不使用 wrapper 脚本**：直接使用 Docker Compose 原生命令
- **在不同目录执行**：只要能访问到 `docker-compose.yml` 文件
- **脚本调试**：直接查看容器内 Python 脚本的输出
- **自动化集成**：在 CI/CD 或其他自动化脚本中嵌入

#### 注意事项

1. **需要指定 compose 文件路径**：
   ```bash
   # 如果在项目根目录，可以省略 -f 参数
   docker compose exec backend python scripts/user_cli.py list

   # 如果在其他目录，需要指定完整路径
   docker compose -f /path/to/ppap/deploy/docker-compose.yml exec backend python scripts/user_cli.py list
   ```

2. **确保 backend 容器正在运行**：
   ```bash
   # 检查容器状态
   docker compose -f deploy/docker-compose.yml ps backend

   # 如果未运行，启动服务
   docker compose -f deploy/docker-compose.yml up -d backend
   ```

3. **脚本路径**：
   - 脚本在容器内的路径是 `/app/scripts/user_cli.py`
   - 当前工作目录是 `/app`
   - 使用相对路径 `python scripts/user_cli.py` 即可

#### 与方式 1 的区别

| 特性 | 方式 1 (Wrapper) | 方式 2 (Docker Compose) |
|------|-------------------|-------------------------|
| **命令长度** | 简短 (`./manage_users.sh list`) | 较长 (`docker compose exec ...`) |
| **目录限制** | 必须在项目根目录 | 可以在任何目录（指定 compose 文件路径） |
| **前提条件** | 需要 wrapper 脚本 | 只需要 Docker Compose |
| **灵活性** | 固定命令格式 | 可自由组合 Docker 命令 |
| **推荐场景** | 日常管理操作 | 脚本调试 / 自动化集成 |

---

## 命令详解

### 1. 列出所有用户

```bash
./manage_users.sh list
```

**输出示例**：
```
🔗 Connecting to database: postgresql://ppap:***@postgres:5432/ppap

📋 Total users: 4

Email                          Username        Role       Admin  Active  Has Password  SSO/LDAP
--------------------------------------------------------------------------------------------------------------
admin@brose.com                admin2           USER       ❌     ✅      ✅ Set        Local
ao.zhou@brose.com              zhouao2          ADMIN      ✅     ✅      ✅ Set        Local
user@example.com               user             USER       ❌     ✅      ✅ Set        Local
admin@example.com              admin            ADMIN      ✅     ✅      ✅ Set        Local
```

**字段说明**：
- `Has Password`: ✅ Set = 已设置密码，❌ NULL = 未设置（SSO/LDAP 用户）
- `SSO/LDAP`: SSO = SSO 登录，LDAP = LDAP 登录，Local = 本地密码登录
- `Admin`: ✅ = 管理员权限，❌ = 普通用户
- `Active`: ✅ = 账号激活，❌ = 账号停用

---

### 2. 检查特定用户

```bash
./manage_users.sh check --email user@example.com
```

**输出示例**：
```
👤 User Details:
   Email:        user@example.com
   Username:     john_doe
   Full Name:    John Doe
   Department:   Engineering
   Role:         USER
   Is Admin:     ❌ No
   Is Active:    ✅ Yes
   Password:     ❌ Not Set
   Auth Provider: SSO
   Created At:   2026-06-25 10:30:00
   Last Login:   2026-06-26 09:15:00
```

---

### 3. 创建新用户

#### 3.1 创建本地用户（需要密码登录）

```bash
./manage_users.sh create \
  --email john@example.com \
  --full-name "John Doe" \
  --password secret123 \
  --role USER \
  --department "Engineering"
```

#### 3.2 创建 SSO/LDAP 用户（无需密码）

```bash
./manage_users.sh create \
  --email sso-user@example.com \
  --full-name "SSO User" \
  --role MANAGER \
  --department "Sales"
```

#### 3.3 创建管理员

```bash
./manage_users.sh create \
  --email admin@company.com \
  --full-name "System Admin" \
  --password admin123 \
  --role ADMIN
```

**参数说明**：
- `--email`: 邮箱地址（必需）
- `--full-name`: 用户全名（必需）
- `--password`: 密码（可选，SSO/LDAP 用户不提供）
- `--role`: 角色（USER / MANAGER / ADMIN，默认：USER）
- `--department`: 部门名称（可选）

---

### 4. 重置用户密码

```bash
./manage_users.sh reset-password \
  --email user@example.com \
  --password newpassword456
```

**适用场景**：
- 用户忘记密码
- 管理员强制重置密码
- 账号安全管理

---

### 5. 激活/停用用户账号

#### 5.1 激活用户

```bash
./manage_users.sh activate --email user@example.com
```

#### 5.2 停用用户

```bash
./manage_users.sh deactivate --email user@example.com
```

**效果**：
- 停用后用户无法登录（返回 403 Forbidden）
- 用户数据保留，仅标记 `is_active = false`

---

### 6. 提升为管理员/降级为普通用户

#### 6.1 提升为管理员

```bash
./manage_users.sh promote-admin --email user@example.com
```

**效果**：
- 设置 `is_admin = true`
- 设置 `role = 'ADMIN'`
- 用户获得所有管理权限

#### 6.2 降级为普通用户

```bash
./manage_users.sh demote-admin --email admin@example.com
```

**效果**：
- 设置 `is_admin = false`
- 设置 `role = 'USER'`
- 移除所有管理权限

---

## 常见使用场景

### 场景 1：首次部署后创建管理员

```bash
# 检查现有用户
./manage_users.sh list

# 创建新管理员
./manage_users.sh create \
  --email admin@company.com \
  --full-name "Company Admin" \
  --password secure123 \
  --role ADMIN

# 验证创建成功
./manage_users.sh check --email admin@company.com
```

---

### 场景 2：用户忘记密码

```bash
# 重置用户密码
./manage_users.sh reset-password \
  --email user@example.com \
  --password newpassword

# 通知用户用新密码登录
```

---

### 场景 3：为 SSO 用户启用密码登录

```bash
# 检查用户当前状态（password_hash 应该为 NULL）
./manage_users.sh check --email sso-user@example.com

# 设置密码
./manage_users.sh reset-password \
  --email sso-user@example.com \
  --password userpassword

# 验证（Has Password 应该变为 Set）
./manage_users.sh list | grep sso-user
```

---

### 场景 4：批量检查用户状态

```bash
# 列出所有用户
./manage_users.sh list

# 找出没有密码的用户（Has Password = ❌ NULL）
# 这些用户只能通过 SSO/LDAP 登录

# 如果需要为本地用户设置密码：
./manage_users.sh reset-password \
  --email user-without-password@example.com \
  --password fallback123
```

---

## 故障排查

### 问题 1：backend 容器未运行

**错误信息**：
```
❌ Error: backend container is not running
Please start the services first: docker compose -f deploy/docker-compose.yml up -d
```

**解决方案**：
```bash
# 启动服务
docker compose -f deploy/docker-compose.yml up -d

# 检查容器状态
docker compose -f deploy/docker-compose.yml ps backend
```

---

### 问题 2：找不到 docker-compose.yml

**错误信息**：
```
❌ Error: docker-compose.yml not found in current directory or deploy/
```

**解决方案**：
```bash
# 确保在项目根目录执行
cd /path/to/ppap

# 或使用完整路径
docker compose -f /path/to/ppap/deploy/docker-compose.yml exec backend python scripts/user_cli.py list
```

---

### 问题 3：脚本未复制到容器

**错误信息**：
```
python: can't open file '/app/scripts/user_cli.py': [Errno 2] No such file or directory
```

**解决方案**：
```bash
# 复制脚本到容器
docker compose -f deploy/docker-compose.yml cp backend/scripts/user_cli.py backend:/app/scripts/user_cli.py

# 重新执行
./manage_users.sh list
```

---

### 问题 4：用户已存在

**错误信息**：
```
❌ Error: User with email 'user@example.com' already exists
```

**解决方案**：
```bash
# 检查现有用户
./manage_users.sh check --email user@example.com

# 如需更新用户信息，请通过 Web UI 或 API
```

---

## 工作原理

### 执行流程

```
manage_users.sh
    │
    ├─ 查找 docker-compose.yml（deploy/ 或 当前目录）
    │
    ├─ 检查 backend 容器是否运行
    │
    └─ 通过 docker compose exec 执行命令：
        docker compose exec backend python scripts/user_cli.py "$@"
            │
            └─ 在 backend 容器内：
                ├─ 读取环境变量（POSTGRES_*, DATABASE_URL）
                ├─ 使用 asyncpg 连接数据库
                └─ 执行 SQL 操作（CREATE / UPDATE / SELECT）
```

### 数据库连接

脚本直接从环境变量读取数据库配置：

```python
DATABASE_URL = os.environ.get("DATABASE_URL")
# 或从 POSTGRES_* 变量构建：
# postgresql+asyncpg://ppap:password@postgres:5432/ppap
```

在 Docker Compose 环境中，这些变量已配置在 `deploy/.env` 和 `docker-compose.yml` 中。

---

## 安全建议

1. **密码强度**：
   - 建议密码长度 ≥ 12 位
   - 包含大小写字母、数字、特殊字符
   - 避免使用常见密码（如 123456、password）

2. **管理员账号**：
   - 限制管理员账号数量
   - 为管理员使用强密码
   - 定期审计管理员列表

3. **停用用户**：
   - 员工离职时及时停用账号
   - 长期未使用的账号建议停用

4. **密码重置**：
   - 重置密码后通知用户通过安全渠道获取新密码
   - 建议用户首次登录后修改密码

---

## 附录：命令速查表

| 命令 | 说明 | 示例 |
|------|------|------|
| `list` | 列出所有用户 | `./manage_users.sh list` |
| `check --email` | 检查用户详情 | `./manage_users.sh check --email user@example.com` |
| `create` | 创建新用户 | `./manage_users.sh create --email x@x.com --full-name "X" --password xxx` |
| `reset-password` | 重置密码 | `./manage_users.sh reset-password --email x@x.com --password new` |
| `activate` | 激活账号 | `./manage_users.sh activate --email x@x.com` |
| `deactivate` | 停用账号 | `./manage_users.sh deactivate --email x@x.com` |
| `promote-admin` | 提升管理员 | `./manage_users.sh promote-admin --email x@x.com` |
| `demote-admin` | 降级用户 | `./manage_users.sh demote-admin --email x@x.com` |

---

*文档版本: v1.1.0*
*最后更新: 2026-06-26*
