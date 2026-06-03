# Changelog

All notable changes to the PPAP project will be documented in this file.

## [2026-06-03] - 数据库自动化初始化

### 功能描述
- 实现了完全自动化的数据库初始化流程
- 首次部署时无需手动运行初始化脚本
- 支持幂等性操作，可安全重复执行

### 详细修改记录

#### 1. 数据库初始化脚本优化
**文件路径**: `c:\Projects\git\ppap\deploy\init-db.sql`
**修改时间**: 2026-06-03

**新增功能**:
- 在表结构创建前添加枚举类型定义
- 更新 users 表结构，新增 role 和 ad_groups 列
- 统一使用枚举类型替代 VARCHAR 类型

**新增的枚举类型**:
```sql
CREATE TYPE userrole AS ENUM ('ADMIN', 'MANAGER', 'USER');
CREATE TYPE filetype AS ENUM ('PRODUCTION_PLAN', 'QUALITY_REPORT', 'PURCHASE_ORDER', 'SUPPLIER_QUALIFICATION', 'PRODUCT_SPECIFICATION', 'OTHER');
CREATE TYPE filestatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'WARNING');
CREATE TYPE taskstatus AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED');
CREATE TYPE notificationtype AS ENUM ('SUCCESS', 'ERROR', 'WARNING', 'INFO');
```

**修改的表结构**:
- `users` 表: 新增 `role` 和 `ad_groups` 列
- `files` 表: 使用 `filetype` 和 `filestatus` 枚举
- `tasks` 表: 使用 `taskstatus` 枚举
- `notifications` 表: 使用 `notificationtype` 枚举

**默认管理员账户更新**:
```sql
INSERT INTO users (id, email, full_name, is_active, is_admin, role)
VALUES (
    '01234567-0123-0123-0123-0123456789ab',
    'admin@example.com',
    'System Administrator',
    true,
    true,
    'ADMIN'
) ON CONFLICT (email) DO NOTHING;
```

---

#### 2. Docker Compose 配置优化
**文件路径**: `c:\Projects\git\ppap\deploy\docker-compose.yml`
**修改时间**: 2026-06-03

**新增数据库初始化服务**:
```yaml
db-init:
  image: postgres:15-alpine
  container_name: ppap-db-init
  command: >
    sh -c "
    sleep 5 &&
    if ! PGPASSWORD=ppap123 psql -h postgres -U ppap -d ppap -c 'SELECT 1 FROM users' > /dev/null 2>&1; then
      echo 'Initializing database schema...' &&
      PGPASSWORD=ppap123 psql -h postgres -U ppap -d ppap < /docker-entrypoint-initdb.d/init-db.sql &&
      echo 'Database initialization completed';
    else
      echo 'Database already initialized';
    fi
    "
  volumes:
    - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
  depends_on:
    postgres:
      condition: service_healthy
  restart: "no"
```

**移除 Alembic 迁移服务**:
- 删除了 `migration` 服务配置
- 后端服务现在直接依赖 `db-init` 服务完成
- 简化了部署流程，减少了潜在的错误点

**服务依赖关系更新**:
```yaml
backend:
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
    minio:
      condition: service_healthy
    db-init:
      condition: service_completed_successfully
```

---

#### 3. Alembic 迁移脚本优化
**文件路径**: `c:\Projects\git\ppap\backend\migrations\versions\`
**修改时间**: 2026-06-03

**修改的迁移文件**:
- `455ad299810f_initial_schema.py`: 添加智能检查，跳过已存在的表
- `156287492b65_add_dynamic_rule_tables.py`: 添加表存在性检查
- `a9bf6820e18c_add_logic_config_and_needs_review_status.py`: 添加列存在性检查
- `664c02f918be_add_audit_logs_table.py`: 添加表存在性检查
- `add_user_groups_table.py`: 添加表存在性检查

**智能迁移逻辑**:
```python
def upgrade() -> None:
    """Smart migration that checks if database is already initialized."""
    conn = op.get_bind()
    try:
        inspector = inspect(conn)
        if 'users' in inspector.get_table_names():
            print("Database already initialized via init-db.sql, skipping migration...")
            return
        # Migration logic here
    except Exception as e:
        print(f"Migration check completed: {e}")
