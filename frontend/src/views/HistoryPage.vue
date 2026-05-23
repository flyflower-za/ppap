<template>
  <div>
    <div class="flex-between mb-4">
      <h2>历史记录</h2>
      <el-button :icon="Download" @click="handleExport">导出 Excel</el-button>
    </div>

    <!-- Filter Bar -->
    <el-card shadow="never" class="mb-4">
      <el-form :inline="true" :model="filters">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 120px;">
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="有警告" value="warning" />
          </el-select>
        </el-form-item>

        <el-form-item label="文件类型">
          <el-select v-model="filters.file_type" placeholder="全部" clearable style="width: 140px;">
            <el-option label="生产计划单" value="production_plan" />
            <el-option label="质量检测报告" value="quality_report" />
            <el-option label="采购订单" value="purchase_order" />
            <el-option label="供应商资质" value="supplier_qualification" />
          </el-select>
        </el-form-item>

        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="输入文件名关键词" style="width: 200px;" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">筛选</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Batch Actions -->
    <div v-if="selectedRows.length > 0" class="batch-actions mb-4">
      <el-tag type="warning">已选择 {{ selectedRows.length }} 项</el-tag>
      <el-button-group style="margin-left: 12px;">
        <el-button size="small">批量下载报告</el-button>
        <el-button size="small">归档</el-button>
        <el-button size="small" type="danger" @click="handleBatchDelete">删除</el-button>
      </el-button-group>
    </div>

    <!-- Data Table -->
    <el-card shadow="never">
      <el-table
        :data="tableData"
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="uploaded_at" label="上传时间" width="180" />
        <el-table-column prop="original_filename" label="文件名" width="220" />
        <el-table-column prop="file_type" label="类型" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <span class="status-badge" :class="row.status">{{ statusText(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="verification_result" label="校验结果摘要" />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleView(row)">查看详情</el-button>
            <el-button link type="primary" size="small" @click="handleDownload(row)">下载报告</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        class="mt-4"
        @size-change="fetchData"
        @current-change="fetchData"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download } from '@element-plus/icons-vue'

const router = useRouter()

const loading = ref(false)
const tableData = ref([])
const selectedRows = ref([])

const filters = reactive({
  status: '',
  file_type: '',
  keyword: '',
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

function statusText(status: string): string {
  const map: Record<string, string> = {
    pending: '等待中',
    processing: '校验中',
    completed: '已完成',
    failed: '失败',
    warning: '有警告',
  }
  return map[status] || status
}

async function fetchData() {
  loading.value = true
  try {
    // TODO: Call API
    // const response = await filesApi.list({ ...filters, ...pagination })
    // tableData.value = response.items
    // pagination.total = response.total
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
  })
  handleSearch()
}

function handleSelectionChange(selection: unknown[]) {
  selectedRows.value = selection
}

function handleView(row: { id: string }) {
  router.push(`/files/${row.id}`)
}

function handleDownload(row: { original_filename: string }) {
  ElMessage.success(`下载 ${row.original_filename} 报告`)
}

async function handleDelete(row: { id: string; original_filename: string }) {
  try {
    await ElMessageBox.confirm(`确定要删除 ${row.original_filename} 吗？`, '确认删除', {
      type: 'warning',
    })
    ElMessage.success('删除成功')
    fetchData()
  } catch {
    // User cancelled
  }
}

async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedRows.value.length} 项吗？`, '确认删除', {
      type: 'warning',
    })
    ElMessage.success('批量删除成功')
    selectedRows.value = []
    fetchData()
  } catch {
    // User cancelled
  }
}

function handleExport() {
  ElMessage.success('正在导出 Excel，请稍候...')
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.batch-actions {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #fff3e0;
  border-radius: 4px;
}
</style>
