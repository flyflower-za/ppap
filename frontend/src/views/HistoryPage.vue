<template>
  <div class="history-dashboard-container animate-fade-in">
    <!-- Header Hero Banner with Statistics -->
    <div class="hero-statistics-row mb-6">
      <div class="hero-left">
        <h2 class="dashboard-title">{{ $t('history.title') }}</h2>
        <p class="dashboard-subtitle">{{ $t('history.subtitle') }}</p>
      </div>
      <div class="hero-right">
        <el-button
          type="primary"
          class="export-button-premium"
          :icon="Download"
          @click="handleExport"
          :loading="exporting"
        >
          {{ $t('history.exportExcel') }}
        </el-button>
      </div>
    </div>

    <!-- Collapsible Filter Control Center -->
    <el-card class="glass-card control-filter-card mb-6" shadow="hover">
      <div class="filter-card-header flex-between cursor-pointer" @click="isCollapsed = !isCollapsed">
        <div class="header-left flex-align-center">
          <span class="filter-icon">🔍</span>
          <span class="filter-title-text font-bold ml-2">{{ $t('history.filterTitle') }}</span>
          <el-tag v-if="hasActiveFilters" size="small" type="warning" class="active-filter-tag ml-3">
            {{ $t('history.filterActive') }}
          </el-tag>
        </div>
        <div class="header-right">
          <el-button link type="primary" class="collapse-toggle-btn">
            {{ isCollapsed ? $t('history.expandFilter') : $t('history.collapseFilter') }}
            <el-icon class="arrow-icon ml-1" :class="{ 'is-active': !isCollapsed }">
              <ArrowDown />
            </el-icon>
          </el-button>
        </div>
      </div>

      <el-collapse-transition>
        <div v-show="!isCollapsed" class="filter-form-wrapper mt-4">
          <el-form :model="filters" label-position="top" class="premium-filter-form">
            <el-row :gutter="20">
              <el-col :xs="24" :sm="8" :md="5">
                <el-form-item :label="$t('history.verifyStatusLabel')">
                  <el-select
                    v-model="filters.status"
                    :placeholder="$t('history.allStatus')"
                    clearable
                    class="premium-select"
                    @change="handleSearch"
                  >
                    <el-option :label="$t('history.statusPending')" value="pending" />
                    <el-option :label="$t('history.statusProcessing')" value="processing" />
                    <el-option :label="$t('history.statusCompleted')" value="completed" />
                    <el-option :label="$t('history.statusWarning')" value="warning" />
                    <el-option :label="$t('history.statusFailed')" value="failed" />
                    <el-option :label="$t('status.needsReview')" value="needs_review" />
                  </el-select>
                </el-form-item>
              </el-col>

              <el-col :xs="24" :sm="8" :md="5">
                <el-form-item :label="$t('history.institutionLabel')">
                  <el-input
                    v-model="filters.institution"
                    :placeholder="$t('history.institutionPlaceholder')"
                    clearable
                    class="premium-input"
                    @clear="handleSearch"
                    @keyup.enter="handleSearch"
                  />
                </el-form-item>
              </el-col>

              <el-col :xs="24" :sm="8" :md="6">
                <el-form-item :label="$t('history.fuzzyMatch')">
                  <el-input
                    v-model="filters.keyword"
                    :placeholder="$t('history.keywordPlaceholder')"
                    clearable
                    class="premium-input"
                    @keyup.enter="handleSearch"
                  />
                </el-form-item>
              </el-col>

              <el-col :xs="24" :sm="24" :md="8">
                <el-form-item :label="$t('history.uploadTimeRange')">
                  <el-date-picker
                    v-model="dateRange"
                    type="daterange"
                    :range-separator="$t('history.dateRangeSeparator')"
                    :start-placeholder="$t('history.startDate')"
                    :end-placeholder="$t('history.endDate')"
                    value-format="YYYY-MM-DD"
                    class="premium-date-picker"
                    @change="handleDateRangeChange"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            
            <div class="flex-end-buttons mt-2">
              <el-button class="reset-button-premium" @click="handleReset">{{ $t('history.resetFilter') }}</el-button>
              <el-button type="primary" class="search-button-premium" @click="handleSearch">{{ $t('history.applyFilter') }}</el-button>
            </div>
          </el-form>
        </div>
      </el-collapse-transition>
    </el-card>


    <!-- Batch Control Toolbar -->
    <div v-if="selectedRows.length > 0" class="batch-control-banner mb-4 animate-slide-down">
      <div class="batch-left">
        <span class="pulse-dot"></span>
        <span class="selected-text">{{ $t('history.selectedRecords', { count: selectedRows.length }) }}</span>
      </div>
      <div class="batch-right">
        <el-button-group>
          <el-button
            size="small"
            type="primary"
            plain
            :icon="Download"
            @click="handleBatchDownload"
          >
            {{ $t('history.batchDownload') }}
          </el-button>
          <el-button
            size="small"
            type="danger"
            :icon="Delete"
            @click="handleBatchDelete"
          >
            {{ $t('history.batchDelete') }}
          </el-button>
        </el-button-group>
      </div>
    </div>

    <!-- Data Display Table -->
    <el-card class="glass-card table-wrapper-card" shadow="hover">
      <el-table
        :data="tableData"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        row-key="id"
        :key="tableKey"
        class="premium-table"
        stripe
        border
      >
        <el-table-column type="selection" width="45" reserve-selection fixed="left" />
        
        <el-table-column
          v-for="col in tableColumns"
          :key="col.prop"
          :prop="col.prop !== 'institution' ? col.prop : undefined"
          :label="col.label"
          :width="col.width"
          :min-width="col.minWidth"
          :align="col.align"
          :show-overflow-tooltip="col.showOverflowTooltip"
        >
          <template #default="{ row }">
            <template v-if="col.prop === 'uploaded_at'">
              <span class="font-mono text-secondary">{{ formatDateTime(row.uploaded_at) }}</span>
            </template>
            <template v-else-if="col.prop === 'original_filename'">
              <div class="file-name-cell">
                <span class="pdf-icon">📄</span>
                <span class="file-title-text" @click="handleView(row)">{{ row.original_filename }}</span>
              </div>
            </template>
            <template v-else-if="col.prop === 'file_type'">
              <el-tag :type="getFileTypeTag(row.file_type)" effect="plain" class="type-tag-premium">
                {{ getFileTypeText(row.file_type) }}
              </el-tag>
            </template>
            <template v-else-if="col.prop === 'institution'">
              <span class="text-secondary font-bold">{{ getInstitution(row) }}</span>
            </template>
            <template v-else-if="col.prop === 'page_count'">
              <span class="font-mono">{{ row.page_count || 1 }}</span>
            </template>
            <template v-else-if="col.prop === 'status'">
              <div class="status-wrapper">
                <span class="status-indicator-dot" :class="row.status"></span>
                <span class="status-label" :class="row.status">{{ statusText(row.status) }}</span>
              </div>
            </template>
            <template v-else-if="col.prop === 'pass_rate'">
              <div v-if="row.status !== 'pending' && row.status !== 'processing'" class="progress-premium-container">
                <div class="progress-header font-mono">
                  <span class="rate-value" :class="getPassRateClass(row.pass_rate)">{{ row.pass_rate }}%</span>
                  <span class="fraction text-secondary">{{ row.pass_count }}/{{ row.pass_count + row.warning_count + row.fail_count }}</span>
                </div>
                <el-progress
                  :percentage="row.pass_rate || 0"
                  :status="getProgressStatus(row.status)"
                  :stroke-width="5"
                  :show-text="false"
                  class="progress-bar-premium"
                />
              </div>
              <div v-else class="status-placeholder text-secondary">
                {{ row.status === 'processing' ? $t('history.diagnosingProgress') : $t('history.waitingProgress') }}
              </div>
            </template>
          </template>
        </el-table-column>
        
        <el-table-column :label="$t('history.actionsColumn')" width="280" fixed="right">
          <template #default="{ row }">
            <div class="table-actions-row">
              <el-button link type="primary" size="small" class="action-btn-view" @click="handleView(row)">
                {{ $t('task.viewDetail') }}
              </el-button>
              <el-button
                link
                type="primary"
                size="small"
                class="action-btn-download"
                @click="handleDownload(row)"
                :disabled="row.status === 'pending' || row.status === 'processing'"
              >
                {{ $t('history.downloadReport') }}
              </el-button>
              <el-button
                link
                type="warning"
                size="small"
                class="action-btn-reverify"
                @click="handleReverify(row)"
                :disabled="row.status === 'pending' || row.status === 'processing'"
              >
                {{ $t('history.reverify') }}
              </el-button>
              <el-button link type="danger" size="small" class="action-btn-delete" @click="handleDelete(row)">
                {{ $t('common.delete') }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination Footer -->
      <div class="pagination-footer-container mt-6">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          class="premium-pagination"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- Execution Trajectory Drawer -->
    <el-drawer
      v-model="trajectoryDrawerVisible"
      :title="$t('history.trajectoryTitle')"
      size="45%"
      direction="rtl"
      :destroy-on-close="false"
      class="trajectory-drawer"
    >
      <div class="trajectory-container">
        <el-timeline>
          <el-timeline-item
            v-for="(log, idx) in executionLogs"
            :key="idx"
            :type="log.status === 'success' || log.pass_status ? 'success' : (log.status === 'error' || log.pass_status === false ? 'danger' : 'primary')"
            :color="log.status === 'running' ? '#409EFF' : ''"
            :hollow="log.status === 'running'"
            :timestamp="formatDateTime(log.timestamp)"
            placement="top"
          >
            <el-card shadow="hover" class="log-card">
              <h4 style="margin:0 0 8px 0; font-size:14px;">{{ log.operator }}</h4>
              <p class="log-msg" style="margin:0; font-size:13px; color:#666;">{{ log.message }}</p>
              <el-collapse v-if="log.extracted_data && Object.keys(log.extracted_data).length > 0" class="log-data-collapse mt-2">
                <el-collapse-item :title="$t('history.extractedData')" name="1">
                  <pre class="log-data-pre">{{ JSON.stringify(log.extracted_data, null, 2) }}</pre>
                </el-collapse-item>
              </el-collapse>
            </el-card>
          </el-timeline-item>
        </el-timeline>
        <el-empty
          v-if="executionLogs.length === 0"
          :description="$t('history.emptyTrajectory')"
        />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Delete, ArrowDown, Tickets } from '@element-plus/icons-vue'
