# Keycloak SSO 集成配置指南

## 🎯 概述

PPAP平台现在支持Keycloak OpenID Connect SSO单点登录，提供安全、便捷的企业级认证体验。

## 📋 当前测试配置

### Keycloak Realm 配置
- **Realm名称**: `my-sso`
- **状态**: 启用

### 客户端配置
- **Client ID**: `my-app`
- **Client Secret**: `my-secret-password`
- **重定向URI**:
  - `http://localhost:5173/auth/callback`
  - `http://localhost:3000/auth/callback`

### 测试用户
- **用户名**: `sso-user`
- **密码**: `sso-password-123`
- **邮箱**: `sso-user@example.com`

### 核心端点
- **发现端点**: `http://47.114.107.127:34321/realms/my-sso/.well-known/openid-configuration`
- **授权端点**: `http://47.114.107.127:34321/realms/my-sso/protocol/openid-connect/auth`
- **令牌端点**: `http://47.114.107.127:34321/realms/my-sso/protocol/openid-connect/token`
- **用户信息端点**: `http://47.114.107.127:34321/realms/my-sso/protocol/openid-connect/userinfo`

## 🚀 快速开始

### 1. 后端配置

#### 方式一：通过API配置（推荐）
```bash
# 启用Keycloak SSO
curl -X POST http://localhost:31234/api/v1/ldap-config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "sso_enabled": true,
    "sso_provider": "keycloak",
    "sso_idp_sso_url": "http://47.114.107.127:34321/realms/my-sso/.well-known/openid-configuration",
    "sso_entity_id": "my-app",
    "sso_sp_key": "my-secret-password",
    "sso_acs_url": "http://localhost:5173/auth/callback",
    "auto_create_users": true,
    "default_role": "USER",
    "ldap_server": "test"
  }'
```

#### 方式二：通过Web UI配置
1. 登录PPAP平台（管理员权限）
2. 进入：`系统设置` → `LDAP/SSO配置`
3. 启用SSO并填入Keycloak配置信息

### 2. 前端集成

前端已经自动支持SSO登录：
- ✅ 自动检测SSO配置状态
- ✅ 显示SSO登录按钮（绿色地球图标）
- ✅ 自动处理OAuth2回调
- ✅ 显示环境标识（测试/正式）

### 3. Keycloak客户端配置

确保Keycloak中的客户端配置正确：

```json
{
  "clientId": "my-app",
  "enabled": true,
  "clientAuthenticatorType": "client-secret",
  "secret": "my-secret-password",
  "redirectUris": [
    "http://localhost:5173/auth/callback",
    "http://localhost:3000/auth/callback"
  ],
  "webOrigins": [
    "http://localhost:5173",
    "http://localhost:3000"
  ],
  "standardFlowEnabled": true,
  "directAccessGrantsEnabled": false
}
```

## 🔧 切换到正式环境

### 更新生产配置

当准备好切换到正式环境时：

```bash
# 更新为正式环境配置
curl -X POST http://your-production-server/api/v1/ldap-config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "sso_enabled": true,
    "sso_provider": "keycloak",
    "sso_idp_sso_url": "https://your-production-keycloak.com/realms/production/.well-known/openid-configuration",
    "sso_entity_id": "ppap-production",
    "sso_sp_key": "your-production-client-secret",
    "sso_acs_url": "https://your-ppap-app.com/auth/callback",
    "auto_create_users": true,
    "default_role": "USER",
    "ldap_server": "production"
  }'
```

### 前端更新
更新前端重定向URI：
```javascript
// frontend/src/views/LoginPage.vue
const ssoConfig = ref({
  enabled: false,
  environment: 'production'  // 将显示"正式环境"
})
```

## 📊 用户角色映射

系统支持基于Keycloak角色的权限映射：

### 配置角色映射
```python
# 在后端配置中设置
admin_roles = ["admin", "ppap-admin", "administrator"]
manager_roles = ["manager", "ppap-manager", "supervisor"]
user_roles = ["user", "ppap-user", "employee"]
```

