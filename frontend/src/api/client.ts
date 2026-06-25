import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'


const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const client: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Pending request tracking for cancellation on route change
const pendingRequests = new Map<string, AbortController>()

function getRequestKey(config: InternalAxiosRequestConfig): string {
  return `${config.method}:${config.url}:${JSON.stringify(config.params || '')}`
}

// Request interceptor
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    if (!(config as any).skipCancel) {
      const key = getRequestKey(config)
      if (pendingRequests.has(key)) {
        pendingRequests.get(key)!.abort()
      }
      const controller = new AbortController()
      config.signal = controller.signal
      pendingRequests.set(key, controller)
    }

    return config
  },
  (error) => Promise.reject(error)
)

// Debounce duplicate error toasts — same message within 2s shows only once
let lastErrorMessage = ''
let lastErrorTime = 0

// Response interceptor
client.interceptors.response.use(
  (response) => {
    const key = getRequestKey(response.config)
    pendingRequests.delete(key)
    return response.data
  },
  (error) => {
    if (error.config) {
      const key = getRequestKey(error.config)
      pendingRequests.delete(key)
    }

    if (axios.isCancel(error)) {
      return new Promise(() => {})
    }

    const config = error.config as AxiosRequestConfig & { skipGlobalError?: boolean }

    if (!config?.skipGlobalError) {
      const message = error.response?.data?.detail || error.message || 'Request failed'
      const now = Date.now()
      if (message !== lastErrorMessage || now - lastErrorTime > 2000) {
        ElMessage.error(message)
        lastErrorMessage = message
        lastErrorTime = now
      }
    }

    if (error.response?.status === 401) {
      // Deferred imports to avoid circular dependency with router
      import('@/stores/auth').then(({ useAuthStore }) => {
        useAuthStore().logout()
      })
      import('@/router').then(({ default: router }) => {
        if (router.currentRoute.value.name !== 'Login') {
          router.push({ name: 'Login', query: { redirect: router.currentRoute.value.fullPath } })
        }
      })
    }

    return Promise.reject(error)
  }
)

export function cancelPendingRequests() {
  for (const [, controller] of pendingRequests) {
    controller.abort()
  }
  pendingRequests.clear()
}

export default client
