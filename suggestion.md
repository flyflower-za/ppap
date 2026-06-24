# PPAP 项目优化建议

> 生成时间: 2026-06-24
> 审计范围: Backend (FastAPI), Frontend (Vue 3), 部署/基础设施

---

## 一、安全问题 (Critical)

### 1.1 登录接口未校验密码
- **文件**: `backend/app/api/auth.py`
- **问题**: 登录接口仅根据邮箱查找用户，从未调用 `verify_password()`。密码字段实际上被忽略，任何人只要知道邮箱即可登录。
- **建议**: 添加 `verify_password(credentials.password, user.password_hash)` 校验，并确保 User 模型包含 `password_hash` 字段。

### 1.2 基于邮箱自动推断角色
- **文件**: `backend/app/api/auth.py`
- **问题**: 邮箱包含 "admin" 即赋予 ADMIN 角色（如 `admin@evil.com`），包含 "manager" 即赋予 MANAGER 角色。
- **建议**: 自动创建的用户默认赋 USER 角色。角色分配应由 SSO Claim 映射或管理员显式配置。

### 1.3 硬编码默认密钥
- **文件**: `backend/app/core/config.py`, `deploy/docker-compose.yml`, `deploy/.env`
- **问题**: `DATABASE_URL` 默认包含 `ppap:ppap123`，`SECRET_KEY` 默认为 `"your-secret-key-change-in-production"`，MinIO 默认 `minioadmin/minioadmin`。
- **建议**: 所有密钥移除默认值，启动时检测未配置则报错。部署脚本应自动生成随机密钥或校验是否仍为默认值。

### 1.4 MinIO Bucket 设为 public
- **文件**: `deploy.sh`, `deploy.ps1`
- **问题**: `mc anonymous set public ppapminio/ppap-files` 使所有上传的 PDF 可被任何人通过 URL 下载。
- **建议**: 改为 `private` 或 `download`（仅预签名 URL 可访问）。

### 1.5 Redis 未鉴权且暴露到宿主机
- **文件**: `deploy/docker-compose.yml`
- **问题**: Redis 端口 6379 映射到宿主机且无密码认证，是常见攻击入口。
- **建议**: 移除端口映射（容器间通过 Docker 网络通信）。如需宿主机访问，添加 `--requirepass`。

### 1.6 OIDC 回调未校验 state 参数
- **文件**: `backend/app/api/oidc.py`
- **问题**: 生成了 `state` 参数但回调时未校验，存在 CSRF 攻击风险。
- **建议**: 在 Redis/session 中存储 state，回调时比对，不匹配则拒绝。

### 1.7 WebSocket 通过 Query 参数传递 Token
- **文件**: `backend/app/api/websocket.py`
- **问题**: Token 出现在 URL 中，会被记录到服务器访问日志、代理日志、浏览器历史。
- **建议**: 通过 WebSocket subprotocol header 或连接后第一条消息传递 token。

---

## 二、性能问题 (High)

### 2.1 Celery 任务中 dispose 共享的 SQLAlchemy Engine
- **文件**: `backend/app/tasks/verification_tasks.py`
- **问题**: `finally` 块中 `await engine.dispose()` 销毁了全局共享的 engine，影响其他并发任务。
- **建议**: 使用异步 Celery worker 或每任务独立的 session，绝不在 finally 中销毁全局 engine。

### 2.2 统计查询加载 1000 条完整 JSON 到内存
- **文件**: `backend/app/api/files.py`
- **问题**: `select(File.verification_result)` 加载 1000 条完整 JSON 文本列，在 Python 中逐条解析计数。
- **建议**: 使用 PostgreSQL `jsonb` 操作符在数据库层面聚合，或至少减小 limit 并分批处理。

### 2.3 同步 MinIO 客户端阻塞异步事件循环
- **文件**: `backend/app/core/minio_client.py`
- **问题**: 使用同步 `minio.Minio` SDK，文件上传/下载阻塞事件循环。
- **建议**: 使用 `run_in_executor` 将 MinIO 操作放入线程池，或使用异步 MinIO 客户端。

### 2.4 N+1 查询模式
- **文件**: `backend/app/services/file_service.py`
- **问题**: 获取文件详情时对 User 表单独查询，列表操作时为 N+1。
- **建议**: 使用 `selectinload(File.uploaded_by_user)` 或 join 预加载。

### 2.5 前端固定 2 秒轮询
- **文件**: `frontend/src/components/TaskList.vue`
- **问题**: `setInterval(fetchTasks, 2000)` 持续轮询，多标签页时成倍增加请求。
- **建议**: 使用指数退避轮询，或切换到 WebSocket/SSE 推送。至少仅对 "processing" tab 轮询。

### 2.6 URLFetchOperator 临时文件未清理
- **文件**: `backend/app/engine/operators/url_fetch_operator.py`
- **问题**: `tempfile.mkstemp()` 创建的临时文件从未清理，长期运行会填满磁盘。
- **建议**: 使用 `with tempfile.NamedTemporaryFile(...)` 上下文管理器或在 finally 中清理。

---

## 三、代码质量问题 (Medium)

### 3.1 VerificationEngine 超大类 (1355+ 行)
- **文件**: `backend/app/engine/core.py`
- **问题**: 单一类负责预分类、机构匹配、规则过滤、算子调度、规则评估、DAG 执行、变量插值、HTTP 调用、统计汇总。
- **建议**: 拆分为 `RuleRouter`、`OperatorScheduler`、`RuleEvaluator`、`DAGExecutor`、`VariableInterpolator`。

### 3.2 RuleGraphEditor 与 FullscreenRuleEditor 大量重复
- **文件**: `frontend/src/components/RuleGraphEditor.vue` (2426行) 与 `frontend/src/views/FullscreenRuleEditor.vue` (1991行)
- **问题**: 两份文件共享大量相同代码：节点注册、变量系统、dry-run 逻辑等。
- **建议**: 提取为 `useGraphEditor.ts` composable + 单一组件。全屏版仅改变布局（移除 inspector 侧边栏宽度限制）。

### 3.3 SettingsPage.vue 超大组件 (2647 行)
- **文件**: `frontend/src/views/SettingsPage.vue`
- **问题**: 包含个人资料、通知、文件保留、SMTP、邮件模板、LDAP/SSO、用户管理、用户组、AI 模型配置等所有功能。
- **建议**: 拆分为 `SmtpConfig.vue`、`LdapConfig.vue`、`UserManagement.vue`、`AiModelConfig.vue` 等子组件。