import Sortable from 'sortablejs'
import { filesApi } from '@/api/files'
import { getErrorMessage } from '@/utils/formatters'
import { getLocale } from '@/locales'

const { t } = useI18n()
const router = useRouter()

const loading = ref(false)
const exporting = ref(false)
const tableData = ref<any[]>([])
const selectedRows = ref<any[]>([])
const dateRange = ref<[string, string] | null>(null)
const isCollapsed = ref(true) // Collapsed by default

const filters = reactive({
  status: '',
  institution: '',
  keyword: '',
  date_from: '',
  date_to: '',
})

const tableKey = ref(1)

const LOCAL_STORAGE_KEY = 'ppap_history_table_columns_order_v1'

const defaultColumns = [
  { prop: 'uploaded_at', label: t('file.uploadedAt'), width: 200 },
  { prop: 'original_filename', label: t('file.filename'), minWidth: 250, showOverflowTooltip: true },
  { prop: 'file_type', label: t('file.fileType'), width: 120, showOverflowTooltip: true },
  { prop: 'institution', label: t('history.institutionLabel'), minWidth: 120, showOverflowTooltip: true },
  { prop: 'page_count', label: t('file.pageCount'), width: 60, align: 'center' },
  { prop: 'status', label: t('history.verifyStatusLabel'), width: 110 },
  { prop: 'pass_rate', label: t('history.passRateLabel'), width: 150 },
]

