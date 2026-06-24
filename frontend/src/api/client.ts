import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const client: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const config = error.config as AxiosRequestConfig & { skipGlobalError?: boolean }

    if (!config?.skipGlobalError) {
      const message = error.response?.data?.detail || error.message || '请求失败'
      ElMessage.error(message)
    }

    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      if (router.currentRoute.value.name !== 'Login') {
        router.push({ name: 'Login', query: { redirect: router.currentRoute.value.fullPath } })
      }
    }

    return Promise.reject(error)
  }
)

export default client