### Keycloak端设置
在Keycloak中为用户分配相应的角色：
- 管理员：`ppap-admin`
- 管理者：`ppap-manager`
- 普通用户：`ppap-user`

## 🔒 安全特性

### CSRF保护
- 每次SSO登录生成唯一的`state`参数
- 回调时验证state防止CSRF攻击
- 自动清理过期的state值

### Token安全
- 使用PKCE (Proof Key for Code Exchange)
- 短期access_token + 长期refresh_token
- 自动token刷新机制

### 会话管理
- 与本地登录统一的会话管理
- JWT token标准认证
- 支持单点登出(SLO)

## 🛠️ 故障排除

### 常见问题

#### 1. SSO按钮不显示
```bash
# 检查SSO配置状态
curl http://localhost:31234/api/v1/keycloak/config \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# 确保返回 {"enabled": true}
```

#### 2. 回调失败
- 检查Keycloak重定向URI配置
- 确认前端路由 `/auth/callback` 存在
- 查看浏览器控制台错误信息

#### 3. Token交换失败
```bash
# 测试Keycloak连接
curl -X POST http://localhost:31234/api/v1/keycloak/test-config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "enabled": true,
    "discovery_url": "http://47.114.107.127:34321/realms/my-sso/.well-known/openid-configuration",
    "client_id": "my-app",
    "client_secret": "my-secret-password",
    "redirect_uri": "http://localhost:5173/auth/callback"
  }'
```

#### 4. 用户信息获取失败
- 确认Keycloak用户有email属性
- 检查客户端权限配置
- 查看后端日志详细信息

### 调试模式

启用详细日志：
```bash
# 后端
export DEBUG=true
export LOG_LEVEL=DEBUG

# 前端浏览器控制台
localStorage.setItem('debug', 'true')
```

## 📈 监控和日志

### 审计日志
SSO登录事件会记录在审计日志中：
- **事件类型**: `SSO_LOGIN`
- **提供商**: `keycloak`
- **用户邮箱**: 记录用户邮箱
- **登录时间**: 自动记录

### 查看日志
```bash
# 查看最近的SSO登录记录
SELECT * FROM audit_logs
WHERE action = 'SSO_LOGIN'
ORDER BY created_at DESC
LIMIT 10;
```

## 🎨 用户体验

### 登录流程

1. **用户访问登录页**
   - 看到两个登录选项：SSO登录 + 账号密码登录
   - SSO按钮显示当前环境（测试/正式）

2. **点击SSO登录**
   - 重定向到Keycloak登录页面
   - 输入Keycloak用户名和密码

3. **认证成功**
   - 自动回调到PPAP平台
   - 创建或更新用户记录
   - 设置会话并跳转到主页

### 多环境支持
- **测试环境**: 显示"SSO登录 (测试环境)"
- **正式环境**: 显示"SSO登录 (正式环境)"
- 用户清楚知道当前登录环境

## 🚀 部署建议

### 测试环境
- 使用当前的测试Keycloak配置
- 充分测试用户创建、角色映射等功能
- 验证回调URL正确性

### 生产环境
- 使用HTTPS协议
- 配置生产环境的Keycloak realm
- 更新客户端密钥和重定向URI
- 设置合适的token过期时间

### 性能优化
- 启用Keycloak缓存
- 配置适当的session超时
- 使用CDN加速静态资源

## 📞 技术支持

遇到问题时的排查步骤：

1. **检查配置**: 使用`/keycloak/config`端点检查配置
2. **测试连接**: 使用`/keycloak/test-config`测试Keycloak连接
3. **查看日志**: 检查前后端错误日志
4. **验证用户**: 确认Keycloak用户配置正确
5. **网络检查**: 确认网络连接和防火墙设置

---

**最后更新**: 2026-05-26
**适用版本**: v1.1.0+
**状态**: 测试配置，待切换到生产环境