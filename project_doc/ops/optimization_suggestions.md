# PPAP 项目优化建议

> 生成时间: 2026-06-24
> 审计范围: Backend (FastAPI), Frontend (Vue 3), 部署/基础设施

---

## 一、安全问题 (Critical) — 全部已完成 ✅

| # | 问题 | 文件 | 状态 |
|---|------|------|------|
| 1.1 | 登录接口未校验密码 | `auth.py` | ✅ |
| 1.2 | 基于邮箱自动推断角色 | `auth.py` | ✅ |
| 1.3 | 硬编码默认密钥 | `config.py`, `docker-compose.yml` | ✅ |
| 1.4 | MinIO Bucket 设为 public | `deploy.sh` | ✅ |
| 1.5 | Redis 未鉴权且暴露到宿主机 | `docker-compose.yml` | ✅ |
| 1.6 | OIDC 回调未校验 state | `oidc.py` | ✅ |
| 1.7 | WebSocket 通过 Query 传 Token | `websocket.py` | ✅ |

---

## 二、性能问题 (High) — 全部已完成 ✅

| # | 问题 | 文件 | 状态 |
|---|------|------|------|
| 2.1 | Celery dispose 共享 engine | `verification_tasks.py` | ✅ |
| 2.2 | 统计查询加载 1000 条 JSON | `files.py` | ✅ |
| 2.3 | 同步 MinIO 阻塞事件循环 | `minio_client.py` | ✅ |
| 2.4 | N+1 查询模式 | `file_service.py` | ✅ |
| 2.5 | 前端固定 2 秒轮询 | `TaskList.vue` | ✅ |
| 2.6 | URLFetchOperator 临时文件未清理 | `url_fetch_operator.py` | ✅ |

---

## 三、代码质量问题 (Medium)

| # | 问题 | 文件 | 建议 | 状态 |
|---|------|------|------|------|
| 3.1 | VerificationEngine 超大类 (1355+ 行) | `engine/core.py` | 拆分为 RuleRouter、OperatorScheduler 等 | 待修复 |
| 3.2 | RuleGraphEditor 与 FullscreenRuleEditor 重复 | 两个 Vue 文件 | 提取 useGraphEditor.ts composable | 待修复 |
| 3.3 | SettingsPage 超大组件 (2647 行) | `SettingsPage.vue` | 拆分为子组件 | 待修复 |
| 3.4 | 重复的状态/文本映射函数 | 多个 Vue 文件 | 提取到 utils/formatters.ts | ✅ 已修复 |
| 3.5 | AI 配置加载重复代码 | 两个 LLM operator | 提取到 ai_config_service.py | ✅ 已修复 |
| 3.6 | 模型时间戳类型不一致 | `verification_module.py` | 统一为 DateTime | 待修复 |
| 3.7 | UUID 存储为字符串 | 多个 model | 使用 UUID(as_uuid=True) | 待修复 |
| 3.8 | 错误响应格式不一致 | `main.py` vs 各路由 | 统一错误响应 schema | 待修复 |
| 3.9 | 多处 TODO 未实现管理员检查 | `settings.py` | 替换为 get_current_admin | ✅ 已修复 |
| 3.10 | 全局可变 Engine 实例 | `modules.py` | 每请求创建实例 | ✅ 已修复 |

---

## 四、前端问题 (Medium)

| # | 问题 | 建议 | 状态 |
|---|------|------|------|
| 4.1 | 大量使用 `any` 类型 | 为每个 API 端点定义响应接口，启用 strict | 待修复 |
| 4.2 | 401 处理器硬跳转 | 使用 router.push('/login') | ✅ 已修复 |
| 4.3 | 通知"全部已读"未调 API | 调用批量标记已读接口 | ✅ 已修复 |
| 4.4 | MainLayout 未读数永远为 0 | 连接 notification store | ✅ 已修复 |
| 4.5 | 全局错误处理器重复弹 toast | 让全局处理器可选 | ✅ 已修复 |
| 4.6 | 请求无取消机制 | 集成 AbortController | 待修复 |
| 4.7 | Element Plus 全量引入 | 使用按需导入 | 待修复 |
| 4.8 | 无响应式设计 | 添加响应式断点 | 待修复 |

---

## 五、基础设施问题 (Medium)

| # | 问题 | 状态 |
|---|------|------|
| 5.1 | 无容器资源限制 | ✅ 已修复 |
| 5.2 | 无健康检查 | ✅ 已修复 |
| 5.3 | 无日志轮转 | ✅ 已修复 |
| 5.4 | Nginx 缺少安全头部 | ✅ 已修复 |
| 5.5 | Nginx 无速率限制 | ✅ 已修复 |
| 5.6 | 防火墙缺少默认拒绝策略 | 待修复 |
| 5.7 | JWT 有效期过长 (24小时) | ✅ 已修复 |
| 5.8 | PostgreSQL 端口暴露宿主机 | ✅ 已修复 |
| 5.9 | Backend Dockerfile 非多阶段构建 | ✅ 已修复 |

