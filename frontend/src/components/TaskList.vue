<template>
  <div class="task-list-container">
    <div v-loading="loading && files.length === 0" class="list-wrapper" element-loading-background="rgba(255, 255, 255, 0.5)">

      <!-- Empty State -->
      <div v-if="files.length === 0" class="empty-state">
        <el-empty :description="emptyText" :image-size="80" class="premium-empty"></el-empty>
      </div>

      <!-- ═══════════════ GRID VIEW ═══════════════ -->
      <div v-else-if="props.viewMode === 'grid'" class="tasks-grid">
        <div
          v-for="file in files"
          :key="file.id"
          class="task-card glass-item-card"
          :class="file.status"
          @click="goToDetail(file.id)"
        >
          <!-- Row 1: Full-width filename -->
          <div class="card-filename" :title="file.original_filename">{{ file.original_filename }}</div>

          <!-- Row 2: Institution chip + status badge -->
          <div class="card-meta-row">
            <span class="institution-chip">{{ getInstitution(file) }}</span>
            <el-tag
              v-if="status === 'all'"
              :type="getFileStatusTag(file.status)"
              size="small"
              effect="dark"
              class="status-tag-mini"
            >
              {{ statusText(file.status) }}
            </el-tag>
          </div>

          <!-- Body -->
          <div class="task-card-body">
            <!-- Processing / Pending -->
            <div v-if="file.status === 'processing' || file.status === 'pending'" class="progress-section">
              <div class="progress-info flex-between mb-1">
                <span class="progress-txt">{{ file.status === 'pending' ? '排队等待诊断中...' : '正在进行合规比对分析...' }}</span>
                <span class="progress-val">{{ file.verification_progress }}%</span>
              </div>
              <div class="card-progress-track">
                <div class="card-progress-fill" :style="{ width: file.verification_progress + '%' }"></div>
              </div>
            </div>

            <!-- Completed / Warning -->
            <div v-else-if="file.status === 'completed' || file.status === 'warning'" class="result-section flex-between">
              <div class="metrics">
                <span class="metric pass"><el-icon><Check /></el-icon> {{ file.pass_count }} 通过</span>
                <span class="metric warn" v-if="file.warning_count > 0"><el-icon><Warning /></el-icon> {{ file.warning_count }} 警告</span>
                <span class="metric fail" v-if="file.fail_count > 0"><el-icon><Close /></el-icon> {{ file.fail_count }} 异常</span>
                <span class="metric ref" v-if="getRefCount(file) > 0"><el-icon><InfoFilled /></el-icon> {{ getRefCount(file) }} 参考</span>
              </div>
              <div class="pass-rate" v-if="file.pass_rate !== undefined">
                <span class="label">通过率</span>
                <span class="value" :class="passRateClass(file.pass_rate)">{{ file.pass_rate }}%</span>
              </div>
            </div>

            <!-- Failed -->
            <div v-else-if="file.status === 'failed'" class="error-section">
              <p class="error-msg" :title="getFailedMessage(file)">
                <el-icon class="mr-1"><Close /></el-icon> {{ getFailedMessage(file) }}
              </p>
            </div>
          </div>

          <!-- Footer -->
          <div class="task-card-footer flex-between">
            <span class="upload-time">{{ formatTime(file.uploaded_at) }}</span>
            <el-button type="primary" link size="small" class="detail-link" @click.stop="goToDetail(file.id)">
              查看分析报告 <el-icon class="arrow-icon"><ArrowRight /></el-icon>
            </el-button>
          </div>
        </div>
      </div>

      <!-- ═══════════════ LIST VIEW ═══════════════ -->
      <div v-else class="tasks-list">
        <div
          v-for="file in files"
          :key="file.id"
          class="list-item"
          :class="file.status"
          @click="goToDetail(file.id)"
        >
          <!-- Left status color strip -->
          <div class="list-strip" :class="file.status"></div>

          <!-- File info: name + institution -->
          <div class="list-file-info">
            <span class="list-filename" :title="file.original_filename">{{ file.original_filename }}</span>
            <span class="list-institution">{{ getInstitution(file) }}</span>
          </div>

          <!-- Status badge -->
          <div class="list-status-cell">
            <el-tag :type="getFileStatusTag(file.status)" size="small" effect="dark">
              {{ statusText(file.status) }}
            </el-tag>
          </div>

          <!-- Metrics -->
          <div class="list-metrics">
            <template v-if="file.status === 'completed' || file.status === 'warning'">
              <span class="metric pass"><el-icon><Check /></el-icon>{{ file.pass_count }}</span>
              <span class="metric warn" v-if="file.warning_count > 0"><el-icon><Warning /></el-icon>{{ file.warning_count }}</span>
              <span class="metric fail" v-if="file.fail_count > 0"><el-icon><Close /></el-icon>{{ file.fail_count }}</span>
              <span class="metric ref" v-if="getRefCount(file) > 0"><el-icon><InfoFilled /></el-icon>{{ getRefCount(file) }}</span>
            </template>
            <template v-else-if="file.status === 'processing' || file.status === 'pending'">
              <span class="list-progress-txt">{{ file.status === 'pending' ? '排队中' : `${file.verification_progress}%` }}</span>
            </template>
            <template v-else>
              <span class="metric fail"><el-icon><Close /></el-icon> 异常</span>
            </template>
          </div>

          <!-- Pass rate -->
          <div class="list-pass-rate">
            <span v-if="file.status === 'completed' || file.status === 'warning'"
              :class="['list-rate-val', passRateClass(file.pass_rate)]">
              {{ file.pass_rate }}%
            </span>
            <span v-else class="list-rate-empty">—</span>
          </div>

          <!-- Time -->
          <span class="list-time">{{ formatTime(file.uploaded_at) }}</span>

          <!-- Action -->
          <el-button type="primary" link size="small" class="detail-link" @click.stop="goToDetail(file.id)">
            查看报告 <el-icon class="arrow-icon"><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { filesApi } from '@/api/files'