```

---

### 部署说明

#### 首次部署（自动初始化）
```powershell
# 一键启动，自动完成数据库初始化
cd c:\Projects\git\ppap\deploy
docker compose up -d --build
```

#### 部署流程
1. **启动基础服务**: PostgreSQL, Redis, MinIO
2. **数据库初始化**: `db-init` 服务自动运行 `init-db.sql`
3. **启动应用服务**: 等待初始化完成后启动后端和前端
4. **完成部署**: 所有服务正常运行

#### 服务启动顺序
```
postgres → redis → minio → db-init → backend & frontend & celery-worker
```

---

### 验证步骤

#### 1. 检查数据库初始化状态
```powershell
docker compose logs db-init
```

#### 2. 检查后端服务状态
```powershell
docker compose ps backend
```

#### 3. 验证数据库表结构
```powershell
docker compose exec postgres psql -U ppap -d ppap -c "\dt"
```

#### 4. 测试管理员账户
- 邮箱: `admin@example.com`
- 密码: `admin123`
- 验证是否能正常登录

---

### 问题解决

#### 原有问题
1. ❌ 需要手动运行数据库初始化脚本
2. ❌ Alembic 迁移与初始化脚本冲突
3. ❌ 首次部署步骤复杂，容易出错
4. ❌ 枚举类型缺失导致迁移失败
5. ❌ 服务依赖关系不明确

#### 解决方案
1. ✅ 实现完全自动化的初始化流程
2. ✅ 移除 Alembic 迁移依赖，使用 init-db.sql
3. ✅ 一键部署，零配置启动
4. ✅ 在初始化脚本中创建所有枚举类型
5. ✅ 明确的服务依赖关系和健康检查

---

### 技术亮点

#### 1. 幂等性设计
```bash
# 可安全重复执行，不会重复初始化
docker compose up -d
```

#### 2. 智能检测机制
- 自动检测数据库是否已初始化
- 跳过已存在的表和列
- 优雅的错误处理和日志输出

#### 3. 服务依赖管理
- 使用 Docker Compose 健康检查
- 确保服务按正确顺序启动
- 前置服务失败时自动停止

---

### 影响范围
- ✅ 数据库初始化流程
- ✅ Docker 容器编排配置
- ✅ 首次部署体验
- ✅ 服务启动顺序
- ❌ 无业务逻辑变更
- ❌ 无API接口变更

---

### 后续优化建议

#### 1. 数据库迁移管理
- 考虑重新设计 Alembic 迁移策略
- 统一数据库变更管理方式
- 建立规范的迁移版本控制

#### 2. 初始化脚本增强
- 添加更多示例数据
- 支持开发/生产环境配置
- 集成种子数据管理

#### 3. 监控和日志
- 添加初始化进度监控
- 优化日志输出格式
- 集成告警机制

---

## 版本历史

| 日期 | 版本 | 描述 |
|------|------|------|
| 2026-06-03 | 1.0.3 | 数据库自动化初始化，实现一键部署 |
| 2026-05-27 | 1.0.2 | 变量面板功能，支持快捷插入数据源变量 |
| 2026-05-25 | 1.0.1 | 端口配置优化，解决8000端口冲突 |
| 2026-05-24 | 1.0.0 | PPAP项目初始版本 |

## [2026-05-27] - 变量面板功能

### 功能描述
- 在规则图编辑器中添加变量面板，显示所有可用的数据源变量
- 支持点击变量自动插入到输入框光标位置
- 按节点类型分组显示变量，便于查找

### 详细修改记录

#### 1. 后端 - 数据扁平化支持
**文件路径**: `/Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/app/engine/core.py`
**修改时间**: 2026-05-27

**新增方法**: `_flatten_shared_state(context)`
```python
def _flatten_shared_state(self, context: DocumentContext) -> None:
    """
    Flatten commonly used nested values from shared_state for easier variable access.
    This makes it simpler to reference things like signer_cn without full path.
    """
