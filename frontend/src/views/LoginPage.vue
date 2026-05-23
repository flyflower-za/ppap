<template>
  <div class="login-page">
    <!-- 左侧品牌展示区域 -->
    <div class="login-left">
      <div class="left-content">
        <div class="brand-info">
          <div class="brand-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="white">
              <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M13,13H11V18A2,2 0 0,1 9,20H7A2,2 0 0,1 5,18V4H13V13Z"/>
            </svg>
          </div>
          <h1>文件校验平台</h1>
          <p class="brand-desc">PPAP File Verification Platform</p>
          <p class="brand-feature">智能化文件校验，提升质量管理效率</p>
        </div>
      </div>
    </div>

    <!-- 右侧登录操作区域 -->
    <div class="login-right">
      <!-- 右上角Logo -->
      <div class="top-logo">
        <img src="/logo.png" alt="Logo" class="logo-img" onerror="this.style.display='none'">
      </div>

      <div class="login-card-wrapper">
        <div class="login-container">
          <div class="login-header">
            <h2>欢迎回来</h2>
            <p>登录您的账户以继续</p>
          </div>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-position="top"
            class="login-form"
          >
            <el-form-item label="账号" prop="email">
              <el-input
                v-model="form.email"
                type="email"
                placeholder="请输入账号"
                size="large"
                clearable
                :prefix-icon="User"
              />
            </el-form-item>

            <el-form-item label="密码" prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
                size="large"
                show-password
                :prefix-icon="Lock"
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <div class="form-options">
              <el-checkbox v-model="rememberMe">记住我</el-checkbox>
              <a href="#" class="forgot-link">忘记密码？</a>
            </div>

            <el-button
              type="primary"
              :loading="loading"
              size="large"
              class="login-button"
              @click="handleLogin"
            >
              {{ loading ? '登录中...' : '登录' }}
            </el-button>
          </el-form>

          <!-- 快捷演示账号面板 (一键登录快捷通道) -->
          <div class="demo-card">
            <div class="demo-title">
              <el-icon><InfoFilled /></el-icon>
              <span>演示快捷通道</span>
            </div>
            <div class="demo-options-list">
              <button class="demo-btn" @click="fillDemo('admin@example.com')">
                <span class="role admin-badge">管理员</span>
                <span class="email">admin@example.com</span>
              </button>
              <button class="demo-btn" @click="fillDemo('manager@example.com')">
                <span class="role manager-badge">经理</span>
                <span class="email">manager@example.com</span>
              </button>
              <button class="demo-btn" @click="fillDemo('user@example.com')">
                <span class="role user-badge">普通用户</span>
                <span class="email">user@example.com</span>
              </button>
            </div>
          </div>

          <div class="login-footer">
            <p>还没有账户？<a href="#" class="register-link">联系管理员开通</a></p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { User, Lock, InfoFilled } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  email: 'admin@example.com',
  password: '',
})

const rememberMe = ref(true)

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' },
  ],
}

// 一键填入演示账号快捷方法
function fillDemo(email: string) {
  form.email = email
  form.password = 'admin123'
  rememberMe.value = true
  ElMessage.info({
    message: `已填入账号: ${email}，默认密码为 admin123`,
    duration: 3000
  })
}

async function handleLogin() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await authStore.login({
        email: form.email,
        password: form.password,
      })

      ElMessage.success('登录成功')

      const redirect = (route.query.redirect as string) || '/tasks'
      router.push(redirect)
    } catch (error: any) {
      ElMessage.error(error.message || '登录失败，请检查邮箱和密码')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  background-color: #f8fafc;
}

.login-left {
  flex: 1;
  background: linear-gradient(135deg, #667eea 0%, #4285f4 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  min-width: 550px;
  padding: 40px;
}

.left-content {
  text-align: center;
  color: white;
  z-index: 2;
  width: 100%;
  max-width: 500px;
  position: relative;
}

.brand-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: transform 0.3s ease;
}

.brand-info:hover {
  transform: translateY(-2px);
}

