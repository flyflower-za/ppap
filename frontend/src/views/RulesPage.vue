<template>
  <div class="rules-page">
    <div class="page-header flex-between" style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h2 class="page-title">规则配置中心</h2>
        <p class="page-subtitle">配置不同文档类型的识别规则与验证规则引擎</p>
      </div>
      <div>
        <el-button type="primary" plain @click="handleRestoreDefaults" :loading="restoringDefaults">
          <el-icon class="mr-1"><Refresh /></el-icon> 一键重置预置系统规则
        </el-button>
      </div>
    </div>

    <el-row :gutter="20" class="rules-container">
      <!-- 左侧分类列表 -->
      <el-col :span="6">
        <el-card class="category-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>文档分类</span>
              <el-button type="primary" link @click="openCategoryDialog()">
                <el-icon><Plus /></el-icon> 新增
              </el-button>
            </div>
          </template>
          
          <el-menu
            :default-active="activeCategoryId"
            class="category-menu"
            @select="handleCategorySelect"
          >
            <el-menu-item 
              v-for="cat in categories" 
              :key="cat.id" 
              :index="cat.id"
            >
              <div class="menu-item-content">
                <span>{{ cat.name }}</span>
                <el-dropdown trigger="click" @command="handleCategoryCommand($event, cat)">
                  <el-icon class="more-icon" @click.stop><MoreFilled /></el-icon>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="edit">编辑</el-dropdown-item>
                      <el-dropdown-item command="delete" class="text-danger">删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </el-menu-item>
          </el-menu>
        </el-card>
      </el-col>

      <!-- 右侧规则列表 -->
      <el-col :span="18">
        <el-card class="rules-list-card" shadow="hover" v-if="activeCategoryId">
          <template #header>
            <div class="card-header">
              <span>{{ activeCategoryName }} - 校验规则</span>
              <el-button type="primary" @click="openRuleDialog()">
                <el-icon><Plus /></el-icon> 添加规则
              </el-button>
            </div>
          </template>

          <el-table :data="rules" style="width: 100%" v-loading="loadingRules">
            <el-table-column prop="rule_name" label="规则名称" min-width="180">
              <template #default="scope">
                <div style="display: flex; align-items: center;">
                  <span class="rule-name-text">{{ scope.row.rule_name }}</span>
                  <el-tag v-if="scope.row.is_system" size="small" type="info" effect="plain" class="system-tag">系统预置</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="rule_type" label="类型" width="100">
              <template #default="scope">
                <el-tag :type="getRuleTypeTag(scope.row.rule_type)" size="small">
                  {{ getRuleTypeName(scope.row.rule_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="operation_mode" label="模式" width="90">
              <template #default="scope">
                <el-tag v-if="scope.row.rule_type === 'llm_prompt'" :type="getOperationModeType(scope.row.logic_config?.llm_operation_mode)" size="small">
                  {{ getOperationModeName(scope.row.logic_config?.llm_operation_mode) }}
                </el-tag>
                <span v-else class="text-placeholder">—</span>
              </template>
            </el-table-column>
            <el-table-column prop="severity" label="级别" width="90">
              <template #default="scope">
                <el-tag v-if="!isExtractionMode(scope.row)" :type="scope.row.severity === 'fail' ? 'danger' : 'warning'" size="small">
                  {{ scope.row.severity === 'fail' ? '拦截' : '警告' }}
                </el-tag>
                <span v-else class="text-placeholder">—</span>
              </template>
            </el-table-column>
            <el-table-column prop="rule_content" label="规则内容" min-width="250" show-overflow-tooltip />
            <el-table-column prop="is_active" label="状态" width="70" align="center">
              <template #default="scope">
                <el-switch v-model="scope.row.is_active" @change="toggleRuleStatus(scope.row)" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right" align="center">
              <template #default="scope">
                <el-button link type="primary" @click="openRuleDialog(scope.row)">编辑</el-button>
                <el-button 
                  link 
                  type="danger" 
                  @click="deleteRuleData(scope.row.id)"
                  :disabled="scope.row.is_system"
                  :title="scope.row.is_system ? '系统预置规则不可物理删除' : ''"
                >删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-empty v-else description="请选择左侧文档分类以查看或配置规则" />
      </el-col>
    </el-row>

    <!-- 分类弹窗 -->
    <el-dialog :title="categoryForm.id ? '编辑文档分类' : '新建文档分类'" v-model="categoryDialogVisible" width="400px">
      <el-form :model="categoryForm" label-width="100px">
        <el-form-item label="分类名称" prop="name" required>
          <el-input v-model="categoryForm.name" placeholder="例如：生产计划单" />
        </el-form-item>
        <el-form-item label="识别关键词" prop="keywords">
          <el-select
            v-model="categoryForm.keywords"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入关键词并回车"
            style="width: 100%"
          >
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="categoryDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveCategory" :loading="saving">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 规则弹窗 -->
    <el-dialog 
      :title="ruleForm.id ? '编辑规则' : '添加规则'" 
      v-model="ruleDialogVisible" 
      :width="ruleForm.rule_type === 'logic_graph' ? '95%' : '80%'"
      destroy-on-close
    >
      <el-form :model="ruleForm" label-width="100px">
        <el-form-item label="规则名称" prop="rule_name" required>
          <el-input v-model="ruleForm.rule_name" placeholder="例如：文档必须包含授权签字" />
        </el-form-item>
        <el-form-item label="规则类型" prop="rule_type" required>
          <el-select v-model="ruleForm.rule_type" style="width: 100%">
            <el-option label="关键字 (Keyword)" value="keyword" />
            <el-option label="正则表达式 (Regex)" value="regex" />
            <el-option label="大模型分析 (LLM Prompt)" value="llm_prompt" />
            <el-option label="可视化节点图 (Logic Graph)" value="logic_graph" />
          </el-select>
        </el-form-item>
        
        <!-- LLM Model Type Selection -->
        <el-form-item label="大模型引擎" v-if="ruleForm.rule_type === 'llm_prompt'" prop="llm_model_type">
          <el-radio-group v-model="ruleForm.llm_model_type">
            <el-radio value="text">纯文本语义分析 (Text LLM)</el-radio>
            <el-radio value="vision">视觉/版式识别 (Vision LLM)</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- LLM Operation Mode -->
        <el-form-item label="操作模式" v-if="ruleForm.rule_type === 'llm_prompt'" prop="llm_operation_mode">
          <div class="operation-mode-selector">
            <div
              class="mode-card"
              :class="{ active: ruleForm.llm_operation_mode === 'verification' }"
              @click="ruleForm.llm_operation_mode = 'verification'"
            >
              <div class="mode-icon">✓</div>
              <div class="mode-content">
                <div class="mode-title">验证模式</div>
                <div class="mode-desc">判断文档是否满足条件，返回通过/不通过</div>
              </div>
              <div class="mode-badge">VERIFICATION</div>
            </div>
            <div
              class="mode-card"
              :class="{ active: ruleForm.llm_operation_mode === 'extraction' }"
              @click="ruleForm.llm_operation_mode = 'extraction'"
            >
              <div class="mode-icon">⋮</div>
              <div class="mode-content">
                <div class="mode-title">提取模式</div>
                <div class="mode-desc">从文档中提取数据，不进行验证判断</div>
              </div>
              <div class="mode-badge">EXTRACTION</div>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="严重级别" prop="severity" required v-if="ruleForm.llm_operation_mode !== 'extraction'">
          <el-radio-group v-model="ruleForm.severity">
            <el-radio value="fail">失败 (直接拦截)</el-radio>
            <el-radio value="warning">警告 (提示风险)</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <!-- Condition Configuration -->
        <el-form-item label="生效条件" prop="condition_institution">
          <el-input 
            v-model="ruleForm.condition_institution" 
            placeholder="选填。输入触发校验的机构名（如：CTI），不填则全局生效" 
          />
        </el-form-item>
        
        <!-- Logic Graph Editor -->
        <el-form-item label="逻辑图配置" v-if="ruleForm.rule_type === 'logic_graph'" prop="logic_config" required>
          <RuleGraphEditor :key="ruleForm.id || 'new'" v-model="ruleForm.logic_config" />
        </el-form-item>
        
        <!-- Standard Content Input -->
        <el-form-item label="规则内容" v-else prop="rule_content" required>
          <el-input 
            v-model="ruleForm.rule_content" 
            type="textarea" 
            :rows="4" 
            placeholder="输入关键字、正则表达式或给大模型的提示词..." 
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="ruleDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveRule" :loading="saving">保存</el-button>
        </span>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Plus, MoreFilled, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import RuleGraphEditor from '../components/RuleGraphEditor.vue'
import { 
  getCategories, createCategory, updateCategory, deleteCategory,
  getRules, createRule, updateRule, deleteRule, restoreDefaultRules,
  type Category, type Rule
} from '../api/rules'

const categories = ref<Category[]>([])
const rules = ref<Rule[]>([])
const activeCategoryId = ref<string>('')

const loadingRules = ref(false)
const saving = ref(false)
const restoringDefaults = ref(false)

// Dialog states
const categoryDialogVisible = ref(false)
const ruleDialogVisible = ref(false)

const categoryForm = ref<Partial<Category>>({ name: '', keywords: [] })
const ruleForm = ref<Partial<Rule & { condition_institution?: string, llm_model_type?: string, llm_operation_mode?: string }>>({
  rule_name: '',
  rule_type: 'llm_prompt',
  severity: 'fail',
  rule_content: '',
  logic_config: null,
  condition_institution: '',
  llm_model_type: 'text',
  llm_operation_mode: 'verification'
})

// Watch rule_type changes to initialize logic_config
watch(() => ruleForm.value.rule_type, (newType, oldType) => {
  if (newType === 'logic_graph' && oldType !== 'logic_graph') {
    // Initialize logic_config when switching to logic_graph
    if (!ruleForm.value.logic_config ||
        !ruleForm.value.logic_config.nodes ||
        ruleForm.value.logic_config.nodes.length === 0) {
      ruleForm.value.logic_config = { nodes: [], edges: [] }
    }
  }
})

const activeCategoryName = computed(() => {
  const cat = categories.value.find(c => c.id === activeCategoryId.value)
  return cat ? cat.name : ''
})

onMounted(async () => {
  await fetchCategories()
  if (categories.value.length > 0) {
    activeCategoryId.value = categories.value[0].id
    await fetchRules()
  }
})

const fetchCategories = async () => {
  try {
    categories.value = await getCategories()
  } catch (error) {
    ElMessage.error('加载文档分类失败')
  }
}

const fetchRules = async () => {
  if (!activeCategoryId.value) return
  loadingRules.value = true
  try {
    rules.value = await getRules(activeCategoryId.value)
  } catch (error) {
    ElMessage.error('加载规则列表失败')
  } finally {
    loadingRules.value = false
  }
}

const handleCategorySelect = (index: string) => {
  activeCategoryId.value = index
  fetchRules()
}

// Category Actions
const openCategoryDialog = (cat?: Category) => {
  if (cat) {
    categoryForm.value = { ...cat, keywords: [...cat.keywords] }
  } else {
    categoryForm.value = { name: '', keywords: [] }
  }
  categoryDialogVisible.value = true
}

const handleCategoryCommand = (command: string, cat: Category) => {
  if (command === 'edit') {
    openCategoryDialog(cat)
  } else if (command === 'delete') {
    ElMessageBox.confirm('确定要删除该分类吗？关联的所有规则也将被删除。', '警告', {
      type: 'warning'
    }).then(async () => {
      try {
        await deleteCategory(cat.id)
        ElMessage.success('分类已删除')
        if (activeCategoryId.value === cat.id) {
          activeCategoryId.value = ''
          rules.value = []
        }
        await fetchCategories()
      } catch (e) {
        ElMessage.error('删除分类失败')
      }
    }).catch(() => {})
  }
}

const saveCategory = async () => {
  if (!categoryForm.value.name) {
    ElMessage.warning('请输入分类名称')
    return
  }
  saving.value = true
  try {
    if (categoryForm.value.id) {
      await updateCategory(categoryForm.value.id, categoryForm.value)
      ElMessage.success('更新成功')
      await fetchCategories()
    } else {
      const newCat = await createCategory(categoryForm.value)
      ElMessage.success('创建成功')
      await fetchCategories()
      activeCategoryId.value = newCat.id
      await fetchRules()
    }
    categoryDialogVisible.value = false
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// Rule Actions
const openRuleDialog = (rule?: Rule) => {
  if (rule) {
    ruleForm.value = { ...rule }
    // Map condition
    ruleForm.value.condition_institution = rule.logic_config?.conditions?.institution || ''
    ruleForm.value.llm_model_type = rule.logic_config?.llm_model_type || 'text'
    ruleForm.value.llm_operation_mode = rule.logic_config?.llm_operation_mode || 'verification'

    // Ensure logic_config is properly initialized for logic_graph rules
    if (rule.rule_type === 'logic_graph') {
      if (!rule.logic_config || !rule.logic_config.nodes || rule.logic_config.nodes.length === 0) {
        ruleForm.value.logic_config = { nodes: [], edges: [] }
      } else {
        // Deep clone to avoid reactivity issues
        ruleForm.value.logic_config = JSON.parse(JSON.stringify(rule.logic_config))
      }
    }
  } else {
    ruleForm.value = {
      category_id: activeCategoryId.value,
      rule_name: '',
      rule_type: 'llm_prompt',
      severity: 'fail',
      rule_content: '',
      logic_config: {}, // Fixed: empty object instead of null to pass backend Pydantic validation
      is_active: true,
      condition_institution: '',
      llm_model_type: 'text',
      llm_operation_mode: 'verification'
    }
  }
  ruleDialogVisible.value = true
}

const saveRule = async () => {
  if (!ruleForm.value.rule_name) {
    ElMessage.warning('请填写规则名称')
    return
  }

  // Validation based on rule type
  if (ruleForm.value.rule_type === 'logic_graph') {
    if (!ruleForm.value.logic_config ||
        !ruleForm.value.logic_config.nodes ||
        ruleForm.value.logic_config.nodes.length === 0) {
      ElMessage.warning('请配置逻辑图节点')
      return
    }
  } else if (!ruleForm.value.rule_content) {
    ElMessage.warning('请填写规则内容')
    return
  }

  saving.value = true
  const payload = { ...ruleForm.value }

  // Inject condition into logic_config
  if (payload.condition_institution) {
    if (!payload.logic_config) payload.logic_config = {}
    if (!payload.logic_config.conditions) payload.logic_config.conditions = {}
    payload.logic_config.conditions.institution = payload.condition_institution
  } else {
    // Clean up if empty
    if (payload.logic_config?.conditions?.institution) {
      delete payload.logic_config.conditions.institution
    }
  }

  if (payload.rule_type === 'llm_prompt') {
    if (!payload.logic_config) payload.logic_config = {}
    payload.logic_config.llm_model_type = payload.llm_model_type || 'text'
    payload.logic_config.llm_operation_mode = payload.llm_operation_mode || 'verification'
  }

  // Clean payload
  delete payload.condition_institution
  delete payload.llm_model_type
  delete payload.llm_operation_mode

  try {
    if (payload.id) {
      await updateRule(payload.id, payload)
      ElMessage.success('更新成功')
    } else {
      await createRule(payload as any)
      ElMessage.success('添加成功')
    }
    ruleDialogVisible.value = false
    await fetchRules()
  } catch (error) {
    ElMessage.error('保存规则失败')
  } finally {
    saving.value = false
  }
}

const deleteRuleData = (id: string) => {
  ElMessageBox.confirm('确定要删除该规则吗？', '警告', {
    type: 'warning'
  }).then(async () => {
    try {
      await deleteRule(id)
      ElMessage.success('规则已删除')
      await fetchRules()
    } catch (e) {
      ElMessage.error('删除规则失败')
    }
  }).catch(() => {})
}

const toggleRuleStatus = async (rule: Rule) => {
  try {
    await updateRule(rule.id, { is_active: rule.is_active })
    ElMessage.success(`规则已${rule.is_active ? '启用' : '禁用'}`)
  } catch (e) {
    rule.is_active = !rule.is_active
    ElMessage.error('切换状态失败')
  }
}

const handleRestoreDefaults = () => {
  ElMessageBox.confirm('确定要恢复所有系统的预置默认规则吗？此操作将重置系统规则的内容配置，但不会删除您自定义的规则。', '恢复系统规则', {
    type: 'warning'
  }).then(async () => {
    restoringDefaults.value = true
    try {
      await restoreDefaultRules()
      ElMessage.success('系统默认规则已重置成功')
      if (activeCategoryId.value || categories.value.length === 0) {
        await fetchRules()
      }
    } catch (e) {
      ElMessage.error('重置规则失败')
    } finally {
      restoringDefaults.value = false
    }
  }).catch(() => {})
}

// Helpers
const getRuleTypeName = (type: string) => {
  const map: Record<string, string> = {
    'keyword': '关键字',
    'regex': '正则',
    'llm_prompt': '大模型',
    'plugin': '插件',
    'logic_graph': '可视化流程',
  }
  return map[type] || type
}

const getRuleTypeTag = (type: string) => {
  const map: Record<string, string> = {
    'keyword': 'info',
    'regex': 'success',
    'llm_prompt': 'primary',
    'plugin': 'warning',
    'logic_graph': 'danger',
  }
  return map[type] || 'info'
}

const getOperationModeName = (mode: string) => {
  const map: Record<string, string> = {
    'verification': '验证',
    'extraction': '提取',
  }
  return map[mode] || '验证'
}

const getOperationModeType = (mode: string) => {
  const map: Record<string, string> = {
    'verification': 'success',
    'extraction': 'info',
  }
  return map[mode] || 'success'
}

const isExtractionMode = (rule: any) => {
  return rule.rule_type === 'llm_prompt' && rule.logic_config?.llm_operation_mode === 'extraction'
}
</script>

<style scoped>
.rules-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.rules-container {
  min-height: calc(100vh - 200px);
}

/* Rules Table Styles */
.rules-table :deep(.el-table__header th) {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.rule-name-text {
  font-weight: 500;
}

.system-tag {
  margin-left: 8px;
  transform: scale(0.9);
}

.text-placeholder {
  color: var(--el-text-color-placeholder);
  font-size: 13px;
}

.category-card, .rules-list-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.category-menu {
  border-right: none;
}

.menu-item-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.more-icon {
  visibility: hidden;
  color: var(--el-text-color-secondary);
}

.el-menu-item:hover .more-icon {
  visibility: visible;
}

.text-danger {
  color: var(--el-color-danger);
}

/* Operation Mode Selector */
.operation-mode-selector {
  display: flex;
  gap: 12px;
  width: 100%;
}

.mode-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 2px solid var(--el-border-color);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--el-bg-color);
  position: relative;
  overflow: hidden;
}

.mode-card:hover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.mode-card.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  box-shadow: 0 0 0 1px var(--el-color-primary-light-7);
}

.mode-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  color: var(--el-text-color-regular);
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.mode-card.active .mode-icon {
  background: var(--el-color-primary);
  color: white;
}

.mode-content {
  flex: 1;
}

.mode-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 2px;
}

.mode-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}

.mode-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  font-size: 9px;
  font-weight: 700;
  color: var(--el-text-color-placeholder);
  opacity: 0.5;
  letter-spacing: 0.5px;
}

.mode-card.active .mode-badge {
  color: var(--el-color-primary);
  opacity: 0.3;
}
</style>
