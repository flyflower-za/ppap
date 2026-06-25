# PPAP 文件验证平台 - 项目架构概览

## 项目概述

**PPAP (Production Part Approval Process)** 是一个基于AI的PDF文档自动验证平台，专门用于生产零部件批准流程文档的质量检验和合规性验证。

### 核心目标
- 自动化PDF文档验证流程
- 提取和验证文档元数据（签名、二维码、印章）
- 使用AI/LLM进行语义分析
- 检测文档篡改和修订
- 强制执行可定制的业务规则和合规性检查
- 提供审计追踪和审批工作流

### 目标用户
- 质量保证团队
- 文档合规专员
- 生产零部件批准人员
- 系统管理员

---

## 技术架构

### 整体架构图

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Frontend  │ ←HTTP→  │   Backend    │ ←Async→ │  Celery     │
│   (Vue 3)   │         │   (FastAPI)  │         │   Workers   │
└─────────────┘         └──────────────┘         └─────────────┘
                               ↓                          ↓
                        ┌──────────────┐         ┌─────────────┐
                        │ PostgreSQL   │         │   Redis     │
                        │   +          │         │             │
                        │ SQLAlchemy   │         └─────────────┘
                        └──────────────┘                  ↓
                               ↓                  ┌─────────────┐
                        ┌──────────────┐         │   MinIO     │
                        │    MinIO     │         │  (Storage)  │
                        └──────────────┘         └─────────────┘