.brand-icon {
  width: 88px;
  height: 88px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 28px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
  transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.brand-info:hover .brand-icon {
  transform: scale(1.08) rotate(8deg);
  background: rgba(255, 255, 255, 0.22);
}

.brand-info h1 {
  font-size: 38px;
  font-weight: 800;
  margin: 0 0 12px 0;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, #ffffff 0%, #e2e8f0 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.brand-desc {
  font-size: 16px;
  opacity: 0.8;
  margin: 0 0 28px 0;
  font-weight: 300;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.brand-feature {
  font-size: 15px;
  opacity: 0.9;
  font-weight: 400;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 30px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

/* ==================== 右侧登录区域 (高阶悬浮卡片) ==================== */
.login-right {
  flex: 0 0 520px;
  background: #ffffff;
  margin: 32px 48px 32px 0; /* Keep distance from top, bottom, and right edge of the page! */
  border-radius: 28px;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.08), 0 1px 3px rgba(15, 23, 42, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.8);
  overflow-y: auto;
  animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.top-logo {
  padding: 32px 40px 0;
  display: flex;
  justify-content: flex-end;
}

.logo-img {
  height: 44px;
  width: auto;
  object-fit: contain;
}

.login-card-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 40px;
}

.login-container {
  width: 100%;
  max-width: 440px;
  background: transparent;
  padding: 0;
  box-shadow: none;
  border: none;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-header {
  margin-bottom: 36px;
  text-align: left;
}

.login-header h2 {
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 8px 0;
  letter-spacing: -0.02em;
}

.login-header p {
  font-size: 14px;
  color: #64748b;
  margin: 0;
}

.login-form {
  margin-bottom: 24px;
}

:deep(.el-form-item) {
  margin-bottom: 20px;
}

:deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  padding-bottom: 6px;
  line-height: 1.5;
}

/* ==================== Element Plus 输入框深度定制 ==================== */
:deep(.el-input__wrapper) {
  height: 48px;
  border-radius: 12px;
  padding: 10px 16px;
  border: 1.5px solid #e2e8f0;
  background-color: #ffffff;
  box-shadow: none !important;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-input__wrapper:hover) {
  border-color: #cbd5e1;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #4285f4 !important;
  box-shadow: 0 0 0 4px rgba(66, 133, 244, 0.12) !important;
}

:deep(.el-input__inner) {
  font-size: 14px;
  color: #0f172a;
  font-weight: 400;
}

:deep(.el-input__prefix) {
  color: #94a3b8;
  transition: color 0.2s;
  margin-right: 8px;
}

:deep(.el-input__wrapper.is-focus) .el-input__prefix {
  color: #4285f4;
}

/* Chrome 自动填充背景覆盖 */
:deep(input:-webkit-autofill) {
  -webkit-box-shadow: 0 0 0 1000px #ffffff inset !important;
  -webkit-text-fill-color: #0f172a !important;
  transition: background-color 5000s ease-in-out 0s;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

:deep(.el-checkbox) {
  height: auto;
}

:deep(.el-checkbox__label) {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

:deep(.el-checkbox__inner) {
  border-radius: 4px;
  border-color: #cbd5e1;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #4285f4;
  border-color: #4285f4;
}

.forgot-link {
  font-size: 13px;
  color: #4285f4;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.forgot-link:hover {
  color: #2563eb;
}

/* ==================== 登录按钮高阶视觉 ==================== */
.login-button {
  width: 100%;
  height: 48px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 12px;
  background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
  border: none !important;
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: white;
}

.login-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.45) !important;
  background: linear-gradient(135deg, #4338ca 0%, #2563eb 100%) !important;
}

.login-button:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2) !important;
}

:deep(.el-button.is-loading) {
  background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
  opacity: 0.8;
}

/* ==================== 快捷演示卡片 ==================== */
.demo-card {
  margin-top: 24px;
  padding: 18px;
  border-radius: 16px;
  border: 1px dashed #e2e8f0;
  background: #f8fafc;
  transition: all 0.3s ease;
}

.demo-card:hover {
  border-color: #4285f4;
  background: #f0f7ff;
}

.demo-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #64748b;
  font-weight: 600;
}

.demo-title :deep(.el-icon) {
  color: #4285f4;
  font-size: 15px;
}

.demo-options-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.demo-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  border: 1px solid transparent;
  background: #f1f5f9;
  padding: 8px 16px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.demo-btn:hover {
  background: #e2e8f0;
  border-color: #cbd5e1;
  transform: translateX(3px);
}

.demo-btn:active {
  transform: translateX(1px);
}

.demo-btn .role {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
  letter-spacing: 0.02em;
}

.admin-badge {
  background: #fee2e2;
  color: #ef4444;
}

.user-badge {
  background: #dbeafe;
  color: #2563eb;
}

.manager-badge {
  background: #fef3c7;
  color: #d97706;
}

.demo-btn .email {
  font-size: 12px;
  color: #475569;
  font-weight: 500;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

/* ==================== 页脚 ==================== */
.login-footer {
  text-align: center;
  padding-top: 20px;
  margin-top: 24px;
  border-top: 1px solid #f1f5f9;
}

.login-footer p {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.register-link {
  color: #4285f4;
  text-decoration: none;
  font-weight: 600;
  transition: color 0.2s;
}

.register-link:hover {
  color: #2563eb;
  text-decoration: underline;
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 1100px) {
  .login-left {
    min-width: 450px;
  }

  .login-right {
    flex: 0 0 500px;
  }
}

@media (max-width: 900px) {
  .login-left {
    display: none;
  }

  .login-right {
    flex: 1;
    background-color: #ffffff;
    margin: 24px;
    border-radius: 24px;
    box-shadow: 0 15px 35px rgba(15, 23, 42, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.8);
    animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
  }

  .login-card-wrapper {
    padding: 12px 24px 32px 24px;
  }

  .login-container {
    background: transparent;
    box-shadow: none;
    border: none;
    padding: 0;
  }

  .top-logo {
    justify-content: center;
    padding: 32px 0 0 0;
  }
}
</style>
