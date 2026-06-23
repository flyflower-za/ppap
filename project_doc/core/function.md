# PPAP 文件验证平台功能清单

> 本文档记录 PPAP (Production Part Approval Process) 文件验证平台的完整功能模块，便于后续针对性优化。

---

## 项目概述

PPAP 是一个基于 AI 的 PDF 文件验证平台，用于自动化检测生产文件中的合规性问题。平台采用前后端分离架构，支持规则引擎、算子扩展、人工审批等工作流。

### 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 | Vue 3.4 + TypeScript 5.3 + Element Plus 2.5 + Vite 5.0 |
| 后端 | FastAPI 0.109 + Python 3.11 + SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL |
| 缓存 | Redis |
| 文件存储 | MinIO |
| AI 服务 | 阿里云 Agent |
| 任务队列 | Celery |
| 容器化 | Docker + Docker Compose |

---

## 一、后端功能模块

### 1.1 认证与授权 (API)

**文件**: `backend/app/api/auth.py`

| 功能 | 端点 | 描述 |
|------|------|------|
| 用户登录 | `POST /api/v1/auth/login` | 支持本地账密、LDAP、OIDC 登录 |
| 获取当前用户 | `GET /api/v1/auth/me` | 获取登录用户信息 |
| 登出 | `POST /api/v1/auth/logout` | 用户登出 |

**认证方式**:
- 本地用户名/密码认证
- LDAP 企业目录集成
- OIDC/Keycloak SSO 单点登录

---

### 1.2 文件管理 (API)

**文件**: `backend/app/api/files.py`

| 功能 | 端点 | 描述 |
|------|------|------|
| 上传文件 | `POST /api/v1/files/upload` | 上传 PDF 文件进行验证 |
| 文件列表 | `GET /api/v1/files` | 分页查询文件列表，支持筛选 |
| 文件详情 | `GET /api/v1/files/{id}` | 获取单个文件详细信息 |
| 下载文件 | `GET /api/v1/files/{id}/download` | 获取临时下载链接 |
| 删除文件 | `DELETE /api/v1/files/{id}` | 删除文件及关联数据 |
| 文件统计 | `GET /api/v1/files/statistics` | 获取合规统计数据 |

---

### 1.3 规则引擎 (API)

**文件**: `backend/app/api/rules.py`

| 功能 | 端点 | 描述 |
|------|------|------|
| 规则列表 | `GET /api/v1/rules` | 获取所有规则 |
| 创建规则 | `POST /api/v1/rules` | 创建新规则 |
| 更新规则 | `PUT /api/v1/rules/{id}` | 更新规则配置 |
| 删除规则 | `DELETE /api/v1/rules/{id}` | 删除规则 |
| 规则版本历史 | `GET /api/v1/rules/{id}/versions` | 获取规则版本历史 |
| 规则回滚 | `POST /api/v1/rules/{id}/rollback` | 回滚到历史版本 |
| 沙盒测试 | `POST /api/v1/rules/dry-run` | 内存级模拟执行规则 |

---

### 1.4 算子注册表 (API)

**文件**: `backend/app/api/operators.py`

| 功能 | 端点 | 描述 |
|------|------|------|
| 获取算子列表 | `GET /api/v1/rule-engine/operators/registry` | 获取所有可用算子定义 |
| 获取算子详情 | `GET /api/v1/rule-engine/operators/{type}` | 获取特定算子的配置schema |

---

### 1.5 审批流程 (API)

**文件**: `backend/app/api/approvals.py`

| 功能 | 端点 | 描述 |
|------|------|------|
| 变更请求列表 | `GET /api/v1/rule-engine/approvals/change-requests` | 获取审批工单列表 |
| 创建变更请求 | `POST /api/v1/rule-engine/approvals/change-requests` | 提交规则变更审批 |
| 审核变更请求 | `POST /api/v1/rule-engine/approvals/change-requests/{id}/review` | 审批通过/拒绝 |
| 部署已审批规则 | `POST /api/v1/rule-engine/approvals/change-requests/{id}/deploy` | 一键部署生效 |
| 审批策略列表 | `GET /api/v1/rule-engine/approvals/policies` | 获取审批策略 |
| 初始化策略 | `POST /api/v1/rule-engine/approvals/policies/init` | 初始化默认审批策略 |