```

### 后端技术栈

**核心框架:**
- **FastAPI 0.109+** - Python 3.11 异步Web框架
- **PostgreSQL 15** - 关系型数据库
- **SQLAlchemy 2.0** - 异步ORM
- **Redis 7** - 缓存和消息队列
- **Celery 5.3** - 后台任务处理
- **MinIO** - S3兼容对象存储

**AI服务:**
- **OpenAI GPT-4o/4o-mini** - 文本语义分析和视觉检查
- **Aliyun Agent** - 备用AI服务提供商

### 前端技术栈

**核心框架:**
- **Vue 3.4** - Composition API
- **TypeScript 5.3** - 类型安全
- **Vite 5.0** - 构建工具

**UI与状态管理:**
- **Element Plus 2.5** - UI组件库
- **Pinia 2.1** - 状态管理
- **Vue Router 4.2** - 路由管理

**专业功能:**
- **PDF.js 4.0** - PDF文档渲染
- **Vue Flow 1.48** - 流程图编辑器

---

## 数据库架构

### 核心数据表

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `users` | 用户账户和权限 | role, ldap_id, sso_id |
| `files` | 文档记录和验证状态 | verification_result (JSONB) |
| `verification_rules` | 验证规则配置 | category, logic_graph |
| `verification_modules` | 可重用验证组件 | operator_type, config |
| `rule_versions` | 规则版本历史 | version_number, change_summary |
| `rule_change_requests` | 审批工作流追踪 | status, requester_id |
| `approval_policies` | 工作流自动化规则 | risk_level, required_approvers |
| `operator_registry` | 可用验证算子 | operator_id, capabilities |
| `rule_templates` | 预配置规则模板 | template_name, category |
| `notifications` | 用户通知 | type, status, recipient_id |
| `audit_logs` | 系统审计追踪 | action, user_id, timestamp |
| `email_templates` | 可定制邮件模板 | template_name, content |

### 主要关系映射
- User → File (一对多)
- File → Task (一对多)
- Rule → RuleVersion (一对多)
- Category → Rule (一对多)
- Rule → Module (多对多)

---

## 核心功能模块

### 1. 文档验证引擎

**验证流水线:**
1. **预分类阶段** - 机构检测、类别分配
2. **基础元数据阶段** - PDF信息、二维码扫描、签名验证
3. **深度分析阶段** - LLM语义分析、视觉检查、修订检测
4. **规则评估** - 自定义业务规则应用与变量插值

**可用算子 (13个模块):**
| 算子名称 | 功能描述 |
|----------|----------|
| `PDFInfoExtractor` | 基础PDF元数据提取 |
| `QRScanner` | 二维码检测和内容提取 |
| `SignatureVerifier` | 数字签名验证 (PDF/Hanko) |
| `TextLLM` | 使用GPT-4o-mini进行文本语义分析 |
| `VisionLLM` | 使用GPT-4o进行视觉检查 |
| `InstitutionSniffer` | 证书颁发机构检测 |
| `RevisionCheck` | 文档篡改检测 |
| `StampDetection` | 物理印章/印章检测 |
| `DocumentDiff` | 文档比较和变更检测 |
| `TableVerification` | 表格数据提取和验证 |
| `OnlineVerification` | 通过二维码URL进行在线验证 |
| `URLFetchOperator` | HTTP内容检索 |
| `TemplateFormatter` | 变量模板格式化 |

### 2. 规则管理系统

**规则类型:**
- **标准规则** - 基于条件的检查
- **逻辑图规则** - 可视化工作流构建器，支持DAG执行

**规则配置:**
- 按类别组织（按机构、文档类型）
- 严重级别（严重、错误、警告、信息、参考）
- 规则模板快速设置
- 支持版本控制和回滚
- 规则变更审批工作流

### 3. 工作流自动化

**审批系统:**
- 规则变更请求与审核流程
- 基于风险级别的审批策略
- 基于角色的审批权限
- 所有变更的审计追踪

**通知系统:**
- WebSocket实时更新
- 任务完成邮件通知
- 每日总结报告
- 可定制通知模板

### 4. 安全与认证

**认证方式:**
- 本地密码认证（bcrypt）
- LDAP/Active Directory集成
- OIDC/SSO（Keycloak支持）
- 多提供商支持

**授权机制:**
- 基于角色的访问控制（ADMIN, MANAGER, USER）
- 细粒度权限系统
- 敏感操作的审计日志

**安全特性:**
- JWT令牌认证（2小时过期）
- OIDC的CSRF保护
- WebSocket令牌安全
- Redis密码认证
- MinIO私有桶与预签名URL

### 5. 国际化支持

**语言支持:**
- 简体中文（主要）
- 英语（次要）
- Vue-i18n集成与18n回退机制

---

## 代码组织结构

### 后端目录结构

```
backend/
├── app/
│   ├── api/              # 15+ API路由处理器
│   ├── core/             # 配置、数据库、安全
│   ├── models/           # SQLAlchemy ORM模型 (18个)
│   ├── schemas/          # Pydantic验证模式
│   ├── services/         # 业务逻辑层
│   ├── engine/           # 验证引擎与算子
│   ├── checkers/         # 专门验证模块
│   ├── tasks/            # Celery后台任务
│   ├── utils/            # 辅助工具函数
│   └── main.py           # 应用程序入口
├── tests/                # 测试套件
└── migrations/           # 数据库迁移
```

### 前端目录结构

```
frontend/
├── src/
│   ├── api/              # API客户端模块
│   ├── components/       # 可重用组件 (RuleGraphEditor等)
│   ├── layouts/          # 页面布局 (MainLayout)
│   ├── router/           # Vue Router配置
│   ├── stores/           # Pinia状态管理
│   ├── views/            # 页面组件 (12+个页面)
│   ├── types/            # TypeScript类型定义
│   └── utils/            # 辅助函数
└── dist/                 # 生产构建
```

### 关键文件

**后端入口点:**
- `backend/app/main.py` - FastAPI应用程序设置
- `backend/app/api/__init__.py` - API路由聚合
- `backend/app/engine/core.py` - 验证引擎编排器

**前端入口点:**
- `frontend/src/main.ts` - Vue应用程序启动
- `frontend/src/router/index.ts` - 路由配置
- `frontend/src/App.vue` - 根组件

**配置文件:**
- `backend/.env` - 后端环境变量
- `deploy/docker-compose.yml` - 容器编排
- `deploy/nginx.conf` - 反向代理配置

---

## 部署架构

### 容器服务（6个主要服务）

| 服务名称 | 技术栈 | 端口 | 功能描述 |
|----------|--------|------|----------|
| `backend` | FastAPI | 31234 | 后端API服务 |
| `frontend` | Nginx | 80 | 前端静态文件服务 |
| `postgres` | PostgreSQL 15 | 5432 | 数据库服务 |
| `redis` | Redis 7 | 6379 | 缓存和消息队列 |
| `minio` | MinIO | 9000/9001 | 对象存储服务 |
| `celery-worker` | Celery | - | 后台任务处理 |

### 基础设施特性
- 所有服务的健康检查
- 资源限制（内存/CPU约束）
- 日志轮转（最大10MB，保留3个文件）
- 自动重启策略
- Docker卷持久化

---

## 开发统计

**代码量统计:**
- 后端：~14,651行Python代码
- 前端：~20,867行TypeScript/Vue代码
- 总计：~35,000+行应用程序代码

**技术债务:**
- 前端类型安全（需要减少`any`使用）
- 测试覆盖率扩展
- 文档更新
- 遗留代码重构

---

## 最近更新 (2026-06-20至25)

### 最新功能
- 前端权限控制（用户角色限制）
- 国际化（i18n）中英文支持
- 印章检测优化，提高准确性
- 前端重构（通知存储、请求取消、响应式设计）

### 最近修复
- 印章检测参数调优
- Docker构建优化（多阶段构建）
- 安全增强（密码哈希、CSRF保护）
- 性能改进（并发处理、数据库优化）

---

## 版本历史

| 版本 | 日期 | 主要功能 |
|------|------|----------|
| v1.1.2 | 2026-06-23 | 模块链接和机构名称标准化 |
| v1.1.0 | 2026-06-04 | P2审批工作流和P3版本管理 |
| v1.0.3 | 2026-06-03 | 数据库初始化自动化 |
| v1.0.2 | 2026-05-27 | 变量面板功能 |
| v1.0.1 | 2026-05-25 | 端口配置优化 |
| v1.0.0 | 2026-05-24 | 初始发布 |

---

## 当前开发重点

### 活跃开发领域
- **计算机视觉增强** - 印章检测、印章识别
- **安全加固** - 认证、授权、数据保护
- **性能优化** - 并发处理、数据库查询
- **用户体验改进** - 响应式设计、国际化

### 技术债务
- 前端类型安全（减少`any`使用）
- 测试覆盖率扩展
- 文档更新
- 遗留代码重构

---

## 总结

PPAP是一个复杂的文档验证平台，结合了传统文档处理（PDF解析、数字签名）和现代AI能力（LLM语义分析、计算机视觉）。架构遵循现代微服务模式，前端/后端分离，正确使用异步处理，并具有全面的安全特性。

该平台已生产就绪，具有强大的部署自动化、安全加固和活跃的开发，专注于用户体验改进和AI能力增强。

---

*文档更新日期: 2026-06-25*