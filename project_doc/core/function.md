# PPAP 文件验证平台功能清单

> 本文档记录 PPAP (Production Part Approval Process) 文件验证平台的完整功能模块，便于后续针对性优化。

---

## 项目概述

PPAP 是一个基于 AI 的 PDF 文件验证平台，用于自动化检测生产文件中的合规性问题。平台采用前后端分离架构，支持规则引擎、算子扩展、人工审批等工作流。

### 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 | Vue 3.4 + TypeScript 5.3 + Element Plus 2.5 + Vite 5.0 + vue-i18n v11 |
| 后端 | FastAPI 0.109 + Python 3.11 + SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL |
| 缓存 | Redis |
| 文件存储 | MinIO |
| AI 服务 | 阿里云 Agent |
| 任务队列 | Celery |
| 容器化 | Docker + Docker Compose |
| 国际化 | vue-i18n v11 (zh-CN / en-US, 947 keys) |

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

### 1.3 规则引擎与文档分类 (API)

**文件**: `backend/app/api/rules.py`

#### 核心端点清单

| 功能 | 端点 | 描述 |
|------|------|------|
| 规则列表 | `GET /api/v1/rule-engine/rules` | 获取所有规则 |
| 创建规则 | `POST /api/v1/rule-engine/rules` | 创建新规则 |
| 更新规则 | `PUT /api/v1/rule-engine/rules/{id}` | 更新规则配置 |
| 删除规则 | `DELETE /api/v1/rule-engine/rules/{id}` | 删除规则 |
| 规则版本历史 | `GET /api/v1/rule-engine/rules/{id}/versions` | 获取规则版本历史 |
| 规则回滚 | `POST /api/v1/rule-engine/rules/{id}/rollback` | 回滚到历史版本 |
| 沙盒测试 | `POST /api/v1/rule-engine/rules/dry-run` | 内存级模拟执行规则 |
| 分类列表 | `GET /api/v1/rule-engine/categories` | 获取全部文档分类 |
| 创建分类 | `POST /api/v1/rule-engine/categories` | 创建新分类（自动挂载底座预置规则） |
| 更新分类 | `PUT /api/v1/rule-engine/categories/{id}` | 更新分类信息 |
| 删除分类 | `DELETE /api/v1/rule-engine/categories/{id}` | 删除分类（级联物理清理底座规则） |
| 一键补齐默认规则 | `POST /api/v1/rule-engine/restore-defaults` | 为所有分类自动补齐缺失的预置规则 |

#### 关键技术设计

- **分类创建自动挂载预置规则**: 当调用 `POST /api/v1/rule-engine/categories` 创建新分类时，系统会自动遍历当前数据库中所有处于激活状态（`is_active == True`）的验证底座模块。自动为该分类创建对应的预置规则（`VerificationRule`），默认状态为“未启用”（`is_active = False`），默认告警级别为 `fail`。
- **直连模块映射**: 规则表结构中增加了 `module_id` 字段直连底座模块，简化了原有的多对多中间表关联设计。
- **校验评分规则**: 执行引擎调度在分析 PDF 文档时，会自动拉取文档分类下所有已启用的规则。当规则绑定了底座模块（`module_id` 不为空）时，直接基于该底座模块的通过情况（`passed`）进行结果判定和计分。

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

**文件**: `backend/app/api/verification_modules.py`

#### 核心端点清单

| 功能 | 端点 | 描述 |
|------|------|------|
| 模块列表 | `GET /api/v1/rule-engine/modules` | 获取所有已注册的底座模块 |
| 创建模块 | `POST /api/v1/rule-engine/modules` | 创建新底座模块 |
| 更新模块 | `PUT /api/v1/rule-engine/modules/{id}` | 更新底座模块配置（包含 metadata 和 is_active） |
| 删除模块 | `DELETE /api/v1/rule-engine/modules/{id}` | 删除底座模块（级联物理清理对应的预置规则） |
| 获取模块元数据 | `GET /api/v1/rule-engine/modules/metadata` | 获取算子元数据定义 |
| 恢复默认模块 | `POST /api/v1/rule-engine/modules/restore-defaults` | 一键初始化系统默认底座模块 |

#### 关键技术设计

