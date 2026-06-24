<template>
  <div class="task-center-container">
    <!-- Header -->
    <div class="flex-between mb-4 header-row">
      <h2 class="page-title">任务中心</h2>
      <el-button 
        :icon="Refresh" 
        @click="handleRefresh" 
        class="refresh-btn glass-btn"
      >
        刷新列表
      </el-button>
    </div>

    <el-row :gutter="24" class="layout-row">
      <!-- Upload Panel -->
      <el-col :xs="24" :md="10" class="col-panel">
        <div class="glass-card upload-card flex-column">
          <div class="section-header flex-between mb-3">
            <span class="section-title">上传文件校验</span>
            <el-checkbox v-model="batchMode" class="batch-checkbox">批量确认模式</el-checkbox>
          </div>

          <!-- Drag and Drop Upload Area -->
          <el-upload
            drag
            action=""
            :auto-upload="false"
            accept=".pdf"
            :multiple="batchMode"
            :show-file-list="false"
            :on-change="handleFileChange"
            class="premium-uploader"
            :disabled="uploading"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              点击上传 PDF 文件 <em>或拖拽到此处</em>
            </div>
            <template #tip>
              <div class="el-upload__tip text-center mt-2">
                支持格式：PDF，单个文件最大 50MB
              </div>
            </template>
          </el-upload>

          <!-- Selected Files Pending Confirmation Queue -->
          <div v-if="fileList.length > 0" class="pending-queue-container mt-4">
            <div class="queue-header flex-between mb-2">
              <span class="queue-title">待上传校验队列 ({{ fileList.length }} 个文件)</span>
              <el-button 
                type="danger" 
                link 
                size="small" 
                @click="clearQueue" 
                :disabled="uploading"
                class="clear-queue-btn"
              >
                清空队列
              </el-button>
            </div>

            <!-- Queue Scroll Area -->
            <div class="queue-list-scroll">
              <TransitionGroup name="list" tag="div" class="queue-list">
                <div 
                  v-for="(fileItem, index) in fileList" 
                  :key="fileItem.uid" 
                  class="queue-item flex-between"
                  :class="fileItem.status"
                >
                  <div class="item-left flex-align-center">
                    <el-icon class="pdf-icon" :size="20"><Document /></el-icon>
                    <div class="item-name-info">
                      <div class="file-name" :title="fileItem.name">{{ fileItem.name }}</div>
                      <div class="file-size">{{ formatFileSize(fileItem.size) }}</div>
                    </div>
                  </div>

                  <div class="item-right flex-align-center">
                    <!-- Status Icons / Text -->
                    <span v-if="fileItem.status === 'pending'" class="status-indicator pending">
                      <span class="status-dot"></span> 等待确认
                    </span>
                    <span v-else-if="fileItem.status === 'uploading'" class="status-indicator uploading">
                      <el-icon class="is-loading"><Loading /></el-icon> 正在上传...
                    </span>
                    <span v-else-if="fileItem.status === 'success'" class="status-indicator success">
                      <el-icon><Check /></el-icon> 成功
                    </span>
                    <span v-else-if="fileItem.status === 'error'" class="status-indicator error">
                      <el-icon><Close /></el-icon> 失败
                    </span>

                    <!-- Remove Item button -->
                    <el-button 
                      v-if="fileItem.status === 'pending'"
                      type="danger" 
                      link 
                      :icon="Delete" 
                      class="remove-item-btn ml-3"
                      @click="removeQueueItem(index)"
                    />
                  </div>
                </div>
              </TransitionGroup>
            </div>

            <!-- Confirm upload button -->
            <div class="queue-actions mt-3">
              <el-button 
                type="primary" 
                class="confirm-upload-btn w-100" 
                :loading="uploading"
                @click="handleConfirmUpload"
              >
                {{ uploading ? '正在批量上传文件...' : `确认批量上传并校验 (${fileList.length}个文件)` }}
              </el-button>
            </div>
          </div>
        </div>
      </el-col>

      <!-- Task Lists Tab Panel -->
      <el-col :xs="24" :md="14" class="col-panel">
        <div class="glass-card tasks-card flex-column">
          <div class="section-header mb-2 flex-between">
            <span class="section-title">校验任务看板</span>
            <span class="section-hint">仅展示最近 15 条任务记录，更多请前往历史记录查看</span>
          </div>

          <div class="tabs-container">
            <el-tabs v-model="activeTab" class="custom-tabs">
              <el-tab-pane label="全部" name="all">
                <TaskList ref="allTaskListRef" :status="'all'" :viewMode="viewMode" />
              </el-tab-pane>
              <el-tab-pane label="进行中" name="processing">
                <TaskList ref="processingTaskListRef" :status="'processing'" :viewMode="viewMode" @task-finished="handleTaskFinished" />
              </el-tab-pane>
              <el-tab-pane label="已完成" name="completed">
                <TaskList ref="completedTaskListRef" :status="'completed'" :viewMode="viewMode" />
              </el-tab-pane>
              <el-tab-pane label="诊断异常" name="failed">
                <TaskList ref="failedTaskListRef" :status="'failed'" :viewMode="viewMode" />
              </el-tab-pane>
            </el-tabs>

            <!-- View Toggle -->
            <div class="view-toggle-group">
              <button class="view-btn" :class="{ active: viewMode === 'grid' }" @click="viewMode = 'grid'" title="卡片视图">
                <el-icon><Grid /></el-icon>
              </button>
              <button class="view-btn" :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'" title="列表视图">
                <el-icon><List /></el-icon>
              </button>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, UploadFilled, Document, Loading, Check, Close, Delete, Grid, List } from '@element-plus/icons-vue'
