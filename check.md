# PPAP 文件校验平台 — 项目遍历报告

> 生成日期: 2026-05-25

---

## 项目概览

**PPAP (Production Part Approval Process)** — 基于 AI 的 PDF 自动校验平台，后端 FastAPI + 前端 Vue 3 + 容器化部署。

---

## 技术栈

| 层 | 技术 | 版本 |
|---|------|------|
| **后端** | Python FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 | Python 3 |
| **数据库** | PostgreSQL 15 (外部端口 5435) + Redis 7 | Docker |
| **对象存储** | MinIO (端口 9000/9001) | Docker |
| **任务队列** | Celery + Celery Beat (Redis broker) | v5.3.6 |
| **前端** | Vue 3.4 + TypeScript 6.0 + Element Plus + Pinia + Vue Router | Vite 5 |
| **部署** | Docker Compose (Nginx 反向代理) | — |

---

## 目录结构

```
ppap/
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── api/                 # 路由层
│   │   │   ├── auth.py          # 认证
│   │   │   ├── files.py         # 文件管理
│   │   │   ├── settings.py      # 系统设置 (含文件保留)
│   │   │   ├── rules.py         # 规则引擎配置
│   │   │   ├── audit.py         # 审计日志
│   │   │   ├── notifications.py # 通知
│   │   │   ├── notes.py         # 审核备注
│   │   │   ├── ldap.py          # LDAP 集成
│   │   │   └── websocket.py     # WebSocket
│   │   ├── core/                # 核心基础设施
│   │   │   ├── config.py        # Pydantic Settings 配置
│   │   │   ├── security.py      # JWT + 密码哈希
│   │   │   ├── database.py      # SQLAlchemy 异步引擎
│   │   │   ├── redis.py         # Redis 客户端封装
│   │   │   ├── minio_client.py  # MinIO 封装
│   │   │   ├── permissions.py   # 权限控制
│   │   │   └── audit_logger.py  # 审计日志记录
│   │   ├── models/              # ORM 模型
│   │   │   ├── user.py, file.py, task.py, rule.py
│   │   │   ├── note.py, notification.py, setting.py
│   │   │   ├── audit.py, ldap_config.py, email_template.py
│   │   ├── schemas/             # Pydantic 校验模型
│   │   ├── services/            # 业务逻辑层
│   │   │   ├── file_service.py
│   │   │   ├── notification_service.py
│   │   │   ├── email_service.py
│   │   │   ├── email_template_service.py
│   │   │   └── aliyun_service.py
│   │   ├── checkers/            # PDF 校验核
│   │   │   ├── pdf_info.py      # 文本型 PDF 结构判定
│   │   │   ├── qr_decoder.py    # 二维码溯源提取
│   │   │   ├── sig_verifier.py  # 标准电子签名验证
│   │   │   └── sig_verifier_manual.py  # 国密电子签名验证
│   │   ├── engine/              # 规则引擎
│   │   │   ├── base.py          # 基础算子接口
│   │   │   ├── core.py          # DAG 引擎核心
│   │   │   └── operators/       # 算子实现
│   │   │       ├── pdf_info_operator.py
│   │   │       ├── qr_operator.py
│   │   │       ├── signature_operator.py
│   │   │       ├── sniffer_operator.py
│   │   │       ├── text_llm_operator.py
│   │   │       └── vision_llm_operator.py
│   │   ├── tasks/               # Celery 任务
│   │   │   ├── celery_app.py
│   │   │   ├── verification_tasks.py
│   │   │   ├── cleanup_tasks.py       # PDF 自动清理
│   │   │   ├── daily_summary.py
│   │   │   └── scheduler_tasks.py     # Celery Beat 调度
│   │   ├── data/                # 初始化脚本
│   │   └── main.py              # FastAPI 入口
│   ├── tests/                   # 测试
│   │   ├── api/, checkers/, engine/, tasks/
│   │   ├── conftest.py, fixtures.py
│   ├── migrations/              # Alembic 迁移
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                    # Vue 3 前端
│   ├── src/
│   │   ├── views/               # 8 个页面
│   │   │   ├── LoginPage.vue
│   │   │   ├── TaskCenterPage.vue
│   │   │   ├── FileDetailPage.vue
│   │   │   ├── HistoryPage.vue
│   │   │   ├── RulesPage.vue
│   │   │   ├── SettingsPage.vue
│   │   │   ├── NotificationsPage.vue
│   │   │   └── AuditLogPage.vue
│   │   ├── components/          # 3 个通用组件
│   │   │   ├── TaskList.vue
│   │   │   ├── NotificationList.vue
│   │   │   └── RuleGraphEditor.vue  # VueFlow DAG 编辑器
│   │   ├── api/                 # 8 个 API 模块
│   │   ├── layouts/MainLayout.vue
│   │   ├── router/index.ts
│   │   ├── stores/auth.ts       # Pinia 状态管理
│   │   ├── types/index.ts
│   │   ├── styles/main.css
│   │   └── main.ts
│   └── package.json
│
├── deploy/                      # 容器化部署
│   ├── docker-compose.yml       # 5 个服务编排
│   ├── nginx.conf               # 反向代理配置
│   ├── init-db.sql              # 数据库初始化 SQL
│   └── .env
│
├── prototype/                   # 高保真原型与设计文档
│   ├── index.html               # 可交互原型
│   ├── project.md               # 设计规范文档
│   └── progress.md              # 开发进度跟踪
│
├── check.md                     # 本文件 — 项目遍历报告
├── CHANGELOG.md                 # 变更日志
├── IMPLEMENTATION_SUMMARY.md    # PDF 自动清理功能实现总结
├── deploy.sh                    # 一键部署脚本
├── setup_firewall.sh            # 防火墙配置
├── start.md                     # 启动命令备忘
└── status.md                    # 项目状态摘要
```