- **底座模块与规则关联关系**: 每一个规则记录通过 `module_id` 与底座模块进行关联。这种关系是一对一的，使得每个规则能够直接指向特定的底座模块（如数字签名、印章检测等）。
- **批量同步规则状态**: 在编辑分类规则时，可以通过批量 API 提交批量更新指令，同步更新模块绑定的规则。

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
| 登录页 | `LoginPage.vue` | 用户登录界面，支持 LDAP/SSO，右上角语言切换按钮 |
| 任务中心 | `TaskCenterPage.vue` | 文件上传、任务列表管理 |
| 历史记录 | `HistoryPage.vue` | 文件历史记录，支持筛选 |
| 文件详情 | `FileDetailPage.vue` | 文件验证详情、PDF 预览、规则匹配、人工仲裁 |
| 规则配置 | `RulesPage.vue` | 规则列表、创建、编辑、分类管理 |
| 全屏编辑器 | `FullscreenRuleEditor.vue` | 可视化规则流程图编辑器 |
| 模块沙盒 | `ModuleSandboxPage.vue` | 模块测试沙盒 |
| 审批中心 | `ApprovalsPage.vue` | 规则变更审批工单管理 |
| 审计日志 | `AuditLogPage.vue` | 操作审计日志查询 |
| 系统设置 | `SettingsPage.vue` | LDAP、SMTP、SSO、用户角色、AI 模型、文件保留配置 |
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

### 2.3 国际化 (i18n)

**目录**: `frontend/src/locales/`

| 文件 | 说明 |
|------|------|
| `index.ts` | vue-i18n 实例创建、locale 切换、localStorage 持久化 |
| `zh-CN.ts` | 中文翻译 (947 keys) |
| `en-US.ts` | 英文翻译 (947 keys) |
| `I18N_PROGRESS.md` | 国际化迁移进度跟踪 |

**切换方式**:
- 导航栏底部语言切换按钮（已登录状态）
- 登录页右上角语言切换下拉（未登录状态）
- Element Plus 组件自动跟随切换

**完成度**: ~85%（15/19 文件），Rules 子系统延后处理

---

### 2.4 规则图编辑器功能

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

### 2.5 人工仲裁 (HITL)

**文件**: `frontend/src/views/FileDetailPage.vue`

| 功能 | 描述 |
|------|------|
| 低置信度警告 | 置信度 < 85% 时显示警告 |
| 人工放行/驳回 | 管理员手动覆盖判定结果 |
| 审计记录 | 记录人工决策和备注 |
| 差异高亮 | 文档差异红绿高亮显示 |

---

### 2.6 规则配置与版本管理

**文件**: `frontend/src/views/RulesPage.vue`

#### 1. 基础预置规则卡片网格 (Preset Rules Grid)
- **极简化快捷配置**: 页面上方直观呈现当前文档分类挂载的所有系统底座预设规则（包括：二维码识别、数字签名验证、印章检测、PDF信息提取、修订历史检查等）。
- **快捷开关与级别**: 每个底座模块卡片包含一个 `Switch` 开关（用于一键启用/禁用该底座规则）以及一个 `Severity` 下拉选择器（配置触发警告或直接不合规 `fail`）。
- **一键批量保存**: 用户可随意调整多个底座模块的开关状态与告警级别，通过右上角「保存基础配置」按钮，一键批量向后端提交更新，免除了对每个底座规则逐个弹窗配置的繁琐。

#### 2. 自定义高级规则列表 (Custom Rules Table)
- **高级模式扩展**: 页面下方展示自定义规则列表，专用于展示和编辑使用“大模型语义提取”或“可视化逻辑图 (Logic Graph)”构建的复杂规则。
- **添加/编辑**: 点击可呼起全屏流程图编辑器进行高阶逻辑自主编排。

#### 3. 版本与变更历史
- **版本历史**: 时间线展示规则的变更版本。
- **一键回滚**: 支持选择任意历史版本进行一键回滚。
- **版本比对**: 自动比对不同版本间的 JSON Schema 或 Logic Graph 差异并进行高亮标记。
- **变更日志**: 与审批工单联动，显示每次规则变更的变更人、时间及详细说明。

---

### 2.7 审批流程

**文件**: `frontend/src/views/ApprovalsPage.vue`

| 功能 | 描述 |
|------|------|
| 待审批列表 | 显示待处理审批工单 |
| 工单详情 | 查看规则变更内容 |
| 审批操作 | 通过/拒绝 + 填写意见 |
| 一键部署 | 审批通过后立即部署 |

---

### 2.8 API 客户端

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
6. **国际化**: 已完成 ~85%（vue-i18n 基础设施 + 15 个页面），剩余 Rules 子系统 3 个文件待迁移

---

*最后更新: 2026-06-25*