import { filesApi } from '@/api/files'
import TaskList from '@/components/TaskList.vue'

const batchMode = ref(true) // Default to batch confirmation mode
const activeTab = ref('all')
const viewMode = ref<'grid' | 'list'>('grid')
const uploading = ref(false)
const fileList = ref<any[]>([])
const concurrencyLimit = ref(3) // Max concurrent uploads

// TaskList references for reactive updates
const allTaskListRef = ref<InstanceType<typeof TaskList> | null>(null)
const processingTaskListRef = ref<InstanceType<typeof TaskList> | null>(null)
const completedTaskListRef = ref<InstanceType<typeof TaskList> | null>(null)
const failedTaskListRef = ref<InstanceType<typeof TaskList> | null>(null)

import { formatFileSize } from '@/utils/formatters'

// Handle file addition in drag or selector
function handleFileChange(uploadFile: any, uploadFiles: any[]) {
  const rawFile = uploadFile.raw
  if (!rawFile) return

  // Validate type
  const isPDF = rawFile.type === 'application/pdf' || rawFile.name.toLowerCase().endsWith('.pdf')
  if (!isPDF) {
    ElMessage.error(`【${rawFile.name}】不是 PDF 文件，已从队列移除`)
    const idx = uploadFiles.indexOf(uploadFile)
    if (idx !== -1) uploadFiles.splice(idx, 1)
    return
  }

  // Validate size
  const isLt50M = rawFile.size / 1024 / 1024 < 50
  if (!isLt50M) {
    ElMessage.error(`【${rawFile.name}】大小超过 50MB，已从队列移除`)
    const idx = uploadFiles.indexOf(uploadFile)
    if (idx !== -1) uploadFiles.splice(idx, 1)
    return
  }

  // If NOT in batch mode, we automatically clear existing files to only queue ONE file
  if (!batchMode.value) {
    fileList.value = [{
      uid: uploadFile.uid,
      name: uploadFile.name,
      size: uploadFile.size,
      raw: rawFile,
      status: 'pending'
    }]
  } else {
    // Check if file is already added by UID or name+size
    const exists = fileList.value.some(f => f.name === uploadFile.name && f.size === uploadFile.size)
    if (exists) {
      ElMessage.warning(`文件【${uploadFile.name}】已在待上传队列中`)
      const idx = uploadFiles.indexOf(uploadFile)
      if (idx !== -1) uploadFiles.splice(idx, 1)
      return
    }

    fileList.value.push({
      uid: uploadFile.uid,
      name: uploadFile.name,
      size: uploadFile.size,
      raw: rawFile,
      status: 'pending'
    })
  }
}

// Remove single queue item
function removeQueueItem(index: number) {
  fileList.value.splice(index, 1)
}

// Clear queue
function clearQueue() {
  fileList.value = []
}

