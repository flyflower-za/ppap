# 变更日志

> 最后更新: 2026-06-26

---

## [2026-06-26] - 数据库字段同步与任务中心稳定性修复

### 功能描述
- **Note 模型新增 author_name**：补充迁移脚本，修复仲裁记录用户名丢失问题
- **上传队列持久化**：MainLayout 添加 KeepAlive 缓存 TaskCenterPage，切换页面不再丢失文件队列
- **登录兼容修复**：存量用户 password_hash 为 NULL 时首次登录自动设置密码，避免死锁
- **安全漏洞修复**：拒绝 password_hash 为 NULL 的用户通过密码登录，防止任意密码抢占账号；bootstrap 脚本只为本地账号（无 SSO/LDAP 标记）设置 fallback 密码
- **人工仲裁通知闭环**：resolve_review 后标记旧通知已读+创建结果通知；更新 verification_result 中 needs_review 标志
- **用户引导脚本**：新增 `scripts/bootstrap_users.py`，每次部署自动确保存在 admin 用户且 password_hash 不空；集成到 Docker entrypoint 中 backend 启动前自动运行
- **用户管理 CLI 工具**：新增 `backend/scripts/user_cli.py` 和 `manage_users.sh` wrapper 脚本，支持列出/创建/重置密码/激活/停用/提升管理员操作
- **数据安全文档**：在 `deployment_flow.md` 新增"数据安全与备份策略"章节，分析重新部署对用户的影响，确认正常部署无需备份

### 影响范围
- ✅ TaskCenterPage 切换页面不丢失上传队列状态
- ✅ 存量用户首次登录自动设密码（避免 401 死锁）
- ✅ 引导脚本：后台启动前自动 bootstrap 用户（Docker entrypoint）

---

## [2026-06-25] - 时区标准化、印章 AI 增强与消息中心优化

### 功能描述
- **时区标准化**：全后端 25 个文件统一使用 `timezone.utc` 替代废弃的 `datetime.utcnow()`，数据库存储转为 naive UTC 语义；docker-compose 6 个容器添加 `TZ=Asia/Shanghai`；前端 dayjs 添加 utc + timezone 插件，自动检测浏览器时区显示
- **印章检测 AI 增强**：StampDetectionOperator 实现 HSV + VLM 两级级联架构，VLM 验证候选区域是否为真实印章并提取文字，误检率从 ~30-40% 降至 <5%，AI 不可用时自动降级
- **消息中心增强**：后端新增 `DELETE /notifications` 接口，前端添加"清除全部"按钮（含确认对话框），修复时区 500 错误导致的页面反复刷新
- **登录页 UI 优化**：语言切换器改为平铺开关（中文/EN），移至记住我下方；Logo 定位到页面右上角
- **AI 介入规划文档**：创建 `project_doc/ops/ai_integration_plan.md`，系统评估 8 个模块的 AI 介入可行性
- **数据库字段同步**：Note 模型新增 `author_name` 列，补充迁移脚本修复仲裁记录用户名丢失问题
- **人工仲裁流程修复**：resolve_review 后标记旧通知已读+创建结果通知；更新 verification_result 中 needs_review 标志
- **上传队列持久化**：MainLayout 添加 KeepAlive 缓存 TaskCenterPage，切换页面不再丢失文件队列和上传状态

### 影响范围
- ✅ 全后端时间处理（模型默认值、API 赋值、服务逻辑、Celery 任务）
- ✅ 部署容器环境（postgres、redis、minio、backend、frontend、celery-worker）
- ✅ 前端时间格式化显示（浏览器自动检测时区）
- ✅ 印章检测精度（HSV 阈值优化 + VLM 验证）
- ✅ 数据库字段同步（Note 模型新增 author_name + 迁移脚本）
- ✅ 人工仲裁通知闭环（标记旧通知已读 + 创建结果通知）
- ✅ 消息中心 UX（清除全部 + 无限刷新修复）
- ✅ 上传队列切换页面不丢失（MainLayout KeepAlive 缓存）

---

## [2026-06-24] - 基础设施加固与代码质量修复

### 功能描述
- **管理员权限校验修复**：`settings.py` 中所有系统管理类端点统一使用 `get_current_admin` 依赖，消除普通用户可修改系统配置的安全漏洞。
- **401 跳转优化**：前端 Token 过期后使用 SPA 导航跳转，不再整页刷新，支持登录后自动回跳原页面。
- **容器资源限制**：6 个 Docker 服务添加内存/CPU 限制。
- **健康检查**：backend、frontend、celery-worker 添加健康检查。
- **日志轮转**：统一配置 `max-size:10m max-file:3`。
- **Nginx 安全头**：添加 X-Content-Type-Options、X-Frame-Options、X-XSS-Protection、Referrer-Policy。
- **Nginx 速率限制**：登录接口 5 次/分钟，通用 API 10 次/秒。
- **JWT 有效期缩短**：从 24 小时缩短至 2 小时。
- **PostgreSQL 端口隐藏**：移除宿主机端口映射。

### 影响范围
- ✅ 鉴权体系（管理员权限校验修复）
- ✅ 前端 401 处理（SPA 跳转 + 回跳原页）
- ✅ 部署基础设施（资源限制、健康检查、日志轮转、安全头）

