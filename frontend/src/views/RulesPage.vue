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
              <div class="header-actions">
                <el-button type="success" plain @click="openTemplateMarket()">
                  <el-icon><Collection /></el-icon> 从模板创建
                </el-button>
                <el-button type="primary" @click="openRuleDialog()">
                  <el-icon><Plus /></el-icon> 添加规则
                </el-button>
              </div>
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
                <el-tag 
                  v-if="!isExtractionMode(scope.row)" 
                  :type="scope.row.severity === 'fail' ? 'danger' : scope.row.severity === 'warning' ? 'warning' : 'info'" 
                  size="small"
                >
                  {{ scope.row.severity === 'fail' ? '拦截' : scope.row.severity === 'warning' ? '警告' : '参考' }}
                </el-tag>
                <span v-else class="text-placeholder">—</span>
              </template>
            </el-table-column>
            <el-table-column prop="rule_content" label="规则内容" min-width="250" show-overflow-tooltip>
              <template #default="scope">
                <span v-if="scope.row.rule_type === 'logic_graph'" class="text-placeholder">
                  [可视化流程] {{ scope.row.logic_config?.nodes?.length || 0 }} 个节点, {{ scope.row.logic_config?.edges?.length || 0 }} 条连线
                </span>
                <span v-else>{{ scope.row.rule_content }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="is_active" label="状态" width="70" align="center">
              <template #default="scope">
                <el-switch v-model="scope.row.is_active" @change="toggleRuleStatus(scope.row)" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right" align="center">
              <template #default="scope">
                <el-button link type="primary" @click="openRuleDialog(scope.row)">编辑</el-button>
                <el-button link type="info" @click="showVersionsHistory(scope.row)">历史</el-button>
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
      v-model="ruleDialogVisible"
      :width="ruleForm.rule_type === 'logic_graph' ? '95%' : '80%'"
      destroy-on-close
    >
      <template #header>
        <div class="rule-dialog-header">
          <span>{{ ruleForm.id ? '编辑规则' : '添加规则' }}</span>
          <el-button
            v-if="ruleForm.rule_type === 'logic_graph'"
            type="primary"
            size="small"
            @click="openFullscreenEditor"
          >
            <el-icon><FullScreen /></el-icon> 全屏编辑
          </el-button>
        </div>
      </template>
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
            <el-radio value="reference">参考 (额外检测，不计入评分)</el-radio>
          </el-radio-group>
          <div v-if="ruleForm.severity === 'reference'" class="reference-hint">
            <el-icon><InfoFilled /></el-icon>
            参考项会完整执行检测并出现在诊断报告中，但结果不影响通过率和最终合规状态。
          </div>
        </el-form-item>
        
        <!-- Condition Configuration -->
        <el-form-item label="生效条件" prop="condition_institution">
          <el-input 
            v-model="ruleForm.condition_institution" 
            placeholder="选填。输入触发校验的机构名（如：CTI），不填则全局生效" 
          />
        </el-form-item>

        <!-- Logic Graph Editor -->
        <el-form-item v-if="ruleForm.rule_type === 'logic_graph'" prop="logic_config" required label="逻辑图配置">
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
    
    <!-- 规则版本历史抽屉 -->
    <el-drawer
      v-model="versionsDrawerVisible"
      title="规则配置版本历史"
      size="45%"
      destroy-on-close
    >
      <div class="version-history-container" v-loading="loadingVersions">
        <el-timeline v-if="versions.length > 0">
          <el-timeline-item
            v-for="(ver, vIdx) in versions"
            :key="ver.id"
            :timestamp="formatDate(ver.created_at)"
            placement="top"
            type="primary"
          >
            <el-card shadow="hover" class="version-card">
              <div class="version-card-header flex-between mb-2">
                <span class="version-tag-number font-bold">版本 #{{ ver.version_number }}</span>
                <span class="version-author text-muted">编辑者: {{ ver.created_by || '系统' }}</span>
              </div>
              <!-- P3: Change Log -->
              <div v-if="ver.change_log" class="version-change-log mb-2">
                <el-icon><ChatDotRound /></el-icon>
                <span>{{ ver.change_log }}</span>
              </div>
              <div class="version-details text-sm mb-3">
                <div class="version-field">
                  <span class="label">名称:</span> {{ ver.rule_name }}
                  <el-tag v-if="vIdx < versions.length - 1 && ver.rule_name !== versions[vIdx + 1].rule_name" size="small" type="warning" effect="plain" class="diff-tag">已变更</el-tag>
                </div>
                <div class="version-field">
                  <span class="label">类型:</span> {{ getRuleTypeName(ver.rule_type) }}
                </div>
                <div class="version-field">
                  <span class="label">级别:</span> {{ ver.severity === 'fail' ? '拦截' : ver.severity === 'warning' ? '警告' : '参考' }}
                  <el-tag v-if="vIdx < versions.length - 1 && ver.severity !== versions[vIdx + 1].severity" size="small" type="warning" effect="plain" class="diff-tag">已变更</el-tag>
                </div>
                <div class="version-field" v-if="ver.rule_type !== 'logic_graph'">
                  <span class="label">内容:</span> <code class="text-monospace">{{ ver.rule_content }}</code>
                  <el-tag v-if="vIdx < versions.length - 1 && ver.rule_content !== versions[vIdx + 1].rule_content" size="small" type="warning" effect="plain" class="diff-tag">已变更</el-tag>
                </div>
              </div>
              <div class="version-actions" style="display: flex; justify-content: flex-end;">
                <el-button 
                  type="warning" 
                  size="small" 
                  @click="handleRollback(ver)"
                  :loading="rollingBack"
                >
                  回滚至此版本
                </el-button>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无历史版本记录" />
      </div>
    </el-drawer>

    <!-- 规则模板市场对话框 -->
    <el-dialog
      v-model="templateMarketVisible"
      title="规则模板市场"
      width="900px"
      destroy-on-close
    >
      <div class="template-market" v-loading="loadingTemplates">
        <!-- 筛选栏 -->
        <div class="template-filters">
          <el-input
            v-model="templateSearchKeyword"
            placeholder="搜索模板名称..."
            prefix-icon="Search"
            style="width: 250px;"
            clearable
          />
          <el-select v-model="templateCategoryFilter" placeholder="按分类筛选" style="width: 150px;" clearable>
            <el-option label="全部" value="" />
            <el-option label="生产计划" value="生产计划" />
            <el-option label="采购订单" value="采购订单" />
            <el-option label="质检报告" value="质检报告" />
          </el-select>
        </div>

        <!-- 模板列表 -->
        <div class="template-list">
          <div
            v-for="template in filteredTemplates"
            :key="template.id"
            class="template-card"
            :class="{ 'system-template': template.is_system }"
          >
            <div class="template-header">
              <div class="template-title">
                <span class="template-icon">📦</span>
                <span class="template-name">{{ template.name }}</span>
                <el-tag v-if="template.is_system" size="small" type="success" effect="plain">系统</el-tag>
                <el-tag v-if="template.is_public && !template.is_system" size="small" type="info" effect="plain">公开</el-tag>
              </div>
              <div class="template-actions">
                <el-button type="primary" size="small" @click="applyTemplate(template)">
                  <el-icon><Check /></el-icon> 应用
                </el-button>
              </div>
            </div>
            <div class="template-description">{{ template.description }}</div>
            <div class="template-meta">
              <div class="template-tags">
                <el-tag
                  v-for="tag in template.tags"
                  :key="tag"
                  size="small"
                  type="info"
                  effect="plain"
                >
                  {{ tag }}
                </el-tag>
              </div>
              <div class="template-stats">
                <span class="template-rules-count">{{ template.template_rules?.length || 0 }} 条规则</span>
                <span v-if="template.usage_count" class="template-usage">使用 {{ template.usage_count }} 次</span>
              </div>
            </div>
            <div class="template-rules-preview">
              <div class="preview-title">包含规则：</div>
              <div class="preview-list">
                <div v-for="(rule, idx) in template.template_rules.slice(0, 3)" :key="idx" class="preview-item">
                  <el-icon class="item-icon"><Document /></el-icon>
                  <span class="item-name">{{ rule.rule_name }}</span>
                  <el-tag :type="rule.severity === 'fail' ? 'danger' : 'warning'" size="small">
                    {{ rule.severity === 'fail' ? '拦截' : '警告' }}
                  </el-tag>
                </div>
                <div v-if="template.template_rules.length > 3" class="preview-more">
                  +{{ template.template_rules.length - 3 }} 更多规则
                </div>
              </div>
            </div>
          </div>
        </div>

        <el-empty v-if="filteredTemplates.length === 0" description="暂无匹配的模板" />
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="templateMarketVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Plus, MoreFilled, Refresh, InfoFilled, Collection, Check, Search, Document, ChatDotRound, FullScreen } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import RuleGraphEditor from '../components/RuleGraphEditor.vue'
import {
  getCategories, createCategory, updateCategory, deleteCategory,
  getRules, createRule, updateRule, deleteRule, restoreDefaultRules,
  getRuleVersions, rollbackRule,
  type Category, type Rule, type RuleVersion
} from '../api/rules'
import {
  getRuleTemplates, applyRuleTemplate, initializeRuleTemplates,
  type RuleTemplate
} from '../api/operators'

const router = useRouter()
const route = useRoute()

const categories = ref<Category[]>([])
const rules = ref<Rule[]>([])
const activeCategoryId = ref<string>('')

const loadingRules = ref(false)
const saving = ref(false)
const restoringDefaults = ref(false)

// Dialog states
const categoryDialogVisible = ref(false)
const ruleDialogVisible = ref(false)

// Template Market states
const templateMarketVisible = ref(false)
const templates = ref<RuleTemplate[]>([])
const loadingTemplates = ref(false)
const templateSearchKeyword = ref('')
const templateCategoryFilter = ref('')

// Filtered templates
const filteredTemplates = computed(() => {
  let result = templates.value

  if (templateSearchKeyword.value) {
    const keyword = templateSearchKeyword.value.toLowerCase()
    result = result.filter(t =>
      t.name.toLowerCase().includes(keyword) ||
      t.description?.toLowerCase().includes(keyword) ||
      t.tags?.some(tag => tag.toLowerCase().includes(keyword))
    )
  }

  if (templateCategoryFilter.value) {
    result = result.filter(t =>
      t.category_suggestions.some(cat => cat.includes(templateCategoryFilter.value))
    )
  }

  return result
})

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

// Watch for route changes to refresh rules when returning from fullscreen editor
watch(() => route.query.refresh, async (newValue) => {
  if (newValue === 'true' && activeCategoryId.value) {
    await fetchRules()
    // Remove the refresh query param
    router.replace({ query: {} })
  }
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

  // Ensure rule_content is present for backend validation
  if (payload.rule_type === 'logic_graph' && !payload.rule_content) {
    payload.rule_content = ''
  }

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

// Fullscreen Editor
const openFullscreenEditor = () => {
  const query: Record<string, string> = {
    categoryId: activeCategoryId.value
  }
  if (ruleForm.value.id) {
    query.ruleId = ruleForm.value.id
  }
  router.push({ name: 'FullscreenRuleEditor', query })
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

// Version History & Rollback States
const versionsDrawerVisible = ref(false)
const loadingVersions = ref(false)
const rollingBack = ref(false)
const versions = ref<RuleVersion[]>([])
const selectedRuleForVersions = ref<Rule | null>(null)

const showVersionsHistory = async (rule: Rule) => {
  selectedRuleForVersions.value = rule
  versionsDrawerVisible.value = true
  loadingVersions.value = true
  try {
    versions.value = await getRuleVersions(rule.id)
  } catch (e) {
    ElMessage.error('加载版本历史失败')
  } finally {
    loadingVersions.value = false
  }
}

// Template Market Actions
const openTemplateMarket = async () => {
  if (!activeCategoryId.value) {
    ElMessage.warning('请先选择一个文档分类')
    return
  }

  templateMarketVisible.value = true
  loadingTemplates.value = true

  try {
    templates.value = await getRuleTemplates()
  } catch (error) {
    ElMessage.error('加载模板列表失败')
  } finally {
    loadingTemplates.value = false
  }
}

const applyTemplate = async (template: RuleTemplate) => {
  try {
    await ElMessageBox.confirm(
      `确定要应用模板「${template.name}」到分类「${activeCategoryName.value}」吗？\n\n这将创建 ${template.template_rules?.length || 0} 条新规则，现有规则不会被替换。`,
      '应用模板确认',
      {
        type: 'warning',
        confirmButtonText: '确定应用',
        cancelButtonText: '取消'
      }
    )

    const result = await applyRuleTemplate(template.id, activeCategoryId.value)

    ElMessage.success(`模板应用成功！创建了 ${result.rules_created} 条规则`)
    templateMarketVisible.value = false

    // 刷新规则列表
    await fetchRules()

    // 记录审计日志
    console.log('[Template Applied]', result)
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '应用模板失败')
    }
  }
}

const handleRollback = async (ver: RuleVersion) => {
  try {
    await ElMessageBox.confirm(`确定要将规则【${ver.rule_name}】回滚至版本 #${ver.version_number} 吗？这会产生一条新的回滚版本记录。`, '版本回滚确认', {
      type: 'warning',
      confirmButtonText: '确定回滚',
      cancelButtonText: '取消'
    })
    rollingBack.value = true
    await rollbackRule(ver.rule_id, ver.version_number)
    ElMessage.success('规则回滚成功')
    versionsDrawerVisible.value = false
    await fetchRules()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error('规则回滚失败')
    }
  } finally {
    rollingBack.value = false
  }
}

const formatDate = (dateStr?: string): string => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  } catch (e) {
    return dateStr
  }
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
  border-radius: 12px;
  overflow: hidden;
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

