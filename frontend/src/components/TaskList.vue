<template>
  <div class="task-list-container">
    <div v-loading="loading && files.length === 0" class="list-wrapper" element-loading-background="rgba(255, 255, 255, 0.5)">
      <!-- Empty State -->
      <div v-if="files.length === 0" class="empty-state">
        <el-empty :description="emptyText" :image-size="80" class="premium-empty"></el-empty>
      </div>

      <!-- Tasks Grid -->
      <div v-else class="tasks-grid">
        <div 
          v-for="file in files" 
          :key="file.id" 
          class="task-card glass-item-card" 
          :class="file.status"
          @click="goToDetail(file.id)"
        >
          <div class="task-card-header flex-between">
            <div class="header-left">
              <span class="file-name" :title="file.original_filename">{{ file.original_filename }}</span>
              <!-- Status tag shown in 'all' view to differentiate records -->
              <el-tag 
                v-if="status === 'all'" 
                :type="getFileStatusTag(file.status)" 
                size="small" 
                effect="dark"
                class="status-tag-mini ml-2"
              >
                {{ statusText(file.status) }}
              </el-tag>
            </div>
            <span class="file-type-badge" :class="file.file_type">{{ fileTypeLabel(file.file_type) }}</span>
          </div>

          <div class="task-card-body">
            <!-- Processing state (pending/processing): show progress bar -->
            <div v-if="file.status === 'processing' || file.status === 'pending'" class="progress-section">
              <div class="progress-info flex-between mb-1">
                <span class="progress-txt">
                  {{ file.status === 'pending' ? '排队等待诊断中...' : '正在进行合规比对分析...' }}
                </span>
                <span class="progress-val">{{ file.verification_progress }}%</span>
              </div>
              <div class="card-progress-track">
                <div class="card-progress-fill" :style="{ width: file.verification_progress + '%' }"></div>
              </div>
            </div>

            <!-- Completed state (completed/warning): show success badges / rates -->
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

            <!-- Failed state (failed): show failure reason -->
            <div v-else-if="file.status === 'failed'" class="error-section">
              <p class="error-msg" :title="file.verification_result_json?.error || '诊断完成：文档核心印章缺失或参数不合规'">
                <el-icon class="mr-1"><Close /></el-icon> {{ file.verification_result_json?.error || '诊断完成：文档核心印章缺失或参数不合规' }}
              </p>
            </div>
          </div>

          <div class="task-card-footer flex-between">
            <span class="upload-time">{{ formatTime(file.uploaded_at) }}</span>
            <el-button type="primary" link size="small" class="detail-link" @click.stop="goToDetail(file.id)">
              查看分析报告 <el-icon class="arrow-icon"><ArrowRight /></el-icon>
            </el-button>
          </div>
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
import dayjs from 'dayjs'

const props = defineProps<{
  status: 'all' | 'processing' | 'completed' | 'failed'
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

function fileTypeLabel(type?: string): string {
  const map: Record<string, string> = {
    production_plan: '生产计划单',
    quality_report: '质量检测报告',
    purchase_order: '采购订单',
    supplier_qualification: '供应商资质证书',
    product_specification: '产品规格说明书',
    other: '常规文档',
  }
  return map[type || ''] || '未分类'
}

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

// Extract reference count from the summary stored in verification_result_json
function getRefCount(file: any): number {
  return file.verification_result_json?.summary?.reference ?? 0
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

    // If we are in the processing tab, and tasks have finished (disappeared from list),
    // we notify parent so other tabs (completed/failed) can reload too!
    if (props.status === 'processing' && files.value.length > 0 && newFiles.length < files.value.length) {
      emit('task-finished')
    }

    files.value = newFiles

    // Manage smart polling if we are in the processing or all tab and there are active tasks
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
  pollTimer = setInterval(() => {
    fetchTasks(true)
  }, 2000)
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

function formatTime(timeStr: string) {
  return dayjs(timeStr).format('YYYY-MM-DD HH:mm')
}

// Watch status change
watch(() => props.status, (newStatus) => {
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

.list-wrapper {
  min-height: 150px;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px 0;
}

.tasks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  padding: 8px 0;
}

/* Glassmorphic Item Cards */
.glass-item-card {
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 12px;
  padding: 10px 14px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.25, 0.8, 0.25, 1);
  position: relative;
  overflow: visible;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 125px;
}

.glass-item-card:hover {
  background: rgba(255, 255, 255, 0.9);
  border-color: #4285f4;
  box-shadow: 0 6px 20px rgba(66, 133, 244, 0.06);
  transform: translateY(-2px);
}

.task-card-header {
  margin-bottom: 8px;
  gap: 6px;
  align-items: flex-start;
  flex-wrap: nowrap;
  overflow: hidden;
}

/* Left section (file name + optional status tag) */
.header-left {
  display: flex;
  align-items: center;
  min-width: 0; /* Allows flex truncation */
  overflow: hidden;
  flex: 1;
}

.file-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex: 1;
}

/* Beautiful Type Badges */
.file-type-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.04);
  color: #4f5b66;
  white-space: nowrap;
  flex-shrink: 0; /* Never shrink or wrap — always visible */
}

.file-type-badge.production_plan { background: rgba(76, 175, 80, 0.1); color: #4caf50; }
.file-type-badge.quality_report { background: rgba(33, 150, 243, 0.1); color: #2196f3; }
.file-type-badge.purchase_order { background: rgba(255, 152, 0, 0.1); color: #ff9800; }
.file-type-badge.supplier_qualification { background: rgba(156, 39, 176, 0.1); color: #9c27b0; }
.file-type-badge.product_specification { background: rgba(0, 150, 136, 0.1); color: #009688; }

.task-card-body {
  margin-bottom: 8px;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

/* Progress Section */
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
  /* Using non-empty content to avoid AV false positive (BehavesLike.PS.Downloader) */
  content: '\00a0';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(
    90deg,
    rgba(255,255,255,0) 0%,
    rgba(255,255,255,0.3) 50%,
    rgba(255,255,255,0) 100%
  );
  animation: shine-bar 1.5s infinite linear;
}

@keyframes shine-bar {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* Results section */
.result-section {
  align-items: center;
}

.metrics {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.metric {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 700;
}

.metric.pass { color: #4caf50; }
.metric.warn { color: #ff9800; }
.metric.fail { color: #f44336; }
.metric.ref { color: #1976d2; }

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
.pass-rate .value.mid { color: #ff9800; }
.pass-rate .value.low { color: #f44336; }

/* Error section for Failed */
.error-section {
  background: rgba(244, 67, 54, 0.05);
  border: 1px solid rgba(244, 67, 54, 0.1);
  border-radius: 8px;
  padding: 8px 12px;
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

.mr-1 {
  margin-right: 4px;
}

/* Card footer */
.task-card-footer {
  border-top: 1px solid rgba(0, 0, 0, 0.04);
  padding-top: 10px;
}

.upload-time {
  font-size: 12px;
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
</style>
