<template>
  <div>
    <div class="flex-between mb-4">
      <h2>{{ $t('notification.center') }}</h2>
      <el-button v-if="hasUnread" :loading="markingAll" @click="handleMarkAllRead">{{ $t('notification.markAllRead') }}</el-button>
    </div>

    <el-card shadow="never" class="notifications-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="$t('notification.allTab')" name="all">
          <NotificationList :unread-only="false" :refresh-key="refreshKey" @unread-change="onUnreadChange" />
        </el-tab-pane>
        <el-tab-pane :label="$t('notification.unreadTab')" name="unread">
          <NotificationList :unread-only="true" :refresh-key="refreshKey" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import NotificationList from '@/components/NotificationList.vue'
import { useNotificationStore } from '@/stores/notification'
import client from '@/api/client'

const { t } = useI18n()

const notificationStore = useNotificationStore()
const activeTab = ref('all')
const hasUnread = ref(true)
const markingAll = ref(false)
const refreshKey = ref(0)

async function handleMarkAllRead() {
  markingAll.value = true
  try {
    await client.post('/notifications/mark-all-read')
    ElMessage.success(t('notification.markSuccess'))
    hasUnread.value = false
    notificationStore.markAllRead()
    refreshKey.value++
  } catch {
    ElMessage.error(t('notification.markFailed'))
  } finally {
    markingAll.value = false
  }
}

function onUnreadChange(count: number) {
  hasUnread.value = count > 0
  notificationStore.setUnreadCount(count)
}
</script>

<style scoped>
.notifications-card {
  border-radius: 12px;
}
</style>
