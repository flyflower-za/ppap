<template>
  <div class="detail-page-container" v-loading="loading" element-loading-background="rgba(245, 247, 250, 0.8)">
    <!-- Back Button -->
    <div class="navigation-header mb-4">
      <el-button 
        :icon="ArrowLeft" 
        @click="router.back()" 
        class="back-btn glass-btn"
      >
        返回历史记录
      </el-button>
    </div>

    <div v-if="file" class="detail-content-layout">
      <!-- File Header Premium Panel -->
      <div class="glass-card header-panel mb-4" :class="statusGlowClass(file.status)">
        <div class="header-main flex-between">
          <div class="file-brand-info">
            <div class="icon-glow-wrapper" :class="file.status">
              <el-icon :size="36"><Document /></el-icon>
            </div>
            <div class="file-details">
              <h2 class="file-title" :title="file.original_filename">{{ file.original_filename }}</h2>
              <div class="file-sub-info">
                <span class="file-type-pill">{{ fileTypeLabel(file.file_type) }}</span>
                <span class="dot-separator">•</span>
                <span class="file-meta-txt">{{ formatFileSize(file.file_size) }}</span>
                <span class="dot-separator">•</span>
                <span class="file-meta-txt">{{ file.page_count || '-' }} 页</span>
              </div>
            </div>
          </div>
          
          <div class="header-actions">
            <span class="premium-status-badge" :class="file.status">
              <span class="pulse-indicator" v-if="file.status === 'processing'"></span>
              {{ statusText(file.status) }}
            </span>
            <el-button 
              type="primary" 
              :icon="Download" 
              @click="handleDownload"
              :disabled="file.status === 'pending' || file.status === 'processing'"
              class="download-report-btn"
            >
              下载原文件
            </el-button>
          </div>
        </div>

        <el-divider class="glass-divider" />

        <!-- File Metadata Grid -->
        <el-row :gutter="24" class="file-meta-grid">
          <el-col :xs="12" :sm="6" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">上传时间</span>
              <span class="meta-value">{{ formatDate(file.uploaded_at) }}</span>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">完成时间</span>
              <span class="meta-value">{{ file.completed_at ? formatDate(file.completed_at) : '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">校验耗时</span>
              <span class="meta-value">{{ file.duration_seconds !== null && file.duration_seconds !== undefined ? formatDuration(file.duration_seconds) : '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">最终通过率</span>
              <span class="meta-value pass-rate-highlight" :class="passRateClass(file.pass_rate)">
                {{ file.pass_rate !== null && file.pass_rate !== undefined ? file.pass_rate + '%' : '-' }}
              </span>
            </div>
          </el-col>
        </el-row>

        <!-- Active Processing Progress Tracker -->
        <div v-if="file.status === 'pending' || file.status === 'processing'" class="live-progress-container mt-4">
          <div class="progress-info-row flex-between mb-2">
            <span class="progress-status-title">正在执行智能校验引擎分析...</span>
            <span class="progress-percent-val">{{ file.verification_progress }}%</span>
          </div>
          <div class="glowing-progress-track">
            <div class="glowing-progress-fill" :style="{ width: file.verification_progress + '%' }"></div>
          </div>
        </div>
      </div>

      <!-- Main Layout: 2 Columns -->
      <el-row :gutter="24" class="content-row">
        <!-- Left Column: Verification Results (Checks List) -->
        <el-col :xs="24" :span="16" class="grid-column">
          <div class="glass-card section-panel">
            <div class="section-title flex-between">
              <h3>校验规则诊断报告</h3>
              <div class="checks-counters" v-if="file.verification_result?.summary">
                <span class="counter-badge pass">{{ file.pass_count }} 通过</span>
                <span class="counter-badge warning" v-if="file.warning_count > 0">{{ file.warning_count }} 警告</span>
                <span class="counter-badge fail" v-if="file.fail_count > 0">{{ file.fail_count }} 不合规</span>
              </div>
            </div>

            <el-empty 
              v-if="!file.verification_result || !file.verification_result.checks || file.verification_result.checks.length === 0" 
              description="校验正在进行中，完成后将自动在此生成详细报告..." 
              :image-size="120"
              class="empty-report-state"
            />

            <div v-else class="diagnostic-checklist">
              <div
                v-for="(check, index) in file.verification_result.checks"
                :key="index"
                class="diagnostic-check-card"
                :class="check.status"
              >
                <div class="check-left-indicator" :class="check.status"></div>
                <div class="diagnostic-check-icon" :class="check.status">
                  <el-icon v-if="check.status === 'pass'"><Check /></el-icon>
                  <el-icon v-else-if="check.status === 'warning'"><Warning /></el-icon>
                  <el-icon v-else><Close /></el-icon>
                </div>
                <div class="diagnostic-check-body">
                  <div class="check-title-row flex-between">
                    <h4>{{ check.name }}</h4>
                    <span class="check-status-tag" :class="check.status">{{ checkStatusLabel(check.status) }}</span>
                  </div>
                  <p class="check-message">{{ check.message }}</p>
                </div>
              </div>
            </div>
          </div>
        </el-col>

        <!-- Right Column: Detail Information & Review Notes -->
        <el-col :xs="24" :span="8" class="grid-column">
          <!-- General Details Card -->
          <div class="glass-card section-panel mb-4 small-card">
            <div class="section-title">
              <h3>文件诊断详情</h3>
            </div>
            <div class="info-details-list">
              <div class="info-detail-item">
                <span class="lbl">校验ID</span>
                <span class="val text-monospace">#{{ file.id.substring(0, 8) }}</span>
              </div>
              <div class="info-detail-item">
                <span class="lbl">上传账号</span>
                <span class="val">{{ file.uploaded_by || '-' }}</span>
              </div>
              <div class="info-detail-item">
                <span class="lbl">校验模型</span>
                <span class="val">{{ file.verification_result?.model_version || file.verification_model || '智能校验引擎 2.0' }}</span>
              </div>
              <div class="info-detail-item">
                <span class="lbl">合规项目</span>
                <span class="val color-pass">{{ file.pass_count }} 项</span>
              </div>
              <div class="info-detail-item">
                <span class="lbl">预警项目</span>
                <span class="val color-warning">{{ file.warning_count }} 项</span>
              </div>
              <div class="info-detail-item">
                <span class="lbl">异常项目</span>
                <span class="val color-fail">{{ file.fail_count }} 项</span>
              </div>
            </div>
          </div>

          <!-- Reviewer Notes Panel -->
          <div class="glass-card section-panel notes-panel">
            <div class="section-title">
              <h3>人工审核备注</h3>
            </div>

            <!-- Notes List with smooth scroll -->
            <div class="notes-timeline-container" v-loading="notesLoading">
              <el-empty 
                v-if="notes.length === 0" 
                description="暂无审核备注。添加备注以记录文件审查细节。" 
                :image-size="60"
                class="empty-notes-state"
              />
              
              <div v-else class="notes-timeline">
                <div 
                  v-for="note in notes" 
                  :key="note.id" 
                  class="timeline-note-bubble"
                >
                  <div class="note-meta flex-between">
                    <div class="author-avatar-info">
                      <div class="avatar-circle">
                        {{ note.author_name ? note.author_name.charAt(0).toUpperCase() : 'U' }}
                      </div>
                      <span class="author-name">{{ note.author_name }}</span>
                    </div>
                    <div class="note-actions">
                      <span class="note-date">{{ formatDate(note.created_at) }}</span>
                      <el-button 
                        v-if="canDeleteNote(note)" 
                        type="danger" 
                        link 
                        :icon="Delete" 
                        class="delete-note-btn"
                        @click="handleDeleteNote(note.id)"
                      />
                    </div>
                  </div>
                  <div class="note-bubble-content">
                    {{ note.content }}
                  </div>
                </div>
              </div>
            </div>

            <el-divider class="glass-divider my-3" />

            <!-- Add Note Form -->
            <div class="add-note-form">
              <el-input
                v-model="newNote"
                type="textarea"
                :rows="3"
                placeholder="撰写人工审核意见或异常备注..."
                maxlength="500"
                show-word-limit
                class="premium-textarea"
                :disabled="submittingNote"
              />
              <div class="flex-between mt-3">
                <span class="input-tips">请确保记录完整的信息，以便追溯核对</span>
                <el-button 
                  type="primary" 
                  @click="handleAddNote" 
                  :loading="submittingNote"
                  :disabled="!newNote.trim()"
                  class="submit-note-btn"
                >
                  发表备注
                </el-button>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Document, Download, Check, Warning, Close, Delete } from '@element-plus/icons-vue'
import { filesApi } from '@/api/files'
import { notesApi } from '@/api/notes'
import { useAuthStore } from '@/stores/auth'
import type { FileDetail, Note } from '@/types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const file = ref<FileDetail | null>(null)
const notes = ref<Note[]>([])
const newNote = ref('')

const loading = ref(true)
const notesLoading = ref(false)
const submittingNote = ref(false)

let pollTimer: any = null

function statusText(status: string): string {
  const map: Record<string, string> = {
    pending: '等待校验',
    processing: '智能分析中',
    completed: '校验通过',
    failed: '校验未通过',
    warning: '合规性预警',
  }
  return map[status] || status
}

function checkStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pass: '通过',
    warning: '预警',
    fail: '不合规',
  }
  return map[status] || status
}

function fileTypeLabel(type?: string): string {
  const map: Record<string, string> = {
    production_plan: '生产计划单',
    quality_report: '质量检测报告',
    purchase_order: '采购订单',
    supplier_qualification: '供应商资质证书',
    product_specification: '产品规格说明书',
    other: '常规文档',
  }
  return map[type || ''] || '未归类文档'
}

function formatFileSize(bytes?: number): string {
  if (bytes === undefined || bytes === null) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatDuration(seconds?: number): string {
  if (seconds === undefined || seconds === null) return '-'
  if (seconds < 60) return `${seconds} 秒`
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return `${min}分${sec}秒`
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  } catch (e) {
    return dateStr
  }
}

function statusGlowClass(status: string): string {
  return `status-glow-${status}`
}

function passRateClass(rate?: number): string {
  if (rate === undefined || rate === null) return ''
  if (rate >= 90) return 'text-pass'
  if (rate >= 60) return 'text-warning'
  return 'text-fail'
}

function canDeleteNote(note: Note): boolean {
  if (!authStore.user) return false
  return authStore.user.id === note.author_id || authStore.user.is_admin
}

// Fetch file detail
async function fetchFileDetail(silent = false) {
  const fileId = route.params.id as string
  if (!silent) loading.value = true
  try {
    const res = await filesApi.getDetail(fileId)
    file.value = res
    
    // Check if we need to poll
    if (res.status === 'pending' || res.status === 'processing') {
      startPolling()
    } else {
      stopPolling()
    }
  } catch (error) {
    stopPolling()
    ElMessage.error('无法载入文件详情')
  } finally {
    if (!silent) loading.value = false
  }
}

// Fetch Notes
async function fetchNotes(silent = false) {
  const fileId = route.params.id as string
  if (!silent) notesLoading.value = true
  try {
    const res = await notesApi.getByFileId(fileId)
    // Notes are already sorted desc by created_at in backend notes.py
    notes.value = res
  } catch (error) {
    ElMessage.error('无法载入备注记录')
  } finally {
    if (!silent) notesLoading.value = false
  }
}

// Download File
async function handleDownload() {
  if (!file.value) return
  try {
    ElMessage.info('正在请求下载链接...')
    const res = await filesApi.getDownloadUrl(file.value.id)
    if (res && res.download_url) {
      window.open(res.download_url, '_blank')
      ElMessage.success('已打开下载通道')
    } else {
      ElMessage.error('未能获取有效下载链接')
    }
  } catch (error) {
    ElMessage.error('获取下载链接失败，请重试')
  }
}

// Add Note
async function handleAddNote() {
  if (!file.value || !newNote.value.trim()) return
  
  submittingNote.value = true
  try {
    const payload = {
      file_id: file.value.id,
      content: newNote.value.trim()
    }
    const res = await notesApi.create(payload)
    // Prepend the new note to the top of the local list
    notes.value.unshift(res)
    newNote.value = ''
    ElMessage.success('备注发表成功')
  } catch (error) {
    ElMessage.error('发表备注失败，请重试')
  } finally {
    submittingNote.value = false
  }
}

// Delete Note
async function handleDeleteNote(noteId: string) {
  try {
    await ElMessageBox.confirm(
      '确定要永久删除这条审核备注吗？此操作无法撤销。',
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
        buttonSize: 'default'
      }
    )
    
    await notesApi.delete(noteId)
    notes.value = notes.value.filter(n => n.id !== noteId)
    ElMessage.success('备注已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除备注失败，请重试')
    }
  }
}

