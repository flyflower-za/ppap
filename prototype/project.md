# 文件校验平台 - 设计文档

## 项目概述

基于 PPAP (Production Part Approval Process) 文件管理需求，开发一个智能文件校验平台。该平台利用 AI Agent 对上传的 PDF 文件进行自动化校验，确保文件符合规范和质量要求。

## 设计规范

### 色彩系统

| 类型 | 颜色代码 | 用途 |
|------|----------|------|
| 主色 | `#4285F4` | 主要操作、链接、强调 |
| 主色悬停 | `#3367D6` | 按钮悬停状态 |
| 成功 | `#4CAF50` | 成功状态、通过校验 |
| 警告 | `#FF9800` / `#F57C00` | 警告状态、待处理 |
| 错误 | `#F44336` / `#D32F2F` | 失败状态、删除操作 |
| 信息 | `#1976D2` | 信息提示 |
| 背景 | `#f5f7fa` | 页面背景 |
| 卡片背景 | `#ffffff` | 卡片、容器背景 |

### 组件规范

#### 按钮样式

```css
/* 主要按钮 */
.btn-primary: background #4285F4, color white

/* 轮廓按钮 */
.btn-outline: transparent background, #4285F4 border

/* 危险按钮 */
.btn-danger: background #F44336, color white

/* 幽灵按钮 */
.btn-ghost: transparent background, #666 color
```

#### 状态徽章

| 状态 | 背景色 | 文字色 |
|------|--------|--------|
| 等待中 (pending) | `#FFF3E0` | `#F57C00` |
| 校验中 (processing) | `#E3F2FD` | `#1976D2` |
| 已完成 (completed) | `#E8F5E9` | `#4CAF50` |
| 失败 (failed) | `#FFEBEE` | `#F44336` |
| 有警告 (warning) | `#FFF3E0` | `#F57C00` |

### 页面布局

#### 导航栏
- 高度: 64px
- 背景: #4285F4
- 内容: Logo | 菜单 | [通知] [语言切换] [用户] [退出]

#### 主内容区
- 最大宽度: 1400px
- 内边距: 32px
- 背景色: #f5f7fa

## 页面结构

### 1. 登录页 (login-page)
- 居中登录卡片
- 邮箱 + 密码表单
- 渐变背景 (#667eea → #4285F4)

### 2. 任务中心页 (task-center-page)
**两栏布局：**
- 左侧：文件上传区（支持批量上传）
- 右侧：任务列表（进行中/已完成/失败）

**核心功能：**
- 拖拽上传 PDF
- 实时任务进度显示
- 任务取消/重新校验

### 3. 历史记录页 (history-page)
**筛选栏：**
- 状态筛选（全部/已完成/失败/有警告）
- 文件类型筛选
- 时间范围选择
- 关键词搜索

**数据表格：**
- 复选框选择
- 批量操作（下载/归档/删除）
- 分页导航

### 4. 详情页 (detail-page)
**三部分内容：**
- 文件头部信息（文件名、状态、元数据）
- 校验结果列表（通过/警告/失败）
- 备注区域（审核记录）

### 5. 消息中心页 (notifications-page)
- 分类标签（全部/未读/已完成）
- 通知列表（成功/错误/警告/信息类型）

### 6. 系统设置页 (settings-page)
**侧边栏导航：**
- 个人信息（只读，SSO 管理）
- 通知设置（邮件开关、SMTP 配置）

## 交互设计

### 弹窗
- 确认退出
- 取消任务
- 删除确认

### 实时通知 (Toast)
- 类型：success/error/warning/info
- 位置：右上角固定
- 自动消失：3秒

### 可折叠区域
- 用于展开复杂配置（如 SMTP 设置）
- 图标旋转指示展开/收起状态

## 文件类型支持

| 类型 | 说明 |
|------|------|
| 生产计划单 | 生产计划相关 PDF 文件 |
| 质量检测报告 | 质量检测相关 PDF 文件 |
| 采购订单 | 采购订单 PDF 文件 |
| 供应商资质 | 供应商资质证明 PDF 文件 |
| 产品规格 | 产品规格说明书 PDF 文件 |

## 校验项

1. 文件格式校验
2. 必要字段完整性
3. 数据一致性校验
4. 签名有效性校验
5. 版本合规性校验
6. 编码规范校验

## 技术约束

- 文件大小限制：50MB
- 支持格式：PDF
- 文件保留期限：30天
- 登录方式：SSO

---

## 技术栈

### 前端技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | 3.4+ | 渐进式框架，组合式 API |
| TypeScript | 5.3+ | 类型安全 |
| Vite | 5.0+ | 构建工具 |
| Element Plus | 2.5+ | UI 组件库 |
| Pinia | 2.1+ | 状态管理 |
| Vue Router | 4.2+ | 路由管理 |
| Axios | 1.6+ | HTTP 客户端 |
| PDF.js | 4.0+ | PDF 预览 |

### 后端技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 编程语言 |
| FastAPI | 0.109+ | Web 框架，异步支持 |
| SQLAlchemy | 2.0+ | ORM |
| AsyncPG | 0.29+ | PostgreSQL 异步驱动 |
| Alembic | 1.13+ | 数据库迁移工具 |
| Pydantic | 2.5+ | 数据验证 |
| Redis | 7+ | 缓存、消息队列 |
| Celery | 5.3+ | 后台任务 |
| MinIO | 最新 | 对象存储 |

### 基础设施

| 技术 | 版本 | 说明 |
|------|------|------|
| PostgreSQL | 15 | 关系型数据库 |
| Redis | 7 | 缓存/队列 |
| MinIO | 最新 | 对象存储 (S3兼容) |
| Nginx | 最新 | 反向代理 |
| Docker | 20+ | 容器化 |
| Docker Compose | 2+ | 容器编排 |

### 第三方服务

| 服务 | 说明 |
|------|------|
| Aliyun Agent | 阿里云 AI 校验引擎（待集成） |
| SSO/LDAP | 企业认证系统（待集成） |

### 项目结构

```
ppap/
├── prototype/          # 原型图
│   ├── index.html     # 原型文件
│   ├── project.md     # 设计文档（本文件）
│   └── progress.md    # 进度文档
├── backend/           # FastAPI 后端
│   ├── app/
│   │   ├── api/       # API 路由
│   │   ├── core/      # 核心配置
│   │   ├── models/    # 数据库模型
│   │   ├── schemas/   # Pydantic schemas
│   │   └── services/  # 业务逻辑
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/          # Vue 3 前端
│   ├── src/
│   │   ├── api/       # API 客户端
│   │   ├── views/     # 页面组件
│   │   ├── layouts/   # 布局组件
│   │   ├── stores/    # Pinia stores
│   │   └── types/     # TypeScript 类型
│   ├── package.json
│   └── Dockerfile
└── deploy/            # 部署配置
    ├── docker-compose.yml
    ├── nginx.conf
    └── init-db.sql
```

### API 设计规范

- **基础路径**: `/api/v1`
- **认证方式**: JWT Bearer Token
- **响应格式**: JSON
- **错误处理**: 统一错误响应
- **文档**: Swagger/OpenAPI (访问 `/docs`)

### 数据库设计

- **users**: 用户表
- **files**: 文件表
- **tasks**: 任务表
- **notifications**: 通知表
- **notes**: 备注表

### 环境变量

后端通过 `.env` 文件配置：
- 数据库连接
- Redis 连接
- MinIO 配置
- JWT 密钥
- 阿里云配置
- SMTP 配置
