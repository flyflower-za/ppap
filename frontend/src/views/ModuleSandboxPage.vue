<template>
  <div class="sandbox-container">
    <div class="header">
      <h2>🧪 模块沙盒 (Module Sandbox)</h2>
      <p class="text-secondary">独立调试和验证底层审核模型与提取算子的效果，无需运行整个流水线。</p>
    </div>

    <el-row :gutter="24">
      <!-- 左侧：参数配置 -->
      <el-col :span="10">
        <el-card shadow="never" class="config-card premium-card">
          <template #header>
            <div class="card-header">
              <span class="font-bold">⚙️ 测试参数配置</span>
            </div>
          </template>

          <el-form :model="form" label-position="top" size="large">
            <!-- 文件源选择 -->
            <template v-if="form.operator_name !== 'URLFetchOperator'">
              <el-form-item label="测试文件来源">
                <el-radio-group v-model="form.fileSourceType" class="premium-radio-group">
                  <el-radio-button value="existing">从历史中选择</el-radio-button>
                  <el-radio-button value="upload">临时上传新文件</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </template>

            <template v-if="form.operator_name !== 'URLFetchOperator'">
              <el-form-item v-if="form.fileSourceType === 'existing'" label="选择已有文件">
                <el-select v-model="form.file_id" filterable placeholder="选择要测试的文档" style="width: 100%">
                  <el-option
                    v-for="f in historyFiles"
                    :key="f.id"
                    :label="f.original_filename"
                    :value="f.id"
                  />
                </el-select>
              </el-form-item>
            </template>

            <template v-if="form.operator_name !== 'URLFetchOperator'">
              <el-form-item v-if="form.fileSourceType === 'upload'" label="上传测试文件">
                <el-upload
                  class="upload-demo"
                  drag
                  action="#"
                  :auto-upload="false"
                  :show-file-list="true"
                  :limit="1"
                  :on-change="handleFileChange"
                  :on-remove="handleFileRemove"
                >
                  <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                  <div class="el-upload__text">拖拽文件到这里或 <em>点击上传</em></div>
                </el-upload>
              </el-form-item>
            </template>

            <!-- 模块选择 -->
            <el-form-item label="目标测试模块">
              <el-select v-model="form.operator_name" placeholder="请选择底层模块" @change="handleModuleChange" style="width: 100%">
                <el-option
                  v-for="mod in availableModules"
                  :key="mod.name"
                  :label="mod.label"
                  :value="mod.name"
                >
                  <span style="float: left">{{ mod.label }}</span>
                  <span style="float: right; color: #8492a6; font-size: 13px">{{ mod.name }}</span>
                </el-option>
              </el-select>
              <div v-if="selectedModuleDesc" class="module-desc text-secondary mt-1 text-sm">
                {{ selectedModuleDesc }}
              </div>
            </el-form-item>

            <!-- 动态参数表单 -->
            <div v-if="selectedModuleParams.length > 0" class="dynamic-params-container p-4 bg-gray-50 rounded-lg border">
              <h4 class="mb-4 mt-0 text-sm font-bold text-gray-700">模块参数</h4>
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
                  :placeholder="'默认: ' + param.default"
                />
                <el-input-number
                  v-else-if="param.type === 'number'"
                  v-model="form.params[param.key]"
                />
                <el-input
                  v-else
                  v-model="form.params[param.key]"
                  :placeholder="'默认: ' + param.default"
                />
              </el-form-item>
              
              <!-- 显式注入底座模型选择 (Open Question 2) -->
              <el-form-item v-if="form.operator_name.includes('LLM')" label="底层 AI 模型 (Base Model)">
                <el-select v-model="form.params.model" placeholder="默认模型" style="width: 100%">
                  <el-option label="默认配置 (Configured Default)" value="" />
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
                🚀 立即执行测试
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
              <span class="font-bold">📊 执行结果与诊断数据</span>
            </div>
          </template>

          <div v-if="!resultData && !testing" class="empty-state text-center mt-20">
            <el-empty description="尚未执行，请在左侧配置参数并点击开始测试" />
          </div>

          <div v-else-if="testing" class="loading-state text-center mt-20">
            <el-skeleton :rows="10" animated />
            <p class="text-secondary mt-4">模块正在全力计算中，大模型视觉推理可能需要 10-30 秒...</p>
          </div>

          <div v-else class="result-display">
            <!-- 概要结果卡片 -->
            <div class="summary-box p-4 mb-4 rounded-lg border" :class="resultData.status === 'success' ? (resultData.pass_status ? 'bg-success-light border-success' : 'bg-danger-light border-danger') : 'bg-gray-100 border-gray-300'">
              <div class="flex justify-between items-center">
                <div>
                  <h3 class="mt-0 mb-2">执行状态：
                    <el-tag :type="resultData.status === 'success' ? 'success' : 'danger'" size="large">
                      {{ resultData.status === 'success' ? '调用成功' : '系统异常' }}
                    </el-tag>
                  </h3>
                  <div v-if="resultData.status === 'success'" class="text-lg font-bold" :class="resultData.pass_status ? 'text-green-600' : 'text-red-600'">
                    逻辑判定：{{ resultData.pass_status ? '✅ 校验通过' : '❌ 校验不合格' }}
                  </div>
                </div>
                <div class="text-right text-sm text-secondary">
                  <div>模块: {{ resultData.operator }}</div>
                </div>
              </div>
              <div class="mt-4 p-3 bg-white rounded border shadow-sm">
                <strong>💡 诊断结论 (Reason)：</strong><br/>
                <span class="text-gray-700">{{ resultData.message || '--' }}</span>
              </div>
            </div>

            <!-- 数据提取可视化 -->
            <h4>🧩 提取到的结构化数据 (Extracted Data)</h4>
            <el-card shadow="none" class="bg-gray-900 text-gray-100 border-0 font-mono text-sm">
              <pre style="margin: 0; white-space: pre-wrap;">{{ JSON.stringify(resultData.extracted_data, null, 2) || '{}' }}</pre>
            </el-card>

            <!-- 运行时上下文数据 -->
            <h4 class="mt-6">🗃️ 运行时共享上下文 (Shared State)</h4>
            <el-collapse class="mt-2">
              <el-collapse-item title="点击展开查看执行上下文变量">
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
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { filesApi } from '@/api/files'
import { modulesApi } from '@/api/modules'
import { settingsApi, ModelProfile } from '@/api/settings'

const historyFiles = ref<any[]>([])
const availableModules = ref<any[]>([])
const aiModelProfiles = ref<ModelProfile[]>([])

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
    const profileRes = await settingsApi.listModelProfiles()
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
      ElMessage.success('测试执行完成')
    } else {
      ElMessage.error(`执行失败: ${res.message}`)
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || e.message || '网络或接口请求错误')
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
.premium-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
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
</style>