// Batch Confirm Upload Handler with concurrency control
async function handleConfirmUpload() {
  if (fileList.value.length === 0) return

  uploading.value = true
  let successCount = 0
  let failCount = 0

  // Concurrency-controlled upload: process files with limited parallelism
  const queue = fileList.value.filter(f => f.status !== 'success')
  const maxConcurrent = concurrencyLimit.value

  async function worker() {
    while (queue.length > 0) {
      const fileItem = queue.shift()
      if (!fileItem) break
      if (fileItem.status === 'success') {
        successCount++
        continue
      }

      fileItem.status = 'uploading'
      try {
        await filesApi.upload(fileItem.raw)
        fileItem.status = 'success'
        successCount++
      } catch (err) {
        fileItem.status = 'error'
        failCount++
        console.error(`Failed to upload ${fileItem.name}:`, err)
      }
    }
  }

  // Start N concurrent workers
  const workers = Array.from({ length: Math.min(maxConcurrent, queue.length) }, () => worker())
  await Promise.all(workers)

  if (failCount === 0) {
    ElMessage.success(`批量上传成功！已成功载入 ${successCount} 个文件进行智能校验。`)
  } else {
    ElMessage.warning(`批量上传完成。成功 ${successCount} 个，失败 ${failCount} 个。`)
  }

  // Refresh dashboard tasks list
  activeTab.value = 'all'
  if (allTaskListRef.value) {
    allTaskListRef.value.refresh()
  }
  if (processingTaskListRef.value) {
    processingTaskListRef.value.refresh()
  }

  // After 1.5 seconds, clear the successful items from queue
  setTimeout(() => {
    fileList.value = fileList.value.filter(f => f.status === 'error')
  }, 1500)

  uploading.value = false
}

function handleTaskFinished() {
  if (allTaskListRef.value) {
    allTaskListRef.value.refresh(true)
  }
  if (completedTaskListRef.value) {
    completedTaskListRef.value.refresh(true)
  }
  if (failedTaskListRef.value) {
    failedTaskListRef.value.refresh(true)
  }
}

function handleRefresh() {
  if (activeTab.value === 'all' && allTaskListRef.value) {
    allTaskListRef.value.refresh()
  } else if (activeTab.value === 'processing' && processingTaskListRef.value) {
    processingTaskListRef.value.refresh()
  } else if (activeTab.value === 'completed' && completedTaskListRef.value) {
    completedTaskListRef.value.refresh()
  } else if (activeTab.value === 'failed' && failedTaskListRef.value) {
    failedTaskListRef.value.refresh()
  }
  ElMessage.success('任务看板已刷新')
}
</script>

<style scoped>
.task-center-container {
  min-height: calc(100vh - 120px);
  padding: 8px 4px;
}

/* Typography */
.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1f36;
  margin: 0;
}

/* Glassmorphism Card Panels */
.glass-card {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
  border-radius: 16px;
  padding: 24px;
  min-height: 520px;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.glass-card:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
}

.flex-column {
  display: flex;
  flex-direction: column;
}

.layout-row {
  align-items: stretch;
}

.col-panel {
  display: flex;
  flex-direction: column;
  margin-bottom: 24px;
}

.col-panel > .glass-card {
  flex: 1;
  height: 100%;
}

/* Glass Buttons */
.glass-btn {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  color: #555;
  font-weight: 600;
  transition: all 0.25s ease;
}

.glass-btn:hover {
  background: #fff;
  border-color: #4285f4;
  color: #4285f4;
  transform: translateY(-1px);
}

/* Section Header styling */
.section-header {
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  padding-bottom: 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #1a1f36;
  position: relative;
  padding-left: 12px;
}

.section-title::before {
  /* Using a non-empty content value to avoid AV false positive (BehavesLike.PS.Downloader) */
  content: '\00a0';
  position: absolute;
  left: 0;
  top: 3px;
  bottom: 3px;
  width: 4px;
  border-radius: 2px;
  background-color: #4285f4;
}

.section-hint {
  font-size: 12px;
  color: #8792a2;
  font-weight: 500;
  display: flex;
  align-items: center;
}

/* Batch checkbox */
.batch-checkbox {
  font-weight: 600;
  color: #4f5b66;
}

/* Premium Uploader Box */
.premium-uploader {
  width: 100%;
}

:deep(.el-upload) {
  width: 100%;
}

:deep(.el-upload-dragger) {
  width: 100%;
  height: 180px;
  background: rgba(66, 133, 244, 0.02);
  border: 2px dashed rgba(66, 133, 244, 0.25);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.el-upload-dragger:hover) {
  background: rgba(66, 133, 244, 0.05);
  border-color: #4285f4;
  transform: scale(1.005);
}

