<template>
  <div>
    <div class="flex-between mb-4">
      <h2>任务中心</h2>
      <el-button :icon="Refresh" @click="handleRefresh">刷新</el-button>
    </div>

    <el-row :gutter="32">
      <!-- Upload Section -->
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <div class="flex-between">
              <span>上传文件</span>
              <el-checkbox v-model="batchMode">批量上传模式</el-checkbox>
            </div>
          </template>

          <el-upload
            drag
            :action="uploadUrl"
            :headers="uploadHeaders"
            accept=".pdf"
            :multiple="batchMode"
            :show-file-list="false"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              点击上传 PDF 文件<em>或拖拽到此处</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持格式：PDF，最大 50MB
              </div>
            </template>
          </el-upload>
        </el-card>
      </el-col>

      <!-- Task List Section -->
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <span>当前任务</span>
          </template>

          <el-tabs v-model="activeTab">
            <el-tab-pane label="进行中" name="processing">
              <TaskList :status="'processing'" />
            </el-tab-pane>
            <el-tab-pane label="已完成" name="completed">
              <TaskList :status="'completed'" />
            </el-tab-pane>
            <el-tab-pane label="失败" name="failed">
              <TaskList :status="'failed'" />
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, UploadFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const batchMode = ref(false)
const activeTab = ref('processing')

const uploadUrl = '/api/v1/files/upload'
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${authStore.token}`,
}))

function beforeUpload(file: File) {
  const isPDF = file.type === 'application/pdf'
  if (!isPDF) {
    ElMessage.error('只支持上传 PDF 文件')
    return false
  }

  const isLt50M = file.size / 1024 / 1024 < 50
  if (!isLt50M) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }

  return true
}

function handleUploadSuccess(response: unknown) {
  ElMessage.success('文件上传成功，开始校验...')
  // Refresh task list
}

function handleUploadError() {
  ElMessage.error('文件上传失败，请重试')
}

function handleRefresh() {
  ElMessage.success('任务列表已刷新')
}
</script>

<style scoped>
:deep(.el-upload-dragger) {
  background: #f8faff;
  border-color: #4285f4;
}

:deep(.el-icon--upload) {
  color: #4285f4;
  font-size: 64px;
  margin-bottom: 16px;
}
</style>