// Live Polling Scheduler
function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    await fetchFileDetail(true)
    // If completed or failed during poll, also refresh notes to pick up potential machine summaries
    if (file.value && file.value.status !== 'pending' && file.value.status !== 'processing') {
      fetchNotes(true)
    }
  }, 1500)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(async () => {
  // Parallel load
  await Promise.all([
    fetchFileDetail(),
    fetchNotes()
  ])
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.detail-page-container {
  min-height: calc(100vh - 120px);
  padding: 8px 4px;
}

/* Glassmorphism card default styles */
.glass-card {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.04);
  border-radius: 16px;
  padding: 24px;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.glass-card:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
}

/* Back Button Style */
.glass-btn {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  color: #555;
  font-weight: 500;
  transition: all 0.25s ease;
}

.glass-btn:hover {
  background: #fff;
  border-color: #4285f4;
  color: #4285f4;
  transform: translateX(-2px);
}

/* Premium Status Glow Borders */
.header-panel {
  border-left: 6px solid rgba(0, 0, 0, 0.08);
}
.header-panel.status-glow-completed {
  border-left-color: #4caf50;
  background: linear-gradient(to right, rgba(76, 175, 80, 0.04), rgba(255, 255, 255, 0.75));
}
.header-panel.status-glow-warning {
  border-left-color: #ff9800;
  background: linear-gradient(to right, rgba(255, 152, 0, 0.04), rgba(255, 255, 255, 0.75));
}
.header-panel.status-glow-failed {
  border-left-color: #f44336;
  background: linear-gradient(to right, rgba(244, 67, 54, 0.04), rgba(255, 255, 255, 0.75));
}
.header-panel.status-glow-processing {
  border-left-color: #2196f3;
  background: linear-gradient(to right, rgba(33, 150, 243, 0.04), rgba(255, 255, 255, 0.75));
}

/* File Brand Block */
.file-brand-info {
  display: flex;
  align-items: center;
  gap: 20px;
  max-width: 70%;
}

.icon-glow-wrapper {
  width: 60px;
  height: 60px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  background: #90a4ae;
}

.icon-glow-wrapper.completed {
  background: linear-gradient(135deg, #81c784, #4caf50);
  box-shadow: 0 6px 20px rgba(76, 175, 80, 0.3);
}
.icon-glow-wrapper.warning {
  background: linear-gradient(135deg, #ffb74d, #ff9800);
  box-shadow: 0 6px 20px rgba(255, 152, 0, 0.3);
}
.icon-glow-wrapper.failed {
  background: linear-gradient(135deg, #e57373, #f44336);
  box-shadow: 0 6px 20px rgba(244, 67, 54, 0.3);
}
.icon-glow-wrapper.processing {
  background: linear-gradient(135deg, #64b5f6, #2196f3);
  box-shadow: 0 6px 20px rgba(33, 150, 243, 0.3);
  animation: pulse-glow 2s infinite ease-in-out;
}

@keyframes pulse-glow {
  0% { transform: scale(1); box-shadow: 0 6px 15px rgba(33, 150, 243, 0.3); }
  50% { transform: scale(1.04); box-shadow: 0 6px 25px rgba(33, 150, 243, 0.5); }
  100% { transform: scale(1); box-shadow: 0 6px 15px rgba(33, 150, 243, 0.3); }
}

.file-details {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.file-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a1f36;
  margin: 0 0 8px 0;
  text-overflow: ellipsis;
  white-space: nowrap;
  overflow: hidden;
}

.file-sub-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.file-type-pill {
  background: rgba(66, 133, 244, 0.1);
  color: #4285f4;
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.dot-separator {
  color: #ccc;
  font-size: 12px;
}

.file-meta-txt {
  font-size: 13px;
  color: #697386;
  font-weight: 500;
}

/* Header Action Pill */
.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.premium-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.premium-status-badge.pending {
  background: rgba(255, 152, 0, 0.1);
  color: #ff9800;
}
.premium-status-badge.processing {
  background: rgba(33, 150, 243, 0.1);
  color: #2196f3;
}
.premium-status-badge.completed {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
}
.premium-status-badge.failed {
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
}
.premium-status-badge.warning {
  background: rgba(255, 152, 0, 0.1);
  color: #ff9800;
}

.pulse-indicator {
  width: 8px;
  height: 8px;
  background-color: #2196f3;
  border-radius: 50%;
  animation: scale-pulse 1.4s infinite ease-in-out;
}

@keyframes scale-pulse {
  0% { transform: scale(0.6); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.4; }
  100% { transform: scale(0.6); opacity: 1; }
}

.download-report-btn {
  background: linear-gradient(135deg, #4285f4, #2b6de0);
  border: none;
  border-radius: 10px;
  font-weight: 600;
  padding: 10px 20px;
  box-shadow: 0 4px 12px rgba(66, 133, 244, 0.2);
  transition: all 0.25s ease;
}

.download-report-btn:hover:not(:disabled) {
  box-shadow: 0 6px 18px rgba(66, 133, 244, 0.35);
  transform: translateY(-1px);
}

.glass-divider {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  margin: 20px 0;
}

/* Metadata Grid styling */
.file-meta-grid {
  margin-bottom: 4px;
}

.meta-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 6px 12px;
}

.meta-label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  color: #8792a2;
  letter-spacing: 0.5px;
}

.meta-value {
  font-size: 15px;
  font-weight: 600;
  color: #3c4257;
}

.pass-rate-highlight {
  font-size: 20px;
  font-weight: 800;
}

.text-pass {
  color: #4caf50;
}
.text-warning {
  color: #ff9800;
}
.text-fail {
  color: #f44336;
}

/* Glowing Progress bar under analyzing */
.live-progress-container {
  background: rgba(0, 0, 0, 0.02);
  padding: 16px;
  border-radius: 12px;
  border: 1px dashed rgba(0, 0, 0, 0.06);
}

.progress-status-title {
  font-size: 13px;
  font-weight: 600;
  color: #4f5b66;
}

.progress-percent-val {
  font-size: 14px;
  font-weight: 700;
  color: #2196f3;
}

.glowing-progress-track {
  width: 100%;
  height: 8px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}

.glowing-progress-fill {
  height: 100%;
  border-radius: 6px;
  background: linear-gradient(90deg, #64b5f6, #2196f3, #00c853);
  box-shadow: 0 0 10px rgba(33, 150, 243, 0.6);
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.glowing-progress-fill::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(
    90deg,
    rgba(255,255,255,0) 0%,
    rgba(255,255,255,0.4) 50%,
    rgba(255,255,255,0) 100%
  );
  animation: shine-bar 1.5s infinite linear;
}

@keyframes shine-bar {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* Two-column dashboard row */
.content-row {
  align-items: stretch;
}

.grid-column {
  display: flex;
  flex-direction: column;
}

.section-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-bottom: 24px;
}

.section-panel.small-card {
  flex: 0 0 auto;
}

.section-title {
  margin-bottom: 20px;
}

.section-title h3 {
  font-size: 16px;
  font-weight: 700;
  color: #1a1f36;
  margin: 0;
  position: relative;
  padding-left: 12px;
}

.section-title h3::before {
  content: '';
  position: absolute;
  left: 0;
  top: 3px;
  bottom: 3px;
  width: 4px;
  border-radius: 2px;
  background-color: #4285f4;
}

/* Diagnostic checklist items */
.diagnostic-checklist {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.diagnostic-check-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(0, 0, 0, 0.04);
  border-radius: 12px;
  position: relative;
  overflow: hidden;
  transition: all 0.25s ease;
}

.diagnostic-check-card:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.7);
  box-shadow: 0 6px 15px rgba(0,0,0,0.03);
}

.check-left-indicator {
  position: absolute;
  top: 0; bottom: 0; left: 0;
  width: 4px;
}
.check-left-indicator.pass { background-color: #4caf50; }
.check-left-indicator.warning { background-color: #ff9800; }
.check-left-indicator.fail { background-color: #f44336; }

.diagnostic-check-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.diagnostic-check-icon.pass {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
}
.diagnostic-check-icon.warning {
  background: rgba(255, 152, 0, 0.1);
  color: #ff9800;
}
.diagnostic-check-icon.fail {
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
}

.diagnostic-check-body {
  flex: 1;
}

.check-title-row h4 {
  font-size: 14px;
  font-weight: 700;
  color: #3c4257;
  margin: 0;
}

.check-status-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.check-status-tag.pass { background: rgba(76, 175, 80, 0.1); color: #4caf50; }
.check-status-tag.warning { background: rgba(255, 152, 0, 0.1); color: #ff9800; }
.check-status-tag.fail { background: rgba(244, 67, 54, 0.1); color: #f44336; }

.check-message {
  font-size: 13px;
  color: #697386;
  margin: 6px 0 0 0;
  line-height: 1.5;
}

.checks-counters {
  display: flex;
  gap: 8px;
}

.counter-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
}

.counter-badge.pass { background: rgba(76, 175, 80, 0.1); color: #4caf50; }
.counter-badge.warning { background: rgba(255, 152, 0, 0.1); color: #ff9800; }
.counter-badge.fail { background: rgba(244, 67, 54, 0.1); color: #f44336; }

.empty-report-state {
  margin: auto;
  padding: 40px 0;
}

/* Info detail items list */
.info-details-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.info-detail-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.info-detail-item .lbl {
  font-size: 13px;
  font-weight: 500;
  color: #8792a2;
}

.info-detail-item .val {
  font-size: 13px;
  font-weight: 600;
  color: #3c4257;
}

.text-monospace {
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
}

.color-pass { color: #4caf50; }
.color-warning { color: #ff9800; }
.color-fail { color: #f44336; }

/* Reviewer Notes timeline and bubbles */
.notes-panel {
  display: flex;
  flex-direction: column;
  max-height: 500px;
}

.notes-timeline-container {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
  max-height: 250px;
  margin-bottom: 12px;
}

/* Custom scrollbar for notes */
.notes-timeline-container::-webkit-scrollbar {
  width: 5px;
}
.notes-timeline-container::-webkit-scrollbar-track {
  background: rgba(0,0,0,0.02);
}
.notes-timeline-container::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.1);
  border-radius: 3px;
}

.empty-notes-state {
  padding: 20px 0;
}

.notes-timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.timeline-note-bubble {
  background: rgba(0, 0, 0, 0.025);
  border: 1px solid rgba(0, 0, 0, 0.02);
  border-radius: 12px;
  padding: 12px;
  transition: background 0.2s ease;
}

.timeline-note-bubble:hover {
  background: rgba(0, 0, 0, 0.04);
}

.note-meta {
  margin-bottom: 8px;
}

.author-avatar-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.avatar-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #4285f4;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.author-name {
  font-size: 12px;
  font-weight: 700;
  color: #3c4257;
}

.note-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.note-date {
  font-size: 11px;
  color: #8792a2;
}

.delete-note-btn {
  padding: 0;
  height: auto;
  font-size: 14px;
  color: #8792a2;
}
.delete-note-btn:hover {
  color: #f44336 !important;
}

.note-bubble-content {
  font-size: 13px;
  line-height: 1.5;
  color: #4f5b66;
  word-break: break-all;
  white-space: pre-wrap;
}

/* Premium Textarea fields */
.premium-textarea :deep(.el-textarea__inner) {
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: rgba(255,255,255,0.6);
  font-size: 13px;
  padding: 10px 12px;
  transition: all 0.25s ease;
}

.premium-textarea :deep(.el-textarea__inner:focus) {
  background: #fff;
  border-color: #4285f4;
  box-shadow: 0 0 0 2px rgba(66,133,244,0.1);
}

.input-tips {
  font-size: 11px;
  color: #8792a2;
}

.submit-note-btn {
  background: #4285f4;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  padding: 8px 16px;
}

.submit-note-btn:hover:not(:disabled) {
  background: #3367d6;
}

.my-3 {
  margin: 12px 0;
}
</style>