### 3.4 重复的状态/文本映射函数
- **文件**: `TaskList.vue`、`HistoryPage.vue`、`FileDetailPage.vue`
- **问题**: 多处独立定义 `statusText()`、`getFileStatusTag()`、`formatDate()` 等相同逻辑。
- **建议**: 提取到 `src/utils/formatters.ts` 或 `useFileFormatting.ts` composable。

### 3.5 AI 配置加载重复代码
- **文件**: `backend/app/engine/operators/text_llm_operator.py` 与 `vision_llm_operator.py`
- **问题**: `_get_ai_config()` 函数在两个文件中几乎完全重复。
- **建议**: 提取到 `app/services/ai_config_service.py`。

### 3.6 模型时间戳类型不一致
- **文件**: `backend/app/models/verification_module.py`
- **问题**: `VerificationModule` 和 `RuleModule` 使用 `Integer` (Unix 时间戳) 存储时间，其他模型使用 `DateTime`。
- **建议**: 统一为 `DateTime`。

### 3.7 UUID 存储为字符串
- **文件**: 多个 model 文件
- **问题**: `UUID(as_uuid=False)` 将 UUID 存为字符串，丢失数据库级校验和索引效率。
- **建议**: 使用 `UUID(as_uuid=True)` 或 PostgreSQL 原生 UUID 类型。

### 3.8 错误响应格式不一致
- **文件**: `backend/app/main.py` 与各 API 路由
- **问题**: 全局异常处理器返回 `{"error": true, "message": "...", "code": ...}`，而 HTTPException 返回 `{"detail": "..."}`。
- **建议**: 统一错误响应 schema。

### 3.9 多处 TODO 未实现管理员检查
- **文件**: `backend/app/api/settings.py`
- **问题**: 多处标注 `# TODO: Check if user is admin` 但仍使用 `get_current_user`。
- **建议**: 替换为 `get_current_admin`。

### 3.10 全局可变 Engine 实例
- **文件**: `backend/app/api/modules.py`
- **问题**: 模块级 `engine = VerificationEngine()` 被所有请求和测试共享。
- **建议**: 每请求创建实例或使用依赖注入。

---

## 四、前端问题 (Medium)

### 4.1 大量使用 `any` 类型
- **文件**: 几乎每个 `.ts` 和 `.vue` 文件
- **问题**: TypeScript 类型安全形同虚设，后端字段变更只能在运行时发现。
- **建议**: 为每个 API 端点定义响应接口，启用 `tsconfig.json` 的 `strict: true`，添加 `@typescript-eslint/no-explicit-any` 规则。

### 4.2 401 处理器使用硬跳转
- **文件**: `frontend/src/api/client.ts`
- **问题**: `window.location.href = '/login'` 导致整页刷新，丢失所有应用状态。
- **建议**: 使用 `router.push('/login')`。

### 4.3 通知"全部已读"未调用 API
- **文件**: `frontend/src/views/NotificationsPage.vue`
- **问题**: 仅设置 `hasUnread.value = false` 并显示成功消息，未实际调用后端接口。
- **建议**: 调用批量标记已读的后端接口。

### 4.4 MainLayout 未读数永远为 0
- **文件**: `frontend/src/layouts/MainLayout.vue`
- **问题**: `const unreadCount = ref(0)` 初始化后从未更新，通知角标永远不显示。
- **建议**: 连接 notification store 或定时查询未读数量。

### 4.5 全局错误处理器重复弹 toast
- **文件**: `frontend/src/api/client.ts`
- **问题**: 每个失败请求都触发 `ElMessage.error`，多请求失败时堆叠显示，组件自身又再弹一次。
- **建议**: 让全局处理器可选（如 `config.skipGlobalError = true`），组件自行决定是否展示用户可见的错误。

### 4.6 请求无取消机制
- **文件**: 所有组件
- **问题**: 用户离开页面时进行中的请求仍会处理，可能更新已卸载组件状态。
- **建议**: 在 axios 实例中集成 AbortController，路由切换/组件卸载时取消请求。

### 4.7 Element Plus 全量引入
- **文件**: `frontend/src/main.ts`
- **问题**: `app.use(ElementPlus)` 导入整个库 (~500KB+)，实际只用到一小部分。
- **建议**: 使用 `unplugin-auto-import` + `unplugin-vue-components` 按需导入。

### 4.8 无响应式设计
- **文件**: `frontend/src/styles/main.css`
- **问题**: `.page-container { min-width: 1200px; }` 在窄屏下强制横向滚动条。
- **建议**: 添加响应式断点，使用流式布局。

---

## 五、基础设施问题 (Medium)

### 5.1 无容器资源限制
- **文件**: `deploy/docker-compose.yml`
- **问题**: 所有服务无 `deploy.resources.limits`，单个 PDF 处理进程可能耗尽内存导致全部容器崩溃。
- **建议**: 为每个服务添加内存/CPU 限制：
  ```yaml
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '1.0'
  ```

### 5.2 无健康检查 (后端/前端/Celery)
- **文件**: `deploy/docker-compose.yml`
- **问题**: 仅 postgres/redis/minio 有 healthcheck，后端崩溃时 Docker 无法感知。
- **建议**: 添加后端健康检查：
  ```yaml
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:31234/health"]
  ```

### 5.3 无日志轮转
- **文件**: `deploy/docker-compose.yml`
- **问题**: Docker 默认 json-file 驱动无大小限制，日志会持续增长填满磁盘。
- **建议**: 添加全局日志配置：
  ```yaml
  logging:
    driver: json-file
    options:
      max-size: "10m"
      max-file: "3"
  ```

### 5.4 Nginx 缺少安全头部和 HTTPS
- **文件**: `deploy/nginx.conf`
- **问题**: 仅监听 80 端口，无 `X-Content-Type-Options`、`X-Frame-Options`、`Strict-Transport-Security` 等安全头。
- **建议**: 添加 443 SSL 配置并重定向 80→443，添加完整安全头部。

### 5.5 Nginx 无速率限制
- **文件**: `deploy/nginx.conf`
- **问题**: 无 `limit_req` 配置，API 端点对暴力登录和爬虫完全开放。
- **建议**: 添加：
  ```nginx
  limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
  ```