---

## 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| 后端 API | 31234 | FastAPI (swagger: /docs) |
| 前端开发 | 5173 | Vite dev server |
| 前端生产 | 80 | Nginx |
| PostgreSQL | 5435→5432 | 外部映射 |
| Redis | 6379 | — |
| MinIO API | 9000 | — |
| MinIO Console | 9001 | 管理界面 |

---

## 已实现的核心功能

| 功能 | 描述 | 涉及模块 |
|------|------|----------|
| **PDF 智能校验引擎** | 文本结构判定、国密/标准电子签名、二维码溯源、页码交叉核查 | `checkers/`, `engine/operators/` |
| **可视化规则引擎** | VueFlow DAG 节点图拖拽编排验证规则 | `components/RuleGraphEditor.vue`, `views/RulesPage.vue` |
| **人工审核工作流** | 自动校验 → 待人工审核 → 人工复核闭环 | `engine/`, `services/` |
| **PDF 在线预览** | pdfjs-dist 集成，校验区域高亮标记 | `views/FileDetailPage.vue` |
| **审计报表导出** | 23 列 Excel 导出 (UTF-8 BOM) | `api/files.py` → 前端 |
| **邮件通知系统** | SMTP 设置管理，Celery 异步发送 | `services/email_service.py`, `tasks/` |
| **PDF 自动清理** | 定时清理 MinIO 过期文件，管理员配置保留天数 | `api/settings.py`, `tasks/cleanup_tasks.py` |
| **数字证书提取** | 证书主体、CA 机构、时效，折叠式 UI | `checkers/sig_verifier.py` |
| **审计日志追踪** | 敏感操作全链路记录 | `core/audit_logger.py`, `views/AuditLogPage.vue` |
| **多 AI 模型配置** | API Key 脱敏管理，多 Profile 切换 | `api/settings.py` |
| **LDAP 集成** | 企业级目录认证 | `api/ldap.py` |
| **文件重新校验** | 一键重新触发校验流程 | `api/files.py` |
| **Alembic 迁移** | 数据库结构版本管理 | `migrations/` |

---

## Git 历史 (最近 20 条)

