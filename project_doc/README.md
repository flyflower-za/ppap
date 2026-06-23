# PPAP 项目文档

本目录包含 PPAP 文件验证平台的项目文档。

## 目录结构

```
project_doc/
├── README.md                    # 本文件
├── core/                        # 核心文档
│   ├── function.md             # 功能清单与模块说明
│   ├── implementation_plan.md  # 实施计划与架构设计
│   ├── status.md               # 项目状态与进度跟踪
│   └── openissue.md            # 待解决问题 (v2.0)
└── guides/                      # 配置指南
    ├── KEYCLOAK_SSO_SETUP.md   # Keycloak SSO 配置
    └── PORT_CONFIGURATION_GUIDE.md  # 端口配置说明
```

## 文档索引

### 📋 核心文档 (`core/`)

| 文档 | 描述 |
|------|------|
| [function.md](core/function.md) | 项目功能清单与模块说明 |
| [implementation_plan.md](core/implementation_plan.md) | 实施计划与架构设计 |
| [status.md](core/status.md) | 项目状态与进度跟踪 |
| [openissue.md](core/openissue.md) | 算子引擎变量传递问题分析 (v2.0 待优化) |

### 🔧 配置指南 (`guides/`)

| 文档 | 描述 |
|------|------|
| [KEYCLOAK_SSO_SETUP.md](guides/KEYCLOAK_SSO_SETUP.md) | Keycloak SSO 单点登录配置指南 |
| [PORT_CONFIGURATION_GUIDE.md](guides/PORT_CONFIGURATION_GUIDE.md) | 端口配置说明 |
| [ONLINE_VERIFICATION_GUIDE.md](guides/ONLINE_VERIFICATION_GUIDE.md) | 在线防伪比对模块配置指南 (含简化提取语法) |
| [ADD_NEW_MODULE_GUIDE.md](guides/ADD_NEW_MODULE_GUIDE.md) | 新校验模块开发指南 (算子与数据表单动态绑定) |
| [LOGIC_GRAPH_VARIABLE_FLOW_GUIDE.md](guides/LOGIC_GRAPH_VARIABLE_FLOW_GUIDE.md) | 逻辑图变量传递与数据流配置指南 |
| [TESTING_AND_INTEGRATION_GUIDE.md](guides/TESTING_AND_INTEGRATION_GUIDE.md) | 测试环境与集成测试运行指南 |
| [MINIO_STORAGE_AND_LIFECYCLE_GUIDE.md](guides/MINIO_STORAGE_AND_LIFECYCLE_GUIDE.md) | MinIO 对象存储与文件生命周期管理指南 |

### 📁 部署文档

| 文档 | 描述 |
|------|------|
| [../deploy/README.md](../deploy/README.md) | Docker 容器化部署指南 |

### 📝 变更日志

| 文档 | 描述 |
|------|------|
| [../CHANGELOG.md](../CHANGELOG.md) | 项目变更日志 (位于项目根目录) |

---

*文档整理日期: 2026-06-23*
