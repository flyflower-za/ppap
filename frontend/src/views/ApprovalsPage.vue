<template>
  <div class="approvals-page" v-loading="loading">
    <div class="page-header">
      <div class="title-section">
        <h2 class="page-title">审批中心</h2>
        <p class="page-subtitle">规则变更审批流程管理与策略配置</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" plain :icon="Setting" @click="showPolicies = true">
          审批策略
        </el-button>
        <el-button type="success" plain @click="handleInitPolicies">
          初始化预置策略
        </el-button>
      </div>
    </div>

    <!-- Stats Cards -->
    <el-row :gutter="16" class="stats-row mb-4">
      <el-col :span="6">
        <div class="stat-card pending">
          <div class="stat-icon">⏳</div>
          <div class="stat-info">
            <span class="stat-value">{{ pendingCount }}</span>
            <span class="stat-label">待审批</span>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card approved">
          <div class="stat-icon">✅</div>
          <div class="stat-info">
            <span class="stat-value">{{ approvedCount }}</span>
            <span class="stat-label">已批准</span>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card deployed">
          <div class="stat-icon">🚀</div>
          <div class="stat-info">
            <span class="stat-value">{{ deployedCount }}</span>
            <span class="stat-label">已部署</span>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card rejected">
          <div class="stat-icon">❌</div>
          <div class="stat-info">
            <span class="stat-value">{{ rejectedCount }}</span>
            <span class="stat-label">已拒绝</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Tab Filter -->
    <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="mb-4">
      <el-tab-pane label="待审批" name="pending" />
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="已批准" name="approved" />
      <el-tab-pane label="已部署" name="deployed" />
      <el-tab-pane label="已拒绝" name="rejected" />
    </el-tabs>

    <!-- Change Requests List -->
    <div class="requests-list">
      <el-empty v-if="filteredRequests.length === 0" description="暂无审批记录" />
      
      <div v-for="cr in filteredRequests" :key="cr.id" class="request-card glass-card">
        <div class="request-header">
          <div class="request-meta">
            <el-tag :type="getChangeTypeTag(cr.change_type)" size="small" effect="dark">
              {{ getChangeTypeName(cr.change_type) }}
            </el-tag>
            <el-tag :type="getPriorityTag(cr.priority)" size="small" effect="plain">
              {{ getPriorityName(cr.priority) }}
            </el-tag>
            <el-tag :type="getStatusTag(cr.status)" size="small">
              {{ getStatusName(cr.status) }}
            </el-tag>
          </div>
          <span class="request-time">{{ formatDate(cr.requested_at) }}</span>
        </div>

        <div class="request-body">
          <h4 class="rule-name">{{ cr.proposed_rule_data?.rule_name || '新规则' }}</h4>
          <p class="request-reason" v-if="cr.reason">
            <span class="label">变更原因：</span>{{ cr.reason }}
          </p>
          <p class="request-impact" v-if="cr.impact_assessment">
            <span class="label">影响评估：</span>{{ cr.impact_assessment }}
          </p>
          <div class="request-people">
            <span v-if="cr.requester_name" class="person">
              <el-icon><User /></el-icon> 申请人: {{ cr.requester_name }}
            </span>
            <span v-if="cr.reviewer_name" class="person">
              <el-icon><Check /></el-icon> 审批人: {{ cr.reviewer_name }}
            </span>
          </div>
          <div v-if="cr.review_comment" class="review-comment">
            <el-icon><ChatDotRound /></el-icon>
            审批意见: {{ cr.review_comment }}
          </div>
        </div>

        <!-- Actions -->
        <div class="request-actions" v-if="cr.status === 'pending' || cr.status === 'approved'">
          <template v-if="cr.status === 'pending'">
            <el-button type="success" size="small" @click="handleReview(cr, 'approve')">
              批准
            </el-button>
            <el-button type="danger" size="small" @click="handleReview(cr, 'reject')">
              驳回
            </el-button>
          </template>
          <template v-if="cr.status === 'approved'">
            <el-button type="primary" size="small" @click="handleDeploy(cr)">
              🚀 部署生效
            </el-button>
          </template>
        </div>
      </div>
    </div>

    <!-- Policies Dialog -->
    <el-dialog v-model="showPolicies" title="审批策略配置" width="700px" destroy-on-close>
      <div v-loading="loadingPolicies">
        <el-empty v-if="policies.length === 0" description="暂无审批策略，请点击「初始化预置策略」" />
        <div v-for="policy in policies" :key="policy.id" class="policy-card">
          <div class="policy-header">
            <h4>{{ policy.name }}</h4>
            <el-tag :type="policy.requires_approval ? 'danger' : 'success'" size="small">
              {{ policy.requires_approval ? '需要审批' : '免审批' }}
            </el-tag>
          </div>
          <p class="policy-desc">{{ policy.description }}</p>
          <div class="policy-conditions">
            <span class="label">触发条件:</span>
            <code>{{ JSON.stringify(policy.conditions) }}</code>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Check, ChatDotRound, Setting } from '@element-plus/icons-vue'
