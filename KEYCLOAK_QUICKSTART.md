# Keycloak SSO 快速开始指南

## 🎯 5分钟快速配置

### 第一步：启用SSO配置

登录PPAP平台，进入`系统设置` → `LDAP/SSO配置`，或使用API：

```bash
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

### 第二步：重启前端

```bash
cd frontend
npm run dev
```

### 第三步：测试SSO登录

1. 访问 `http://localhost:5173/login`
2. 点击绿色的 **"SSO登录 (测试环境)"** 按钮
3. 输入Keycloak测试用户凭证：
   - 用户名: `sso-user`
   - 密码: `sso-password-123`
4. 自动完成SSO认证并登录

## 🚀 预期结果

### 登录页面
- ✅ 显示SSO登录按钮（绿色，带地球图标）
- ✅ 显示"测试环境"标识
- ✅ 保留原有的账号密码登录选项

### 认证流程
- ✅ 点击SSO按钮 → 跳转到Keycloak登录页
- ✅ Keycloak登录成功 → 自动回调PPAP平台
- ✅ 自动创建用户记录（如果首次登录）
- ✅ 设置合适的用户角色权限

### 用户体验
- ✅ 无缝单点登录体验
- ✅ 自动会话管理
- ✅ 支持记住登录状态

## 🔧 配置参数说明

### 核心参数
- `sso_enabled`: 是否启用SSO (true/false)
- `sso_provider`: 固定值 "keycloak"
- `sso_idp_sso_url`: Keycloak发现端点
- `sso_entity_id`: 客户端ID (my-app)
- `sso_sp_key`: 客户端密钥 (my-secret-password)
- `sso_acs_url`: 回调地址 (http://localhost:5173/auth/callback)
- `ldap_server`: 环境标识 (test/production)

### 高级参数
- `auto_create_users`: 自动创建用户 (推荐true)
- `default_role`: 默认用户角色 (USER/MANAGER/ADMIN)

## 🎯 切换到正式环境

### 更新配置
```bash
curl -X POST http://your-production-server/api/v1/ldap-config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "sso_enabled": true,
    "sso_provider": "keycloak",
    "sso_idp_sso_url": "https://your-keycloak.com/realms/production/.well-known/openid-configuration",
    "sso_entity_id": "ppap-production",
    "sso_sp_key": "your-production-secret",
    "sso_acs_url": "https://your-app.com/auth/callback",
    "auto_create_users": true,
    "default_role": "USER",
    "ldap_server": "production"
  }'
```

### 前端更新
- SSO按钮将显示"正式环境"
- 使用HTTPS协议
- 更新回调域名

## 🛠️ 测试工具

### 1. 检查配置状态
```bash
curl http://localhost:31234/api/v1/keycloak/config \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 2. 测试Keycloak连接
```bash
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

### 3. 获取授权URL
```bash
curl http://localhost:31234/api/v1/keycloak/auth-url
```

## 📱 用户登录流程

### 用户体验
1. **访问登录页** → 看到SSO登录按钮
2. **点击SSO登录** → 跳转到Keycloak
3. **输入凭证** → Keycloak认证
4. **自动回调** → 完成PPAP登录
5. **跳转主页** → 开始使用系统

### 技术流程
1. **前端** → 请求授权URL
2. **后端** → 生成state并返回Keycloak授权URL
3. **前端** → 重定向到Keycloak
4. **Keycloak** → 用户认证，返回code
5. **前端** → 发送code到后端
6. **后端** → 交换token，获取用户信息，创建/更新用户
7. **后端** → 返回JWT token
8. **前端** → 设置token，完成登录

## 🔒 安全特性

### CSRF保护
- 每次登录生成唯一state
- 回调时验证state值
- 防止跨站请求伪造攻击

### Token安全
- 使用授权码流程（PKCE）
- 短期access_token + 长期refresh_token
- 安全的token存储

### 会话管理
- 与本地登录统一会话管理
- JWT标准认证
- 支持单点登出

## 📊 故障排除

### SSO按钮不显示
```bash
# 检查配置
curl http://localhost:31234/api/v1/keycloak/config
# 确保返回 {"enabled": true}
```

### 回调失败
- 检查Keycloak重定向URI配置
- 确认前端路由存在
- 查看浏览器控制台错误

### 连接失败
```bash
# 测试Keycloak连接
curl -X POST http://localhost:31234/api/v1/keycloak/test-config
```

## 📞 获取帮助

详细配置指南请参考：
- 📖 [完整配置指南](./KEYCLOAK_SSO_SETUP.md)
- 🔧 [API文档](http://localhost:31234/docs)
- 📊 [系统状态](http://localhost:31234/api/v1/system/health)

---

**快速开始** | **测试配置** | **正式部署**
:---:|:---:|:---:
✅ 5分钟配置 | ✅ 测试环境可用 | 🚀 准备生产部署