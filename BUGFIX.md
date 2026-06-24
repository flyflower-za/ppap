# 问题修复清单

> 最后更新: 2026-06-24

## 已修复问题

### 🔴 Critical（已修复 7/7）

| # | 问题 | 根因 | 修复方案 | 状态 | 修复日期 |
|---|------|------|----------|------|----------|
| 1.1 | 登录接口未校验密码 | `auth.py` 仅查邮箱，从未调用 `verify_password()` | 新增密码校验逻辑 | ✅ | 2026-06-24 |
| 1.2 | 邮箱推断角色 | 含 "admin" 即赋 ADMIN 角色 | 移除推断逻辑，新用户默认 USER | ✅ | 2026-06-24 |
| 1.3 | 硬编码默认密钥 | docker-compose 和脚本中明文密码 | 部署脚本自动生成强密钥，compose 使用 `${VAR}` 引用 | ✅ | 2026-06-24 |
| 1.4 | MinIO Bucket 设为 public | `mc anonymous set public` | 改为 `download`（仅预签名 URL 可访问） | ✅ | 2026-06-24 |
| 1.5 | Redis 未鉴权且暴露宿主机 | 端口 6379 映射且无密码 | 移除端口映射 + `--requirepass` | ✅ | 2026-06-24 |
| 1.6 | OIDC 回调未校验 state | 生成 state 但回调未比对 | Redis 存储 state（10分钟过期），回调时校验并删除 | ✅ | 2026-06-24 |
| 1.7 | WebSocket token 泄露 | token 通过 URL query 传递 | 改为连接后首条消息认证 | ✅ | 2026-06-24 |

### 🟠 High（已修复 6/6）

| # | 问题 | 根因 | 修复方案 | 状态 | 修复日期 |
|---|------|------|----------|------|----------|
| 2.1 | Celery dispose 共享 engine | `finally: await engine.dispose()` 销毁全局 engine | 删除 finally 块，依赖上下文管理器自动清理 | ✅ | 2026-06-24 |
| 2.2 | 统计查询加载 1000 条 JSON | Python 端逐条解析 | 改用 PostgreSQL `jsonb_array_elements` 聚合 | ✅ | 2026-06-24 |
| 2.3 | 同步 MinIO 阻塞事件循环 | 同步 SDK 调用 | 新增 `*_async` 方法 + `run_in_executor` | ✅ | 2026-06-24 |
| 2.4 | N+1 查询 | 文件详情单独查 User | `selectinload(File.uploaded_by_user)` | ✅ | 2026-06-24 |
| 2.5 | 前端固定 2 秒轮询 | `setInterval(fetchTasks, 2000)` | 改为指数退避 `setTimeout`（2s→30s） | ✅ | 2026-06-24 |
| 2.6 | URLFetchOperator 临时文件未清理 | `mkstemp` 创建后未删除 | 记录到 `_temp_files` 列表，任务完成后清理 | ✅ | 2026-06-24 |

### 🟡 部署期间发现的运行时问题（已修复 9/9）

