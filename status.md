# PPAP 文件校验平台 - 项目遍历报告

本报告记录了项目当前的代码结构、技术栈设计、已有进度以及未来的关键待办任务，作为项目开发后续的参考基准。

---

## 📂 项目整体目录结构

本平台为一个基于 **PPAP (生产件批准程序) 的智能文件校验平台**。项目包含以下四大核心模块：

```text
ppap/
├── prototype/          # 交互式原型图与产品设计文档
│   ├── index.html     # 可在浏览器中直接打开的高保真交互原型
│   ├── project.md     # 系统设计说明书（色彩、组件规范、校验项定义）
│   └── progress.md    # 开发进度跟踪表
├── backend/           # 基于 Python FastAPI 的异步后端
│   ├── app/           # 后端核心业务逻辑
│   ├── requirements.txt # 后端依赖清单
│   └── Dockerfile     # 后端容器化配置
├── frontend/          # 基于 Vue 3 + TypeScript 的现代前端
│   ├── src/           # 前端源代码（Views/Components/Layouts/Stores）
│   ├── package.json   # 前端依赖配置
│   └── Dockerfile     # 前端容器化配置
└── deploy/            # 容器化部署编排配置
    ├── docker-compose.yml # 包含 PG, Redis, MinIO, Backend, Frontend
    ├── nginx.conf     # 反向代理与动静分离配置
    └── init-db.sql    # 数据库初始化脚本
```

---

## 🖥️ 后端架构深入 (`backend/app`)

后端使用了 **FastAPI + SQLAlchemy 2.0 (异步) + Pydantic v2 + Redis + MinIO** 的现代企业级技术栈：

1. **核心组件 (`core/`)**：
   * `config.py`: 基于 Pydantic Settings 的强类型环境变量与应用配置。
   * `database.py`: 配置了 SQLAlchemy 异步引擎 (`create_async_engine`)。
   * `security.py`: 提供 JWT 编码/解码与密码 Hash 加密。
   * `redis.py`: 封装了基于 `redis-py` 的异步 Redis 客户端连接。
   * `minio_client.py`: 封装了 MinIO 存储服务，负责 PDF 文件生命周期管理。
2. **数据模型与 Schema (`models/` & `schemas/`)**：
   * 包含 `User` (用户表)、`File` (文件表)、`Task` (AI 校验任务表)、`Notification` (系统通知表)、`Note` (审核备注表) 对应的 ORM 模型与 Pydantic 校验模型。
3. **业务逻辑层 (`services/`)**：
   * `file_service.py`: 处理文件上传、生命周期管理与解析。
   * `notification_service.py`: 管理未读消息、标记已读及全局消息分发。
   * `aliyun_service.py`: 预留阿里云 AI 校验引擎的模拟及后期真实集成逻辑。
4. **API 控制层 (`api/`)**：
   * 细分为 `auth`、`files`、`notifications`、`notes` 等子路由。通过 `deps.py` 提供统一的 JWT 依赖注入（如 `get_current_user`）。
5. **服务入口 (`main.py`)**：
   * 使用 `asynccontextmanager` 生命周期管理器管理 Redis 和 MinIO 的异步连接初始化与释放。

---

## 🎨 前端架构深入 (`frontend/src`)

前端采用 **Vue 3 (Composition API) + TypeScript + Vite + Element Plus + Pinia**：

1. **主布局与导航 (`layouts/`)**：
   * `MainLayout.vue`: 实现了规范的 64px 蓝色导航栏布局（Logo、面包屑、通知中心、用户 SSO 头像、退出）。
2. **状态管理与路由 (`stores/` & `router/`)**：
   * `stores/auth.ts`: 管理用户登录 Token、SSO 状态与用户信息。
   * `router/index.ts`: 路由守卫机制，未登录重定向至登录页，支持面包屑自动生成。
3. **视图页面 (`views/`)**：
   * `LoginPage.vue`: 带有渐变背景的卡片登录页面。
   * `TaskCenterPage.vue`: 批量拖拽文件上传区与校验任务列表（双栏）。
   * `HistoryPage.vue`: 综合筛选（状态/类型/时间/检索）+ 批量下载/删除 + 分页表格。
   * `FileDetailPage.vue`: 三段式结构（元数据、校验大纲、审核意见/批注）。
   * `NotificationsPage.vue`: 消息分类查看与标记已读。
   * `SettingsPage.vue`: 个人信息（SSO 制度只读）与折叠式邮件/SMTP 设置。

