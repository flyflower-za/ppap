import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { cancelPendingRequests } from '@/api/client'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginPage.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/auth/callback',
    name: 'AuthCallback',
    component: () => import('@/views/LoginPage.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: { name: 'TaskCenter' },
      },
      {
        path: 'tasks',
        name: 'TaskCenter',
        component: () => import('@/views/TaskCenterPage.vue'),
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/HistoryPage.vue'),
      },
      {
        path: 'files/:id',
        name: 'FileDetail',
        component: () => import('@/views/FileDetailPage.vue'),
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/views/NotificationsPage.vue'),
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/SettingsPage.vue'),
      },
      {
        path: 'rules',
        name: 'Rules',
        component: () => import('@/views/RulesPage.vue'),
        meta: { requiresAdmin: true },
      },
      {
        path: 'modules',
        name: 'Modules',
        component: () => import('@/views/ModulesPage.vue'),
        meta: { requiresAdmin: true },
      },
      {
        path: 'sandbox',
        name: 'Sandbox',
        component: () => import('@/views/ModuleSandboxPage.vue'),
        meta: { requiresAdmin: true },
      },
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('@/views/AuditLogPage.vue'),
        meta: { requiresAdmin: true },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard
router.beforeEach(async (to, _from, next) => {
  cancelPendingRequests()
  const authStore = useAuthStore()

  // Auto-fetch user details on page refresh / initialization if authenticated
  if (authStore.isAuthenticated && !authStore.user) {
    try {
      await authStore.fetchMe()
    } catch (error) {
      console.error('Failed to fetch user profile, logging out:', error)
      authStore.logout()
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && authStore.isAuthenticated) {
    next({ name: 'TaskCenter' })
  } else if (to.meta.requiresAdmin && !authStore.user?.is_admin) {
    // Non-admin user trying to access admin-only route
    next({ name: 'TaskCenter' })
  } else {
    next()
  }
})

export default router

