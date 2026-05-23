<template>
  <div>
    <el-button :icon="ArrowLeft" @click="router.back()" class="mb-4">返回历史记录</el-button>

    <!-- File Header -->
    <el-card shadow="never" class="mb-4">
      <div class="flex-between">
        <div class="file-info">
          <el-icon :size="48" color="#4285f4"><Document /></el-icon>
          <div class="file-details">
            <h3>{{ file?.original_filename }}</h3>
            <p class="text-secondary">{{ formatFileSize(file?.file_size) }} · {{ file?.page_count }} 页</p>
          </div>
        </div>
        <div class="flex-between" style="gap: 12px;">
          <span class="status-badge" :class="file?.status">{{ statusText(file?.status) }}</span>
          <el-button type="primary" :icon="Download" @click="handleDownload">下载报告</el-button>
        </div>
      </div>

      <el-divider />

      <el-row :gutter="32" class="file-meta">
        <el-col :span="6">
          <div class="meta-item">
            <span class="label">上传时间</span>
            <span class="value">{{ file?.uploaded_at }}</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="meta-item">
            <span class="label">完成时间</span>
            <span class="value">{{ file?.completed_at || '-' }}</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="meta-item">
            <span class="label">校验耗时</span>
            <span class="value">{{ file?.duration_seconds ? formatDuration(file.duration_seconds) : '-' }}</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="meta-item">
            <span class="label">校验通过率</span>
            <span class="value">{{ file?.pass_rate }}%</span>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- Verification Results -->
    <el-row :gutter="24">
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <span>校验结果</span>
          </template>

          <el-empty v-if="!file?.verification_result" description="暂无校验结果" />

          <div v-else class="check-results">
            <div
              v-for="(check, index) in file.verification_result.checks"
              :key="index"
              class="check-item"
              :class="check.status"
            >
              <div class="check-icon" :class="check.status">
                <el-icon v-if="check.status === 'pass'"><Check /></el-icon>
                <el-icon v-else-if="check.status === 'warning'"><Warning /></el-icon>
                <el-icon v-else><Close /></el-icon>
              </div>
              <div class="check-content">
                <h4>{{ check.name }}</h4>
                <p>{{ check.message }}</p>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never">
          <template #header>
            <span>详细信息</span>
          </template>

          <div class="info-list">
            <div class="info-item">
              <span>文件 ID</span>
              <span>#{{ file?.id }}</span>
            </div>
            <div class="info-item">
              <span>上传用户</span>
              <span>{{ file?.uploaded_by }}</span>
            </div>
            <div class="info-item">
              <span>校验模型</span>
              <span>{{ file?.verification_result?.model_version }}</span>
            </div>
            <div class="info-item">
              <span>通过项目</span>
              <span style="color: #4caf50;">{{ file?.pass_count }} 项</span>
            </div>
            <div class="info-item">
              <span>警告项目</span>
              <span style="color: #ff9800;">{{ file?.warning_count }} 项</span>
            </div>
            <div class="info-item">
              <span>失败项目</span>
              <span style="color: #f44336;">{{ file?.fail_count }} 项</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Notes Section -->
    <el-card shadow="never" class="mt-4">
      <template #header>
        <span>审核备注</span>
      </template>

      <div class="notes-list">
        <div v-for="note in notes" :key="note.id" class="note-item">
          <div class="note-header">
            <span class="note-author">{{ note.author_name }}</span>
            <span class="note-time">{{ note.created_at }}</span>
          </div>
          <div class="note-content">{{ note.content }}</div>
        </div>
      </div>

      <el-input
        v-model="newNote"
        type="textarea"
        :rows="3"
        placeholder="添加备注..."
        class="mt-4"
      />
      <el-button type="primary" class="mt-4" @click="handleAddNote">添加备注</el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Document, Download, Check, Warning, Close } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const file = ref<any>(null)
const notes = ref([])
const newNote = ref('')

function statusText(status: string): string {
  const map: Record<string, string> = {
    pending: '等待校验',
    processing: '校验中',
    completed: '校验完成',
    failed: '校验失败',
    warning: '有警告',
  }
  return map[status] || status
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return '-'
  const mb = bytes / 1024 / 1024
  return `${mb.toFixed(1)} MB`
}

function formatDuration(seconds?: number): string {
  if (!seconds) return '-'
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return `${min}分${sec}秒`
}

function handleDownload() {
  ElMessage.success('校验报告下载中...')
}

function handleAddNote() {
  if (!newNote.value.trim()) {
    ElMessage.warning('请输入备注内容')
    return
  }
  ElMessage.success('备注已添加')
  newNote.value = ''
}

onMounted(async () => {
  const fileId = route.params.id as string
  // TODO: Fetch file detail and notes
  // file.value = await filesApi.getDetail(fileId)
})
</script>

<style scoped>
.file-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.file-details h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}

.text-secondary {
  color: #999;
  font-size: 14px;
}

.file-meta {
  margin-top: 16px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-item .label {
  font-size: 12px;
  color: #999;
}

.meta-item .value {
  font-size: 14px;
  font-weight: 500;
}

.check-results {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.check-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  border: 1px solid #eee;
  border-radius: 6px;
  border-left-width: 4px;
}

.check-item.pass {
  border-left-color: #4caf50;
}

.check-item.warning {
  border-left-color: #ff9800;
}

.check-item.fail {
  border-left-color: #f44336;
}

.check-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.check-icon.pass {
  background: #e8f5e9;
  color: #4caf50;
}

.check-icon.warning {
  background: #fff3e0;
  color: #ff9800;
}

.check-icon.fail {
  background: #ffebee;
  color: #f44336;
}

.check-content h4 {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.check-content p {
  font-size: 13px;
  color: #666;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid #eee;
}

.info-item:last-child {
  border-bottom: none;
}

.notes-list {
  max-height: 300px;
  overflow-y: auto;
}

.note-item {
  padding: 12px;
  background: #f9f9f9;
  border-radius: 6px;
  margin-bottom: 8px;
}

.note-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.note-author {
  font-size: 13px;
  font-weight: 500;
}

.note-time {
  font-size: 12px;
  color: #999;
}

.note-content {
  font-size: 14px;
  color: #666;
}
</style>