const loadColumns = () => {
  const saved = localStorage.getItem(LOCAL_STORAGE_KEY)
  if (saved) {
    try {
      const parsedProps = JSON.parse(saved)
      const ordered = parsedProps.map((prop: string) => defaultColumns.find(c => c.prop === prop)).filter(Boolean)
      const missing = defaultColumns.filter(c => !parsedProps.includes(c.prop))
      return [...ordered, ...missing]
    } catch {
      return [...defaultColumns]
    }
  }
  return [...defaultColumns]
}

const tableColumns = ref(loadColumns())

const initSortable = () => {
  const el = document.querySelector('.table-wrapper-card .el-table__header-wrapper tr')
  if (!el) return

  Sortable.create(el as HTMLElement, {
    animation: 150,
    delay: 0,
    onEnd: (evt) => {
      const oldIndex = (evt.oldIndex as number) - 1
      const newIndex = (evt.newIndex as number) - 1

      if (oldIndex < 0 || newIndex < 0) return
      if (oldIndex >= tableColumns.value.length || newIndex >= tableColumns.value.length) return

      const targetRow = tableColumns.value.splice(oldIndex, 1)[0]
      tableColumns.value.splice(newIndex, 0, targetRow)
      
      // Persist the new order
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(tableColumns.value.map(c => c.prop)))
      
      tableKey.value++
      nextTick(() => {
        initSortable()
      })
    }
  })
}