import type { File } from '@/types'
import { Check, Warning, Close, ArrowRight, InfoFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  status: 'all' | 'processing' | 'completed' | 'failed'
  viewMode: 'grid' | 'list'
}>()

const emit = defineEmits(['task-finished'])

const router = useRouter()
const files = ref<File[]>([])
const loading = ref(false)
let pollTimer: any = null

const emptyText = computed(() => {
  if (props.status === 'all') return '暂无任何校验任务记录'
  if (props.status === 'processing') return '当前没有进行中的校验任务'
  if (props.status === 'completed') return '暂无已完成的校验文件'
  return '暂无失败的校验记录'
})

function statusText(status: string): string {
  const map: Record<string, string> = {
    pending: '排队中',
    processing: '诊断中',
    completed: '合规通过',
    warning: '有风险警告',
    failed: '不合格',
    needs_review: '需人工仲裁',
  }
  return map[status] || status
}

function getFileStatusTag(status: string): string {
  const map: Record<string, string> = {
    pending: 'info',
    processing: '',
    completed: 'success',
    warning: 'warning',
    failed: 'danger',
    needs_review: 'warning',
  }
  return map[status] || 'info'
}

function passRateClass(rate?: number): string {
  if (rate === undefined || rate === null) return ''
  if (rate >= 90) return 'high'
  if (rate >= 60) return 'mid'
  return 'low'
}

// Extract reference count from summary stored in verification_result_json
function getRefCount(file: any): number {
  return file.verification_result_json?.summary?.reference ?? 0
}

// Show sniffed institution, fall back to "-"
function getInstitution(file: any): string {
  const inst = file.verification_result_json?.summary?.institution
  return inst || '-'
}

