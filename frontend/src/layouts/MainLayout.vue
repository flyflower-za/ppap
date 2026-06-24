<template>
  <div class="page-container">
    <nav class="navbar">
      <div class="navbar-left">
        <div class="navbar-logo" @click="router.push('/tasks')">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
            <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M14,13V11H10V13H14Z"/>
          </svg>
          文件校验平台
        </div>
        <div class="navbar-menu">
          <router-link to="/tasks">任务中心</router-link>
          <router-link to="/history">历史记录</router-link>
          <!-- <router-link to="/dashboard">业务大屏</router-link> -->
          <router-link to="/rules">规则配置</router-link>
          <router-link to="/approvals">审批中心</router-link>
          <router-link to="/sandbox">模块沙盒</router-link>
          <router-link to="/audit">审计日志</router-link>
          <router-link to="/settings">系统设置</router-link>
        </div>
      </div>
      <div class="navbar-right">
        <el-badge :value="unreadCount" :hidden="unreadCount === 0">
          <el-icon :size="20" style="cursor: pointer;" @click="router.push('/notifications')">
            <Bell />
          </el-icon>
        </el-badge>
        <el-divider direction="vertical" style="border-color: rgba(255,255,255,0.3); height: 20px;" />
        <span>{{ authStore.user?.full_name || authStore.user?.email }}</span>
        <el-button type="info" plain size="small" @click="handleLogout">退出</el-button>
      </div>
    </nav>

    <div class="main-content">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Bell } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import client from '@/api/client'

const router = useRouter()
const authStore = useAuthStore()

const unreadCount = ref(0)
let pollTimer: ReturnType<typeof setTimeout> | null = null

async function fetchUnreadCount() {
  try {
    const res: any = await client.get('/notifications?limit=1')
    unreadCount.value = res.unread_count ?? 0
  } catch {
    // silent — 非关键请求
  }
  pollTimer = setTimeout(fetchUnreadCount, 60_000)
}

onMounted(fetchUnreadCount)
onUnmounted(() => { if (pollTimer) clearTimeout(pollTimer) })

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '确认退出', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    })
    authStore.logout()
    router.push('/login')
  } catch {
    // User cancelled
  }
}
</script>
