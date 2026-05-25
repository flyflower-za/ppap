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
            <el-table-column prop="rule_name" label="规则名称" min-width="200">
              <template #default="scope">
                <div style="display: flex; align-items: center;">
                  <span>{{ scope.row.rule_name }}</span>
                  <el-tag v-if="scope.row.is_system" size="small" type="info" effect="plain" style="margin-left: 8px;">系统预置</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="rule_type" label="类型" width="120">
              <template #default="scope">
                <el-tag :type="getRuleTypeTag(scope.row.rule_type)">
                  {{ getRuleTypeName(scope.row.rule_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="severity" label="严重级别" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.severity === 'fail' ? 'danger' : 'warning'">
                  {{ scope.row.severity === 'fail' ? '失败 (Fail)' : '警告 (Warn)' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="rule_content" label="规则内容" show-overflow-tooltip />
            <el-table-column prop="is_active" label="状态" width="80">
              <template #default="scope">
                <el-switch v-model="scope.row.is_active" @change="toggleRuleStatus(scope.row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
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
        <el-form-item label="严重级别" prop="severity" required>
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
const ruleForm = ref<Partial<Rule & { condition_institution?: string }>>({
  rule_name: '',
  rule_type: 'llm_prompt',
  severity: 'fail',
  rule_content: '',
  logic_config: null,
  condition_institution: ''
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
      rule_type: 'keyword',
      severity: 'fail',
      rule_content: '',
      logic_config: {}, // Fixed: empty object instead of null to pass backend Pydantic validation
      is_active: true,
      condition_institution: ''
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

  // Clean payload
  delete payload.condition_institution

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
</style>