### 5.6 防火墙缺少默认拒绝策略
- **文件**: `setup_firewall.sh`
- **问题**: 仅添加允许规则，未设置 `ufw default deny incoming`。
- **建议**: 在允许规则之前添加默认拒绝策略和 `ufw logging on`。

### 5.7 JWT 有效期过长 (24小时)
- **文件**: `backend/.env.example`
- **问题**: `ACCESS_TOKEN_EXPIRE_MINUTES=1440`，token 泄漏后 24 小时内有效。
- **建议**: 缩短至 60-120 分钟，实现 refresh token 机制。

### 5.8 PostgreSQL 端口暴露到宿主机
- **文件**: `deploy/docker-compose.yml`
- **问题**: `ports: - "5435:5432"` 将数据库暴露到宿主机。
- **建议**: 移除端口映射，仅通过 Docker 内部网络访问。

### 5.9 Backend Dockerfile 非多阶段构建
- **文件**: `backend/Dockerfile`
- **问题**: 单阶段构建将 pytest、black、ruff 等开发依赖打包进最终镜像。
- **建议**: 使用多阶段构建，仅保留运行时依赖。

---

## 六、运维与 CI/CD (Medium)

### 6.1 无 CI/CD 流水线
- **问题**: 无 `.github/workflows/` 或任何 CI 配置，无自动化测试/构建/部署。
- **建议**: 添加 GitHub Actions 工作流：
  - 后端: `pytest`, `ruff check`
  - 前端: `npm run lint`, `npm run build`
  - 集成: `docker compose up -d` + 健康检查

### 6.2 无自动备份策略
- **问题**: 仅 `deploy/README.md` 中有手动 `pg_dump` 说明，无自动化备份。
- **建议**: 添加备份脚本定时执行 `pg_dump` 和 MinIO 数据备份，存储到远程位置。

### 6.3 开发依赖混入生产 requirements
- **文件**: `backend/requirements.txt`
- **问题**: `pytest`、`black`、`ruff` 与生产依赖在同一文件。
- **建议**: 拆分为 `requirements.txt` (prod) 和 `requirements-dev.txt` (dev)。

### 6.4 依赖版本不一致
- **文件**: `backend/requirements.txt`
- **问题**: 部分包精确锁定 (`redis==5.0.1`)，部分使用最小版本 (`fastapi>=0.109.0`)。
- **建议**: 统一精确锁定版本，或使用 `pip-tools`/`poetry` 管理。

---

## 七、配置问题 (Low)

### 7.1 DEBUG 模式默认为 True
- **文件**: `backend/app/core/config.py`
- **问题**: `DEBUG: bool = True`，未显式设置时会输出所有 SQL 查询到 stdout。
- **建议**: 默认改为 `False`。

### 7.2 APP_BASE_URL 默认为 localhost
- **文件**: `backend/app/core/config.py`
- **问题**: 用于 OIDC 回调，生产环境未配置时会回调到 localhost。
- **建议**: 移除默认值，要求通过环境变量设置。

### 7.3 文件保留期限三处定义
- **文件**: `config.py` (FILE_RETENTION_DAYS=30), `cleanup_tasks.py` (默认30), `file_service.py` (硬编码30)
- **建议**: 统一使用 `settings.FILE_RETENTION_DAYS`。

### 7.4 deploy/README.md 内容过时
- **问题**: 引用后端端口 8000 (已改为 31234)，使用旧版 `docker-compose` 命令。
- **建议**: 更新为当前配置。

### 7.5 缺少架构图和运维手册
- **问题**: 无服务间通信拓扑图，无凭证轮换/故障排查/升级指南。
- **建议**: 创建 `project_doc/runbooks/` 和架构图文档。

---

## 优化优先级总结

| 优先级 | 数量 | 关键项 |
|--------|------|--------|
| **Critical** | 7 | 已全部完成 ✅ |
| **High** | 6 | 已全部完成 ✅ |
| **Medium** | 28 | 超大类/组件、代码重复、`any` 类型、安全头部、资源限制、健康检查、日志轮转、CI/CD |
| **Low** | 5 | DEBUG 默认值、BASE_URL 默认值、过时文档、缺少架构图 |

---

## 建议实施路线图

### 第一阶段 (安全加固)
1. 修复登录密码校验
2. 移除邮箱角色推断
3. 密钥默认值移除 + 启动检查
4. MinIO bucket 改为 private
5. Redis 移除端口映射 + 添加鉴权
6. OIDC state 校验
7. Nginx 安全头部 + HTTPS

### 第二阶段 (性能与稳定性) — 全部完成 ✅
8. ~~修复 Celery engine.dispose~~ ✅
9. ~~优化统计查询~~ ✅
10. ~~添加容器资源限制和健康检查~~ ✅ (合并至跨平台优化)
11. ~~添加日志轮转~~ ✅ (合并至跨平台优化)
12. ~~同步 MinIO 阻塞事件循环~~ ✅
13. ~~N+1 查询优化~~ ✅
14. ~~前端轮询优化~~ ✅
15. ~~临时文件清理~~ ✅

### 第三阶段 (代码质量)
14. 拆分超大类/组件
15. 消除重复代码
16. TypeScript 严格模式
17. 统一错误响应格式
18. Element Plus 按需导入

### 第四阶段 (运维完善)
19. CI/CD 流水线
20. 自动备份策略
21. 依赖版本管理
22. 文档更新 + 运维手册

---

## 八、跨平台部署改进方案 (P0-P2)

> 适用场景：Linux / macOS / Windows 三平台间切换开发和测试
> 最后更新: 2026-06-24
> 状态: ✅ 全部 6 项已完成

### 8.0 当前跨平台断点分析

| # | 断点 | Linux | macOS | Windows | 根因 | 状态 |
|---|------|-------|-------|---------|------|------|
| 1 | MinIO bucket 创建 (`docker run --network container:`) | ✅ | ⚠️ | ❌ | Windows Docker Desktop 不支持 container 网络模式 | ✅ 已修复 |
| 2 | Frontend nginx.conf 依赖 volume mount | ✅ | ⚠️ | ❌ | macOS/Windows 文件同步慢且不可靠 | ✅ 已修复 |
| 3 | 密码硬编码在 docker-compose 和脚本中 | ⚠️ | ⚠️ | ⚠️ | 三平台共用同一套弱密钥 | ✅ 已修复 |
| 4 | 健康检查硬编码 `localhost` | ✅ | ⚠️ | ⚠️ | 远程服务器/端口转发场景失败 | ✅ 已修复 |
| 5 | deploy.ps1 依赖 `git rev-parse` | — | ✅ | ⚠️ | zip 下载或 CI 环境失败 | ✅ 已修复 |