import {
  getChangeRequests, reviewChangeRequest, deployChangeRequest,
  getApprovalPolicies, initApprovalPolicies,
  type ChangeRequest, type ApprovalPolicy
} from '../api/approvals'

const loading = ref(false)
const requests = ref<ChangeRequest[]>([])
const activeTab = ref('pending')
const showPolicies = ref(false)
const loadingPolicies = ref(false)
const policies = ref<ApprovalPolicy[]>([])

// Stats
const pendingCount = computed(() => requests.value.filter(r => r.status === 'pending').length)
const approvedCount = computed(() => requests.value.filter(r => r.status === 'approved').length)
const deployedCount = computed(() => requests.value.filter(r => r.status === 'deployed').length)
const rejectedCount = computed(() => requests.value.filter(r => r.status === 'rejected').length)

const filteredRequests = computed(() => {
  if (activeTab.value === 'all') return requests.value
  return requests.value.filter(r => r.status === activeTab.value)
})

onMounted(async () => {
  await fetchRequests()
})

const fetchRequests = async () => {
  loading.value = true
  try {
    requests.value = await getChangeRequests()
  } catch (e) {
    ElMessage.error('加载审批列表失败')
  } finally {
    loading.value = false
  }
}

const handleTabChange = () => {
  // Filtering is client-side via computed, no fetch needed
}

const handleReview = async (cr: ChangeRequest, action: 'approve' | 'reject') => {
  const actionName = action === 'approve' ? '批准' : '驳回'
  try {
    const { value: comment } = await ElMessageBox.prompt(
      `请输入审批意见（可选）`,
      `确认${actionName}`,
      {
        confirmButtonText: actionName,
        cancelButtonText: '取消',
        inputPlaceholder: '审批意见...',
        type: action === 'approve' ? 'success' : 'warning',
      }
    )
    await reviewChangeRequest(cr.id, action, comment || undefined)
    ElMessage.success(`已${actionName}`)
    await fetchRequests()
  } catch (e: any) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      ElMessage.error(`${actionName}操作失败`)
    }
  }
}

const handleDeploy = async (cr: ChangeRequest) => {
  try {
    await ElMessageBox.confirm('确定将此变更部署生效？规则将立即更新。', '确认部署', { type: 'warning' })
    await deployChangeRequest(cr.id)
    ElMessage.success('变更已成功部署生效')
    await fetchRequests()
  } catch (e: any) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      ElMessage.error('部署失败')
    }
  }
}

const handleInitPolicies = async () => {
  try {
    const res = await initApprovalPolicies()
    ElMessage.success((res as any).message || '预置策略初始化完成')
    if (showPolicies.value) await fetchPolicies()
  } catch (e) {
    ElMessage.error('初始化策略失败')
  }
}

const fetchPolicies = async () => {
  loadingPolicies.value = true
  try {
    policies.value = await getApprovalPolicies()
  } catch (e) {
    ElMessage.error('加载策略失败')
  } finally {
    loadingPolicies.value = false
  }
}

// Auto-fetch policies when dialog opens
import { watch } from 'vue'
watch(showPolicies, (val) => { if (val) fetchPolicies() })

