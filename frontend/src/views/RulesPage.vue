<template>
  <div class="rules-page">
    <div class="page-header flex-between" style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h2 class="page-title">规则配置中心</h2>
        <p class="page-subtitle">配置不同文档类型的识别规则与验证规则引擎</p>
      </div>
      <div class="header-actions">
        <el-button type="info" plain @click="router.push('/modules')">
          <el-icon><Management /></el-icon> 模块管理
        </el-button>
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
        <div v-if="activeCategoryId">
          <!-- 1. 基础配置：底座预设规则 -->
          <el-card class="rules-list-card preset-card mb-4" shadow="hover">
            <template #header>
              <div class="card-header flex-between" style="display: flex; justify-content: space-between; align-items: center;">
                <span>{{ activeCategoryName }} - 基础底座配置 (预设规则清单)</span>
                <div style="display: flex; align-items: center; gap: 10px;">
                  <el-tag v-if="presetDirty" type="warning" effect="dark" size="small" style="animation: pulse 1.5s infinite;">
                    ⚠ 配置已修改，请保存
                  </el-tag>
                  <el-button type="success" :loading="savingPreset" @click="savePresetRules">
                    <el-icon><Check /></el-icon> 保存基础配置
                  </el-button>
                </div>
              </div>
            </template>

            <div class="preset-rules-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px;">
              <div v-for="rule in presetRules" :key="rule.id" class="preset-rule-item" style="border: 1px solid var(--el-border-color-light); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 10px; background: var(--el-fill-color-blank);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-weight: 600; font-size: 14px;">{{ rule.rule_name }}</span>
                  <el-switch v-model="rule.is_active" size="small" @change="presetDirty = true" />
                </div>
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
                  <span style="font-size: 12px; color: var(--el-text-color-secondary);">告警级别:</span>
                  <el-select v-model="rule.severity" size="small" style="width: 120px;" @change="presetDirty = true">
                    <el-option label="拦截 (Fail)" value="fail" />
                    <el-option label="警告 (Warning)" value="warning" />
                    <el-option label="参考 (Reference)" value="reference" />
                  </el-select>
                </div>
              </div>
            </div>
          </el-card>

        </div>

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

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, MoreFilled, Refresh, Management } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getCategories, createCategory, updateCategory, deleteCategory,
  getRules, restoreDefaultRules,
  type Category
} from '../api/rules'

const router = useRouter()

const categories = ref<Category[]>([])
const rules = ref<any[]>([])
const activeCategoryId = ref<string>('')

const loadingRules = ref(false)
const saving = ref(false)
const restoringDefaults = ref(false)
const savingPreset = ref(false)
const presetDirty = ref(false)

// Preset rules
const presetRules = computed(() => {
  return rules.value.filter((r: any) => r.is_system && r.module_id)
})

const savePresetRules = async () => {
  savingPreset.value = true
  try {
    const { updateRule } = await import('../api/rules')
    for (const rule of presetRules.value) {
      await updateRule(rule.id, {
        is_active: rule.is_active,
        severity: rule.severity
      })
    }
    ElMessage.success('基础配置保存成功')
    presetDirty.value = false
    await fetchRules()
  } catch (error) {
    ElMessage.error('保存基础配置失败')
  } finally {
    savingPreset.value = false
  }
}

// Category dialog
const categoryDialogVisible = ref(false)
const categoryForm = ref<Partial<Category>>({ name: '', keywords: [] })

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

/* Header Actions */
.header-actions {
  display: flex;
  gap: 10px;
}

/* Pulse animation for dirty state indicator */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
</style>