---

### ~~改进 1：MinIO bucket 创建容器化~~ [P0] ✅ 已完成

**修改内容**：
- `deploy/docker-compose.yml`：新增 `minio-init` 服务，依赖 minio healthcheck，`restart: "no"`
- `deploy.sh`：删除 `docker run --rm --network container:ppap-minio` 代码，改为轮询容器状态
- `deploy.ps1`：PowerShell 等效修改
- 权限从 `public` 改为 `download`（仅预签名 URL 可访问）

**效果**：完全在 Docker 内部网络执行，三平台行为一致。

---

### ~~改进 2：前端 Dockerfile 内置 nginx.conf~~ [P0] ✅ 已完成

**修改内容**：
- `frontend/nginx.conf`：新增文件，从 `deploy/nginx.conf` 复制
- `frontend/Dockerfile`：添加 `COPY nginx.conf /etc/nginx/nginx.conf`（内置配置）
- `deploy/docker-compose.yml`：frontend volume 标注为 optional

**效果**：镜像可独立运行 `docker run -p 80:80 ppap-frontend`，不再依赖 volume mount 文件同步。

---

### ~~改进 3：密钥自动生成~~ [P1] ✅ 已完成

**修改内容**：
- `deploy.sh`：首次部署用 `openssl rand` 自动生成强密钥（SECRET_KEY 64位 hex，密码 20 位随机字符），自动区分 macOS/Linux 的 `sed` 语法差异
- `deploy.ps1`：使用 `Get-Random` 生成等效随机密钥
- `deploy/docker-compose.yml`：所有硬编码密码替换为 `${VAR}` 引用：
  - `ppap123` → `${POSTGRES_PASSWORD}`（postgres/backend/celery-worker/db-init）
  - `minioadmin` → `${MINIO_ROOT_USER}` / `${MINIO_ROOT_PASSWORD}`
  - `${SECRET_KEY:-change-this-in-production}` → `${SECRET_KEY}`
- 旧 `.env` 存在时复用已有密钥，不重新生成

**效果**：首次部署自动生成强密钥，后续复用。compose 中不再暴露明文密码。

---

### 改进 4：健康检查环境变量化 [P1] ⏳ 待实施

**问题**：`curl -sf http://localhost:31234/docs` 硬编码 localhost，远程服务器/SSH 端口转发场景失败。

**方案**：

**deploy.sh 顶部新增**：

```bash
# 可配置的主机和端口（默认 localhost）
API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-31234}"
MINIO_PORT="${MINIO_PORT:-9000}"
```

所有 curl 检查替换为变量（如 `http://${API_HOST}:${API_PORT}/docs`）。

**deploy.ps1** 使用 `$env:API_HOST ?? "localhost"` 等效替换。

---

### 改进 5：db-init 改用环境变量 [P2] ⏳ 待实施

> 注：改进 3 已将 compose 中 `PGPASSWORD=ppap123` 替换为 `${POSTGRES_PASSWORD}`。
> 剩余未完成项：`init-db.sql` 中 admin 密码 `admin123` 仍为硬编码，如需完全统一需 SQL 模板化（复杂度较高）。

---

### 改进 6：deploy.ps1 移除 git 依赖 [P2] ⏳ 待实施

**问题**：`git rev-parse --show-toplevel` 在非 git 克隆环境（zip 下载、CI/CD pipeline）中失败。

**方案**：用 `$PSScriptRoot | Split-Path -Parent` 获取项目根目录，仅在 `.git` 目录存在时调用 git。

---

### 改进前后对比

| 场景 | 改进前 | 改进后 |
|------|--------|--------|
| **Windows 首次部署** | MinIO bucket 创建失败 | ✅ 通过 compose 服务完成 |
| **macOS 文件同步** | volume mount 慢/卡 | ✅ 镜像内置配置，volume 仅用于覆盖 |
| **三平台密钥** | 统一弱密码 ppap123 | ✅ 自动生成强密钥 |
| **远程服务器部署** | localhost 检查失败 | ✅ 可通过 API_HOST 指定 |
| **Windows zip 部署** | git 命令报错 | ✅ 优雅降级 |
| **旧 .env 兼容** | — | ✅ 环境变量引用 + fallback |
| **MinIO 安全** | bucket 设为 public | ✅ 改为 download（仅预签名 URL） |

---

### 跨平台兼容性矩阵（改进后）

| 平台 | 改进前 | 改进后 | 说明 |
|------|--------|--------|------|
| **Ubuntu/Debian (amd64)** | ✅ 完全支持 | ✅ 完全支持 | 最佳体验 |
| **macOS (Intel)** | ✅ 基本可用 | ✅ 完全支持 | volume mount 问题消除 |
| **macOS (Apple Silicon)** | ⚠️ 需测试 | ✅ 基本可用 | Docker Desktop 原生支持 |
| **Windows 10/11** | ⚠️ MinIO 失败 | ✅ 完全支持 | container 网络模式问题消除 |
| **WSL2 (Ubuntu)** | ⚠️ 需调整 | ✅ 基本可用 | localhost 可配置 |
| **远程服务器** | ❌ localhost 不通 | ✅ 可配置 | API_HOST 环境变量 |

---

### 实施进度

| 阶段 | 改进项 | 涉及文件 | 状态 |
|------|--------|----------|------|
| **P0** | MinIO 容器化 | docker-compose.yml, deploy.sh, deploy.ps1 | ✅ |
| **P0** | 前端内置 nginx.conf | frontend/Dockerfile, frontend/nginx.conf | ✅ |
| **P1** | 密钥自动生成 (+ Redis) | deploy.sh, deploy.ps1, docker-compose.yml, .env.example, .env | ✅ |
| **P1** | 健康检查环境变量化 | deploy.sh, deploy.ps1 | ✅ |
| **P2** | db-init admin 密码模板化 | deploy.sh, deploy.ps1 | ✅ |
| **P2** | deploy.ps1 去 git 化 | deploy.ps1 | ✅ |

> 跨平台部署 6 项全部完成。三平台部署、密钥安全、远程访问、zip 部署全部支持。

