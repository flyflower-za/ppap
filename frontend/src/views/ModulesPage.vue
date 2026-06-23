<template>
  <div class="modules-page">
    <div class="page-header flex-between">
      <div>
        <h2 class="page-title">校验模块管理</h2>
        <p class="page-subtitle">管理文档校验模块，作为简化版的规则配置方案</p>
      </div>
      <div class="header-actions">
        <el-button type="info" plain @click="handleRestoreDefaults" :loading="restoring">
          <el-icon><Refresh /></el-icon> 恢复默认模块
        </el-button>
        <el-button type="primary" @click="openModuleDialog()">
          <el-icon><Plus /></el-icon> 新建模块
        </el-button>
      </div>
    </div>

    <!-- 模块类型筛选 -->
    <el-card class="filter-card" shadow="hover">
      <el-row :gutter="20" align="middle">
        <el-col :span="8">
          <el-select v-model="filters.module_type" placeholder="筛选模块类型" clearable @change="loadModules">
            <el-option label="全部类型" value="" />
            <el-option v-for="(meta, key) in moduleMetadata" :key="key" :label="meta.label" :value="key" />
          </el-select>
        </el-col>
        <el-col :span="8">
          <el-select v-model="filters.severity" placeholder="筛选严重级别" clearable @change="loadModules">
            <el-option label="全部级别" value="" />
            <el-option label="关键" value="critical" />
            <el-option label="告警" value="warning" />
            <el-option label="信息" value="info" />
          </el-select>
        </el-col>
        <el-col :span="8">
          <el-select v-model="filters.is_active" placeholder="筛选状态" clearable @change="loadModules">
            <el-option label="全部状态" value="" />
            <el-option label="已启用" :value="true" />
            <el-option label="已禁用" :value="false" />
          </el-select>
        </el-col>
      </el-row>
    </el-card>

    <!-- 模块列表 -->
    <el-card class="modules-list-card" shadow="hover" v-loading="loading">
      <el-table :data="modules" style="width: 100%">
        <el-table-column label="模块信息" min-width="200">
          <template #default="scope">
            <div class="module-info">
              <span class="module-icon">{{ scope.row.metadata?.icon || '📦' }}</span>
              <div class="module-text">
                <div class="module-name">{{ scope.row.name }}</div>
                <div class="module-desc">{{ scope.row.description || scope.row.metadata?.description }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="module_type" label="类型" width="150">
          <template #default="scope">
            <el-tag size="small" type="info">{{ scope.row.metadata?.label || scope.row.module_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="严重级别" width="100">
          <template #default="scope">
            <el-tag
              :type="scope.row.severity === 'critical' ? 'danger' : scope.row.severity === 'warning' ? 'warning' : 'info'"
              size="small"
            >
              {{ scope.row.severity === 'critical' ? '关键' : scope.row.severity === 'warning' ? '告警' : '信息' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="scope">
            <el-switch
              v-model="scope.row.is_active"
              @change="handleToggleActive(scope.row)"
              :disabled="scope.row.is_system"
            />
          </template>
        </el-table-column>
        <el-table-column prop="is_system" label="系统模块" width="90">
          <template #default="scope">
            <el-tag v-if="scope.row.is_system" size="small" type="success" effect="plain">系统</el-tag>
            <span v-else class="text-placeholder">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button link type="primary" size="small" @click="openModuleDialog(scope.row)">编辑</el-button>
            <el-button
              link
              type="danger"
              size="small"
              @click="handleDelete(scope.row)"
              :disabled="scope.row.is_system"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 模块编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建校验模块' : '编辑校验模块'"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="120px">
        <el-form-item label="模块名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入模块名称" maxlength="100" show-word-limit />
        </el-form-item>

        <el-form-item label="模块类型" prop="module_type">
          <el-select v-model="form.module_type" placeholder="选择模块类型" :disabled="dialogMode === 'edit'">
            <el-option
              v-for="(meta, key) in moduleMetadata"
              :key="key"
              :label="`${meta.icon} ${meta.label}`"
              :value="key"
            >
              <div style="display: flex; align-items: center; gap: 8px;">
                <span>{{ meta.icon }}</span>
                <span>{{ meta.label }}</span>
                <span style="color: var(--el-text-color-secondary); font-size: 12px;">{{ meta.description }}</span>
              </div>
            </el-option>
          </el-select>
          <div v-if="selectedModuleMeta" class="form-tip">
            {{ selectedModuleMeta.description }}
          </div>
        </el-form-item>

        <el-form-item label="严重级别" prop="severity">
          <el-radio-group v-model="form.severity">
            <el-radio-button value="critical">
              <el-icon><WarningFilled /></el-icon> 关键
            </el-radio-button>
            <el-radio-button value="warning">
              <el-icon><Warning /></el-icon> 告警
            </el-radio-button>
            <el-radio-button value="info">
              <el-icon><InfoFilled /></el-icon> 信息
            </el-radio-button>
          </el-radio-group>
          <div class="form-tip">
            关键：失败会导致验证不通过 | 告警：警告但不阻止通过 | 信息：仅作记录
          </div>
        </el-form-item>

        <el-form-item label="模块描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="请输入模块描述"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <!-- 动态配置表单 -->
        <el-divider content-position="left">模块配置</el-divider>
        <template v-if="selectedModuleMeta?.config_fields">
          <el-form-item
            v-for="field in selectedModuleMeta.config_fields"
            :key="field.key"
            :label="field.label"
          >
            <!-- 文本输入 -->
            <el-input
              v-if="field.type === 'text'"
              v-model="form.config[field.key]"
              :placeholder="`默认值: ${field.default ?? '空'}`"
            />
            <!-- 多行文本 -->
            <el-input
              v-else-if="field.type === 'textarea'"
              v-model="form.config[field.key]"
              type="textarea"
              :rows="3"
              :placeholder="`默认值: ${field.default ?? '空'}`"
            />
            <!-- 数字输入 -->
            <el-input-number
              v-else-if="field.type === 'number'"
              v-model="form.config[field.key]"
              :placeholder="field.default"
              :min="-99999"
              :max="99999"
            />
            <!-- 布尔值 -->
            <el-switch
              v-else-if="field.type === 'boolean'"
              v-model="form.config[field.key]"
            />
            <!-- 下拉选择 -->
            <el-select
              v-else-if="field.type === 'select'"
              v-model="form.config[field.key]"
            >
              <el-option
                v-for="opt in field.options"
                :key="opt"
                :label="opt"
                :value="opt"
              />
            </el-select>
          </el-form-item>
        </template>
        <div v-else class="no-config">
          该模块类型无需额外配置
        </div>

        <el-form-item label="排序顺序">
          <el-input-number v-model="form.sort_order" :min="0" :max="999" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh, WarningFilled, Warning, InfoFilled } from '@element-plus/icons-vue'
import { verificationModulesApi, type VerificationModule, type VerificationModuleCreate, type ModuleMetadata } from '@/api/verificationModules'

// 数据
const modules = ref<VerificationModule[]>([])
const moduleMetadata = ref<ModuleMetadata['module_types']>({})
const loading = ref(false)
const restoring = ref(false)

// 筛选
const filters = reactive({
  module_type: '',
  severity: '',
  is_active: ''
})

// 对话框
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive<VerificationModuleCreate>({
  name: '',
  description: '',
  module_type: '',
  severity: 'warning',
  config: {},
  is_active: true,
  sort_order: 0
})

const editingModuleId = ref<string>()

// 表单规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入模块名称', trigger: 'blur' }
  ],
  module_type: [
    { required: true, message: '请选择模块类型', trigger: 'change' }
  ],
  severity: [
    { required: true, message: '请选择严重级别', trigger: 'change' }
  ]
}

// 计算属性
const selectedModuleMeta = computed(() => {
  if (!form.module_type) return null
  return moduleMetadata.value[form.module_type] || null
})

// 方法
const loadMetadata = async () => {
  try {
    const data = await verificationModulesApi.getMetadata()
    moduleMetadata.value = data.module_types
  } catch (error) {
    console.error('Failed to load module metadata:', error)
  }
}

const loadModules = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (filters.module_type) params.module_type = filters.module_type
    if (filters.severity) params.severity = filters.severity
    if (filters.is_active !== '') params.is_active = filters.is_active

    const data = await verificationModulesApi.listModules(params)
    modules.value = data
  } catch (error) {
    ElMessage.error('加载模块列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleToggleActive = async (module: VerificationModule) => {
  try {
    await verificationModulesApi.updateModule(module.id, { is_active: module.is_active })
    ElMessage.success('状态更新成功')
  } catch (error) {
    ElMessage.error('状态更新失败')
    module.is_active = !module.is_active
  }
}

const handleDelete = async (module: VerificationModule) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除模块 "${module.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await verificationModulesApi.deleteModule(module.id)
    ElMessage.success('删除成功')
    loadModules()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleRestoreDefaults = async () => {
  try {
    await ElMessageBox.confirm(
      '恢复默认模块将重置所有系统预设模块，是否继续？',
      '确认恢复',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    restoring.value = true
    await verificationModulesApi.restoreDefaults()
    ElMessage.success('默认模块恢复成功')
    loadModules()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('恢复失败')
    }
  } finally {
    restoring.value = false
  }
}

const openModuleDialog = (module?: VerificationModule) => {
  if (module) {
    dialogMode.value = 'edit'
    editingModuleId.value = module.id
    form.name = module.name
    form.description = module.description || ''
    form.module_type = module.module_type
    form.severity = module.severity
    form.config = { ...module.config }
    form.is_active = module.is_active
    form.sort_order = module.sort_order
  } else {
    dialogMode.value = 'create'
    editingModuleId.value = undefined
    form.name = ''
    form.description = ''
    form.module_type = ''
    form.severity = 'warning'
    form.config = {}
    form.is_active = true
    form.sort_order = 0
  }
  dialogVisible.value = true
}

const handleDialogClose = () => {
  formRef.value?.resetFields()
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      const data = { ...form }

      if (dialogMode.value === 'create') {
        await verificationModulesApi.createModule(data)
        ElMessage.success('创建成功')
      } else {
        await verificationModulesApi.updateModule(editingModuleId.value!, data)
        ElMessage.success('保存成功')
      }

      dialogVisible.value = false
      loadModules()
    } catch (error) {
      ElMessage.error(dialogMode.value === 'create' ? '创建失败' : '保存失败')
    } finally {
      submitting.value = false
    }
  })
}

// 生命周期
onMounted(() => {
  loadMetadata()
  loadModules()
})
</script>

<style scoped>
.modules-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.page-subtitle {
  color: var(--el-text-color-secondary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.filter-card {
  margin-bottom: 20px;
}

.modules-list-card {
  min-height: 400px;
}

.module-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.module-icon {
  font-size: 24px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.module-text {
  flex: 1;
}

.module-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.module-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.form-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.no-config {
  padding: 20px 0;
  text-align: center;
  color: var(--el-text-color-secondary);
}

.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mr-1 {
  margin-right: 4px;
}

:deep(.el-divider__text) {
  font-weight: 500;
  color: var(--el-text-color-regular);
}
</style>
