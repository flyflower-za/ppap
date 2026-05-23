<template>
  <div class="login-page">
    <!-- 左侧装饰区域 -->
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

        <!-- 装饰性图形 -->
        <div class="decorative-shapes">
          <div class="shape shape-1"></div>
          <div class="shape shape-2"></div>
          <div class="shape shape-3"></div>
        </div>
      </div>
    </div>

    <!-- 右侧登录区域 -->
    <div class="login-right">
      <!-- 右上角Logo -->
      <div class="top-logo">
        <img src="/logo.png" alt="Logo" class="logo-img" onerror="this.style.display='none'">
      </div>

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
            />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              show-password
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
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  email: 'admin@example.com',
  password: '',
})

const rememberMe = ref(false)

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
}

/* ==================== 左侧装饰区域 ==================== */
.login-left {
  flex: 1;
  background: linear-gradient(135deg, #667eea 0%, #4285f4 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  min-width: 500px;
}

.left-content {
  text-align: center;
  color: white;
  z-index: 2;
  padding: 60px;
}

.brand-info {
  margin-bottom: 60px;
}

.brand-icon {
  width: 96px;
  height: 96px;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  border-radius: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.brand-info h1 {
  font-size: 42px;
  font-weight: 700;
  margin: 0 0 16px 0;
  letter-spacing: -0.5px;
}

.brand-desc {
  font-size: 18px;
  opacity: 0.95;
  margin: 0 0 32px 0;
  font-weight: 300;
}

.brand-feature {
  font-size: 16px;
  opacity: 0.85;
  font-weight: 400;
}

/* 装饰性图形 */
.decorative-shapes {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  pointer-events: none;
}

.shape {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(5px);
}

.shape-1 {
  width: 400px;
  height: 400px;
  top: -100px;
  left: -100px;
}

.shape-2 {
  width: 300px;
  height: 300px;
  bottom: -80px;
  right: -50px;
}

.shape-3 {
  width: 200px;
  height: 200px;
  top: 50%;
  left: 10%;
  background: rgba(255, 255, 255, 0.03);
}

/* ==================== 右侧登录区域 ==================== */
.login-right {
  flex: 0 0 560px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.08);
  padding-right: 48px;
}

.top-logo {
  padding: 32px 48px 0;
  display: flex;
  justify-content: flex-end;
}

.logo-img {
  height: 48px;
  width: auto;
  object-fit: contain;
}

.login-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 60px;
  max-width: 480px;
  margin: 0 auto;
  width: 100%;
}

.login-header {
  margin-bottom: 48px;
}

.login-header h2 {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 12px 0;
  letter-spacing: -0.5px;
}

.login-header p {
  font-size: 15px;
  color: #666;
  margin: 0;
}

.login-form {
  margin-bottom: 32px;
}

:deep(.el-form-item) {
  margin-bottom: 24px;
}

:deep(.el-form-item__label) {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  padding-bottom: 8px;
  line-height: 1.5;
}

:deep(.el-input__wrapper) {
  height: 52px;
  border-radius: 12px;
  padding: 14px 16px;
  border: 2px solid #e5e7eb;
  box-shadow: none !important;
  transition: all 0.2s;
}

:deep(.el-input__wrapper:hover) {
  border-color: #4285f4;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #4285f4 !important;
  box-shadow: 0 0 0 4px rgba(66, 133, 244, 0.1) !important;
}

:deep(.el-input__inner) {
  font-size: 15px;
  color: #1a1a1a;
  font-weight: 400;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

:deep(.el-checkbox__label) {
  font-size: 14px;
  color: #666;
}

.forgot-link {
  font-size: 14px;
  color: #4285f4;
  text-decoration: none;
  transition: color 0.2s;
}

.forgot-link:hover {
  color: #3367d6;
  text-decoration: underline;
}

.login-button {
  width: 100%;
  height: 52px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #4285f4 100%) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(66, 133, 244, 0.3);
  transition: all 0.3s;
}

.login-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(66, 133, 244, 0.4) !important;
}

.login-button:active {
  transform: translateY(0);
}

:deep(.el-button.is-loading) {
  background: linear-gradient(135deg, #667eea 0%, #4285f4 100%) !important;
}

.login-footer {
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}

.login-footer p {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.register-link {
  color: #4285f4;
  text-decoration: none;
  font-weight: 600;
  transition: color 0.2s;
}

.register-link:hover {
  color: #3367d6;
  text-decoration: underline;
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 1024px) {
  .login-left {
    min-width: 400px;
  }

  .login-right {
    flex: 0 0 460px;
  }

  .login-container {
    padding: 0 40px;
  }
}

@media (max-width: 768px) {
  .login-page {
    flex-direction: column;
  }

  .login-left {
    min-width: auto;
    padding: 40px 20px;
  }

  .left-content {
    padding: 20px;
  }

  .brand-info h1 {
    font-size: 32px;
  }

  .login-right {
    flex: 1;
    box-shadow: none;
  }

  .top-logo {
    padding: 24px;
  }

  .login-container {
    padding: 0 32px;
  }
}
</style>