| # | 问题 | 根因 | 修复方案 | 状态 | 修复日期 |
|---|------|------|----------|------|----------|
| D.1 | `init-db.sql` 缺少 `password_hash` 列 | 新增安全功能时未同步更新建表脚本 | 在 `users` 表定义中添加 `password_hash VARCHAR(255)` | ✅ | 2026-06-24 |
| D.2 | `.env` 中 bcrypt 哈希 `$` 被 Docker Compose 吞掉 | `$AKHaPkhaa` 被解释为变量引用 | 使用 `$$` 转义（Docker Compose 语法） | ✅ | 2026-06-24 |
| D.3 | `passlib 1.7.4` 与 `bcrypt 5.0.0` 不兼容 | passlib 内部 `detect_wrap_bug` 触发 bcrypt 长度校验 | 移除 passlib，直接用 `bcrypt` 库 | ✅ | 2026-06-24 |
| D.4 | 已有数据库 admin 用户 `password_hash` 为 NULL | 迁移只加列不更新数据 | db-init 服务每次启动执行 `UPDATE users SET password_hash` | ✅ | 2026-06-24 |
| D.5 | `verification_rules.module_id` 列缺失 | 模型新增字段未同步到数据库 | `ALTER TABLE` 添加列 + 更新 `db_migrations.sql` | ✅ | 2026-06-24 |
| D.6 | `severity` 枚举缺少 `reference` 值 | 代码新增枚举值未同步到数据库 | `ALTER TYPE severity ADD VALUE 'reference'` | ✅ | 2026-06-24 |
| D.7 | 在线防伪比对 URL 模板变量未替换 | `OnlineVerificationOperator` 仅支持 `{{var}}` 双花括号替换，用户配置的 `{var}` 单花括号无法匹配 | 同时支持 `{{var}}` 和 `{var}` 两种占位符格式，更新 schema placeholder 提示 | ✅ | 2026-06-24 |
| D.8 | Celery 任务跨事件循环崩溃 | `asyncio.run()` 每次创建新事件循环，但全局 SQLAlchemy engine 连接池绑定在旧循环上 | 三个 Celery 任务文件改为每次创建独立 engine，任务结束后 `dispose()` | ✅ | 2026-06-24 |
| D.9 | `*` 通配符非贪婪匹配导致路径提取错误 | `*/{var}` 中 `*` 转为 `.*?` 匹配到第一个 `/` 就停止，捕获整个路径而非最后一段 | 将通配符转换从 `.*?`（非贪婪）改为 `.*`（贪婪），利用 `[^&\s]+` 回溯保证正确提取 | ✅ | 2026-06-24 |

### 🔵 跨平台部署改进（已完成 6/6）

| # | 改进项 | 状态 | 修复日期 |
|---|--------|------|----------|
| C.1 | MinIO bucket 创建容器化 | ✅ | 2026-06-24 |
| C.2 | 前端 Dockerfile 内置 nginx.conf | ✅ | 2026-06-24 |
| C.3 | 密钥自动生成（deploy.sh / deploy.ps1） | ✅ | 2026-06-24 |
| C.4 | 健康检查环境变量化（API_HOST / API_PORT） | ✅ | 2026-06-24 |
| C.5 | db-init admin 密码模板化 | ✅ | 2026-06-24 |
| C.6 | deploy.ps1 移除 git 依赖 | ✅ | 2026-06-24 |

---

## 待修复问题

### 🟡 Medium - 前端（8 项）

| # | 问题 | 文件 | 影响 | 优先级 |
|---|------|------|------|--------|
| F.1 | 大量使用 `any` 类型 | 几乎所有 `.ts`/`.vue` | 类型安全形同虚设 | 中 |
| F.2 | 401 处理器硬跳转 | `api/client.ts` | 整页刷新丢失状态 | 高 |
| F.3 | 通知"全部已读"未调 API | `NotificationsPage.vue` | 假功能 | 中 |
| F.4 | MainLayout 未读数永远为 0 | `MainLayout.vue` | 通知角标无效 | 中 |
| F.5 | 全局错误处理器重复弹 toast | `api/client.ts` | 多请求失败时堆叠 | 低 |
| F.6 | 请求无取消机制 | 所有组件 | 离开页面请求继续 | 低 |
| F.7 | Element Plus 全量引入 | `main.ts` | 首屏多 500KB+ | 中 |
| F.8 | 无响应式设计 | `main.css` | 窄屏强制横滚 | 中 |

### 🟡 Medium - 基础设施（9 项）