// Generate meaningful error message from verification result
function getFailedMessage(file: any): string {
  const vr = file.verification_result_json
  if (!vr) return '校验失败，无法获取检测结果'

  // If there's an explicit error field, use it
  if (vr.error) return vr.error

  const summary = vr.summary
  const checks = vr.checks || []

  // If no checks were executed at all
  if (checks.length === 0) {
    if (summary?.matched_category === null) {
      return '未匹配到任何检测分类，未执行检测项目'
    }
    return '校验完成但未产生任何检测项'
  }

  // Extract failed check descriptions
  const failedChecks = checks.filter((c: any) => c.severity === 'fail' || c.status === 'fail')
  if (failedChecks.length > 0) {
    const reasons = failedChecks.map((c: any) => c.title || c.rule_name || c.message || '未知检测项').slice(0, 2)
    const suffix = failedChecks.length > 2 ? ` 等 ${failedChecks.length} 项` : ''
    return `${reasons.join('、')}${suffix} 未通过`
  }

  // Fallback: use summary counts
  if (summary) {
    const { pass = 0, warning = 0, fail = 0, total = 0 } = summary
    if (total === 0) return '未执行任何检测项目'
    if (fail > 0) return `${fail} 项检测未通过`
    if (warning > 0) return `${warning} 项检测存在风险`
  }

  return '校验未通过，请查看详细报告'
}

async function fetchTasks(silent = false) {
  if (!silent) loading.value = true
  try {
    const params: any = {
      page: 1,
      page_size: 15
    }
    if (props.status !== 'all') {
      params.status = props.status
    }

    const res = await filesApi.list(params)
    const newFiles = res.items || []

    if (props.status === 'processing' && files.value.length > 0 && newFiles.length < files.value.length) {
      emit('task-finished')
    }

    files.value = newFiles

    const hasActive = newFiles.some(f => f.status === 'processing' || f.status === 'pending')
    if (hasActive) {
      startPolling()
    } else {
      stopPolling()
    }
  } catch (error) {
    console.error('获取任务列表失败:', error)
    stopPolling()
  } finally {
    if (!silent) loading.value = false
  }
}

function startPolling() {
  if (pollTimer) return
  let interval = 2000  // Start at 2s
  const maxInterval = 30000  // Cap at 30s
  const schedule = () => {
    pollTimer = setTimeout(() => {
      fetchTasks(true)
      interval = Math.min(interval * 1.5, maxInterval)
      schedule()
    }, interval)
  }
  schedule()
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function goToDetail(id: string) {
  router.push(`/files/${id}`)
}

import { formatTime } from '@/utils/formatters'

watch(() => props.status, () => {
  stopPolling()
  fetchTasks()
})

onMounted(fetchTasks)

onUnmounted(() => {
  stopPolling()
})

defineExpose({
  refresh: fetchTasks
})
</script>

<style scoped>
.task-list-container {
  min-height: 200px;
}

/* ── Common ── */
.list-wrapper {
  min-height: 150px;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px 0;
}

/* ══════════════════════════════
   GRID VIEW
══════════════════════════════ */
.tasks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  padding: 4px 0;
}

.glass-item-card {
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 12px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.25, 0.8, 0.25, 1);
  position: relative;
  overflow: visible;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.glass-item-card:hover {
  background: rgba(255, 255, 255, 0.9);
  border-color: #4285f4;
  box-shadow: 0 6px 20px rgba(66, 133, 244, 0.06);
  transform: translateY(-2px);
}

/* Row 1: filename */
.card-filename {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 100%;
  line-height: 1.4;
}

/* Row 2: institution + status tag */
.card-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  min-width: 0;
}

.institution-chip {
  font-size: 11px;
  font-weight: 600;
  color: #6b7c93;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 4px;
  padding: 1px 7px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100px;
  flex-shrink: 1;
}

/* Card body */
.task-card-body {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  margin: 2px 0;
}

/* Progress */
.progress-section {
  display: flex;
  flex-direction: column;
}

.progress-info {
  font-size: 11px;
  color: #8792a2;
}

.progress-txt {
  font-weight: 600;
}

.progress-val {
  font-weight: 700;
  color: #4285f4;
}