// Helpers
const getChangeTypeName = (type: string) => {
  const map: Record<string, string> = { create: '新建', update: '修改', delete: '删除', deactivate: '停用' }
  return map[type] || type
}
const getChangeTypeTag = (type: string) => {
  const map: Record<string, string> = { create: 'success', update: 'primary', delete: 'danger', deactivate: 'warning' }
  return (map[type] || 'info') as any
}
const getPriorityName = (p: string) => {
  const map: Record<string, string> = { low: '低', normal: '普通', high: '高', urgent: '紧急' }
  return map[p] || p
}
const getPriorityTag = (p: string) => {
  const map: Record<string, string> = { low: 'info', normal: '', high: 'warning', urgent: 'danger' }
  return (map[p] || 'info') as any
}
const getStatusName = (s: string) => {
  const map: Record<string, string> = { draft: '草稿', pending: '待审批', approved: '已批准', rejected: '已拒绝', deployed: '已部署', rolled_back: '已回滚' }
  return map[s] || s
}
const getStatusTag = (s: string) => {
  const map: Record<string, string> = { draft: 'info', pending: 'warning', approved: 'success', rejected: 'danger', deployed: 'primary', rolled_back: 'info' }
  return (map[s] || 'info') as any
}
const formatDate = (d: string | null) => {
  if (!d) return ''
  return new Date(d).toLocaleString('zh-CN')
}
</script>

<style scoped>
.approvals-page {
  padding: 8px 4px;
  min-height: calc(100vh - 120px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1f36;
  margin: 0 0 6px 0;
}

.page-subtitle {
  font-size: 13px;
  color: #697386;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* Stats */
.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  border-radius: 14px;
  background: rgba(255,255,255,0.75);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.5);
  box-shadow: 0 6px 24px rgba(0,0,0,0.04);
  transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 32px rgba(0,0,0,0.08);
}
.stat-icon { font-size: 28px; }
.stat-value { font-size: 28px; font-weight: 800; color: #1a1f36; display: block; }
.stat-label { font-size: 12px; color: #697386; font-weight: 600; }

/* Request Cards */
.glass-card {
  background: rgba(255,255,255,0.75);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.5);
  box-shadow: 0 6px 24px rgba(0,0,0,0.04);
  border-radius: 14px;
  padding: 20px;
  transition: all 0.25s ease;
}
.glass-card:hover {
  box-shadow: 0 10px 36px rgba(0,0,0,0.08);
}

.request-card {
  margin-bottom: 16px;
}

.request-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.request-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}
.request-time {
  font-size: 12px;
  color: #8792a2;
}

.request-body {
  margin-bottom: 12px;
}
.rule-name {
  font-size: 16px;
  font-weight: 700;
  color: #1a1f36;
  margin: 0 0 8px 0;
}
.request-reason, .request-impact {
  font-size: 13px;
  color: #4f566b;
  margin: 4px 0;
}
.request-reason .label, .request-impact .label {
  font-weight: 600;
  color: #697386;
}
.request-people {
  display: flex;
  gap: 20px;
  margin-top: 8px;
  font-size: 12px;
  color: #8792a2;
}
.person {
  display: flex;
  align-items: center;
  gap: 4px;
}
.review-comment {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(0,0,0,0.02);
  border-radius: 8px;
  font-size: 13px;
  color: #4f566b;
  display: flex;
  align-items: center;
  gap: 6px;
}

.request-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid rgba(0,0,0,0.04);
}

/* Policy Cards */
.policy-card {
  padding: 16px;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 10px;
  margin-bottom: 12px;
}
.policy-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.policy-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #1a1f36;
}
.policy-desc {
  font-size: 13px;
  color: #697386;
  margin: 0 0 8px 0;
}
.policy-conditions {
  font-size: 12px;
  color: #8792a2;
}
.policy-conditions .label {
  font-weight: 600;
  margin-right: 6px;
}
.policy-conditions code {
  font-size: 11px;
  background: rgba(0,0,0,0.03);
  padding: 2px 6px;
  border-radius: 4px;
}

.mb-4 { margin-bottom: 16px; }
</style>