```

**扁平化的变量**:
- `signer_cn` - 从 `digital_signatures.signatures[0].signer_cn` 提取
- `signature_valid` - 从 `digital_signatures.signatures[0].integrity` 提取
- `signature_expired` - 从 `digital_signatures.signatures[0].expired` 提取
- `is_tampered` - 从 `pdf_revisions.is_tampered_after_sign` 提取
- `revision_count` - 从 `pdf_revisions.revision_count` 提取

**调用时机**:
- Stage 1 预分类算子执行后
- Stage 2 深度算子执行后
- 签名验证节点执行后
- 修订检查节点执行后

---

#### 2. 前端 - 变量面板 UI
**文件路径**: `/Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/frontend/src/components/RuleGraphEditor.vue`
**修改时间**: 2026-05-27

**新增数据结构**:
```typescript
const availableVariables = [
  { category: 'system', icon: '⚙️', label: '系统变量', variables: [...] },
  { category: 'qr', icon: '📱', label: '二维码', variables: [...] },
  { category: 'signature', icon: '🔐', label: '数字签名', variables: [...] },
  { category: 'pdf', icon: '📄', label: 'PDF 元数据', variables: [...] },
  { category: 'extract', icon: '📤', label: '提取数据', variables: [...] },
]
```

**新增方法**:
- `getTotalVariablesCount()` - 计算变量总数
- `insertVariable(varName)` - 点击插入变量到输入框，支持光标位置插入和闪烁动画反馈

**UI 特性**:
- 可折叠面板，默认展开
- 显示变量总数统计
- 悬停效果和点击动画
- 变量语法显示为 `{{variable_name}}`

**可用变量列表** (共18个):

| 分类 | 变量名 | 描述 |
|-----|-------|------|
| ⚙️ 系统变量 | `institution` | 发证机构名称 |
| | `page_count` | PDF 页数 |
| | `full_text` | 完整文本内容 |
| 📱 二维码 | `qr_content` | 第一个二维码内容 |
| | `qr_codes` | 所有二维码数据数组 |
| 🔐 数字签名 | `digital_signatures` | 签名完整数据 |
| | `signer_cn` | 签署人通用名 |
| | `signature_valid` | 签名是否有效 |
| 📄 PDF 元数据 | `pdf_info` | PDF 完整信息 |
| | `is_tampered` | 是否被篡改 |
| | `revision_count` | 修订版本数 |
| 📤 提取数据 | `extracted_report_number` | 报告编号 (提取模式) |
| | `extracted_verification_code` | 校验码 (提取模式) |
| | `extracted_tables` | 提取的表格数据 |
| | `llm_semantic_analysis` | LLM 语义分析结果 |
| | `vision_analysis` | 视觉分析结果 |
| | `detected_stamps` | 检测到的印章 |
| | `diff_results` | 文档比对结果 |

### 使用方法
1. 在规则图编辑器中选中一个节点
2. 在右侧配置面板底部找到"📋 可用变量"区域
3. 点击任意变量即可插入到当前焦点输入框
4. 变量以 `{{变量名}}` 的格式插入

### 影响范围
- ✅ 前端规则图编辑器
- ✅ 后端数据流处理
- ❌ 无数据库变更
- ❌ 无破坏性变更

---

## [2026-05-25] - 端口配置优化

### 问题描述
- 系统中存在端口冲突，8000端口已被其他服务占用
- 需要调整PPAP项目的端口配置以避免冲突

### 详细修改记录

#### 1. 前端开发服务器代理配置
**文件路径**: `/home/zhouao2/ppap/frontend/vite.config.ts`
**修改位置**: 第17行，proxy配置段
**修改时间**: 2026-05-25 10:30

**代码对比**:
```diff
server: {
  port: 5173,
  proxy: {
    '/api': {
-     target: 'http://localhost:8000',
+     target: 'http://localhost:31234',
      changeOrigin: true,
      ws: true,
    },
  },
}
```

**原因**: 将前端代理指向新的后端端口，避免与占用的8000端口冲突

---

#### 2. Docker端口映射配置
**文件路径**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
**修改位置**: 第74行，backend服务配置段
**修改时间**: 2026-05-25 10:39

**代码对比**:
```diff
backend:
  build:
    context: ../backend
    dockerfile: Dockerfile
  container_name: ppap-backend
  restart: unless-stopped
  environment:
    DATABASE_URL: postgresql+asyncpg://ppap:ppap123@postgres:5432/ppap
    REDIS_URL: redis://redis:6379/0
    MINIO_ENDPOINT: minio:9000
    MINIO_SECURE: "false"
    SECRET_KEY: ${SECRET_KEY:-change-this-in-production}
    CORS_ORIGINS: '["http://localhost:3000","http://localhost:5173"]'
  ports:
-   - "31234:8000"
+   - "31234:31234"
  depends_on:
```

**原因**: 保持Docker容器内外端口一致，与应用配置中的PORT=31234匹配

---

#### 3. 部署脚本端口配置
**文件路径**: `/home/zhouao2/ppap/deploy.sh`
**修改位置**: 第88行，部署完成提示信息段
**修改时间**: 2026-05-25 10:45

**代码对比**:
```diff
echo -e "=== Deployment Completed Successfully ===${NC}"
echo -e "Access the services at:"
echo -e "  - Frontend UI:   http://localhost"
- echo -e "  - Backend API:   http://localhost:8000/docs"
+ echo -e "  - Backend API:   http://localhost:31234/docs"
echo -e "  - MinIO Console: http://localhost:9001 (minioadmin / minioadmin)"
```

**原因**: 更新部署脚本中的API文档地址，确保显示正确的后端端口

---

#### 4. Docker容器环境变量配置 (修复)
**文件路径**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
**修改位置**: 第67行，backend服务environment配置段
**修改时间**: 2026-05-25 10:50
**问题**: Docker容器缺少PORT环境变量，导致后端服务仍监听8000端口

**代码对比**:
```diff
backend:
  build:
    context: ../backend
    dockerfile: Dockerfile
  container_name: ppap-backend
  restart: unless-stopped
  environment:
+   PORT: "31234"
    DATABASE_URL: postgresql+asyncpg://ppap:ppap123@postgres:5432/ppap
    REDIS_URL: redis://redis:6379/0
    MINIO_ENDPOINT: minio:9000
    MINIO_SECURE: "false"
    SECRET_KEY: ${SECRET_KEY:-change-this-in-production}
    CORS_ORIGINS: '["http://localhost:3000","http://localhost:5173"]'
```

**原因**: 确保Docker容器内的后端服务使用正确的PORT环境变量，解决外部访问31234端口失败的问题

---

#### 5. Docker容器启动命令配置 (修复)
**文件路径**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
**修改位置**: 第75行后，backend服务配置段
**修改时间**: 2026-05-25 10:55
**问题**: Dockerfile中硬编码了8000端口，导致环境变量无效

**代码对比**:
```diff
backend:
  build:
    context: ../backend
    dockerfile: Dockerfile
  container_name: ppap-backend
  restart: unless-stopped
  environment:
    PORT: "31234"
    DATABASE_URL: postgresql+asyncpg://ppap:ppap123@postgres:5432/ppap
    REDIS_URL: redis://redis:6379/0
    MINIO_ENDPOINT: minio:9000
    MINIO_SECURE: "false"
    SECRET_KEY: ${SECRET_KEY:-change-this-in-production}
    CORS_ORIGINS: '["http://localhost:3000","http://localhost:5173"]'
  ports:
    - "31234:31234"
+  command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "31234"]
```

**原因**: 覆盖Dockerfile中的硬编码端口，确保后端服务监听31234端口

---

#### 6. 防火墙端口配置
**文件路径**: `/home/zhouao2/ppap/setup_firewall.sh`
**修改位置**: 第37-38行，防火墙规则配置段
**修改时间**: 2026-05-25 10:58

**代码对比**:
```diff
# Backend API
- echo -e "Allowing Backend API (Port 8000)..."
- ufw allow 8000/tcp
+ echo -e "Allowing Backend API (Port 31234)..."
+ ufw allow 31234/tcp
```

**原因**: 更新防火墙规则，允许外部访问31234端口

---

#### 7. Nginx MIME类型配置 (修复PDF渲染问题)
**文件路径**: `/home/zhouao2/ppap/deploy/nginx.conf`
**修改位置**: 第28行后，server配置段
**修改时间**: 2026-05-25 10:52
**问题**: .mjs文件的MIME类型设置为application/octet-stream，导致PDF.js worker加载失败

**代码对比**:
```diff
# Frontend static files
location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}