---

## [2026-06-24] - 安全加固与登录认证修复

### 功能描述
- **登录密码校验**：新增密码验证，移除邮箱推断角色，新用户默认 USER。
- **OIDC state 校验**：SSO 回调增加 CSRF 防护，state 存储到 Redis 并在回调时校验。
- **WebSocket token 安全**：改为连接后首条消息认证。
- **Redis 鉴权**：添加密码认证，移除宿主机端口映射。
- **密钥自动生成**：部署脚本自动生成强密钥。
- **跨平台部署优化**：MinIO bucket 创建容器化、前端 nginx.conf 内置、健康检查环境变量化。

### 详细修改记录

#### 后端 - 安全与认证
- **auth.py**：新增 `verify_password()` 密码校验；移除邮箱推断角色；无密码哈希的旧用户拒绝登录
- **user.py**：新增 `password_hash` 字段
- **security.py**：移除 passlib，改用 bcrypt 库
- **oidc.py**：state 存储到 Redis（10 分钟过期），回调校验并删除
- **websocket.py**：移除 URL query token，改为首条消息认证

#### 部署 - 安全加固
- **docker-compose.yml**：Redis 移除端口映射 + `--requirepass`；db-init 新增环境变量
- **deploy.sh / deploy.ps1**：自动生成强密钥
- **init-db.sql**：新增 password_hash 列

---

## [2026-06-24] - 在线防伪算子输出增强与预设规则 UX 修复

### 功能描述
- 在线防伪比对算子输出详细化（结构化多维度报告）
- 二维码识别内容可见化（显示具体解码内容）
- 文档差异比对算子元数据增强
- 在线防伪提取语法简化（支持 `{report_id}` 占位符 + `*` 通配符）
- 预设规则 Dirty State 提醒（未保存提示标签 + pulse 动画）

---

## [2026-06-23] - 极简预置规则自初始化与规则管理界面优化

### 功能描述
- 分类创建时自动初始化底座规则
- 规则配置页面重排：基础配置卡片 + 高级自定义列表
- 规则-模块外键直连重构（废除 junction 表）
- 修复级联删除与 NameError 缺陷

---

## [2026-06-23] - 校验模块联动与引擎比对功能增强

### 功能描述
- 引擎机构归一化比对修复（`normalize_institution_name`）
- 自定义规则关联模块配置（多选勾选框）
- Docker 构建忽略文件（`.dockerignore`）

---

## [2026-06-23] - Windows 部署脚本修复

- PowerShell 脚本功能对齐 Bash 脚本
- 添加 `--remove-orphans` 参数
- 后端 API 健康检查 + MinIO bucket 重试

---

## [2026-06-04] - 规则页面全面检查与优化

- 修复 logic_graph 规则保存（`rule_content` 字段缺失）
- 修复全屏编辑器保存后列表不刷新
- 添加规则列表自动刷新

---

## [2026-06-04] - 自主规则配置与逻辑图数据流优化

- 算子注册表去重与前后端命名对准（snake-case 统一）
- 属性面板变量数据流联动
- 全量算子及逻辑图测试套件

---

## [2026-06-04] - P2&P3 规则变更审批流程与版本管理增强

- 规则变更审批流程（ApprovalPolicy + RuleChangeRequest）
- 版本管理中新增 `change_log` 与 `change_request_id`
- 审批中心 UI（ApprovalsPage.vue）

---

## [2026-06-03] - 平台核心功能升级

- AI 置信度与人机协同审核（HITL）
- 可视化文档差异比对高亮
- 规则版本控制与沙盒模拟测试（Dry Run）
- 合规分析仪表盘（DashboardPage.vue）
- 文件列表响应式截断优化

---

## [2026-06-03] - 统一设置页面样式

- LDAP/SSO 与 SMTP 视觉风格统一
- 操作按钮配色对齐
- 本地前端 dist 目录挂载优化

---

## [2026-05-27] - 变量面板功能

- 规则图编辑器添加变量面板（18 个可用变量，按节点类型分组）
- 支持点击变量自动插入到输入框光标位置

---

## [2026-05-25] - 端口配置优化

- 后端端口从 8000 迁移到 31234
- 前端开发服务器代理指向新端口
- Nginx MIME 类型修复（PDF.js worker）
- PDF.js Worker 加载方式修复（CDN）

---

## 版本历史

| 日期 | 版本 | 描述 |
|------|------|------|
| 2026-06-25 | 1.2.0 | 时区标准化 + 印章 AI 增强 + 消息中心优化 |
| 2026-06-25 | 1.1.3 | username 字段支持 + 登录方式扩展 |
| 2026-06-23 | 1.1.2 | 校验模块联动与引擎机构归一化比对修复 |
| 2026-06-23 | 1.1.1 | Windows 部署脚本修复，功能对齐 deploy.sh |
| 2026-06-04 | 1.1.0 | P2 审批流程与 P3 版本管理增强 |
| 2026-06-03 | 1.0.3 | 数据库初始化自动化与 Windows 部署支持 |
| 2026-05-27 | 1.0.2 | 变量面板功能 |
| 2026-05-25 | 1.0.1 | 端口配置优化（8000→31234） |
| 2026-05-24 | 1.0.0 | PPAP 项目初始版本 |
