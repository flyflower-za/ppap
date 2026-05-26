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

          <!-- SSO Login Button -->
          <div v-if="ssoConfig.enabled" class="sso-section">
            <el-button
              type="success"
              :loading="ssoLoading"
              size="large"
              class="sso-button"
              @click="handleSSOLogin"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" class="sso-icon">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
              </svg>
              {{ ssoLoading ? 'SSO登录中...' : `${ssoConfig.provider === 'generic' ? 'SSO登录' : ssoConfig.provider.toUpperCase() + ' 登录'} (${ssoConfig.environment === 'test' ? '测试环境' : '正式环境'})` }}
            </el-button>
            <div class="divider-section">
              <div class="divider-line"></div>
              <span class="divider-text">或使用账号密码登录</span>
              <div class="divider-line"></div>
            </div>
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


          <div class="login-footer">
            <p>还没有账户？<a href="#" class="register-link">联系管理员开通</a></p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const ssoLoading = ref(false)
const rememberMe = ref(false)

// SSO Configuration
const ssoConfig = ref({
  enabled: false,
  environment: 'test',
  provider: 'generic'  // keycloak, auth0, okta, azure, google, etc.
})

const form = reactive({
  email: '',
  password: ''
})

const rules: FormRules = {
  email: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ]
}

// Check for SSO configuration and callback
onMounted(async () => {
  await checkSSOConfig()

  // Check if this is a callback from OIDC provider
  const code = route.query.code as string
  const state = route.query.state as string

  if (code) {
    await handleSSOCallback(code, state)
  }
})

async function checkSSOConfig() {
  try {
    // Check if SSO is enabled using public endpoint (no auth required)
    const response = await fetch('/api/v1/oidc/config/public')
    if (response.ok) {
      const config = await response.json()
      ssoConfig.value = {
        enabled: config.enabled || false,
        environment: config.environment || 'test',
        provider: config.provider_name || 'generic'
      }
    }
  } catch (error) {
    console.error('Failed to check SSO config:', error)
    // Silent fail - just use local login
  }
}

async function handleSSOLogin() {
  ssoLoading.value = true
  try {
    // Get authorization URL from backend
    const response = await fetch('/api/v1/oidc/auth-url')
    if (!response.ok) {
      throw new Error('获取SSO授权URL失败')
    }

    const data = await response.json()

    // Store state for CSRF protection
    sessionStorage.setItem('sso_state', data.state)

    // Redirect to OIDC provider login page
    window.location.href = data.auth_url

  } catch (error: any) {
    ElMessage.error(error.message || 'SSO登录失败')
    ssoLoading.value = false
  }
}

async function handleSSOCallback(code: string, state: string) {
  ssoLoading.value = true
  try {
    // Verify state to prevent CSRF attacks
    const storedState = sessionStorage.getItem('sso_state')
    if (state !== storedState) {
      throw new Error('安全验证失败，请重新登录')
    }

    // Exchange code for token with backend
    const response = await fetch('/api/v1/oidc/callback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        code: code,
        state: state
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'SSO认证失败')
    }

    const data = await response.json()

    // Store token and user info
    await authStore.setToken(data.access_token)
    await authStore.setUser(data.user)

    ElMessage.success('SSO登录成功')

    // Clear state
    sessionStorage.removeItem('sso_state')

    // Redirect to dashboard or originally requested page
    const redirect = route.query.redirect as string || '/'
    router.push(redirect)

  } catch (error: any) {
    ElMessage.error(error.message || 'SSO认证失败')
    router.push('/login')
  } finally {
    ssoLoading.value = false
  }
}

async function handleLogin() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await authStore.login({
        email: form.email,
        password: form.password
      })

      ElMessage.success('登录成功')

      // Redirect to dashboard or originally requested page
      const redirect = route.query.redirect as string || '/'
      router.push(redirect)

    } catch (error: any) {
      ElMessage.error(error.message || '登录失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-page {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.login-left {
  flex: 1;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.left-content {
  max-width: 500px;
}

.brand-info {
  color: white;
}

.brand-icon {
  margin-bottom: 24px;
}

.brand-info h1 {
  font-size: 48px;
  font-weight: 700;
  margin-bottom: 8px;
  color: white;
}

.brand-desc {
  font-size: 18px;
  opacity: 0.9;
  margin-bottom: 16px;
  color: white;
}

.brand-feature {
  font-size: 16px;
  opacity: 0.8;
  color: white;
}

.login-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: linear-gradient(160deg, #f8f9ff 0%, #eef0fb 100%);
}

.top-logo {
  position: absolute;
  top: 20px;
  right: 20px;
}

.logo-img {
  height: 40px;
  width: auto;
}

.login-card-wrapper {
  width: 100%;
  max-width: 450px;
}

.login-container {
  background: white;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(99, 102, 241, 0.12), 0 2px 8px rgba(0, 0, 0, 0.06);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h2 {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
}

.login-header p {
  color: #6b7280;
  font-size: 14px;
}

/* SSO Styles */
.sso-section {
  margin-bottom: 24px;
}

.sso-button {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.sso-icon {
  width: 20px;
  height: 20px;
}

.divider-section {
  display: flex;
  align-items: center;
  margin: 24px 0;
}

.divider-line {
  flex: 1;
  height: 1px;
  background-color: #e5e7eb;
}

.divider-text {
  padding: 0 16px;
  color: #6b7280;
  font-size: 14px;
}

/* Form Styles */
.login-form {
  margin-top: 24px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.forgot-link {
  color: #6366f1;
  text-decoration: none;
  font-size: 14px;
}

.forgot-link:hover {
  text-decoration: underline;
}

.login-button {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  border-radius: 8px;
  margin-top: 16px;
}

.login-footer {
  text-align: center;
  margin-top: 24px;
  color: #6b7280;
  font-size: 14px;
}

.register-link {
  color: #6366f1;
  text-decoration: none;
  font-weight: 500;
}

.register-link:hover {
  text-decoration: underline;
}

/* Responsive */
@media (max-width: 768px) {
  .login-left {
    display: none;
  }

  .login-right {
    flex: 1;
  }

  .login-container {
    padding: 24px;
  }
}
</style>