**问题**：`docker run --network container:ppap-minio` 在 Windows Docker Desktop 上不可用。

**方案**：将 `minio/mc` 作为 compose 临时服务，通过 Docker 内部网络执行：

```yaml
# deploy/docker-compose.yml 新增服务
  minio-init:
    image: minio/mc:latest
    container_name: ppap-minio-init
    command: >
      sh -c "
      mc alias set ppapminio http://minio:9000 ${MINIO_ROOT_USER:-minioadmin} ${MINIO_ROOT_PASSWORD:-minioadmin} &&
      mc mb ppapminio/ppap-files --ignore-existing &&
      mc anonymous set download ppapminio/ppap-files
      "
    depends_on:
      minio:
        condition: service_healthy
    restart: "no"
```

**配套修改**：删除 `deploy.sh` 和 `deploy.ps1` 中约 20 行 `docker run --rm --network container:ppap-minio` 相关代码。

**效果**：完全在 Docker 内部网络执行，三平台行为一致，`restart: "no"` 确保执行一次后退出。

---

### ~~改进 2：前端 Dockerfile 内置 nginx.conf~~ [P0] ✅ 已完成

**修改内容**：
- `frontend/nginx.conf`：新增文件，从 `deploy/nginx.conf` 复制
- `frontend/Dockerfile`：添加 `COPY nginx.conf /etc/nginx/nginx.conf`（内置配置）
- `deploy/docker-compose.yml`：frontend volume 标注为 optional

**效果**：镜像可独立运行 `docker run -p 80:80 ppap-frontend`，不再依赖 volume mount 文件同步。

---

### ~~改进 3：密钥自动生成~~ [P1] ✅ 已完成

**修改内容**：
- `deploy.sh`：首次部署用 `openssl rand` 自动生成强密钥（SECRET_KEY 64位 hex，密码 20 位随机字符），自动区分 macOS/Linux 的 `sed` 语法差异
- `deploy.ps1`：使用 `Get-Random` 生成等效随机密钥
- `deploy/docker-compose.yml`：所有硬编码密码替换为 `${VAR}` 引用：
  - `ppap123` → `${POSTGRES_PASSWORD}`（postgres/backend/celery-worker/db-init）
  - `minioadmin` → `${MINIO_ROOT_USER}` / `${MINIO_ROOT_PASSWORD}`
  - `${SECRET_KEY:-change-this-in-production}` → `${SECRET_KEY}`
- 旧 `.env` 存在时复用已有密钥，不重新生成

**效果**：首次部署自动生成强密钥，后续复用。compose 中不再暴露明文密码。

---

### 改进 4：健康检查环境变量化 [P1] ⏳ 待实施

**问题**：`curl -sf http://localhost:31234/docs` 硬编码 localhost，远程服务器/SSH 端口转发场景失败。

**方案**：

**deploy.sh 顶部新增**：

```dockerfile
# 生产阶段修改
FROM nginx:alpine

# 内置配置文件（volume mount 可覆盖，但有默认值）
COPY nginx.conf /etc/nginx/nginx.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Step 3**：`docker-compose.yml` 中 volume 改为可选（开发环境可保留用于热更新配置）：

```yaml
frontend:
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro  # 可选：覆盖内置配置
```

**效果**：
- 镜像可独立运行：`docker run -p 80:80 ppap-frontend`
- Windows/macOS 不再依赖 volume mount 文件同步
- 开发环境仍可通过 volume 覆盖配置

---

### 改进 3：密钥自动生成 [P1]

**问题**：三平台共用 `ppap123` / `minioadmin` 等弱密钥，安全风险高。

**方案**：deploy 脚本首次运行时自动生成强密钥写入 `.env`，后续复用。

**deploy.sh 修改**（在设置环境变量步骤）：

```bash
if [ ! -f .env ]; then
    cp .env.example .env
    
    # 自动生成密钥
    if command -v openssl &> /dev/null; then
        GENERATED_SECRET=$(openssl rand -hex 32)
        GENERATED_DB_PASS=$(openssl rand -base64 16 | tr -d '/+==' | head -c 20)
        GENERATED_MINIO_PASS=$(openssl rand -base64 16 | tr -d '/+==' | head -c 20)
        
        # macOS sed 需要空字符串参数，Linux 不需要
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i'' -e "s/^SECRET_KEY=.*/SECRET_KEY=${GENERATED_SECRET}/" .env
            sed -i'' -e "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${GENERATED_DB_PASS}/" .env
            sed -i'' -e "s/^MINIO_ROOT_PASSWORD=.*/MINIO_ROOT_PASSWORD=${GENERATED_MINIO_PASS}/" .env
        else
            sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${GENERATED_SECRET}/" .env
            sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${GENERATED_DB_PASS}/" .env
            sed -i "s/^MINIO_ROOT_PASSWORD=.*/MINIO_ROOT_PASSWORD=${GENERATED_MINIO_PASS}/" .env
        fi
    fi
    
    echo -e "${GREEN}[+] Created .env with auto-generated secrets${NC}"
fi
```

**deploy.ps1 修改**：

```powershell
if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    
    # 自动生成密钥
    $secretKey = -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })
    $dbPass = -join ((1..20) | ForEach-Object { "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"[(Get-Random -Maximum 62)] })
    $minioPass = -join ((1..20) | ForEach-Object { "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"[(Get-Random -Maximum 62)] })
    
    (Get-Content $envFile) -replace '^SECRET_KEY=.*', "SECRET_KEY=$secretKey" | Set-Content $envFile
    (Get-Content $envFile) -replace '^POSTGRES_PASSWORD=.*', "POSTGRES_PASSWORD=$dbPass" | Set-Content $envFile
    (Get-Content $envFile) -replace '^MINIO_ROOT_PASSWORD=.*', "MINIO_ROOT_PASSWORD=$minioPass" | Set-Content $envFile
    
    Write-Success "[+] Created .env with auto-generated secrets"
}
```

**docker-compose.yml 同步修改**：所有硬编码密码改为 `${VAR}` 引用：

```yaml
postgres:
  environment:
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

backend:
  environment:
    DATABASE_URL: postgresql+asyncpg://ppap:${POSTGRES_PASSWORD}@postgres:5432/ppap
    SECRET_KEY: ${SECRET_KEY}

minio:
  environment:
    MINIO_ROOT_USER: ${MINIO_ROOT_USER}
    MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}