:deep(.el-icon--upload) {
  color: #4285f4;
  font-size: 56px;
  margin-bottom: 10px;
  opacity: 0.85;
}

.el-upload__text em {
  color: #4285f4;
  font-style: normal;
  font-weight: 600;
}

.el-upload__tip {
  font-size: 12px;
  color: #8792a2;
}

/* File confirmation queue list */
.pending-queue-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(0, 0, 0, 0.015);
  border: 1px solid rgba(0, 0, 0, 0.03);
  border-radius: 12px;
  padding: 16px;
}

.queue-title {
  font-size: 13px;
  font-weight: 700;
  color: #4f5b66;
}

.clear-queue-btn {
  font-size: 12px;
  font-weight: 600;
}

.queue-list-scroll {
  max-height: 160px;
  overflow-y: auto;
  flex: 1;
  padding-right: 4px;
}

/* Custom Scrollbar */
.queue-list-scroll::-webkit-scrollbar {
  width: 4px;
}
.queue-list-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.queue-list-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 2px;
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.queue-item {
  padding: 10px 12px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 10px;
  transition: all 0.25s ease;
}

.queue-item.uploading {
  border-color: rgba(33, 150, 243, 0.3);
  background: rgba(33, 150, 243, 0.02);
}
.queue-item.success {
  border-color: rgba(76, 175, 80, 0.3);
  background: rgba(76, 175, 80, 0.02);
}
.queue-item.error {
  border-color: rgba(244, 67, 54, 0.3);
  background: rgba(244, 67, 54, 0.02);
}

.flex-align-center {
  display: flex;
  align-items: center;
}

.pdf-icon {
  color: #4285f4;
  margin-right: 12px;
}

.item-left {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  margin-right: 12px;
}

.item-name-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 13px;
  font-weight: 600;
  color: #3c4257;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 11px;
  color: #8792a2;
  font-weight: 500;
}

.status-indicator {
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.status-indicator.pending {
  color: #8792a2;
}

.status-indicator.pending .status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #8792a2;
}

.status-indicator.uploading {
  color: #2196f3;
}

.status-indicator.success {
  color: #4caf50;
}

.status-indicator.error {
  color: #f44336;
}

.remove-item-btn {
  padding: 0;
  height: auto;
  font-size: 14px;
  color: #8792a2;
}
.remove-item-btn:hover {
  color: #f44336 !important;
}

/* Confirm Upload Queue Action Button */
.confirm-upload-btn {
  background: linear-gradient(135deg, #4285f4, #2b6de0);
  border: none;
  border-radius: 10px;
  font-weight: 700;
  padding: 12px 20px;
  box-shadow: 0 4px 12px rgba(66, 133, 244, 0.2);
  transition: all 0.25s ease;
}

.confirm-upload-btn:hover:not(:disabled) {
  box-shadow: 0 6px 18px rgba(66, 133, 244, 0.35);
  transform: translateY(-1px);
}

.w-100 {
  width: 100%;
}

.ml-3 {
  margin-left: 12px;
}

/* Tabs container */
.tabs-container {
  position: relative;
}

/* View Toggle */
.view-toggle-group {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  gap: 2px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8px;
  padding: 3px;
  z-index: 10;
}

.custom-tabs :deep(.el-tabs__header) {
  margin-right: 80px;
}

.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #8792a2;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 15px;
}

.view-btn:hover {
  color: #4285f4;
  background: rgba(66, 133, 244, 0.08);
}

.view-btn.active {
  background: #fff;
  color: #4285f4;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

/* Custom tabs styling */
.custom-tabs :deep(.el-tabs__item) {
  font-weight: 700;
  color: #8792a2;
  font-size: 14px;
  transition: all 0.2s ease;
}

.custom-tabs :deep(.el-tabs__item:hover) {
  color: #4285f4;
}

.custom-tabs :deep(.el-tabs__item.is-active) {
  color: #4285f4;
  font-size: 15px;
}

.custom-tabs :deep(.el-tabs__active-bar) {
  background-color: #4285f4;
  height: 3px;
  border-radius: 2px;
}

/* Smooth Slide Animations for Queue Items */
.list-enter-active,
.list-leave-active {
  transition: all 0.4s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
</style>
