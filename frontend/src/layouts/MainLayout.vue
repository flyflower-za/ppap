<template>
  <div class="page-container">
    <nav class="navbar">
      <div class="navbar-left">
        <div class="navbar-logo" @click="router.push('/tasks')">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
            <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M14,13V11H10V13H14Z"/>
          </svg>
          {{ $t('nav.platformName') }}
        </div>
        <div class="navbar-menu">
          <router-link to="/tasks">{{ $t('nav.taskCenter') }}</router-link>
          <router-link to="/history">{{ $t('nav.history') }}</router-link>
          <router-link v-if="authStore.user?.is_admin" to="/rules">{{ $t('nav.rules') }}</router-link>
          <router-link v-if="authStore.user?.is_admin" to="/approvals">{{ $t('nav.approvals') }}</router-link>
          <router-link v-if="authStore.user?.is_admin" to="/sandbox">{{ $t('nav.sandbox') }}</router-link>
          <router-link v-if="authStore.user?.is_admin" to="/audit">{{ $t('nav.audit') }}</router-link>
          <router-link to="/settings">{{ $t('nav.settings') }}</router-link>
        </div>
      </div>
      <div class="navbar-right">
        <el-badge :value="unreadCount" :hidden="unreadCount === 0">
          <el-icon :size="20" style="cursor: pointer;" @click="router.push('/notifications')">
            <Bell />
          </el-icon>
        </el-badge>
        <el-dropdown trigger="click" @command="handleLocaleChange">
          <span class="locale-switcher">
            {{ currentLocaleLabel }}
            <el-icon :size="12"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="loc in availableLocales"
                :key="loc.value"
                :command="loc.value"
                :disabled="loc.value === currentLocale"
              >
                {{ loc.label }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-divider direction="vertical" style="border-color: rgba(255,255,255,0.3); height: 20px;" />
        <span>{{ authStore.user?.full_name || authStore.user?.email }}</span>
        <el-button type="info" plain size="small" @click="handleLogout">{{ $t('auth.logout') }}</el-button>
      </div>
    </nav>

    <div class="main-content">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notification'
import { availableLocales, setLocale, getLocale } from '@/locales'
import { Bell, ArrowDown } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const notificationStore = useNotificationStore()

const unreadCount = computed(() => notificationStore.unreadCount)
const currentLocale = computed(() => getLocale())
const currentLocaleLabel = computed(() => {
  return availableLocales.find(l => l.value === currentLocale.value)?.label || '中文'
})

function handleLocaleChange(locale: string) {
  setLocale(locale)
}

onMounted(() => notificationStore.startPolling())
onUnmounted(() => notificationStore.stopPolling())

async function handleLogout() {
  try {
    await ElMessageBox.confirm(t('auth.logoutConfirm'), t('auth.logoutConfirmTitle'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    })
    authStore.logout()
    router.push('/login')
  } catch {
    // User cancelled
  }
}
</script>

<style scoped>
.locale-switcher {
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.3s;
}
.locale-switcher:hover {
  color: white;
  background: rgba(255, 255, 255, 0.15);
}
</style>
