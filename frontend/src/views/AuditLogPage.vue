<template>
  <div class="audit-page">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">系统审计日志</h1>
        <p class="page-subtitle">追踪系统敏感操作，保障数据安全与溯源</p>
      </div>
      <div class="header-right">
        <el-button @click="fetchLogs" :loading="loading" :icon="Refresh">刷新</el-button>
      </div>
    </div>

    <!-- Filters -->
    <div class="filter-card">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="操作类型">
          <el-select v-model="filters.action" placeholder="全部类型" clearable class="w-200">
            <el-option label="系统登录 (LOGIN)" value="LOGIN" />
            <el-option label="新增规则 (CREATE_RULE)" value="CREATE_RULE" />
            <el-option label="修改规则 (UPDATE_RULE)" value="UPDATE_RULE" />
            <el-option label="删除规则 (DELETE_RULE)" value="DELETE_RULE" />
            <el-option label="上传文件 (UPLOAD_DOCUMENT)" value="UPLOAD_DOCUMENT" />
            <el-option label="人工审核 (RESOLVE_REVIEW)" value="RESOLVE_REVIEW" />
          </el-select>
        </el-form-item>
        <el-form-item label="资源类别">
          <el-select v-model="filters.resource_type" placeholder="全部资源" clearable class="w-150">
            <el-option label="用户系统 (SYSTEM)" value="SYSTEM" />
            <el-option label="校验规则 (RULE)" value="RULE" />
            <el-option label="业务文档 (DOCUMENT)" value="DOCUMENT" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-select v-model="filters.days" class="w-150">
            <el-option label="最近 7 天" :value="7" />
            <el-option label="最近 30 天" :value="30" />
            <el-option label="最近半年" :value="180" />
            <el-option label="不限时间" :value="3650" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchLogs">筛选</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- Table -->
    <el-card class="table-card" :body-style="{ padding: '0px' }">
      <el-table 
        v-loading="loading" 
        :data="logs" 
        style="width: 100%" 
        height="calc(100vh - 280px)"
        class="modern-table"
      >
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            <span class="mono-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="user_email" label="操作人" min-width="150">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="24" :src="`https://api.dicebear.com/7.x/identicon/svg?seed=${row.user_email || 'anonymous'}`" />
              <span>{{ row.user_email || 'System' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="action" label="动作" width="160">
          <template #default="{ row }">
            <el-tag :type="getActionTagType(row.action)" effect="light" class="mono-tag">
              {{ row.action }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="resource_type" label="资源类型" width="120">
          <template #default="{ row }">
            <span class="resource-text">{{ row.resource_type || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="resource_id" label="资源 ID" width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono-text sm-text text-gray">{{ row.resource_id || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP 地址" width="140">
          <template #default="{ row }">
            <span class="mono-text sm-text">{{ row.ip_address || '内部/未知' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetails(row)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="logs.length > 0 && logs.length === pageSize ? currentPage * pageSize + 1 : (currentPage - 1) * pageSize + logs.length"
          @size-change="fetchLogs"
          @current-change="fetchLogs"
        />
        <span class="pagination-hint" v-if="logs.length === pageSize">（总数较多，请按需翻页）</span>
      </div>
    </el-card>

    <!-- Details Dialog -->
    <el-dialog 
      v-model="detailsVisible" 
      title="日志详情" 
      width="600px" 
      custom-class="details-dialog"
      destroy-on-close
    >
      <div v-if="currentLog" class="log-details-container">
        <div class="detail-header">
          <div class="detail-icon">
            <el-icon :size="24" :color="getActionColor(currentLog.action)"><Platform /></el-icon>
          </div>
          <div class="detail-title">
            <h3>{{ currentLog.action }}</h3>
            <p>{{ formatTime(currentLog.created_at) }}</p>
          </div>
        </div>

        <el-descriptions :column="1" border class="modern-descriptions mt-4">
          <el-descriptions-item label="操作人">{{ currentLog.user_email || 'System' }}</el-descriptions-item>
          <el-descriptions-item label="资源类型">{{ currentLog.resource_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="资源 ID"><span class="mono-text">{{ currentLog.resource_id || '-' }}</span></el-descriptions-item>
          <el-descriptions-item label="来源 IP"><span class="mono-text">{{ currentLog.ip_address || '-' }}</span></el-descriptions-item>
        </el-descriptions>

        <div class="detail-section mt-4">
          <div class="section-title">
            <span>执行上下文 (Context details)</span>
          </div>
          <div class="json-viewer">
            <pre>{{ formatJson(currentLog.details) }}</pre>
          </div>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="detailsVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Refresh, Platform } from '@element-plus/icons-vue'
import { getAuditLogs, type AuditLog, type GetAuditLogsParams } from '@/api/audit'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const logs = ref<AuditLog[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(50)

const filters = ref({
  action: '',
  resource_type: '',
  days: 30
})

const detailsVisible = ref(false)
const currentLog = ref<AuditLog | null>(null)

onMounted(() => {
  fetchLogs()
})

const fetchLogs = async () => {
  loading.value = true
  try {
    const params: GetAuditLogsParams = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      days: filters.value.days
    }
    if (filters.value.action) params.action = filters.value.action
    if (filters.value.resource_type) params.resource_type = filters.value.resource_type
    
    const data = await getAuditLogs(params)
    logs.value = data || []
  } catch (error) {
    console.error('Failed to fetch audit logs:', error)
    ElMessage.error('无法加载审计日志')
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.value = {
    action: '',
    resource_type: '',
    days: 30
  }
  currentPage.value = 1
  fetchLogs()
}

const viewDetails = (log: AuditLog) => {
  currentLog.value = log
  detailsVisible.value = true
}

// Formatters
const formatTime = (isoStr: string) => {
  if (!isoStr) return '-'
  return dayjs(isoStr).format('YYYY-MM-DD HH:mm:ss')
}

const formatJson = (obj: any) => {
  if (!obj || Object.keys(obj).length === 0) return '无详细上下文参数'
  return JSON.stringify(obj, null, 2)
}

const getActionColor = (action: string) => {
  if (action.includes('CREATE') || action.includes('UPLOAD')) return '#10b981'
  if (action.includes('DELETE')) return '#ef4444'
  if (action.includes('UPDATE') || action.includes('RESOLVE')) return '#f59e0b'
  if (action.includes('LOGIN')) return '#3b82f6'
  return '#64748b'
}

const getActionTagType = (action: string) => {
  if (action.includes('CREATE') || action.includes('UPLOAD')) return 'success'
  if (action.includes('DELETE')) return 'danger'
  if (action.includes('UPDATE') || action.includes('RESOLVE')) return 'warning'
  if (action.includes('LOGIN')) return ''
  return 'info'
}
</script>

<style scoped>
.audit-page {
  padding: 24px;
  background-color: #f8fafc;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 4px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #64748b;
  margin: 0;
}

.filter-card {
  background: white;
  border-radius: 12px;
  padding: 20px 20px 2px 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  border: 1px solid #e2e8f0;
}

.w-150 { width: 150px; }
.w-200 { width: 200px; }

.table-card {
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.05), 0 2px 4px -1px rgba(15, 23, 42, 0.03);
}

.modern-table {
  --el-table-border-color: #f1f5f9;
  --el-table-header-bg-color: #f8fafc;
  --el-table-header-text-color: #475569;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #334155;
}

.mono-text {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.mono-tag {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.sm-text {
  font-size: 12px;
}

.text-gray {
  color: #94a3b8;
}

.resource-text {
  font-weight: 600;
  color: #475569;
}

.pagination-container {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  background: white;
  border-top: 1px solid #f1f5f9;
}

.pagination-hint {
  margin-left: 16px;
  font-size: 12px;
  color: #94a3b8;
}

/* Dialog Styles */
.detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.detail-icon {
  width: 48px;
  height: 48px;
  background: #f1f5f9;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.detail-title h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
  color: #0f172a;
}

.detail-title p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.mt-4 {
  margin-top: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.json-viewer {
  background: #0f172a;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
}

.json-viewer pre {
  margin: 0;
  color: #e2e8f0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.5;
}

:deep(.modern-descriptions .el-descriptions__label) {
  width: 100px;
  color: #64748b;
  font-weight: 500;
  background-color: #f8fafc;
}
</style>
