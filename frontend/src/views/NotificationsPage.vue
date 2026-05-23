<template>
  <div>
    <div class="flex-between mb-4">
      <h2>消息中心</h2>
      <el-button v-if="hasUnread" @click="handleMarkAllRead">全部已读</el-button>
    </div>

    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="全部" name="all">
          <NotificationList :unread-only="false" />
        </el-tab-pane>
        <el-tab-pane label="未读" name="unread">
          <NotificationList :unread-only="true" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import NotificationList from '@/components/NotificationList.vue'

const activeTab = ref('all')
const hasUnread = ref(true)

function handleMarkAllRead() {
  ElMessage.success('已全部标记为已读')
  hasUnread.value = false
}
</script>