```
828b51b Fix digital signature detection and display issues
6bb2cc0 fix: 端口配置优化和PDF渲染问题修复
feecebe refactor: suppress database init output and consolidate MinIO bucket configuration
e35e77f chore: upgrade typescript to 6.0.3, update build script
cee106c feat: add deployment script and testing utilities
c52ef41 fix: resolve institution sniffing and fix celery & pydantic async/serialization issues
fa602b3 feat: implement file re-verification workflow, enhance PDF annotation rendering, enable HTTPS
1fd84ce feat: add Celery macOS startup script, enhance audit logging metadata
5528c9c feat: implement audit logging for model profile management, improve file detail navigation
32207ec feat: implement multi-profile AI model management with API key masking
1446894 feat(audit): implement full-stack audit logging for sensitive operations
f2004a9 fix: remove fullscreen mode for logic graph rules and add playwright dependency
f5c08ea fix(frontend): resolve VueFlow initialization warning and TypeScript types
c5e0cde fix(frontend): resolve rule graph editor rendering timing, null config validation
4c1aad9 fix(frontend): remove JSON.stringify deep cloning in RuleGraphEditor
6d139df fix(frontend): import watch from vue in RulesPage to fix crash
fd69a3e fix(frontend): deep clone nodes/edges and use nextTick in RuleGraphEditor
dde6ce6 fix(frontend): default rule type for new rules to keyword in RulesPage
e2dfbb4 fix(frontend): add prop attributes to all el-form-item fields
932e984 fix(frontend): resolve incorrect use of <label for=FORM_ELEMENT> warning
```

---

## Git 当前状态 (未提交/未跟踪)

- **未暂存删除**: `.DS_Store`, `.memory/project-constraints.md`, 旧 PDF 文件, `PDF_CLEANUP_FEATURE.md`, `RULE_GRAPH_FIX.md`, `implementation_plan.md`
- **未跟踪**: `.claude/` 配置, 后端若干 PDF 签名测试脚本, `deploy/.env`, `deploy/package-lock.json`

---

## 待完成的 P1 事项

- [ ] **实时进度推送** — 引入 WebSocket 或 SSE 机制，实现后台校验进度向前端的实时推送

## 待完成的 P2 事项

- [ ] 审计日志可视化面板增强
- [ ] 批量文件处理优化
- [ ] 清理前邮件通知
- [ ] 文件归档功能 (冷存储)

---

## 架构需求 vs 当前实现 — 差距分析

> 基于 `Agent + Workflow` PDF 校验架构设计文档的逐项比对

### 一、 前端设计

| 需求 | 当前状态 | 差距 |
|------|----------|------|
| **批量上传队列** | ✅ 已有 `fileList` 队列 + batch mode | — |
| **上传并发控制** | ✅ 已实现 | 默认并发上限 3，使用 worker 池模式处理 |
| **分片上传/断点续传** | ❌ 不支持 | 大文件（>10MB）无分片 |
| **前端预校验** | ✅ 检查 .pdf 后缀、MIME 类型、≤50MB 大小限制 | — |
| **SSE/WebSocket 实时进度** | ⚠️ 部分实现 | WebSocket 仅挂载在 FileDetailPage，TaskCenterPage 无实时进度 |
| **自定义规则配置 UI (VueFlow)** | ✅ RuleGraphEditor.vue 完整实现 | — |

### 二、 核心校验逻辑 (Workflow / 确定性流程)

| 需求 | 当前状态 | 差距 |
|------|----------|------|
| **加密检测** | ⚠️ 部分实现 | `sig_verifier.py` 中作为签名检查的副产物处理，没有独立的加密检测节点/规则 |
| **数字签名验证** | ✅ pyHanko 异步验证 PKCS#7 签名完整性 | — |
| **Revision 检测 (增量更新/二次修改)** | ✅ **已实现** | `checkers/revision_checker.py` 通过 xref 计数检测修订版本数，`RevisionCheckOperator` 跨引用签名数据，`Revision > 1 + 已签名` 时标记篡改风险。前端 RuleGraphEditor 新增 `revision-check` 节点，支持配置允许增量更新 |
| **内容提取 (文本 + 空间块)** | ✅ pdf_info.py 使用 PyMuPDF 提取文本、字符数、blocks | — |
| **表格提取** | ❌ 无专用表格解析 | 仅在 `pdf_info.py` 中提取原始 blocks，无结构化表格识别 |
| **OCR (扫描件识别)** | ❌ **缺失** | 无 PaddleOCR/Tesseract 集成。扫描版 PDF 无法提取文字 |
| **安全沙箱** | ❌ **缺失** | PDF 解析在 Celery worker 主进程中直接运行，无 Docker/gVisor 隔离。恶意 PDF 有安全风险 |

