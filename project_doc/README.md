# PPAP 项目文档

> 最后更新: 2026-06-25

---

## 目录结构

```
project_doc/
├── README.md                    # 本文件（文档索引）
├── core/                        # 核心文档
│   ├── project_overview.md     # 项目架构总览与技术栈
│   ├── function.md             # 功能清单与模块说明
│   ├── implementation_plan.md  # 实施计划与架构设计
│   ├── status.md               # 项目状态与进度跟踪
│   └── openissue.md            # 待解决问题 (v2.0)
├── features/                    # 功能特性
│   ├── llm_features.md         # AI 模型与 LLM 算子
│   ├── walkthrough.md          # 在线防伪比对 v2 验收汇报
│   └── i18n_progress.md        # 前端国际化迁移进度
├── guides/                      # 配置与开发指南
│   ├── KEYCLOAK_SSO_SETUP.md   # Keycloak SSO 配置
│   ├── PORT_CONFIGURATION_GUIDE.md  # 端口配置说明
│   ├── ONLINE_VERIFICATION_GUIDE.md  # 在线防伪比对模块配置
│   ├── ADD_NEW_MODULE_GUIDE.md  # 新校验模块开发指南
│   ├── LOGIC_GRAPH_VARIABLE_FLOW_GUIDE.md  # 逻辑图变量传递
│   ├── TESTING_AND_INTEGRATION_GUIDE.md  # 测试环境与集成
│   └── MINIO_STORAGE_AND_LIFECYCLE_GUIDE.md  # MinIO 存储管理
└── ops/                         # 运维记录
    └── bugfix_history.md       # 问题修复清单（70 项）
    └── changelog.md            # 变更日志（v1.0.0 - v1.1.3）
    └── optimization_suggestions.md  # 优化建议与路线图
```

---

## 核心文档

| 文档 | 描述 |
|------|------|
| [项目概览](core/project_overview.md) | 架构、技术栈、目录结构、服务清单 |
| [功能清单](core/function.md) | 全功能特性列表（认证、文件、规则引擎、13+算子等） |
| [项目状态](core/status.md) | P0-P3 开发进度与完成情况 |
| [开放问题](core/openissue.md) | 逻辑图引擎变量传递不稳定问题与 3 种解决提案 |
| [实施计划](core/implementation_plan.md) | Dify 风格结构化变量传递系统设计 |

## 功能特性

| 文档 | 描述 |
|------|------|
| [LLM 功能](features/llm_features.md) | TextLLMOperator、VisionLLMOperator、ModelProfile 配置 |
| [在线防伪验收汇报](features/walkthrough.md) | 在线防伪比对 v2 输出增强与 UX 修复验收 |
| [i18n 翻译进度](features/i18n_progress.md) | 前端国际化迁移进度（~85%） |

## 配置与开发指南

| 文档 | 描述 |
|------|------|
| [Keycloak SSO 设置](guides/KEYCLOAK_SSO_SETUP.md) | OIDC/SAML SSO 集成配置 |
| [端口配置指南](guides/PORT_CONFIGURATION_GUIDE.md) | 端口映射规划与迁移（8000→31234） |
| [在线校验指南](guides/ONLINE_VERIFICATION_GUIDE.md) | 在线防伪比对模块使用指南 |
| [新增模块指南](guides/ADD_NEW_MODULE_GUIDE.md) | 新增校验模块的完整步骤 |
| [逻辑图变量流指南](guides/LOGIC_GRAPH_VARIABLE_FLOW_GUIDE.md) | 规则图编辑器变量数据流说明 |
| [测试与集成指南](guides/TESTING_AND_INTEGRATION_GUIDE.md) | 测试策略与集成流程 |
| [MinIO 存储与生命周期指南](guides/MINIO_STORAGE_AND_LIFECYCLE_GUIDE.md) | 对象存储配置与生命周期管理 |

## 运维记录

| 文档 | 描述 |
|------|------|
| [问题修复清单](ops/bugfix_history.md) | 70 项问题修复记录（55/70 已完成） |
| [变更日志](ops/changelog.md) | 版本发布历史（v1.0.0 - v1.1.3） |
| [优化建议](ops/optimization_suggestions.md) | 36 项优化建议与实施路线图 |

## 外部文档

| 文档 | 描述 |
|------|------|
| [部署指南](../deploy/README.md) | Docker 容器化部署指南 |
| [后端开发](../backend/README.md) | FastAPI 后端快速开始 |
| [前端开发](../frontend/README.md) | Vue 3 前端快速开始 |

---

## 项目概况

| 维度 | 数据 |
|------|------|
| 代码总量 | ~35,000+ 行 |
| 后端 | FastAPI + SQLAlchemy + Celery |
| 前端 | Vue 3 + TypeScript + Element Plus |
| 数据库 | PostgreSQL + Redis |
| 服务数 | 6 个 Docker 服务 |
| 验证算子 | 13 个 |
| 数据库表 | 13+ |
| i18n 键 | 947 个（zh-CN / en-US） |