const trajectoryDrawerVisible = ref(false)
const currentTrajectoryFile = ref<any>(null)

const executionLogs = computed(() => {
  if (!currentTrajectoryFile.value || !currentTrajectoryFile.value.verification_result_json) return []
  
  let logs: any[] = []
  const v = currentTrajectoryFile.value.verification_result_json
  
  if (v.execution_trajectory && Array.isArray(v.execution_trajectory)) {
    v.execution_trajectory.forEach((traj: any, index: number) => {
      logs.push({
        operator: t('history.engineFlow'),
        message: traj.message,
        timestamp: traj.time || traj.timestamp,
        status: 'success',
        _order: index
      })
    })
  }
  
  const opLogs = v.operator_logs || {}
  let opIndex = 1000
  Object.entries(opLogs).forEach(([operator, data]: [string, any]) => {
    logs.push({
      operator: operator,
      message: data.message,
      extracted_data: data.extracted_data,
      status: data.pass_status === false ? 'error' : 'success',
      timestamp: currentTrajectoryFile.value?.completed_at,
      _order: opIndex++
    })
  })
  
  logs.sort((a, b) => {
    const timeA = new Date(a.timestamp || 0).getTime()
    const timeB = new Date(b.timestamp || 0).getTime()
    if (timeA === timeB) {
      return (a._order || 0) - (b._order || 0)
    }
    return timeA - timeB
  })
  
  return logs
})

const hasActiveFilters = computed(() => {
  return !!(filters.status || filters.institution || filters.keyword || filters.date_from || filters.date_to)
})

const pagination = reactive({
  page: 1,
  page_size: 10,
  total: 0,
})

