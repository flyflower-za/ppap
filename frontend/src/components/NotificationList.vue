<template>
  <div class="notification-list-container">
    <div v-loading="loading" class="list-wrapper">
      <div v-if="notifications.length === 0" class="empty-state">
        <el-empty :description="unreadOnly ? '暂无未读消息' : '暂无系统消息'" :image-size="80"></el-empty>
      </div>

      <div v-else class="notifications-list">
        <div 
          v-for="item in notifications" 
          :key="item.id" 
          class="notification-item"
          :class="{ 'unread': !item.is_read }"
          @click="markAsRead(item)"
        >
          <div class="status-marker" v-if="!item.is_read"></div>
          
          <div class="icon-section">
            <el-icon :class="item.type"><component :is="getIcon(item.type)" /></el-icon>
          </div>

          <div class="content-section">
            <h4 class="title">{{ item.title }}</h4>
            <p class="message" v-if="item.message">{{ item.message }}</p>
            <span class="timestamp">{{ formatTime(item.created_at) }}</span>
          </div>

          <div class="action-section" v-if="!item.is_read">
            <el-button type="primary" link size="small" @click.stop="markAsRead(item)">标记已读</el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import client from '@/api/client'
import type { Notification } from '@/types'
import { SuccessFilled, CircleCloseFilled, WarningFilled, InfoFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  unreadOnly: boolean
  refreshKey?: number
}>()

const emit = defineEmits<{
  (e: 'unread-change', count: number): void
}>()

const notifications = ref<Notification[]>([])
const loading = ref(false)

function getIcon(type: string) {
  if (type === 'success') return SuccessFilled
  if (type === 'error') return CircleCloseFilled
  if (type === 'warning') return WarningFilled
  return InfoFilled
}

async function fetchNotifications() {
  loading.value = true
  try {
    const res: any = await client.get('/notifications')
    const items = res.items || []
    if (props.unreadOnly) {
      notifications.value = items.filter((n: Notification) => !n.is_read)
    } else {
      notifications.value = items
    }
    if (!props.unreadOnly) {
      emit('unread-change', res.unread_count ?? 0)
    }
  } catch (error) {
    console.error('获取通知列表失败:', error)
  } finally {
    loading.value = false
  }
}

async function markAsRead(item: Notification) {
  if (item.is_read) return
  try {
    await client.post(`/notifications/mark-read`, { notification_ids: [item.id] })
    item.is_read = true
    if (props.unreadOnly) {
      notifications.value = notifications.value.filter(n => n.id !== item.id)
    }
  } catch (error) {
    console.error('标记已读失败:', error)
  }
}

import { formatTime } from '@/utils/formatters'

watch(() => props.unreadOnly, fetchNotifications)
watch(() => props.refreshKey, fetchNotifications)

onMounted(fetchNotifications)
</script>

<style scoped>
.notification-list-container {
  min-height: 200px;
}

.list-wrapper {
  min-height: 150px;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px 0;
}

.notifications-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  padding: 16px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #f1f5f9;
  cursor: pointer;
  position: relative;
  transition: all 0.2s ease;
  gap: 14px;
}

.notification-item:hover {
  border-color: #e2e8f0;
  background: #f8fafc;
  transform: translateY(-1px);
}

.notification-item.unread {
  background: #f8faff;
  border-color: #dbeafe;
}

.notification-item.unread:hover {
  background: #f0f5ff;
}

.status-marker {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 8px;
  height: 8px;
  background: #3b82f6;
  border-radius: 50%;
}

.icon-section {
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}

.icon-section :deep(.el-icon) {
  width: 24px;
  height: 24px;
}

.icon-section :deep(.el-icon.success) {
  color: #10b981;
}

.icon-section :deep(.el-icon.error) {
  color: #ef4444;
}

.icon-section :deep(.el-icon.warning) {
  color: #f59e0b;
}

.icon-section :deep(.el-icon.info) {
  color: #3b82f6;
}

.content-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.message {
  font-size: 13px;
  color: #64748b;
  margin: 0;
  line-height: 1.5;
}

.timestamp {
  font-size: 11px;
  color: #94a3b8;
}

.action-section {
  display: flex;
  align-items: center;
  align-self: center;
  padding-right: 12px;
}
</style>
