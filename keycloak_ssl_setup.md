# 🎯 Keycloak SSL 设置详细指南

## 📍 正确的设置位置

### 1️⃣ 进入 Realm 设置
1. 访问 Keycloak 管理控制台：`http://47.114.107.127:34321/`
2. 登录：`admin` / `admin`
3. 在左上角下拉菜单中选择 **`my-sso`** realm

### 2️⃣ 找到 SSL Required 设置
**导航路径：**
```
左上角 Realm 选择器 → my-sso
↓
Realm settings (Realm 设置)
↓
Login 标签页
↓
SSL required 下拉菜单
```

**具体步骤：**
1. 点击左侧菜单的 **`Realm settings`** (Realm 设置)
2. 点击顶部的 **`Login`** 标签页
3. 向下滚动找到 **`SSL required`** 下拉菜单
4. 将 `External requests` 改为 **`None`**
5. 点击页面底部的 **`Save`** 按钮

## 🆚 区别说明

### ❌ 您找到的设置（不正确）
- **HSTS** (HTTP Strict Transport Security)
- 位置：Realm settings → General 标签页
- 作用：浏览器HTTPS强制策略

### ✅ 需要修改的设置（正确）
- **SSL Required**
- 位置：Realm settings → Login 标签页
- 作用：Keycloak连接的SSL要求

## 🔍 截图说明位置

**在 Realm settings → Login 标签页中，您应该看到：**

```
Realm Settings - Login
├── User registration          [OFF]
├── Forgot password            [ON]
├── Remember me                [OFF]
├── Verify email               [OFF]
├── Login with email           [OFF]
├── Duplicate emails allowed   [OFF]
├── SSL required               [External requests] ← 改为 [None]
├── ...
```

## ⚠️ 常见问题

### Q: 找不到 Login 标签页？
**A:** 确保您选择了正确的 Realm (`my-sso`)，而不是主 Realm。

### Q: 只看到 General、Keys、Sessions 等标签页？
**A:** Keycloak 版本不同，请查找包含 "Login"、"Authentication"、"Security" 等关键词的标签页。

### Q: 找到 SSL required 但没有 None 选项？
**A:** 应该有这些选项：`All`、`External`、`None`，请选择 `None`。

## 🧪 验证步骤

修改完成后：

1. **保存设置**
2. **刷新 PPAP 登录页面**
3. **点击 SSO 登录按钮**
4. **应该跳转到 Keycloak 登录页面**

---

**如果仍然找不到，请告诉我您在 Keycloak 中看到的所有菜单选项和标签页，我会帮您定位正确的设置位置。**