---

### 1.6 系统设置 (API)

**文件**: `backend/app/api/settings.py`

| 功能 | 端点 | 描述 |
|------|------|------|
| 获取设置 | `GET /api/v1/settings` | 获取系统配置 |
| 更新设置 | `PUT /api/v1/settings` | 更新系统配置 |
| 测试 LDAP | `POST /api/v1/settings/test-ldap` | 测试 LDAP 连接 |
| 测试 SMTP | `POST /api/v1/settings/test-smtp` | 测试邮件发送 |
| 测试 OIDC | `POST /api/v1/settings/test-oidc` | 测试 SSO 连接 |

**配置项**:
- LDAP 配置 (服务器、Base DN、用户过滤)
- SMTP 配置 (服务器、端口、发件人)
- OIDC/SSO 配置 (授权端点、Token端点、客户端ID)
- 默认用户角色设置

---

### 1.7 模块管理 (API)

**文件**: `backend/app/api/modules.py`

| 功能 | 端点 | 描述 |
|------|------|------|
| 模块列表 | `GET /api/v1/modules` | 获取所有模块 |
| 创建模块 | `POST /api/v1/modules` | 创建新模块 |
| 更新模块 | `PUT /api/v1/modules/{id}` | 更新模块配置 |
| 删除模块 | `DELETE /api/v1/modules/{id}` | 删除模块 |

---

### 1.8 通知与审计 (API)

**文件**: `backend/app/api/notifications.py`, `backend/app/api/audit.py`

| 功能 | 端点 | 描述 |
|------|------|------|
| 获取通知 | `GET /api/v1/notifications` | 获取用户通知列表 |
| 标记已读 | `POST /api/v1/notifications/mark-read` | 批量标记已读 |
| 审计日志 | `GET /api/v1/audit-logs` | 查询操作审计日志 |

---

### 1.9 WebSocket 实时通信

**文件**: `backend/app/api/websocket.py`

| 功能 | 描述 |
|------|------|
| 任务进度推送 | 文件验证进度实时推送 |
| 状态更新 | 实时通知用户任务状态变化 |

---

### 1.10 验证引擎核心

**文件**: `backend/app/engine/core.py`

**功能**: 规则执行引擎，支持 DAG 流程图执行

- **Stage 1 预分类**: 快速检查 PDF 基本信息页数、格式
- **Stage 2 深度验证**: 执行用户配置的规则链
- **变量上下文**: 维护全局共享状态，支持节点间数据传递
- **变量扁平化**: 自动提取常用嵌套字段 (如 `signer_cn`, `signature_valid`)

---

### 1.11 算子库 (Operators)

**文件**: `backend/app/engine/operators/`

| 算子 | 文件 | 功能描述 |
|------|------|----------|
| 二维码识别 | `qr_operator.py` | 识别 PDF 中的二维码内容 |
| PDF 信息提取 | `pdf_info_operator.py` | 提取 PDF 元数据 (页数、标题、作者) |
| 数字签名验证 | `signature_operator.py` | 验证 PDF 数字签名有效性 |
| 修订检查 | `revision_operator.py` | 检测 PDF 签名后的修订 |
| 印章检测 | `stamp_operator.py` | 检测 PDF 中的印章 |
| 表格提取 | `table_operator.py` | 提取 PDF 中的表格数据 |
| 文档比对 | `diff_operator.py` | 比对两份文档的差异 |
| 机构嗅探 | `sniffer_operator.py` | 根据内容识别发证机构 (CTI/SGS等) |
| 文本 LLM 分析 | `text_llm_operator.py` | 使用 LLM 进行文本语义分析 |
| 视觉 LLM 分析 | `vision_llm_operator.py` | 使用视觉模型分析页面 |
| URL 数据获取 | `url_fetch_operator.py` | 从远程 URL 获取验证数据 |

---