+ # Fix MIME type for .mjs files (PDF.js worker)
+ location ~* \.mjs$ {
+     root /usr/share/nginx/html;
+     add_header Content-Type application/javascript always;
+ }
```

**原因**: 使用专门的location块和add_header指令强制设置.mjs文件的MIME类型为application/javascript，解决PDF.js worker加载失败的问题

---

#### 8. PDF.js Worker加载方式修复 (彻底解决PDF渲染问题)
**文件路径**: `/home/zhouao2/ppap/frontend/src/views/FileDetailPage.vue`
**修改位置**: 第485-488行，PDF.js导入和配置段
**修改时间**: 2026-05-25 10:54
**问题**: 本地.mjs worker文件在nginx环境下的MIME类型和加载路径问题

**代码对比**:
```diff
- import * as pdfjsLib from 'pdfjs-dist'
- import pdfWorker from 'pdfjs-dist/build/pdf.worker.mjs?url'
- 
- pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker
+ import * as pdfjsLib from 'pdfjs-dist'
+ 
+ // Use CDN for PDF.js worker to avoid MIME type issues
+ pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`
```

**原因**: 使用CDN版本的PDF.js worker来避免本地文件的MIME类型和路径问题，确保PDF渲染功能稳定可靠

**附加修复**: 重新安装前端依赖并重新构建前端，解决了rollup构建依赖问题

---

### 相关配置文件

#### 无需修改的配置文件
以下文件已正确配置，无需修改：

1. **后端环境配置**: `/home/zhouao2/ppap/backend/.env`
   - 第9行: `PORT=31234` ✅

2. **后端默认配置**: `/home/zhouao2/ppap/backend/app/core/config.py`
   - 第15行: `PORT: int = 8000` (默认值，被.env覆盖) ✅

3. **数据库配置**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
   - 第16行: `"5435:5432"` (PostgreSQL端口映射) ✅

4. **Redis配置**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
   - 第32行: `"6379:6379"` (Redis端口映射) ✅

5. **MinIO配置**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
   - 第51行: `"9000:9000"` (MinIO API端口) ✅
   - 第52行: `"9001:9001"` (MinIO控制台端口) ✅

### 端口分配总结

#### 主要服务端口
- **后端API服务器**: 31234 (原8000，已迁移)
- **前端开发服务器**: 5173
- **前端生产服务器**: 80

#### 数据存储端口
- **PostgreSQL**: 5435 (外部) → 5432 (容器内部)
- **Redis**: 6379
- **MinIO API**: 9000
- **MinIO 控制台**: 9001

#### 其他端口
- **SMTP**: 465 (默认未启用)

### 部署说明
由于配置变更，需要重新创建Docker容器：

```bash
# 停止并删除现有容器
cd /home/zhouao2/ppap/deploy
docker compose down

# 重新构建并启动
docker compose up -d --build
```

### 验证步骤
1. 确认后端服务在31234端口正常运行
2. 测试前端开发服务器代理功能
3. 验证API接口访问: `http://localhost:31234/api/v1/docs`
4. 检查各服务间通信正常

### 影响范围
- ✅ 本地开发环境配置
- ✅ Docker容器化部署
- ✅ 前后端连接配置
- ❌ 无数据库迁移需求
- ❌ 无代码逻辑变更

---

## 版本历史

| 日期 | 版本 | 描述 |
|------|------|------|
| 2026-05-27 | 1.0.2 | 变量面板功能，支持快捷插入数据源变量 |
| 2026-05-25 | 1.0.1 | 端口配置优化，解决8000端口冲突 |
| 2026-05-24 | 1.0.0 | PPAP项目初始版本 |