.card-progress-track {
  width: 100%;
  height: 6px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.card-progress-fill {
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, #64b5f6, #4285f4);
  box-shadow: 0 0 4px rgba(66, 133, 244, 0.4);
  transition: width 0.3s ease;
  position: relative;
  overflow: hidden;
}

.card-progress-fill::after {
  /* Non-empty content to avoid AV false positive */
  content: '\00a0';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.3) 50%, rgba(255,255,255,0) 100%);
  animation: shine-bar 1.5s infinite linear;
}

@keyframes shine-bar {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* Metrics */
.result-section {
  align-items: center;
}

.metrics {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.metric {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  font-weight: 700;
}

.metric.pass { color: #4caf50; }
.metric.warn { color: #ff9800; }
.metric.fail { color: #f44336; }
.metric.ref  { color: #1976d2; }

.pass-rate {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.pass-rate .label {
  font-size: 9px;
  color: #8792a2;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.2px;
}

.pass-rate .value {
  font-size: 15px;
  font-weight: 800;
}

.pass-rate .value.high { color: #4caf50; }
.pass-rate .value.mid  { color: #ff9800; }
.pass-rate .value.low  { color: #f44336; }

/* Error section */
.error-section {
  background: rgba(244, 67, 54, 0.05);
  border: 1px solid rgba(244, 67, 54, 0.1);
  border-radius: 8px;
  padding: 6px 10px;
}

.error-msg {
  font-size: 12px;
  color: #f44336;
  display: flex;
  align-items: center;
  margin: 0;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Card footer */
.task-card-footer {
  border-top: 1px solid rgba(0, 0, 0, 0.04);
  padding-top: 8px;
  margin-top: auto;
}

.upload-time {
  font-size: 11px;
  color: #8792a2;
  font-weight: 500;
}

.detail-link {
  font-weight: 600;
  font-size: 12px;
  color: #4285f4;
  padding: 0;
}

.detail-link:hover {
  color: #3367d6;
}

.detail-link:hover .arrow-icon {
  transform: translateX(2px);
}

.arrow-icon {
  font-size: 12px;
  transition: transform 0.2s ease;
}

/* ══════════════════════════════
   LIST VIEW
══════════════════════════════ */
.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 0;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 10px;
  padding: 10px 14px 10px 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.list-item:hover {
  background: rgba(255, 255, 255, 0.95);
  border-color: #4285f4;
  box-shadow: 0 3px 12px rgba(66, 133, 244, 0.06);
  transform: translateX(2px);
}

/* Colored left strip by status */
.list-strip {
  width: 3px;
  align-self: stretch;
  border-radius: 2px;
  flex-shrink: 0;
}
.list-strip.completed  { background: #4caf50; }
.list-strip.warning    { background: #ff9800; }
.list-strip.failed     { background: #f44336; }
.list-strip.processing { background: #4285f4; }
.list-strip.pending    { background: #b0bec5; }
.list-strip.needs_review { background: #ff9800; }

/* File info column */
.list-file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.list-filename {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.list-institution {
  font-size: 11px;
  color: #8792a2;
  font-weight: 500;
}

/* Status cell */
.list-status-cell {
  flex-shrink: 0;
}

/* Metrics cell */
.list-metrics {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  min-width: 80px;
}

.list-progress-txt {
  font-size: 12px;
  font-weight: 700;
  color: #4285f4;
}

/* Pass rate cell */
.list-pass-rate {
  flex-shrink: 0;
  min-width: 44px;
  text-align: right;
}

.list-rate-val {
  font-size: 14px;
  font-weight: 800;
}

.list-rate-val.high { color: #4caf50; }
.list-rate-val.mid  { color: #ff9800; }
.list-rate-val.low  { color: #f44336; }

.list-rate-empty {
  font-size: 13px;
  color: #b0bec5;
}

/* Time cell */
.list-time {
  font-size: 11px;
  color: #8792a2;
  font-weight: 500;
  flex-shrink: 0;
  white-space: nowrap;
}

/* Shared utilities */
.mr-1 {
  margin-right: 4px;
}

.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mb-1 { margin-bottom: 4px; }
</style>
