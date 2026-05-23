<template>
  <div>
    <h2 class="mb-4">系统设置</h2>

    <el-row :gutter="32">
      <el-col :span="6">
        <el-menu :default-active="activeMenu" @select="handleMenuSelect">
          <el-menu-item index="profile">
            <el-icon><User /></el-icon>
            <span>个人信息</span>
          </el-menu-item>
          <el-menu-item index="notification">
            <el-icon><Bell /></el-icon>
            <span>通知设置</span>
          </el-menu-item>
        </el-menu>
      </el-col>

      <el-col :span="18">
        <!-- Profile Section -->
        <el-card v-if="activeMenu === 'profile'" shadow="never">
          <template #header>
            <span>基本信息</span>
          </template>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="登录名">{{ authStore.user?.email }}</el-descriptions-item>
            <el-descriptions-item label="姓名">{{ authStore.user?.full_name }}</el-descriptions-item>
            <el-descriptions-item label="部门">{{ authStore.user?.department || '-' }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ authStore.user?.email }}</el-descriptions-item>
            <el-descriptions-item label="登录方式">
              <el-tag size="small">SSO</el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <el-alert
            type="info"
            :closable="false"
            class="mt-4"
          >
            个人信息由企业 LDAP/SSO 系统统一管理，如需修改请联系系统管理员。
          </el-alert>
        </el-card>

        <!-- Notification Section -->
        <el-card v-if="activeMenu === 'notification'" shadow="never">
          <template #header>
            <span>邮件通知</span>
          </template>

          <div class="notification-setting">
            <div class="setting-item">
              <div class="setting-info">
                <h4>启用邮件通知</h4>
                <p>当文件校验完成时发送邮件通知</p>
              </div>
              <el-switch v-model="emailEnabled" />
            </div>

            <el-divider />

            <div class="setting-item">
              <div class="setting-info">
                <h4>校验失败通知</h4>
                <p>当校验失败时立即发送邮件提醒</p>
              </div>
              <el-switch v-model="notifyOnFailure" />
            </div>

            <el-divider />

            <div class="setting-item">
              <div class="setting-info">
                <h4>每日汇总报告</h4>
                <p>每天发送当日校验任务汇总到邮箱</p>
              </div>
              <el-switch v-model="dailySummary" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { User, Bell } from '@element-plus/icons-vue'

const authStore = useAuthStore()
const activeMenu = ref('profile')

const emailEnabled = ref(true)
const notifyOnFailure = ref(true)
const dailySummary = ref(false)

function handleMenuSelect(index: string) {
  activeMenu.value = index
}
</script>

<style scoped>
.notification-setting {
  padding: 16px 0;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.setting-info h4 {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.setting-info p {
  font-size: 13px;
  color: #999;
}
</style>