celery-worker:
  environment:
    DATABASE_URL: postgresql+asyncpg://ppap:${POSTGRES_PASSWORD}@postgres:5432/ppap
```

**效果**：
- 首次部署自动生成强密钥（SECRET_KEY 64 位 hex，密码 20 位随机字符）
- 后续部署复用 `.env`，不会重新生成
- 旧 `.env` 仍兼容（需保留 fallback 机制用于迁移过渡期）

---

### 改进 4：健康检查环境变量化 [P1]

**问题**：`curl -sf http://localhost:31234/docs` 硬编码 localhost，远程服务器/SSH 端口转发场景失败。

**方案**：

**deploy.sh 顶部新增**：

```bash
# 可配置的主机和端口（默认 localhost）
API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-31234}"
MINIO_PORT="${MINIO_PORT:-9000}"
```

**所有 curl 检查替换为变量**：

```bash
# Before
until curl -sf http://localhost:31234/docs > /dev/null 2>&1
# After
until curl -sf http://${API_HOST}:${API_PORT}/docs > /dev/null 2>&1

# Before
until curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1
# After
until curl -sf http://${API_HOST}:${MINIO_PORT}/minio/health/live > /dev/null 2>&1
```

**deploy.ps1 修改**：

```powershell
$apiHost = $env:API_HOST ?? "localhost"
$apiPort = $env:API_PORT ?? "31234"
$minioPort = $env:MINIO_PORT ?? "9000"

# 所有 Invoke-WebRequest 替换为变量
$response = Invoke-WebRequest -Uri "http://$apiHost`:$apiPort/docs" -UseBasicParsing -TimeoutSec 2
$response = Invoke-WebRequest -Uri "http://$apiHost`:$minioPort/minio/health/live" -UseBasicParsing -TimeoutSec 2
```

**使用场景**：

```bash
# 本地测试（默认行为不变）
bash deploy.sh

# 远程服务器通过 SSH 端口转发
API_HOST=127.0.0.1 bash deploy.sh

# 指定非标准端口
API_PORT=8080 bash deploy.sh

# PowerShell 等效
$env:API_HOST="127.0.0.1"; .\deploy.ps1
```

---

### 改进 5：db-init 改用环境变量 [P2]

**问题**：`PGPASSWORD=ppap123` 硬编码在 docker-compose.yml 中。

**方案**：

```yaml
db-init:
  environment:
    PGPASSWORD: ${POSTGRES_PASSWORD}
  command: >
    sh -c "
    psql -h postgres -U ppap -d ppap -c 'SELECT 1 FROM users' > /dev/null 2>&1 ||
    (echo 'Initializing database schema...' && psql -h postgres -U ppap -d ppap < /docker-entrypoint-initdb.d/init-db.sql)
    "
```

**注意**：`init-db.sql` 中默认 admin 密码仍为硬编码值（`admin123`），如需完全统一，可将 SQL 模板化（用 `envsubst` 或 sed 预处理），但复杂度较高，建议作为后续改进。

---

### 改进 6：deploy.ps1 移除 git 依赖 [P2]

**问题**：`git rev-parse --show-toplevel` 在非 git 克隆环境（zip 下载、CI/CD pipeline）中失败。

**方案**：

```powershell
# 获取项目根目录（不依赖 git）
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path -Parent $scriptDir