### 1.12 校验器 (Checkers)

**文件**: `backend/app/checkers/`

| 模块 | 功能 |
|------|------|
| `pdf_info.py` | PDF 基本信息校验 |
| `qr_decoder.py` | 二维码解码 |
| `revision_checker.py` | 修订历史检查 |
| `sig_verifier.py` | 数字签名验证器 |

---

### 1.13 业务服务

**文件**: `backend/app/services/`

| 服务 | 功能 |
|------|------|
| `aliyun_service.py` | 阿里云 AI 服务集成 |
| `email_service.py` | 邮件发送服务 |
| `file_service.py` | 文件处理服务 |
| `notification_service.py` | 通知推送服务 |

---

## 二、前端功能模块

### 2.1 页面视图 (Views)

**目录**: `frontend/src/views/`

| 页面 | 组件 | 功能描述 |
|------|------|----------|
| 登录页 | `LoginPage.vue` | 用户登录界面，支持 LDAP/SSO |
| 任务中心 | `TaskCenterPage.vue` | 文件上传、任务列表管理 |
| 历史记录 | `HistoryPage.vue` | 文件历史记录，支持筛选 |
| 文件详情 | `FileDetailPage.vue` | 文件验证详情、PDF 预览、规则匹配、人工仲裁 |
| 规则配置 | `RulesPage.vue` | 规则列表、创建、编辑、分类管理 |
| 全屏编辑器 | `FullscreenRuleEditor.vue` | 可视化规则流程图编辑器 |
| 模块沙盒 | `ModuleSandboxPage.vue` | 模块测试沙盒 |
| 审批中心 | `ApprovalsPage.vue` | 规则变更审批工单管理 |
| 审计日志 | `AuditLogPage.vue` | 操作审计日志查询 |
| 系统设置 | `SettingsPage.vue` | LDAP、SMTP、SSO、用户角色配置 |
| 通知中心 | `NotificationsPage.vue` | 用户通知查看 |
| 合规大屏 | `DashboardPage.vue` | 数据统计仪表盘 |

---

### 2.2 可复用组件 (Components)

**目录**: `frontend/src/components/`

| 组件 | 功能 |
|------|------|
| `RuleGraphEditor.vue` | 可视化规则流程图编辑器 (核心组件) |
| `TaskList.vue` | 任务列表组件 |
| `NotificationList.vue` | 通知列表组件 |

---

### 2.3 规则图编辑器功能

**文件**: `frontend/src/components/RuleGraphEditor.vue`

| 功能 | 描述 |
|------|------|
| 节点拖拽 | 支持拖拽创建算子节点 |
| 连线配置 | 节点间数据流连线 |
| 属性配置 | 右侧面板配置节点参数 |
| 变量面板 | 显示可用变量，点击插入 |
| 变量数据流 | 显示节点的输入/输出变量 |
| 沙盒测试 | 选中样例文件进行模拟执行 |
| 自动布局 | 自动排列节点位置 |

---

### 2.4 人工仲裁 (HITL)

**文件**: `frontend/src/views/FileDetailPage.vue`

| 功能 | 描述 |
|------|------|
| 低置信度警告 | 置信度 < 85% 时显示警告 |
| 人工放行/驳回 | 管理员手动覆盖判定结果 |
| 审计记录 | 记录人工决策和备注 |
| 差异高亮 | 文档差异红绿高亮显示 |

---

### 2.5 规则版本管理

| 功能 | 描述 |
|------|------|
| 版本历史 | 时间线展示规则版本 |
| 一键回滚 | 恢复到任意历史版本 |
| 版本比对 | 高亮显示版本间差异 |
| 变更日志 | 显示每次变更的说明 |

---

### 2.6 审批流程

**文件**: `frontend/src/views/ApprovalsPage.vue`

| 功能 | 描述 |
|------|------|
| 待审批列表 | 显示待处理审批工单 |
| 工单详情 | 查看规则变更内容 |
| 审批操作 | 通过/拒绝 + 填写意见 |
| 一键部署 | 审批通过后立即部署 |

---

### 2.7 API 客户端