function formatDateTime(isoString: string): string {
  if (!isoString) return '--'
  try {
    const d = new Date(isoString)
    return d.toLocaleString(getLocale() === 'zh-CN' ? 'zh-CN' : 'en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).replace(/\//g, '-')
  } catch {
    return isoString
  }
}

function statusText(status: string): string {
  const map: Record<string, string> = {
    pending: t('history.statusPending'),
    processing: t('task.diagnosing'),
    completed: t('task.compliant'),
    failed: t('task.notQualified'),
    warning: t('task.hasWarning'),
    needs_review: t('status.needsReview'),
  }
  return map[status] || status
}

function getFileTypeText(type: string): string {
  const map: Record<string, string> = {
    production_plan: t('file.production_plan'),
    quality_report: t('file.quality_report'),
    purchase_order: t('file.purchase_order'),
    supplier_qualification: t('file.supplier_qualification'),
    product_specification: t('file.product_specification'),
    other: t('file.other'),
  }
  return map[type] || t('history.unknownFileType')
}

function getFileTypeTag(type: string): string {
  const map: Record<string, string> = {
    production_plan: 'success',
    quality_report: 'warning',
    purchase_order: 'primary',
    supplier_qualification: 'info',
    product_specification: 'danger',
  }
  return map[type] || 'info'
}

function getProgressStatus(status: string): string {
  if (status === 'completed') return 'success'
  if (status === 'warning') return 'warning'
  if (status === 'failed') return 'exception'
  return ''
}

function getPassRateClass(rate: number | null): string {
  if (rate === null) return 'text-secondary'
  if (rate >= 90) return 'text-success'
  if (rate >= 60) return 'text-warning'
  return 'text-danger'
}

function getInstitution(row: any): string {
  const vr = row.verification_result_json
  if (!vr || !vr.operator_logs || !vr.operator_logs.InstitutionSniffer) {
    return '--'
  }
  return vr.operator_logs.InstitutionSniffer.extracted_data?.institution || '--'
}

function handleDateRangeChange(val: [string, string] | null) {
  if (val && val.length === 2) {
    filters.date_from = `${val[0]}T00:00:00`
    filters.date_to = `${val[1]}T23:59:59`
  } else {
    filters.date_from = ''
    filters.date_to = ''
  }
  handleSearch()
}

async function fetchData() {
  loading.value = true
  try {
    const params = {
      status: filters.status || undefined,
      institution: filters.institution || undefined,
      keyword: filters.keyword || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      page: pagination.page,
      page_size: pagination.page_size,
    }
    const response = await filesApi.list(params)
    tableData.value = response.items || []
    pagination.total = response.total || 0
  } catch (err: unknown) {
    console.error('Failed to fetch historical files:', err)
    ElMessage.error(getErrorMessage(err, t('history.fetchFailed')))
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchData()
}

function handleReset() {
  Object.assign(filters, {
    status: '',
    institution: '',
    keyword: '',
    date_from: '',
    date_to: '',
  })
  dateRange.value = null
  handleSearch()
}

function handleSizeChange(size: number) {
  pagination.page_size = size
  pagination.page = 1
  fetchData()
}

function handleCurrentChange(page: number) {
  pagination.page = page
  fetchData()
}

function handleSelectionChange(selection: any[]) {
  selectedRows.value = selection
}

function handleView(row: { id: string }) {
  router.push(`/files/${row.id}`)
}

function handleViewTrajectory(row: any) {
  currentTrajectoryFile.value = row
  trajectoryDrawerVisible.value = true
}

async function handleDownload(row: { id: string; original_filename: string }) {
  try {
    const res = await filesApi.getDownloadUrl(row.id)
    if (res && res.download_url) {
      window.open(res.download_url, '_blank')
      ElMessage.success(t('history.downloadStarted', { name: row.original_filename }))
    } else {
      throw new Error(t('history.downloadUrlInvalid'))
    }
  } catch (err: unknown) {
    console.error('Failed to get download URL:', err)
    ElMessage.error(getErrorMessage(err, t('history.downloadUrlFailed')))
  }
}

async function handleReverify(row: { id: string; original_filename: string }) {
  try {
    await ElMessageBox.confirm(
      t('history.reverifyConfirmMessage', { name: row.original_filename }),
      t('history.reverifyConfirmTitle'),
      {
        confirmButtonText: t('history.reverifyConfirmButton'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      }
    )
    
    await filesApi.reverify(row.id)
    ElMessage.success(t('history.reverifySuccess'))
    fetchData() // Refresh list
  } catch {
    // cancelled or failed
  }
}

async function handleBatchDownload() {
  if (selectedRows.value.length === 0) return
  ElMessage.info(t('history.batchDownloadPreparing', { count: selectedRows.value.length }))
  
  let successCount = 0
  for (const row of selectedRows.value) {
    try {
      const res = await filesApi.getDownloadUrl(row.id)
      if (res && res.download_url) {
        const a = document.createElement('a')
        a.href = res.download_url
        a.download = row.original_filename
        a.style.display = 'none'
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        successCount++
      }
      await new Promise(resolve => setTimeout(resolve, 300))
    } catch {
      // Continue next
    }
  }
  ElMessage.success(t('history.batchDownloadSuccess', { count: successCount }))
}

async function handleDelete(row: { id: string; original_filename: string }) {
  try {
    await ElMessageBox.confirm(
      t('history.deleteConfirmMessage', { name: row.original_filename }),
      t('history.deleteConfirmTitle'),
      {
        confirmButtonText: t('history.deleteConfirmButton'),
        cancelButtonText: t('common.cancel'),
        confirmButtonClass: 'el-button--danger',
        type: 'warning',
      }
    )
    await filesApi.delete(row.id)
    ElMessage.success(t('history.deleteSuccess'))
    fetchData()
  } catch {
    // cancelled
  }
}

async function handleBatchDelete() {
  if (selectedRows.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      t('history.batchDeleteConfirmMessage', { count: selectedRows.value.length }),
      t('history.batchDeleteConfirmTitle'),
      {
        confirmButtonText: t('history.batchDeleteConfirmButton'),
        cancelButtonText: t('common.cancel'),
        confirmButtonClass: 'el-button--danger',
        type: 'warning',
      }
    )
    const ids = selectedRows.value.map(row => row.id)
    await filesApi.batchDelete(ids)
    ElMessage.success(t('history.batchDeleteSuccess', { count: ids.length }))
    selectedRows.value = []
    fetchData()
  } catch {
    // cancelled
  }
}

async function handleExport() {
  exporting.value = true
  try {
    const params = {
      status: filters.status || undefined,
      institution: filters.institution || undefined,
      keyword: filters.keyword || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      page: 1,
      page_size: 1000,
    }
    const response = await filesApi.list(params)
    const records = response.items || []

    if (records.length === 0) {
      ElMessage.warning(t('history.exportNoData'))
      return
    }

    // Helper to escape CSV fields
    const esc = (val: string) => `"${(val || '').replace(/"/g, '""')}"`
    const checkStatusText = (s: string) => s === 'pass' ? t('history.csvStatusPass') : (s === 'warning' ? t('history.csvStatusWarning') : (s === 'info' ? t('history.csvStatusInfo') : (s === 'fail' ? t('history.csvStatusFail') : s)))

    // Phase 1: Discover all unique check names across all records (preserve order)
    const checkNames: string[] = []
    records.forEach((row: any) => {
      const checks = row.verification_result_json?.checks || []
      checks.forEach((c: any) => {
        const name = c.name || c.rule_name || t('task.unknownCheckItem')
        if (!checkNames.includes(name)) checkNames.push(name)
      })
    })

    // Phase 2: Build CSV header
    const fixedHeaders = [t('history.csvHeaderFileId'), t('history.csvHeaderOriginalFilename'), t('history.csvHeaderUploadedAt'), t('history.csvHeaderInstitution'), t('history.csvHeaderMatchedCategory'), t('history.csvHeaderFileType'), t('history.csvHeaderPageCount'), t('history.csvHeaderStatus'), t('history.csvHeaderPassRate'), t('history.csvHeaderPassCount'), t('history.csvHeaderWarningCount'), t('history.csvHeaderFailCount'), t('history.csvHeaderRefCount'), t('history.csvHeaderDuration')]
    const dynamicHeaders: string[] = []
    checkNames.forEach(name => {
      dynamicHeaders.push(`${name}${t('history.csvStatusSuffix')}`, `${name}${t('history.csvDetailSuffix')}`)
    })
    const allHeaders = [...fixedHeaders, ...dynamicHeaders, t('history.csvHeaderManualRemark')]
    let csvContent = '\uFEFF' + allHeaders.join(',') + '\n'

    // Phase 3: Build rows
    records.forEach((row: any) => {
      const vr = row.verification_result_json
      const refCount = vr?.summary?.reference ?? 0
      const matchedCategory = vr?.summary?.matched_category || '--'
      const institutionName = getInstitution(row)
      const passRate = row.pass_rate !== null ? `${row.pass_rate}%` : '--'
      const duration = row.duration_seconds !== null ? `${row.duration_seconds}` : '--'

      // Build a lookup map for this row's checks
      const checkMap: Record<string, any> = {}
      const checks = vr?.checks || []
      checks.forEach((c: any) => {
        const name = c.name || c.rule_name || t('task.unknownCheckItem')
        checkMap[name] = c
      })

      // Dynamic check columns
      const dynamicCols: string[] = []
      checkNames.forEach(name => {
        const c = checkMap[name]
        if (c) {
          dynamicCols.push(checkStatusText(c.status || ''), esc(c.message || ''))
        } else {
          dynamicCols.push('--', '--')
        }
      })

      const fixedCols = [
        row.id,
        esc(row.original_filename || ''),
        formatDateTime(row.uploaded_at),
        esc(institutionName),
        esc(matchedCategory),
        getFileTypeText(row.file_type),
        row.page_count || 1,
        statusText(row.status),
        passRate,
        row.pass_count ?? 0,
        row.warning_count ?? 0,
        row.fail_count ?? 0,
        refCount,
        duration,
      ]

      const notes = esc(row.notes_summary || '')
      csvContent += [...fixedCols, ...dynamicCols, notes].join(',') + '\n'
    })

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const dateStr = new Date().toISOString().slice(0, 10)
    link.href = URL.createObjectURL(blob)
    link.setAttribute('download', `PPAP_audit_report_${dateStr}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success(t('history.exportSuccess', { count: records.length }))
  } catch (err) {
    console.error('Export failed:', err)
    ElMessage.error(t('history.exportFailed'))
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  fetchData()
  nextTick(() => {
    initSortable()
  })
})
</script>

<style scoped>
/* Dashboard Container & Grid Theme */
.history-dashboard-container {
  padding: 12px 4px;
}

.dashboard-title {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 6px 0;
  letter-spacing: -0.5px;
}

.dashboard-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.hero-statistics-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

/* Premium Filter Layout */
.premium-filter-form {
  padding: 8px 4px;
}

.flex-end-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.reset-button-premium {
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.search-button-premium,
.export-button-premium {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border: none;
  border-radius: 6px;
  font-weight: 500;
  box-shadow: 0 4px 10px rgba(59, 130, 246, 0.25);
  transition: all 0.2s ease;
}

.search-button-premium:hover,
.export-button-premium:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(59, 130, 246, 0.35);
  opacity: 0.95;
}

/* Glassmorphism Panel styles */
.glass-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card:hover {
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.05), 0 8px 10px -6px rgba(59, 130, 246, 0.05);
}

/* Premium Form Elements */
.premium-select :deep(.el-input__wrapper),
.premium-input :deep(.el-input__wrapper),
.premium-date-picker :deep(.el-input__wrapper) {
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: none !important;
  transition: border-color 0.2s ease;
}

.premium-select :deep(.el-input__wrapper):hover,
.premium-input :deep(.el-input__wrapper):hover,
.premium-date-picker :deep(.el-input__wrapper):hover {
  border-color: #cbd5e1;
}

.premium-select :deep(.el-input__wrapper).is-focus,
.premium-input :deep(.el-input__wrapper).is-focus,
.premium-date-picker :deep(.el-input__wrapper).is-focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
}

/* Table Style & Typo */
.premium-table {
  border-radius: 8px;
  overflow: hidden;
}

.font-mono {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
  font-size: 13px;
}

.text-secondary {
  color: #64748b;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  width: 100%;
}

.pdf-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.file-title-text {
  font-weight: 500;
  color: #1e293b;
  cursor: pointer;
  transition: color 0.15s ease;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.file-title-text:hover {
  color: #3b82f6;
  text-decoration: underline;
}

.type-tag-premium {
  border-radius: 6px;
  font-weight: 500;
}

/* Pulse indicator dot */
.status-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  position: relative;
}

.status-indicator-dot.pending { background-color: #94a3b8; }
.status-indicator-dot.processing {
  background-color: #3b82f6;
  box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
  animation: pulse 1.6s infinite;
}
.status-indicator-dot.completed { background-color: #10b981; }
.status-indicator-dot.warning { background-color: #f59e0b; }
.status-indicator-dot.failed { background-color: #ef4444; }

.status-label {
  font-size: 13px;
  font-weight: 500;
}
.status-label.pending { color: #64748b; }
.status-label.processing { color: #3b82f6; }
.status-label.completed { color: #10b981; }
.status-label.warning { color: #d97706; }
.status-label.failed { color: #ef4444; }

/* Pass rate styles */
.progress-premium-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 12px;
}

.rate-value {
  font-weight: 700;
  font-size: 14px;
}

.rate-value.text-success { color: #10b981; }
.rate-value.text-warning { color: #d97706; }
.rate-value.text-danger { color: #ef4444; }

.progress-bar-premium :deep(.el-progress-bar__inner) {
  border-radius: 4px;
  background: linear-gradient(90deg, #3b82f6 0%, #10b981 100%);
}

.progress-bar-premium :deep(.el-progress-bar__outer) {
  border-radius: 4px;
  background-color: #f1f5f9;
}

/* Action button items */
.table-actions-row {
  display: flex;
  gap: 12px;
}

.action-btn-view, .action-btn-download, .action-btn-delete {
  font-weight: 500;
  transition: all 0.15s ease;
}

.action-btn-view:hover { color: #2563eb; }
.action-btn-download:hover { color: #059669; }
.action-btn-delete:hover { color: #dc2626; }

/* Batch banner */
.batch-control-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(239, 246, 255, 0.9);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  padding: 10px 16px;
  backdrop-filter: blur(8px);
}

.pulse-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  background-color: #3b82f6;
  border-radius: 50%;
  margin-right: 8px;
  animation: pulse 1.2s infinite;
}

.selected-text {
  font-size: 13px;
  color: #1e3a8a;
}

/* Pagination container */
.pagination-footer-container {
  display: flex;
  justify-content: flex-end;
}

.premium-pagination :deep(.el-pager li.is-active) {
  background-color: #3b82f6;
  color: #fff;
  border-radius: 4px;
}

/* Collapsible Filter Header Styles */
.filter-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  user-select: none;
  padding: 4px 2px;
}

.cursor-pointer {
  cursor: pointer;
}

.filter-icon {
  font-size: 16px;
}

.filter-title-text {
  font-size: 15px;
  color: #1e293b;
  font-weight: 700;
}

.collapse-toggle-btn {
  font-weight: 500;
  font-size: 13px;
}

.arrow-icon {
  font-size: 13px;
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.arrow-icon.is-active {
  transform: rotate(180deg);
}

/* Micro-animations */
.animate-fade-in {
  animation: fadeIn 0.4s ease-out;
}

.animate-slide-down {
  animation: slideDown 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
  70% { transform: scale(1); box-shadow: 0 0 0 5px rgba(59, 130, 246, 0); }
  100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
}
</style>