---

## ⚙️ 部署环境 (`deploy/`)

* 配置了 `docker-compose.yml`，一键启动包含 **PostgreSQL 15**、**Redis 7**、**MinIO (对象存储)**、**FastAPI 后端**、**Nginx 前端** 和 **Celery 异步 Worker** 在内的全套容器服务。
* 使用 `init-db.sql` 自动初始化必要的物理表结构和演示账号数据。

---

## 📌 当前项目开发进度与待开发项

目前**核心框架和接口已搭建完毕，且前端页面已完成高保真实现与关键 Runtime Bug 修复**，后续的关键开发任务（按照优先级排序）包括：

### 🚀 已完成的重要里程碑
1. **🎨 登录页面视觉与交互高级重构**：
   * 移除了动态流动极光背景，改用扁平沉稳的紫蓝渐变背景。
   * 右侧操作登录区重新打造为精致的高级悬浮质感卡片，配合圆角圆滑设计 (`border-radius: 28px`)，并在大屏及小屏下与侧边边界均留出合理的视觉缝隙，呈现卓越的立体悬浮感。
   * 快捷演示通道选项重构为雅致的灰色药丸（Pill）徽章按钮，避免与输入框混淆，并将演示邮箱后缀统一为 `@example.com`。
2. **🔌 数据库端口冲突与类型崩溃修复**：
   * 将容器 PostgreSQL 的本地映射端口调整为 `5435`，避开 Host 机器 Dify 容器的 5432 端口冲突。
   * 修改 SQLAlchemy 全部 5 个核心 ORM 模型主键及外键 ID 类型为 `UUID(as_uuid=False)`，彻底解决 Python 异步驱动准备语句中的 String-to-UUID 强制转换异常（`DatatypeMismatchError`）。
3. **💻 前端核心展示组件补全与 Runtime 闪白修复**：
   * 全面实现并挂载了 `TaskList.vue`（任务中心右侧卡片）与 `NotificationList.vue` 核心组件。
   * 修复了 [MainLayout.vue](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/frontend/src/layouts/MainLayout.vue) 中缺失 Vue `ref` 导入导致的全局 runtime 引用崩溃。
   * 重构了 [router/index.ts](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/frontend/src/router/index.ts)，将重复注册的顶级 `/` 路径合并，消除路由冲突；同时在导航守卫中引入 Startup Profile 自动加载机制，在 Token 存在但用户状态为空时自动拉取用户信息（`fetchMe`），若 Token 失效则平滑退登。
4. **⚙️ 接口请求传参参数类型订正**：
   * 将后端 `backend/app/api/files.py` 路由中文件查询接口的 `status` 参数类型从错误的 `FileTypeEnum` 订正为 `FileStatusEnum`，根除了任务中心切换状态 Tab 时由于接口参数验证错误返回 422 导致的挂起与渲染崩溃。
   * 自动为 demo 注册用户添加了角色检查，使包含 `admin` 的邮箱（如 `admin@example.com`）自动在库中设为管理员账户。

### 优先级 P0 (核心功能)
1. **数据库迁移** - 配置 Alembic 进行物理数据库迁移与升级管理。
2. **校验任务异步处理** - 实现 Celery 后台异步校验任务与 Redis 队列消费。

### 优先级 P1 (重要功能)
3. **阿里云 AI 真实集成** - 接入真实的阿里云 AI OCR/文本比对与智能校验服务。
4. **实时进度推送** - 引入 WebSocket 或 SSE 机制，实现后台校验进度向前端的实时推送。
5. **文件下载与导出** - 完善原始 PDF 文件以及 Excel 格式的校验报告导出功能。
6. **邮件通知系统** - 集成 SMTP，实现校验失败或触发重大警告时的自动邮件提醒。

### 优先级 P2 (增强体验)
7. **PDF.js 在线预览** - 集成 PDF.js 渲染器，支持在文件详情页在线查看并高亮异常字段。
8. **审计日志追踪** - 记录用户的敏感操作及系统校验轨迹。
9. **定时任务文件清理** - 配合 Celery Beat 自动清理超过保留期限（30天）的失效文件。