### 三、Agent 引擎 (非确定性流程)

| 需求 | 当前状态 | 差距 |
|------|----------|------|
| **Agent 框架 (LangGraph / Dify)** | ❌ 未集成 | 当前用自定义 `VerificationEngine` + `BaseOperator` 简单编排，无 LangGraph/Dify 支持 |
| **阿里云百炼 Workflow 集成** | ❌ **缺失** | `aliyun_service.py` 是**纯 mock**，所有 `call_qwen_async` 返回硬编码模拟数据。与百炼 API 的正式集成未开始 |
| **LLM 内容校验** | ⚠️ 部分实现 | `TextLLMOperator` / `VisionLLMOperator` 有完整框架但实际 AI 调用为 mock 回退（无真实 API Key 时返回硬编码数据） |
| **外部数据比对 (工商/发票验真)** | ❌ 无插件系统 | 无外部 API 调用节点 |

### 四、后端工程化

| 需求 | 当前状态 | 差距 |
|------|----------|------|
| **异步任务队列 (Celery + Redis)** | ✅ 完整实现 | — |
| **进度推送 (Redis Pub/Sub → WebSocket)** | ✅ 实现（`websocket.py` + `verification_tasks.py` 中的 `publish_progress`） | — |
| **SSE 流式响应** | ❌ 未实现 | 仅有 WebSocket，无 SSE endpoint |
| **文件生命周期管理** | ✅ cleanup_tasks 定时清理过期文件 | — |
| **敏感操作审计** | ✅ audit_logger + AuditLogPage | — |
| **通知系统** | ✅ 站内通知 + Celery 邮件 | — |

### 五、核心避坑清单 Compliance

| 避坑项 | 当前是否已规避 | 说明 |
|--------|--------------|------|
| **不用大模型做验签/查篡改** | ✅ 是 | 签名和基础校验走 pyHanko / PyMuPDF，LLM 仅用于语义分析 |
| **Revision (增量更新) 检测** | ✅ **已规避** | 通过 `revision_checker.py` 检查 xref 计数，`RevisionCheckOperator` 在引擎中自动运行 |
| **大模型上下文窗口与成本控制** | ⚠️ 部分 | `text_llm_operator.py` 截断到 10000 字符，但无关键页智能提取 |
| **前端防崩溃 (并发控制)** | ✅ **已规避** | 上传队列使用 worker 池模式，默认并发上限 3 |
| **安全沙箱 (恶意 PDF)** | ❌ **未规避** | Celery worker 无容器隔离 |
| **OCR 扫描件支持** | ❌ **未规避** | 扫描版 PDF 完全无法处理 |

### 优先级建议

| 优先级 | 事项 | 影响 | 状态 |
|--------|------|------|------|
| **P0** | **Revision 检测 (增量更新/二次修改)** | 核心合规需求，误判直接影响业务决策 | ✅ **已完成** |
| **P0** | **阿里云百炼 Workflow 真实集成** | 当前 `aliyun_service.py` 为 mock，无法实际对接 | ⏳ 待实现 |
| **P1** | **OCR 集成** | 扫描件 PDF 当前完全无法处理 | ⏳ 待实现 |
| **P1** | **安全沙箱 (容器隔离)** | 恶意 PDF 安全风险 | ⏳ 待实现 |
| **P1** | **上传并发控制** | 浏览器崩溃风险 | ✅ **已完成** |
| **P2** | **分片上传/断点续传** | 大文件上传体验 | ⏳ 待实现 |
| **P2** | **SSE 流式响应** | 进度推送补充方案 | ⏳ 待实现 |
| **P2** | **LangGraph/Dify 集成** | 增强 Agent 编排能力 | ⏳ 待实现 |