**目录**: `frontend/src/api/`

| 模块 | 功能 |
|------|------|
| `auth.ts` | 认证接口 |
| `files.ts` | 文件接口 |
| `rules.ts` | 规则接口 |
| `approvals.ts` | 审批接口 |
| `modules.ts` | 模块接口 |
| `settings.ts` | 设置接口 |
| `notifications.ts` | 通知接口 |

---

## 三、数据库模型

**目录**: `backend/app/models/`

| 模型 | 文件 | 描述 |
|------|------|------|
| 用户 | `user.py` | 用户账户、角色 |
| 用户组 | `user_group.py` | 用户组管理 |
| 文件 | `file.py` | 文件记录、验证状态 |
| 任务 | `task.py` | 异步任务记录 |
| 规则 | `rule.py` | 规则定义 |
| 规则版本 | `rule_version.py` | 规则版本历史 |
| 规则模板 | `rule_template.py` | 规则模板 |
| 规则审批 | `rule_approval.py` | 审批工作流 |
| 算子注册表 | `operator_registry.py` | 算子定义 |
| 审计日志 | `audit.py` | 操作审计 |
| 通知 | `notification.py` | 用户通知 |
| 笔记 | `note.py` | 文件笔记 |
| LDAP 配置 | `ldap_config.py` | LDAP 设置 |
| 系统设置 | `setting.py` | 系统配置 |

---

## 四、部署与基础设施

### 4.1 容器化服务

**文件**: `deploy/docker-compose.yml`

| 服务 | 端口 | 描述 |
|------|------|------|
| frontend | 80 | Nginx + Vue 3 静态文件 |
| backend | 31234 | FastAPI 应用 |
| postgres | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis 缓存/队列 |
| minio | 9000 | MinIO 对象存储 |
| minio-console | 9001 | MinIO 管理界面 |
| celery-worker | - | Celery 后台任务处理 |
| db-init | - | 数据库初始化 (一次性) |

---

### 4.2 部署脚本

| 脚本 | 功能 |
|------|------|
| `deploy.sh` | Linux/macOS 一键部署脚本 |
| `deploy.ps1` | Windows 一键部署脚本 |
| `init-db.sh` | 数据库初始化脚本 |
| `init-db.sql` | 数据库表结构与初始数据 |
| `setup_firewall.sh` | 防火墙配置 |

---

### 4.3 网络配置

**文件**: `deploy/nginx.conf`

- 反向代理配置
- API 路由转发
- 静态文件服务
- MIME 类型修复 (PDF.js worker)

---

## 五、扩展功能

### 5.1 LDAP 企业目录集成

**文件**: `backend/app/api/ldap.py`

- 支持多 LDAP 服务器配置
- 用户同步与自动创建
- 用户组成员关系映射
- 登录测试功能

---

### 5.2 SMTP 邮件服务

**文件**: `backend/app/services/email_service.py`

- SMTP 配置管理
- 邮件模板系统
- 测试发送功能
- 通知邮件推送

---

### 5.3 OIDC/SSO 单点登录

**文件**: `backend/app/api/oidc.py`

- Keycloak 集成
- OpenID Connect 认证流程
- Token 验证与刷新

---

## 六、技术特性

### 6.1 性能优化

- 异步 I/O (asyncpg, asyncio)
- Redis 缓存层
- Celery 后台任务
- 数据库连接池

---

### 6.2 安全性

- JWT 令牌认证
- RBAC 角色权限控制
- 审计日志记录
- 敏感配置加密

---

### 6.3 可扩展性

- 算子插件系统
- 规则模板市场
- 模块化架构
- Docker 容器化

---

## 七、待优化模块

以下模块已识别，待后续优化：

1. **规则引擎性能**: 大规模规则执行效率
2. **AI 置信度阈值**: 可配置的置信度阈值
3. **批量文件处理**: 支持批量上传与验证
4. **报表导出**: PDF/Excel 格式验证报告
5. **移动端适配**: 响应式布局优化
6. **国际化**: 多语言支持

---

*最后更新: 2026-06-23*