# 检测代码变更（仅当 .git 目录存在时）
$hasChanges = $false
if (Test-Path "$projectRoot\.git") {
    try {
        $changedFiles = git -C $projectRoot status --porcelain backend frontend 2>$null
        if ($changedFiles) {
            $hasChanges = $true
            Write-Warning "Detected uncommitted changes in backend/frontend code."
            Write-Host "  Use '.\deploy.ps1 -ForceRebuild' to force rebuild containers."
        }
    } catch {
        # git 不可用，跳过变更检测
    }
}
```

---

### 改进前后对比

| 场景 | 改进前 | 改进后 |
|------|--------|--------|
| **Windows 首次部署** | MinIO bucket 创建失败 | ✅ 通过 compose 服务完成 |
| **macOS 文件同步** | volume mount 慢/卡 | ✅ 镜像内置配置，volume 仅用于覆盖 |
| **三平台密钥** | 统一弱密码 ppap123 | ✅ 自动生成强密钥 |
| **远程服务器部署** | localhost 检查失败 | ✅ 可通过 API_HOST 指定 |
| **Windows zip 部署** | git 命令报错 | ✅ 优雅降级 |
| **旧 .env 兼容** | — | ✅ 环境变量引用 + fallback |
| **MinIO 安全** | bucket 设为 public | ✅ 改为 download（仅预签名 URL） |

---

### 跨平台兼容性矩阵（改进后）

| 平台 | 改进前 | 改进后 | 说明 |
|------|--------|--------|------|
| **Ubuntu/Debian (amd64)** | ✅ 完全支持 | ✅ 完全支持 | 最佳体验 |
| **macOS (Intel)** | ✅ 基本可用 | ✅ 完全支持 | volume mount 问题消除 |
| **macOS (Apple Silicon)** | ⚠️ 需测试 | ✅ 基本可用 | Docker Desktop 原生支持 |
| **Windows 10/11** | ⚠️ MinIO 失败 | ✅ 完全支持 | container 网络模式问题消除 |
| **WSL2 (Ubuntu)** | ⚠️ 需调整 | ✅ 基本可用 | localhost 可配置 |
| **远程服务器** | ❌ localhost 不通 | ✅ 可配置 | API_HOST 环境变量 |

---

### 跨平台改进实施优先级

| 阶段 | 改进项 | 涉及文件 | 预计改动量 |
|------|--------|----------|------------|
| **P0** | MinIO 容器化 | docker-compose.yml, deploy.sh, deploy.ps1 | ~30 行 |
| **P0** | 前端内置 nginx.conf | frontend/Dockerfile, 新增 frontend/nginx.conf | ~10 行 |
| **P1** | 密钥自动生成 | deploy.sh, deploy.ps1, .env.example, docker-compose.yml | ~50 行 |
| **P1** | 健康检查环境变量化 | deploy.sh, deploy.ps1 | ~20 行 |
| **P2** | db-init 环境变量化 | docker-compose.yml | ~5 行 |
| **P2** | deploy.ps1 去 git 化 | deploy.ps1 | ~15 行 |

> P0 两项改完后，三平台基础部署即可跑通。P1 提升安全性和灵活性。P2 消除边缘场景问题。

---

## 九、安全加固实施记录

> 最后更新: 2026-06-24
> 来源: suggestion.md 第一节「安全问题 (Critical)」

### 9.1 登录接口密码校验 ✅ 已完成

**修改内容**：
- `backend/app/models/user.py`：新增 `password_hash` 字段
- `backend/app/schemas/user.py`：`UserLogin` 新增 `password: str` 字段
- `backend/app/api/auth.py`：登录增加密码校验；移除邮箱推断角色（新用户默认 USER）
- `deploy/init-db.sql`：admin 用户增加 bcrypt 密码哈希
- `db_migrations.sql` + `backend/migrations/versions/add_password_hash_column.py`：新增迁移

**效果**：
| 场景 | 改进前 | 改进后 |
|------|--------|--------|
| 已知邮箱登录 | 免密登录 | 必须校验密码 |
| 新用户自动创建 | 邮箱推断角色 | 默认 USER + 自动设置密码 |
| 旧用户（无密码） | 免密登录 | 拒绝登录，提示联系管理员 |

### 9.2 Redis 鉴权 + 端口隐藏 ✅ 已完成

**修改内容**：
- `deploy/docker-compose.yml`：移除 Redis 端口 `6379:6379` 映射；添加 `--requirepass ${REDIS_PASSWORD}`；backend/celery-worker REDIS_URL 包含密码
- `deploy/.env.example` / `deploy/.env`：新增 `REDIS_PASSWORD`
- `deploy.sh` / `deploy.ps1`：自动生成 16 位 Redis 密码

**效果**：
- Redis 不再暴露到宿主机，仅容器内部网络可访问
- 所有 Redis 连接需密码认证
- 首次部署自动生成强密码

### 1.6 OIDC 回调 state 校验 ✅ 已完成

**修改内容**：
- `backend/app/api/oidc.py`：`/auth-url` 生成 state 后存储到 Redis（10 分钟过期）；`/callback` 校验 state 一致性，通过后立即删除（一次性使用）
- state 不匹配或已过期 → 返回 403 + CSRF 警告
- Redis 不可用时降级为日志警告，不阻断流程

### 1.7 WebSocket token 泄露修复 ✅ 已完成

**修改内容**：
- `backend/app/api/websocket.py`：移除 `token: str = Query(None)`；改为连接后等待第一条 JSON 消息 `{"type": "auth", "token": "..."}` 进行认证（5 秒超时）
- `frontend/src/views/FileDetailPage.vue`：WebSocket URL 不再包含 `?token=xxx`；`socket.onopen` 时发送认证消息

**效果**：Token 不再出现在 URL 中，避免被服务器访问日志、代理日志、浏览器历史记录捕获。

### 安全改进进度总览

| # | 安全项 | 状态 |
|---|--------|------|
| 1.1 | 登录接口密码校验 | ✅ |
| 1.2 | ~~邮箱自动推断角色~~ (已在 1.1 中一并修复) | ✅ |
| 1.3 | ~~硬编码默认密钥~~ (已在跨平台优化 3 中修复) | ✅ |
| 1.4 | ~~MinIO public bucket~~ (已在跨平台优化 1 中修复) | ✅ |
| 1.5 | Redis 鉴权 + 端口隐藏 | ✅ |
| 1.6 | OIDC 回调未校验 state | ✅ |
| 1.7 | WebSocket token 泄露 | ✅ |

### 跨平台部署实施记录

> 最后更新: 2026-06-24

### P1-4 健康检查环境变量化 ✅ 已完成

**修改内容**：
- `deploy.sh`：顶部新增 `API_HOST` / `API_PORT` / `MINIO_PORT` / `MINIO_CONSOLE_PORT` 环境变量，所有 curl 检查和输出地址使用变量
- `deploy.ps1`：顶部新增 `$apiHost` / `$apiPort` / `$minioPort` / `$minioConsolePort`，所有 `Invoke-WebRequest` 和输出地址使用变量

**效果**：
- 本地测试：`bash deploy.sh`（默认 localhost）
- 远程服务器：`API_HOST=127.0.0.1 bash deploy.sh`
- 自定义端口：`API_PORT=8080 MINIO_PORT=9999 bash deploy.sh`

### P2-5 db-init admin 密码模板化 ✅ 已完成

**修改内容**：
- `deploy.sh`：首次部署自动生成 12 位随机 admin 密码，通过 `passlib` 生成 bcrypt 哈希，替换 `init-db.sql` 中的硬编码哈希
- `deploy.ps1`：PowerShell 等效实现，生成 admin 密码并更新 `init-db.sql`
- 部署完成时输出显示的 admin 密码为自动生成的值（非固定的 `admin123`）

**效果**：
- 首次部署 admin 密码与所有其他密钥一起自动生成
- 旧 `.env` 存在时复用已有密码，不重新生成
- Python/passlib 不可用时降级为默认密码 `admin123`

---

### 2.2 统计查询加载 1000 条完整 JSON 到内存 ✅ 已完成

**修改内容**：
- `backend/app/api/files.py`：将 Python 端逐条解析 1000 条 JSON 的逻辑替换为 PostgreSQL 原生 `jsonb` 聚合查询
- 使用 `jsonb_array_elements` + `CAST(::jsonb)` 在数据库层面展开 checks 数组、过滤 fail 状态、分组计数

**效果**：
- 不再加载 1000 条完整 JSON 文本列到 Python 内存
- 聚合、过滤、排序全部在 PostgreSQL 内完成
- 异常时返回空列表（不阻断 dashboard 加载）

---

## 十、性能优化实施记录

> 最后更新: 2026-06-24
> 来源: suggestion.md 第二节「性能问题 (High)」

### 2.1 Celery dispose 共享 engine ✅ 已完成

**修改内容**：
- `backend/app/tasks/verification_tasks.py`：删除 `_run_all()` 中 `finally: await engine.dispose()` 块
- 保留异常处理和审计日志闭环逻辑

**效果**：
- 并发 Celery 任务不再因其他任务销毁 engine 而失去数据库连接
- 每个任务通过 `async_session_maker()` 的 `async with` 上下文自动清理连接
- Engine 作为共享资源，只在应用关闭时销毁

### 2.2 统计查询 JSONB 聚合 ✅ 已完成

**修改内容**：
- `backend/app/api/files.py`：将 Python 端逐条解析 1000 条 JSON 替换为 PostgreSQL 原生 `jsonb_array_elements` 聚合查询
- 使用 `text()` 直接执行优化后的 SQL，避免 N+1 内存加载

**效果**：
- 不再加载 1000 条完整 JSON 文本列到 Python 内存
- 聚合、过滤、排序全部在 PostgreSQL 内完成
- 异常时返回空列表（不阻断 dashboard 加载）

### 2.3 异步 MinIO 客户端 ✅ 已完成

**修改内容**：
- `backend/app/core/minio_client.py`：新增 `upload_file_async`、`download_file_async`、`delete_file_async` 三个异步方法
- 同步 MinIO 调用通过 `asyncio.get_event_loop().run_in_executor()` 放入线程池执行

**效果**：
- 高并发时 MinIO 操作不再阻塞 asyncio 事件循环
- 现有同步接口完全保留，渐进式迁移

### 2.4 N+1 查询优化 ✅ 已完成

**修改内容**：
- `backend/app/services/file_service.py`：`get_file_detail()` 使用 `select(File).options(selectinload(File.uploaded_by_user))` 替换先查 File 再查 User 的两次查询

**效果**：
- 原有 2 次 SQL 查询合并为 1 次 JOIN
- 列表查询时 N+1 问题消除

### 2.5 前端轮询指数退避 ✅ 已完成

**修改内容**：
- `frontend/src/components/TaskList.vue`：`startPolling()` 从固定 2 秒 `setInterval` 改为指数退避 `setTimeout` 链
- 退避策略：2s → 3s → 4.5s → 6.75s → ... → 上限 30s

**效果**：
- 多标签页时请求量显著下降
- 长时间处理任务时轮询间隔自适应

### 2.6 URLFetchOperator 临时文件清理 ✅ 已完成

**修改内容**：
- `backend/app/engine/operators/url_fetch_operator.py`：`mkstemp` 创建的临时文件路径记录到 `context.shared_state["_temp_files"]`
- `backend/app/tasks/verification_tasks.py`：引擎执行完成后遍历清理 `_temp_files` 列表

**效果**：
- 长期运行不再积累临时 PDF 文件
- 异常时文件保留在磁盘（调试用途），正常完成时清理

---

## 十一、上线优先级评估

> 评估时间: 2026-06-24
> 目标: 保证系统安全、稳定地上线生产环境

### 🔴 第一梯队：上线前必须解决（预计 1-2 天）

这些问题会导致**系统崩溃、数据泄露、或被攻击**，不解决不能上线。

| # | 问题 | 来源 | 风险 | 工作量 |
|---|------|------|------|--------|
| 1 | 容器无资源限制 | 5.1 | 一个大 PDF 处理可耗尽内存，全部容器崩溃 | 小 |
| 2 | 后端/前端/Celery 无健康检查 | 5.2 | 服务挂了 Docker 不知道，不会自动重启 | 小 |
| 3 | 无日志轮转 | 5.3 | 日志持续增长，几天内填满磁盘 | 小 |
| 4 | Nginx 无 HTTPS + 安全头 | 5.4 | 明文传输 token/密码，XSS/点击劫持无防护 | 中 |
| 5 | Nginx 无速率限制 | 5.5 | 登录接口可被暴力破解 | 小 |
| 6 | PostgreSQL 端口暴露宿主机 | 5.8 | 数据库可被外部直接攻击 | 小 |
| 7 | Settings API 未校验管理员 | 3.9 | 普通用户可修改系统配置（SMTP/SSO/用户管理） | 小 |
| 8 | JWT 有效期 24 小时 | 5.7 | token 泄露后长时间可用 | 小 |

### 🟡 第二梯队：上线后一周内解决

影响**用户体验和运维效率**，不阻塞上线但应尽快修复。

| # | 问题 | 来源 | 影响 |
|---|------|------|------|
| 9 | 前端 `any` 类型泛滥 | 4.1 | 后端字段变更只能运行时发现，容易出线上 bug |
| 10 | 401 硬跳转丢状态 | 4.2 | 用户 token 过期后整页刷新，体验差 |
| 11 | 未读数永远为 0 | 4.4 | 通知功能形同虚设 |
| 12 | 通知"全部已读"未调 API | 4.3 | 假功能，刷新后又变未读 |
| 13 | Element Plus 全量引入 | 4.7 | 首屏加载多 500KB+，弱网下明显卡顿 |
| 14 | 无响应式设计 | 4.8 | 平板/手机完全无法使用 |
| 15 | DEBUG 模式默认 True | 7.1 | 生产环境输出所有 SQL 到 stdout |
| 16 | 错误响应格式不一致 | 3.8 | 前端难以统一处理错误 |
| 17 | Backend Dockerfile 非多阶段构建 | 5.9 | 镜像体积大，包含测试依赖 |

### 🟢 第三梯队：可排期迭代

代码质量和长期维护性，不影响上线运行。

| # | 问题 | 来源 |
|---|------|------|
| 18 | VerificationEngine 超大类拆分（1355+ 行） | 3.1 |
| 19 | RuleGraphEditor / FullscreenRuleEditor 重复代码 | 3.2 |
| 20 | SettingsPage 超大组件拆分（2647 行） | 3.3 |
| 21 | 重复的状态/文本映射函数提取 | 3.4 |
| 22 | AI 配置加载重复代码 | 3.5 |
| 23 | 模型时间戳类型不一致 | 3.6 |
| 24 | UUID 存储为字符串 | 3.7 |
| 25 | 全局可变 Engine 实例 | 3.10 |
| 26 | 请求无取消机制（AbortController） | 4.6 |
| 27 | 全局错误处理器重复弹 toast | 4.5 |
| 28 | 防火墙缺默认拒绝策略 | 5.6 |
| 29 | APP_BASE_URL 默认 localhost | 7.2 |
| 30 | 文件保留期限三处定义 | 7.3 |
| 31 | deploy/README.md 内容过时 | 7.4 |
| 32 | 缺少架构图和运维手册 | 7.5 |
| 33 | 无 CI/CD 流水线 | 6.1 |
| 34 | 无自动备份策略 | 6.2 |
| 35 | 开发依赖混入生产 requirements | 6.3 |
| 36 | 依赖版本不一致 | 6.4 |
