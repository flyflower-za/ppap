<template>
  <div class="history-dashboard-container animate-fade-in">
    <!-- Header Hero Banner with Statistics -->
    <div class="hero-statistics-row mb-6">
      <div class="hero-left">
        <h2 class="dashboard-title">合规历史审计中心</h2>
        <p class="dashboard-subtitle">实时审计并追溯所有历史上传 PDF 的文本层、印章签名及二维码追溯结果</p>
      </div>
      <div class="hero-right">
        <el-button 
          type="primary" 
          class="export-button-premium"
          :icon="Download" 
          @click="handleExport"
          :loading="exporting"
        >
          导出 Excel 审计报表
        </el-button>
      </div>
    </div>

    <!-- Collapsible Filter Control Center -->
    <el-card class="glass-card control-filter-card mb-6" shadow="hover">
      <div class="filter-card-header flex-between cursor-pointer" @click="isCollapsed = !isCollapsed">
        <div class="header-left flex-align-center">
          <span class="filter-icon">🔍</span>
          <span class="filter-title-text font-bold ml-2">数据条件筛选</span>
          <el-tag v-if="hasActiveFilters" size="small" type="warning" class="active-filter-tag ml-3">
            已启用筛选条件
          </el-tag>
        </div>
        <div class="header-right">
          <el-button link type="primary" class="collapse-toggle-btn">
            {{ isCollapsed ? '展开筛选面板' : '收起筛选面板' }}
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
                <el-form-item label="校验状态">
                  <el-select 
                    v-model="filters.status" 
                    placeholder="全部状态" 
                    clearable 
                    class="premium-select"
                    @change="handleSearch"
                  >
                    <el-option label="等待中" value="pending" />
                    <el-option label="校验中" value="processing" />
                    <el-option label="已通过 (合规)" value="completed" />
                    <el-option label="有警告 (含风险)" value="warning" />
                    <el-option label="校验失败 (不合格)" value="failed" />
                  </el-select>
                </el-form-item>
              </el-col>

              <el-col :xs="24" :sm="8" :md="5">
                <el-form-item label="文件类型">
                  <el-select 
                    v-model="filters.file_type" 
                    placeholder="全部类型" 
                    clearable 
                    class="premium-select"
                    @change="handleSearch"
                  >
                    <el-option label="生产计划单" value="production_plan" />
                    <el-option label="质量检测报告" value="quality_report" />
                    <el-option label="采购订单" value="purchase_order" />
                    <el-option label="供应商资质" value="supplier_qualification" />
                    <el-option label="产品规格书" value="product_specification" />
                    <el-option label="常规合规文件" value="other" />
                  </el-select>
                </el-form-item>
              </el-col>

              <el-col :xs="24" :sm="8" :md="6">
                <el-form-item label="模糊匹配">
                  <el-input 
                    v-model="filters.keyword" 
                    placeholder="输入文件名关键词..." 
                    clearable
                    class="premium-input"
                    @keyup.enter="handleSearch"
                  />
                </el-form-item>
              </el-col>

              <el-col :xs="24" :sm="24" :md="8">
                <el-form-item label="上传时间范围">
                  <el-date-picker
                    v-model="dateRange"
                    type="daterange"
                    range-separator="至"
                    start-placeholder="开始日期"
                    end-placeholder="结束日期"
                    value-format="YYYY-MM-DD"
                    class="premium-date-picker"
                    @change="handleDateRangeChange"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            
            <div class="flex-end-buttons mt-2">
              <el-button class="reset-button-premium" @click="handleReset">重置筛选</el-button>
              <el-button type="primary" class="search-button-premium" @click="handleSearch">执行筛选</el-button>
            </div>
          </el-form>
        </div>
      </el-collapse-transition>
    </el-card>


    <!-- Batch Control Toolbar -->
    <div v-if="selectedRows.length > 0" class="batch-control-banner mb-4 animate-slide-down">
      <div class="batch-left">
        <span class="pulse-dot"></span>
        <span class="selected-text">已选中 <strong>{{ selectedRows.length }}</strong> 项历史合规记录</span>
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
            批量下载 PDF
          </el-button>
          <el-button 
            size="small" 
            type="danger" 
            :icon="Delete" 
            @click="handleBatchDelete"
          >
            批量删除记录
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
        class="premium-table"
        stripe
      >
        <el-table-column type="selection" width="55" reserve-selection />
        
        <el-table-column prop="uploaded_at" label="上传时间" width="170">
          <template #default="{ row }">
            <span class="font-mono text-secondary">{{ formatDateTime(row.uploaded_at) }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="original_filename" label="文件名" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="file-name-cell">
              <span class="pdf-icon">📄</span>
              <span class="file-title-text" @click="handleView(row)">{{ row.original_filename }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="file_type" label="文件类型" width="130">
          <template #default="{ row }">
            <el-tag :type="getFileTypeTag(row.file_type)" effect="plain" class="type-tag-premium">
              {{ getFileTypeText(row.file_type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="page_count" label="页数" width="70" align="center">
          <template #default="{ row }">
            <span class="font-mono">{{ row.page_count || 1 }} 页</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="校验状态" width="120">
          <template #default="{ row }">
            <div class="status-wrapper">
              <span class="status-indicator-dot" :class="row.status"></span>
              <span class="status-label" :class="row.status">{{ statusText(row.status) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="pass_rate" label="指标通过率" width="180">
          <template #default="{ row }">
            <div v-if="row.status !== 'pending' && row.status !== 'processing'" class="progress-premium-container">
              <div class="progress-header font-mono">
                <span class="rate-value" :class="getPassRateClass(row.pass_rate)">{{ row.pass_rate }}%</span>
                <span class="fraction text-secondary">{{ row.pass_count }}/{{ row.pass_count + row.warning_count + row.fail_count }} 项</span>
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
              {{ row.status === 'processing' ? '正在诊断中...' : '等待诊断队列...' }}
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="duration_seconds" label="核对耗时" width="90" align="center">
          <template #default="{ row }">
            <span class="font-mono text-secondary">{{ row.duration_seconds ? `${row.duration_seconds} 秒` : '--' }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="table-actions-row">
              <el-button link type="primary" size="small" class="action-btn-view" @click="handleView(row)">
                查看详情
              </el-button>
              <el-button 
                link 
                type="primary" 
                size="small" 
                class="action-btn-download" 
                @click="handleDownload(row)"
                :disabled="row.status === 'pending' || row.status === 'processing'"
              >
                下载报告
              </el-button>
              <el-button link type="danger" size="small" class="action-btn-delete" @click="handleDelete(row)">
                删除
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Delete, ArrowDown } from '@element-plus/icons-vue'
import { filesApi } from '@/api/files'

const router = useRouter()

const loading = ref(false)
const exporting = ref(false)
const tableData = ref<any[]>([])
const selectedRows = ref<any[]>([])
const dateRange = ref<[string, string] | null>(null)
const isCollapsed = ref(true) // Collapsed by default

const filters = reactive({
  status: '',
  file_type: '',
  keyword: '',
  date_from: '',
  date_to: '',
})

const hasActiveFilters = computed(() => {
  return !!(filters.status || filters.file_type || filters.keyword || filters.date_from || filters.date_to)
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
    return d.toLocaleString('zh-CN', {
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
    pending: '等待中',
    processing: '诊断中',
    completed: '合规通过',
    failed: '不合格',
    warning: '有风险警告',
  }
  return map[status] || status
}

function getFileTypeText(type: string): string {
  const map: Record<string, string> = {
    production_plan: '生产计划单',
    quality_report: '质量检测报告',
    purchase_order: '采购订单',
    supplier_qualification: '供应商资质',
    product_specification: '产品规格书',
    other: '常规合规文件',
  }
  return map[type] || '未定类型'
}

function getFileTypeTag(type: string): string {
  const map: Record<string, string> = {
    production_plan: 'success',
    quality_report: 'warning',
    purchase_order: 'primary',
    supplier_qualification: 'info',
    product_specification: 'danger',
  }
  return map[type] || ''
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
      file_type: filters.file_type || undefined,
      keyword: filters.keyword || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      page: pagination.page,
      page_size: pagination.page_size,
    }
    const response = await filesApi.list(params)
    tableData.value = response.items || []
    pagination.total = response.total || 0
  } catch (err: any) {
    console.error('Failed to fetch historical files:', err)
    ElMessage.error(err.response?.data?.detail || '拉取历史数据失败，请重试')
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
    file_type: '',
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

async function handleDownload(row: { id: string; original_filename: string }) {
  try {
    const res = await filesApi.getDownloadUrl(row.id)
    if (res && res.download_url) {
      window.open(res.download_url, '_blank')
      ElMessage.success(`开始下载: ${row.original_filename}`)
    } else {
      throw new Error('未获取到合法的下载链接')
    }
  } catch (err: any) {
    console.error('Failed to get download URL:', err)
    ElMessage.error(err.message || '获取下载地址失败，请检查文件是否在库')
  }
}

async function handleBatchDownload() {
  if (selectedRows.value.length === 0) return
  ElMessage.info(`正在批量准备 ${selectedRows.value.length} 份报告链接...`)
  
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
  ElMessage.success(`成功触发 ${successCount} 个文件的下载`)
}

async function handleDelete(row: { id: string; original_filename: string }) {
  try {
    await ElMessageBox.confirm(
      `您确定要永久删除文件【${row.original_filename}】及全部关联诊断报告吗？此操作无法撤销。`,
      '危险删除警告',
      {
        confirmButtonText: '确定永久删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
        type: 'warning',
      }
    )
    await filesApi.delete(row.id)
    ElMessage.success('记录已安全移除')
    fetchData()
  } catch {
    // cancelled
  }
}

async function handleBatchDelete() {
  if (selectedRows.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `您确定要永久删除所选的 ${selectedRows.value.length} 项诊断记录吗？此操作将彻底删除归档，不可恢复。`,
      '批量删除危险提示',
      {
        confirmButtonText: '确定批量删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
        type: 'warning',
      }
    )
    const ids = selectedRows.value.map(row => row.id)
    await filesApi.batchDelete(ids)
    ElMessage.success(`成功删除 ${ids.length} 项记录`)
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
      file_type: filters.file_type || undefined,
      keyword: filters.keyword || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      page: 1,
      page_size: 1000,
    }
    const response = await filesApi.list(params)
    const records = response.items || []

    if (records.length === 0) {
      ElMessage.warning('当前筛选条件下无数据可供导出')
      return
    }

    let csvContent = '\uFEFF' // UTF-8 BOM for Excel compatibility
    csvContent += '文件ID,原文件名,上传时间,文件分类,页数,诊断状态,指标通过率,核对通过项,风险警告项,不合格项,核对耗时(秒),规则1-文本层检测状态,规则1-文本层检测详情,规则2-数字签名校验状态,规则2-数字签名校验详情,规则3-二维码识别状态,规则3-二维码识别详情,规则4-装订完整性校验状态,规则4-装订完整性校验详情,业务属性规则校验项,业务属性规则校验状态,业务属性规则校验详情,人工审核备注\n'
    
    records.forEach((row: any) => {
      const escapedName = `"${(row.original_filename || '').replace(/"/g, '""')}"`
      const typeText = getFileTypeText(row.file_type)
      const statusLabel = statusText(row.status)
      const passRate = row.pass_rate !== null ? `${row.pass_rate}%` : '--'
      const duration = row.duration_seconds !== null ? `${row.duration_seconds}` : '--'
      
      // Extract the 4 standardized PDF checker rules and business rules
      let textPdfStatus = '未检测'
      let textPdfMsg = '未检测'
      let signatureStatus = '未检测'
      let signatureMsg = '未检测'
      let qrCodeStatus = '未检测'
      let qrCodeMsg = '未检测'
      let bindingStatus = '未检测'
      let bindingMsg = '未检测'

      let businessCheckName = '无'
      let businessCheckStatus = '无'
      let businessCheckMsg = '无此分类下的业务指标核对规则'

      const vr = row.verification_result_json
      if (vr && vr.checks) {
        const c1 = vr.checks.find((c: any) => c.name.includes('文本'))
        if (c1) {
          textPdfStatus = c1.status === 'pass' ? '通过' : (c1.status === 'warning' ? '警告' : '不合格')
          textPdfMsg = c1.message || ''
        }

        const c2 = vr.checks.find((c: any) => c.name.includes('签名'))
        if (c2) {
          signatureStatus = c2.status === 'pass' ? '通过' : (c2.status === 'warning' ? '警告' : '不合格')
          signatureMsg = c2.message || ''
        }

        const c3 = vr.checks.find((c: any) => c.name.includes('二维码') || c.name.includes('QR'))
        if (c3) {
          qrCodeStatus = c3.status === 'pass' ? '通过' : (c3.status === 'warning' ? '警告' : '不合格')
          qrCodeMsg = c3.message || ''
        }

        const c4 = vr.checks.find((c: any) => c.name.includes('完整性') || c.name.includes('装订'))
        if (c4) {
          bindingStatus = c4.status === 'pass' ? '通过' : (c4.status === 'warning' ? '警告' : '不合格')
          bindingMsg = c4.message || ''
        }

        // Find simulated business rule
        const standardNames = ['文本', '签名', '二维码', 'QR', '完整性', '装订']
        const bus = vr.checks.find((c: any) => {
          return !standardNames.some((name: string) => c.name.includes(name))
        })
        if (bus) {
          businessCheckName = bus.name || ''
          businessCheckStatus = bus.status === 'pass' ? '通过' : (bus.status === 'warning' ? '警告' : '不合格')
          businessCheckMsg = bus.message || ''
        }
      }

      const escapedNotes = `"${(row.notes_summary || '').replace(/"/g, '""')}"`
      const escapedTextPdfStatus = `"${textPdfStatus.replace(/"/g, '""')}"`
      const escapedTextPdfMsg = `"${textPdfMsg.replace(/"/g, '""')}"`
      const escapedSignatureStatus = `"${signatureStatus.replace(/"/g, '""')}"`
      const escapedSignatureMsg = `"${signatureMsg.replace(/"/g, '""')}"`
      const escapedQrCodeStatus = `"${qrCodeStatus.replace(/"/g, '""')}"`
      const escapedQrCodeMsg = `"${qrCodeMsg.replace(/"/g, '""')}"`
      const escapedBindingStatus = `"${bindingStatus.replace(/"/g, '""')}"`
      const escapedBindingMsg = `"${bindingMsg.replace(/"/g, '""')}"`
      const escapedBusinessCheckName = `"${businessCheckName.replace(/"/g, '""')}"`
      const escapedBusinessCheckStatus = `"${businessCheckStatus.replace(/"/g, '""')}"`
      const escapedBusinessCheckMsg = `"${businessCheckMsg.replace(/"/g, '""')}"`
      
      csvContent += `${row.id},${escapedName},${formatDateTime(row.uploaded_at)},${typeText},${row.page_count || 1},${statusLabel},${passRate},${row.pass_count},${row.warning_count},${row.fail_count},${duration},${escapedTextPdfStatus},${escapedTextPdfMsg},${escapedSignatureStatus},${escapedSignatureMsg},${escapedQrCodeStatus},${escapedQrCodeMsg},${escapedBindingStatus},${escapedBindingMsg},${escapedBusinessCheckName},${escapedBusinessCheckStatus},${escapedBusinessCheckMsg},${escapedNotes}\n`
    })

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const dateStr = new Date().toISOString().slice(0, 10)
    link.href = URL.createObjectURL(blob)
    link.setAttribute('download', `PPAP_合规诊断审计报表_${dateStr}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    ElMessage.success(`成功导出 ${records.length} 条审计记录！`)
  } catch (err) {
    console.error('Export failed:', err)
    ElMessage.error('报表导出失败，请重试')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  fetchData()
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
}

.pdf-icon {
  font-size: 16px;
}

.file-title-text {
  font-weight: 500;
  color: #1e293b;
  cursor: pointer;
  transition: color 0.15s ease;
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