---

## 六、运维与 CI/CD (Medium)

| # | 问题 | 状态 |
|---|------|------|
| 6.1 | 无 CI/CD 流水线 | 待修复 |
| 6.2 | 无自动备份策略 | 待修复 |
| 6.3 | 开发依赖混入生产 requirements | ✅ 已修复 |
| 6.4 | 依赖版本不一致 | 待修复 |

---

## 七、配置问题 (Low)

| # | 问题 | 状态 |
|---|------|------|
| 7.1 | DEBUG 模式默认 True | ✅ 已修复 |
| 7.2 | APP_BASE_URL 默认 localhost | ✅ 已修复 |
| 7.3 | 文件保留期限三处定义 | ✅ 已修复 |
| 7.4 | deploy/README.md 内容过时 | ✅ 已修复 |
| 7.5 | 缺少架构图和运维手册 | 待修复 |

---

## 优化优先级总结

| 优先级 | 数量 | 关键项 | 完成 |
|--------|------|--------|------|
| **Critical** | 7 | 登录校验、密钥、MinIO、Redis、OIDC、WebSocket | ✅ 全部完成 |
| **High** | 6 | Engine dispose、统计查询、异步 MinIO、N+1、轮询、临时文件 | ✅ 全部完成 |
| **Medium** | 28 | 超大类/组件、`any` 类型、CI/CD、防火墙 | 完成 14/28 |
| **Low** | 5 | DEBUG、BASE_URL、文档过时 | 完成 4/5 |

---

## 建议实施路线图

### 第一阶段 (安全加固) — 全部完成 ✅
1. 修复登录密码校验
2. 移除邮箱角色推断
3. 密钥默认值移除 + 启动检查
4. MinIO bucket 改为 private
5. Redis 移除端口映射 + 添加鉴权
6. OIDC state 校验
7. Nginx 安全头部 + HTTPS

### 第二阶段 (性能与稳定性) — 全部完成 ✅
8. 修复 Celery engine.dispose
9. 优化统计查询
10. 容器资源限制和健康检查
11. 日志轮转
12. 异步 MinIO
13. N+1 查询优化
14. 前端轮询优化
15. 临时文件清理

### 第三阶段 (代码质量) — 待推进
16. 拆分超大类/组件
17. 消除重复代码
18. TypeScript 严格模式
19. 统一错误响应格式
20. Element Plus 按需导入

### 第四阶段 (运维完善) — 待推进
21. CI/CD 流水线
22. 自动备份策略
23. 依赖版本管理
24. 文档更新 + 运维手册

---

## 上线优先级评估

### 🔴 第一梯队：上线前必须解决 — 全部完成 ✅
| # | 问题 | 风险 |
|---|------|------|
| 1 | 容器无资源限制 | 内存耗尽全部崩溃 |
| 2 | 无健康检查 | 服务挂了不会自动重启 |
| 3 | 无日志轮转 | 日志填满磁盘 |
| 4 | Nginx 无 HTTPS + 安全头 | 明文传输、XSS |
| 5 | Nginx 无速率限制 | 暴力破解 |
| 6 | PostgreSQL 端口暴露 | 数据库被攻击 |
| 7 | Settings API 未校验管理员 | 普通用户可修改配置 |
| 8 | JWT 有效期 24 小时 | token 泄露后长期可用 |

### 🟡 第二梯队：上线后一周内解决
| # | 问题 | 影响 |
|---|------|------|
| 9 | 前端 `any` 类型泛滥 | 后端字段变更只能运行时发现 |
| 10 | 401 硬跳转丢状态 | 已修复 |
| 11 | 未读数永远为 0 | 已修复 |
| 12 | 通知"全部已读"未调 API | 已修复 |
| 13 | Element Plus 全量引入 | 首屏多 500KB+ |
| 14 | 无响应式设计 | 窄屏无法使用 |
| 15 | DEBUG 模式默认 True | 已修复 |
| 16 | 错误响应格式不一致 | 前端难统一处理 |
| 17 | Backend Dockerfile 非多阶段构建 | 已修复 |

### 🟢 第三梯队：可排期迭代
| # | 问题 |
|---|------|
| 18 | VerificationEngine 超大类拆分 |
| 19 | RuleGraphEditor / FullscreenRuleEditor 重复代码 |
| 20 | SettingsPage 超大组件拆分 |
| 21 | 防火墙缺默认拒绝策略 |
| 22 | 无 CI/CD 流水线 |
| 23 | 无自动备份策略 |
| 24 | 缺少架构图和运维手册 |
