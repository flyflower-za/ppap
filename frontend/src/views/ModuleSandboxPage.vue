<template>
  <div class="sandbox-container">
    <div class="header">
      <h2>🧪 {{ $t('modules.sandbox.title') }}</h2>
      <p class="text-secondary">{{ $t('modules.sandbox.subtitle') }}</p>
    </div>

    <el-row :gutter="24">
      <!-- 左侧：参数配置 -->
      <el-col :span="10">
        <el-card shadow="never" class="config-card premium-card">
          <template #header>
            <div class="card-header">
              <span class="font-bold">⚙️ {{ $t('modules.sandbox.testConfig') }}</span>
            </div>
          </template>

          <el-form :model="form" label-position="top" size="large">
            <!-- 文件源选择 -->
            <template v-if="form.operator_name !== 'URLFetchOperator'">
              <el-form-item :label="$t('modules.sandbox.fileSource')">
                <el-radio-group v-model="form.fileSourceType" class="premium-radio-group">
                  <el-radio-button value="existing">{{ $t('modules.sandbox.selectFromHistory') }}</el-radio-button>
                  <el-radio-button value="upload">{{ $t('modules.sandbox.uploadNewFile') }}</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </template>

            <template v-if="form.operator_name !== 'URLFetchOperator'">
              <el-form-item v-if="form.fileSourceType === 'existing'" :label="$t('modules.sandbox.selectExistingFile')">
                <el-select v-model="form.file_id" filterable :placeholder="$t('modules.sandbox.selectDocument')" style="width: 100%" popper-class="sandbox-file-select-dropdown">
                  <el-option
                    v-for="f in historyFiles"
                    :key="f.id"
                    :label="f.original_filename"
                    :value="f.id"
                    class="file-select-option"
                  >
                    <div class="file-option-content" :title="f.original_filename">
                      {{ f.original_filename }}
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
            </template>

            <template v-if="form.operator_name !== 'URLFetchOperator'">
              <el-form-item v-if="form.fileSourceType === 'upload'" :label="$t('modules.sandbox.uploadTestFile')">
                <el-upload
                  class="upload-demo sandbox-upload"
                  drag
                  action="#"
                  :auto-upload="false"
                  :show-file-list="true"
                  :limit="1"
                  :on-change="handleFileChange"
                  :on-remove="handleFileRemove"
                >
                  <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                  <div class="el-upload__text">{{ $t('modules.sandbox.dragOrClick') }} <em>{{ $t('modules.sandbox.clickUpload') }}</em></div>
                </el-upload>
              </el-form-item>
            </template>

            <!-- 模块选择 -->
            <el-form-item :label="$t('modules.sandbox.targetModule')">
              <el-select v-model="form.operator_name" :placeholder="$t('modules.sandbox.selectModule')" @change="handleModuleChange" style="width: 100%" popper-class="sandbox-module-select-dropdown">
                <el-option
                  v-for="mod in availableModules"
                  :key="mod.name"
                  :label="mod.label"
                  :value="mod.name"
                  class="module-select-option"
                >
                  <div class="module-option-content">
                    <span class="module-label">{{ mod.label }}</span>
                    <span class="module-name">{{ mod.name }}</span>
                  </div>
                </el-option>
              </el-select>
              <div v-if="selectedModuleDesc" class="module-desc text-secondary mt-1 text-sm">
                {{ selectedModuleDesc }}
              </div>
            </el-form-item>

            <!-- 动态参数表单 -->
            <div v-if="selectedModuleParams.length > 0" class="dynamic-params-container p-4 bg-gray-50 rounded-lg border">
              <h4 class="mb-4 mt-0 text-sm font-bold text-gray-700">{{ $t('modules.sandbox.moduleParams') }}</h4>
              <el-form-item
                v-for="param in selectedModuleParams"
                :key="param.key"
                :label="param.label"
              >
                <!-- 大模型底座切换特例 -->
                <template v-if="param.key === 'model' || (form.operator_name.includes('LLM') && !selectedModuleParams.some(p => p.key === 'model'))">
                  <!-- Handled dynamically or injected below -->
                </template>

                <el-input
                  v-if="param.type === 'textarea'"
                  v-model="form.params[param.key]"
                  type="textarea"
                  :rows="3"
                  :placeholder="$t('modules.sandbox.defaultPrefix') + param.default"
                />
                <el-input-number
                  v-else-if="param.type === 'number'"
                  v-model="form.params[param.key]"
                />
                <el-input
                  v-else
                  v-model="form.params[param.key]"
                  :placeholder="$t('modules.sandbox.defaultPrefix') + param.default"
                />
              </el-form-item>

              <!-- 显式注入底座模型选择 (Open Question 2) -->
              <el-form-item v-if="form.operator_name.includes('LLM')" :label="$t('modules.sandbox.baseModel')">
                <el-select v-model="form.params.model" :placeholder="$t('modules.sandbox.defaultModel')" style="width: 100%">
                  <el-option :label="$t('modules.sandbox.configuredDefault')" value="" />
                  <el-option
                    v-for="profile in aiModelProfiles"
                    :key="profile.model_name"
                    :label="profile.name + ' (' + profile.model_name + ')'"
                    :value="profile.model_name"
                  />
                </el-select>
              </el-form-item>
            </div>

            <div class="action-bar mt-6">
              <el-button
                type="primary"
                size="large"
                :loading="testing"
                @click="runTest"
                :disabled="!canSubmit"
                style="width: 100%"
              >
                🚀 {{ $t('modules.sandbox.runTest') }}
              </el-button>
            </div>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：执行结果 -->
      <el-col :span="14">
        <el-card shadow="never" class="result-card premium-card h-full" style="min-height: 600px;">
          <template #header>
            <div class="card-header">
              <span class="font-bold">📊 {{ $t('modules.sandbox.resultTitle') }}</span>
            </div>
          </template>

          <div v-if="!resultData && !testing" class="empty-state text-center mt-20">
            <el-empty :description="$t('modules.sandbox.emptyResult')" />
          </div>

          <div v-else-if="testing" class="loading-state text-center mt-20">
            <el-skeleton :rows="10" animated />
            <p class="text-secondary mt-4">{{ $t('modules.sandbox.processing') }}</p>
          </div>

          <div v-else class="result-display">
            <!-- 概要结果卡片 -->
            <div class="summary-box p-4 mb-4 rounded-lg border" :class="resultData.status === 'success' ? (resultData.pass_status ? 'bg-success-light border-success' : 'bg-danger-light border-danger') : 'bg-gray-100 border-gray-300'">
              <div class="flex justify-between items-center">
                <div>
                  <h3 class="mt-0 mb-2">{{ $t('modules.sandbox.executionStatus') }}
                    <el-tag :type="resultData.status === 'success' ? 'success' : 'danger'" size="large">
                      {{ resultData.status === 'success' ? $t('modules.sandbox.callSuccess') : $t('modules.sandbox.systemError') }}
                    </el-tag>
                  </h3>
                  <div v-if="resultData.status === 'success'" class="text-lg font-bold" :class="resultData.pass_status ? 'text-green-600' : 'text-red-600'">
                    {{ $t('modules.sandbox.logicResult') }}{{ resultData.pass_status ? $t('modules.sandbox.passed') : $t('modules.sandbox.failed') }}
                  </div>
                </div>
                <div class="text-right text-sm text-secondary">
                  <div>{{ $t('modules.sandbox.moduleLabel') }} {{ resultData.operator }}</div>
                </div>
              </div>
              <div class="mt-4 p-3 bg-white rounded border shadow-sm">
                <strong>{{ $t('modules.sandbox.diagnosis') }}</strong><br/>
                <span class="text-gray-700">{{ resultData.message || '--' }}</span>
              </div>
            </div>

            <!-- 数据提取可视化 -->
            <h4>{{ $t('modules.sandbox.extractedData') }}</h4>
            <el-card shadow="none" class="bg-gray-900 text-gray-100 border-0 font-mono text-sm">
              <pre style="margin: 0; white-space: pre-wrap;">{{ JSON.stringify(resultData.extracted_data, null, 2) || '{}' }}</pre>
            </el-card>

            <!-- 运行时上下文数据 -->
            <h4 class="mt-6">{{ $t('modules.sandbox.sharedState') }}</h4>
            <el-collapse class="mt-2">
              <el-collapse-item :title="$t('modules.sandbox.expandContext')">
                <pre class="bg-gray-50 p-4 rounded text-xs overflow-auto">{{ JSON.stringify(resultData.shared_state, null, 2) || '{}' }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { filesApi } from '@/api/files'
import { modulesApi } from '@/api/modules'
import { settingsApi, PublicModelProfile } from '@/api/settings'
import { getErrorMessage } from '@/utils/formatters'

const { t } = useI18n()

const historyFiles = ref<any[]>([])
const availableModules = ref<any[]>([])
const aiModelProfiles = ref<PublicModelProfile[]>([])

const form = reactive({
  fileSourceType: 'existing',
  file_id: '',
  uploadFile: null as File | null,
  operator_name: '',
  params: {} as Record<string, any>
})

const testing = ref(false)
const resultData = ref<any>(null)

const selectedModuleDesc = computed(() => {
  const mod = availableModules.value.find(m => m.name === form.operator_name)
  return mod ? mod.description : ''
})

const selectedModuleParams = computed(() => {
  const mod = availableModules.value.find(m => m.name === form.operator_name)
  return mod ? mod.params : []
})

const canSubmit = computed(() => {
  if (!form.operator_name) return false
  if (form.operator_name === 'URLFetchOperator') return true
  if (form.fileSourceType === 'existing' && !form.file_id) return false
  if (form.fileSourceType === 'upload' && !form.uploadFile) return false
  return true
})

onMounted(async () => {
  try {
    const fileRes = await filesApi.list({ page: 1, page_size: 50 })
    historyFiles.value = fileRes.items || []
  } catch (e) {
    console.error('Failed to load files:', e)
  }

  try {
    const modRes = await modulesApi.listModules()
    availableModules.value = modRes.modules || []
  } catch (e) {
    console.error('Failed to load modules:', e)
  }

  try {
    // Use public endpoint for model profiles (works for non-admin users)
    const profileRes = await settingsApi.listPublicModelProfiles()
    aiModelProfiles.value = profileRes || []
  } catch (e) {
    console.error('Failed to load AI model profiles:', e)
  }
})

function handleModuleChange() {
  form.params = {}
  // Pre-fill defaults
  selectedModuleParams.value.forEach((p: any) => {
    form.params[p.key] = p.default
  })
}

function handleFileChange(uploadFile: any) {
  form.uploadFile = uploadFile.raw
}

function handleFileRemove() {
  form.uploadFile = null
}

async function runTest() {
  if (!canSubmit.value) return

  testing.value = true
  resultData.value = null

  try {
    const formData = new FormData()
    formData.append('operator_name', form.operator_name)
    formData.append('params', JSON.stringify(form.params))

    if (form.fileSourceType === 'existing') {
      formData.append('file_id', form.file_id)
    } else if (form.uploadFile) {
      formData.append('file', form.uploadFile)
    }

    const res = await modulesApi.testModule(formData)
    resultData.value = res
    if (res.status === 'success') {
      ElMessage.success(t('modules.sandbox.testComplete'))
    } else {
      ElMessage.error(t('modules.sandbox.testFailed', { message: res.message }))
    }
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, t('common.networkError')))
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.sandbox-container {
  padding: 24px;
}
.header {
  margin-bottom: 24px;
}

/* 左右卡片高度对齐 */
:deep(.el-row) {
  display: flex;
  align-items: stretch;
}

:deep(.el-col) {
  display: flex;
  flex-direction: column;
}

.premium-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.premium-card .el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.card-header {
  font-size: 16px;
  display: flex;
  align-items: center;
}
.bg-success-light { background-color: #f0f9eb; }
.border-success { border-color: #67c23a; }
.bg-danger-light { background-color: #fef0f0; }
.border-danger { border-color: #f56c6c; }

/* 文件名截断优化 */
.file-option-content {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  display: block;
}

/* 上传组件文件列表优化 */
:deep(.sandbox-upload .el-upload-list__item-name) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

/* 拖拽上传区域宽度优化 */
:deep(.sandbox-upload .el-upload-dragger) {
  width: 100% !important;
  max-width: 100% !important;
  padding: 20px !important;
  box-sizing: border-box !important;
}

:deep(.sandbox-upload .el-upload-dragger .el-icon--upload) {
  font-size: 48px !important;
  color: #409eff !important;
}

:deep(.sandbox-upload .el-upload-dragger .el-upload__text) {
  font-size: 14px !important;
  color: #606266 !important;
  margin-top: 12px !important;
}

:deep(.sandbox-upload .el-upload-dragger .el-upload__text em) {
  color: #409eff !important;
  font-style: normal !important;
}

/* 上传组件容器宽度 */
:deep(.sandbox-upload) {
  width: 100%;
}

:deep(.sandbox-upload .el-upload) {
  width: 100%;
  display: block !important;
}

/* 选择器下拉框宽度控制 */
:deep(.sandbox-file-select-dropdown .el-select-dropdown__item) {
  max-width: 400px;
}

/* 配置卡片宽度控制 */
.config-card {
  max-width: 100%;
  overflow: hidden;
}

/* 表单项宽度控制 */
:deep(.config-card .el-form-item__content) {
  max-width: 100%;
  overflow: hidden;
}

/* 模块选择器样式优化 */
.module-option-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  max-width: 400px;
}

.module-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 12px;
}

.module-name {
  color: #8492a6;
  font-size: 13px;
  flex-shrink: 0;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 模块下拉框宽度控制 */
:deep(.sandbox-module-select-dropdown .el-select-dropdown__item) {
  max-width: 450px;
}
</style>