| # | 问题 | 文件 | 影响 | 优先级 |
|---|------|------|------|--------|
| I.1 | 无容器资源限制 | `docker-compose.yml` | 单进程耗尽内存全部崩溃 | **高** |
| I.2 | 后端/前端/Celery 无健康检查 | `docker-compose.yml` | 服务挂了无法自动重启 | **高** |
| I.3 | 无日志轮转 | `docker-compose.yml` | 日志填满磁盘 | **高** |
| I.4 | Nginx 缺 HTTPS + 安全头 | `nginx.conf` | 明文传输、XSS | **高** |
| I.5 | Nginx 无速率限制 | `nginx.conf` | 暴力登录无防护 | **高** |
| I.6 | 防火墙缺默认拒绝策略 | `setup_firewall.sh` | 仅允许规则不安全 | 中 |
| I.7 | JWT 有效期 24 小时 | `.env.example` | token 泄露后长时间有效 | **高** |
| I.8 | PostgreSQL 端口暴露宿主机 | `docker-compose.yml` | 数据库可被外部攻击 | **高** |
| I.9 | Backend Dockerfile 非多阶段构建 | `Dockerfile` | 镜像含测试依赖 | 低 |

### 🟡 Medium - 代码质量（10 项）

| # | 问题 | 文件 | 影响 | 优先级 |
|---|------|------|------|--------|
| Q.1 | VerificationEngine 超大类（1355+ 行） | `engine/core.py` | 维护困难 | 低 |
| Q.2 | RuleGraphEditor / FullscreenRuleEditor 重复 | 两个 Vue 文件 | 改一处忘另一处 | 中 |
| Q.3 | SettingsPage 超大组件（2647 行） | `SettingsPage.vue` | 维护困难 | 低 |
| Q.4 | 重复的状态/文本映射函数 | 多个 Vue 文件 | 逻辑分散 | 低 |
| Q.5 | AI 配置加载重复代码 | 两个 LLM operator | 改一处忘另一处 | 低 |
| Q.6 | 模型时间戳类型不一致 | `verification_module.py` | Integer vs DateTime | 低 |
| Q.7 | UUID 存储为字符串 | 多个 model | 丢失数据库级校验 | 低 |
| Q.8 | 错误响应格式不一致 | `main.py` vs 各路由 | 前端难统一处理 | 中 |
| Q.9 | 多处 TODO 未实现管理员检查 | `settings.py` | 普通用户可改系统配置 | **高** |
| Q.10 | 全局可变 Engine 实例 | `modules.py` | 测试/并发问题 | 低 |

### 🟢 Low - 配置与文档（5 项）

| # | 问题 | 文件 | 优先级 |
|---|------|------|--------|
| L.1 | DEBUG 模式默认 True | `config.py` | 中 |
| L.2 | APP_BASE_URL 默认 localhost | `config.py` | 低 |
| L.3 | 文件保留期限三处定义 | 多处硬编码 30 | 低 |
| L.4 | deploy/README.md 内容过时 | 引用旧端口 8000 | 低 |
| L.5 | 缺少架构图和运维手册 | 无文档 | 低 |

### 🟢 Low - CI/CD 运维（4 项）

| # | 问题 | 优先级 |
|---|------|--------|
| CI.1 | 无 CI/CD 流水线 | 中 |
| CI.2 | 无自动备份策略 | 中 |
| CI.3 | 开发依赖混入生产 requirements | 低 |
| CI.4 | 依赖版本不一致 | 低 |

---

## 修复统计

| 类别 | 总数 | 已修复 | 待修复 |
|------|------|--------|--------|
| Critical（安全） | 7 | 7 ✅ | 0 |
| High（性能） | 6 | 6 ✅ | 0 |
| 部署运行时问题 | 9 | 9 ✅ | 0 |
| 跨平台部署改进 | 6 | 6 ✅ | 0 |
| Medium（前端） | 8 | 0 | 8 |
| Medium（基础设施） | 9 | 0 | 9 |
| Medium（代码质量） | 10 | 0 | 10 |
| Low（配置文档） | 5 | 0 | 5 |
| Low（CI/CD） | 4 | 0 | 4 |
| **合计** | **64** | **28** | **36** |