/* Reference Severity Hint */
.reference-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 12px;
  color: #1976d2;
  background: rgba(33, 150, 243, 0.06);
  border: 1px solid rgba(33, 150, 243, 0.2);
  border-radius: 8px;
  padding: 8px 12px;
  line-height: 1.5;
}

/* Version History Styles */
.version-history-container {
  padding: 10px 4px;
}
.version-card {
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(0, 0, 0, 0.05);
}
.version-card-header {
  font-size: 13px;
}
.version-tag-number {
  color: var(--el-color-primary);
}
.version-author {
  color: var(--el-text-color-secondary);
}
.version-field {
  margin-bottom: 4px;
  line-height: 1.4;
}
.version-field .label {
  font-weight: 600;
  color: var(--el-text-color-regular);
  margin-right: 4px;
}
.text-monospace {
  font-family: SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  background: var(--el-fill-color-light);
  padding: 2px 4px;
  border-radius: 4px;
}

/* Rule Dialog Header */
.rule-dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.rule-dialog-header span {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

/* Header Actions */
.header-actions {
  display: flex;
  gap: 10px;
}

/* Template Market Styles */
.template-market {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.template-filters {
  display: flex;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.template-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 16px;
  max-height: 500px;
  overflow-y: auto;
}

.template-card {
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  padding: 16px;
  background: var(--el-bg-color);
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.template-card:hover {
  border-color: var(--el-color-primary);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
  transform: translateY(-2px);
}

.template-card.system-template {
  border-color: var(--el-color-success-light-5);
  background: linear-gradient(135deg, rgba(103, 194, 58, 0.03) 0%, rgba(255, 255, 255, 0) 100%);
}

.template-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.template-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.template-icon {
  font-size: 20px;
}

.template-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.template-description {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
  min-height: 38px;
}

.template-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.template-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.template-stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.template-rules-preview {
  background: var(--el-fill-color-light);
  border-radius: 8px;
  padding: 10px;
  margin-top: 4px;
}

.preview-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
}

.preview-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.preview-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.item-icon {
  color: var(--el-color-primary);
  font-size: 14px;
}

.item-name {
  flex: 1;
  color: var(--el-text-color-regular);
}

.preview-more {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  text-align: center;
  padding: 4px 0;
}

/* P3: Version Change Log */
.version-change-log {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: rgba(64, 158, 255, 0.06);
  border-radius: 6px;
  font-size: 12px;
  color: #4f566b;
}

.diff-tag {
  margin-left: 6px;
  font-size: 10px;
}
</style>
