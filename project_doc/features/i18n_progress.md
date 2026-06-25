# 前端 i18n 翻译迁移进度

> 更新日期：2026-06-25（第二轮更新）

## 总览

| 指标 | 数值 |
|---|---|
| Locale 文件同步 | ✅ zh-CN.ts / en-US.ts 947 键 100% 同步 |
| `$t()` 调用覆盖率 | **~85%** |
| 已完成文件 | **16 / ~19** |
| 未完成文件 | 3 个（Rules 子系统，可延后） |

---

## 已完成 ✅

以下文件已**全部**使用 `$t()` / `t()` 调用，无残留硬编码中文：

| 文件 | 状态 |
|---|---|
| `layouts/MainLayout.vue` | ✅ 完成 |
| `App.vue` | ✅ 完成 |
| `components/NotificationList.vue` | ✅ 完成 |
| `components/TaskList.vue` | ✅ 完成 |
| `views/LoginPage.vue` | ✅ 完成 |
| `views/AuditLogPage.vue` | ✅ 完成 |
| `views/FileDetailPage.vue` | ✅ 完成 |
| `views/ModulesPage.vue` | ✅ 完成 |
| `views/ModuleSandboxPage.vue` | ✅ 完成 |
| `views/TaskCenterPage.vue` | ✅ 完成 |
| `views/HistoryPage.vue` | ✅ 完成 |
| `views/DashboardPage.vue` | ✅ 完成 |
| `views/ApprovalsPage.vue` | ✅ 完成 |
| `views/NotificationsPage.vue` | ✅ 完成 |
| `views/SettingsPage.vue` | ✅ 完成（模板 + script 区全部迁移） |
| `api/client.ts` | ✅ fallback 已替换为英文 |
| `utils/formatters.ts` | ✅ fallback 已替换为英文 |

---

## 未开始 ❌（可延后，不影响上线）

### Rules 子系统 — 需新建 `rules.*` locale 键空间

| 文件 | 硬编码中文行数 |
|---|---|
| `views/RulesPage.vue` | ~161 |
| `views/FullscreenRuleEditor.vue` | ~107 |
| `components/RuleGraphEditor.vue` | ~144 |
| **合计** | **~412** |

---

## 基础设施

| 组件 | 状态 |
|---|---|
| vue-i18n v11.4.6 | ✅ 已安装 |
| `src/locales/zh-CN.ts` | ✅ 947 keys |
| `src/locales/en-US.ts` | ✅ 947 keys |
| `src/locales/index.ts` | ✅ i18n 实例 + localStorage 持久化 |
| `main.ts` 注册 i18n 插件 | ✅ |
| Element Plus 动态 locale | ✅ App.vue 中绑定 |
| 语言切换 UI | ✅ MainLayout 导航栏 |

---

## 影响部署？

**翻译未完成不影响部署。** 硬编码的中文在中文环境下正常显示，只是切换到英文时 Rules 子系统的文本不会翻译。可以随时部署。
