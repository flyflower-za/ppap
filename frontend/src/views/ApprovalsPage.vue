<template>
  <div class="approvals-page" v-loading="loading">
    <div class="page-header">
      <div class="title-section">
        <h2 class="page-title">{{ $t('approvals.title') }}</h2>
        <p class="page-subtitle">{{ $t('approvals.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" plain :icon="Setting" @click="showPolicies = true">
          {{ $t('approvals.policies') }}
        </el-button>
        <el-button type="success" plain @click="handleInitPolicies">
          {{ $t('approvals.initPolicies') }}
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
            <span class="stat-label">{{ $t('approvals.pending') }}</span>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card approved">
          <div class="stat-icon">✅</div>
          <div class="stat-info">
            <span class="stat-value">{{ approvedCount }}</span>
            <span class="stat-label">{{ $t('approvals.approved') }}</span>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card deployed">
          <div class="stat-icon">🚀</div>
          <div class="stat-info">
            <span class="stat-value">{{ deployedCount }}</span>
            <span class="stat-label">{{ $t('approvals.deployed') }}</span>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card rejected">
          <div class="stat-icon">❌</div>
          <div class="stat-info">
            <span class="stat-value">{{ rejectedCount }}</span>
            <span class="stat-label">{{ $t('approvals.rejected') }}</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Tab Filter -->
    <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="mb-4">
      <el-tab-pane :label="$t('approvals.pending')" name="pending" />
      <el-tab-pane :label="$t('common.all')" name="all" />
      <el-tab-pane :label="$t('approvals.approved')" name="approved" />
      <el-tab-pane :label="$t('approvals.deployed')" name="deployed" />
      <el-tab-pane :label="$t('approvals.rejected')" name="rejected" />
    </el-tabs>

    <!-- Change Requests List -->
    <div class="requests-list">
      <el-empty v-if="filteredRequests.length === 0" :description="$t('approvals.emptyRecords')" />

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
          <h4 class="rule-name">{{ cr.proposed_rule_data?.rule_name || $t('approvals.newRule') }}</h4>
          <p class="request-reason" v-if="cr.reason">
            <span class="label">{{ $t('approvals.changeReason') }}</span>{{ cr.reason }}
          </p>
          <p class="request-impact" v-if="cr.impact_assessment">
            <span class="label">{{ $t('approvals.impactAssessment') }}</span>{{ cr.impact_assessment }}
          </p>
          <div class="request-people">
            <span v-if="cr.requester_name" class="person">
              <el-icon><User /></el-icon> {{ $t('approvals.requester') }} {{ cr.requester_name }}
            </span>
            <span v-if="cr.reviewer_name" class="person">
              <el-icon><Check /></el-icon> {{ $t('approvals.reviewer') }} {{ cr.reviewer_name }}
            </span>
          </div>
          <div v-if="cr.review_comment" class="review-comment">
            <el-icon><ChatDotRound /></el-icon>
            {{ $t('approvals.reviewComment') }} {{ cr.review_comment }}
          </div>
        </div>

        <!-- Actions -->
        <div class="request-actions" v-if="cr.status === 'pending' || cr.status === 'approved'">
          <template v-if="cr.status === 'pending'">
            <el-button type="success" size="small" @click="handleReview(cr, 'approve')">
              {{ $t('approvals.approve') }}
            </el-button>
            <el-button type="danger" size="small" @click="handleReview(cr, 'reject')">
              {{ $t('approvals.reject') }}
            </el-button>
          </template>
          <template v-if="cr.status === 'approved'">
            <el-button type="primary" size="small" @click="handleDeploy(cr)">
              {{ $t('approvals.deployEffect') }}
            </el-button>
          </template>
        </div>
      </div>
    </div>

    <!-- Policies Dialog -->
    <el-dialog v-model="showPolicies" :title="$t('approvals.policyConfigTitle')" width="700px" destroy-on-close>
      <div v-loading="loadingPolicies">
        <el-empty v-if="policies.length === 0" :description="$t('approvals.emptyPolicies')" />
        <div v-for="policy in policies" :key="policy.id" class="policy-card">
          <div class="policy-header">
            <h4>{{ policy.name }}</h4>
            <el-tag :type="policy.requires_approval ? 'danger' : 'success'" size="small">
              {{ policy.requires_approval ? $t('approvals.requiresApproval') : $t('approvals.noApproval') }}
            </el-tag>
          </div>
          <p class="policy-desc">{{ policy.description }}</p>
          <div class="policy-conditions">
            <span class="label">{{ $t('approvals.triggerConditions') }}</span>
            <code>{{ JSON.stringify(policy.conditions) }}</code>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Check, ChatDotRound, Setting } from '@element-plus/icons-vue'
import { getLocale } from '@/locales'
import {
  getChangeRequests, reviewChangeRequest, deployChangeRequest,
  getApprovalPolicies, initApprovalPolicies,
  type ChangeRequest, type ApprovalPolicy
} from '../api/approvals'

const { t } = useI18n()

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
    ElMessage.error(t('approvals.loadFailed'))
  } finally {
    loading.value = false
  }
}

const handleTabChange = () => {
  // Filtering is client-side via computed, no fetch needed
}

const handleReview = async (cr: ChangeRequest, action: 'approve' | 'reject') => {
  const actionName = action === 'approve' ? t('approvals.approve') : t('approvals.reject')
  try {
    const { value: comment } = await ElMessageBox.prompt(
      t('approvals.reviewPrompt'),
      t('approvals.confirmAction', { action: actionName }),
      {
        confirmButtonText: actionName,
        cancelButtonText: t('common.cancel'),
        inputPlaceholder: t('approvals.reviewPlaceholder'),
        type: action === 'approve' ? 'success' : 'warning',
      }
    )
    await reviewChangeRequest(cr.id, action, comment || undefined)
    ElMessage.success(t('approvals.actionSuccess', { action: actionName }))
    await fetchRequests()
  } catch (e: unknown) {
    if (e !== 'cancel') {
      ElMessage.error(t('approvals.actionFailed', { action: actionName }))
    }
  }
}

const handleDeploy = async (cr: ChangeRequest) => {
  try {
    await ElMessageBox.confirm(t('approvals.deployConfirmMsg'), t('approvals.deployConfirmTitle'), { type: 'warning' })
    await deployChangeRequest(cr.id)
    ElMessage.success(t('approvals.deploySuccess'))
    await fetchRequests()
  } catch (e: unknown) {
    if (e !== 'cancel') {
      ElMessage.error(t('approvals.deployFailed'))
    }
  }
}

const handleInitPolicies = async () => {
  try {
    const res = await initApprovalPolicies()
    ElMessage.success((res as any).message || t('approvals.initPoliciesSuccess'))
    if (showPolicies.value) await fetchPolicies()
  } catch (e) {
    ElMessage.error(t('approvals.initPoliciesFailed'))
  }
}

const fetchPolicies = async () => {
  loadingPolicies.value = true
  try {
    policies.value = await getApprovalPolicies()
  } catch (e) {
    ElMessage.error(t('approvals.loadPoliciesFailed'))
  } finally {
    loadingPolicies.value = false
  }
}

// Auto-fetch policies when dialog opens
import { watch } from 'vue'
watch(showPolicies, (val) => { if (val) fetchPolicies() })

// Helpers
const getChangeTypeName = (type: string) => {
  const map: Record<string, string> = {
    create: t('approvals.changeTypeCreate'),
    update: t('approvals.changeTypeUpdate'),
    delete: t('approvals.changeTypeDelete'),
    deactivate: t('approvals.changeTypeDeactivate'),
  }
  return map[type] || type
}
const getChangeTypeTag = (type: string) => {
  const map: Record<string, string> = { create: 'success', update: 'primary', delete: 'danger', deactivate: 'warning' }
  return (map[type] || 'info') as any
}
const getPriorityName = (p: string) => {
  const map: Record<string, string> = {
    low: t('approvals.priorityLow'),
    normal: t('approvals.priorityNormal'),
    high: t('approvals.priorityHigh'),
    urgent: t('approvals.priorityUrgent'),
  }
  return map[p] || p
}
const getPriorityTag = (p: string) => {
  const map: Record<string, string> = { low: 'info', normal: '', high: 'warning', urgent: 'danger' }
  return (map[p] || 'info') as any
}
const getStatusName = (s: string) => {
  const map: Record<string, string> = {
    draft: t('approvals.statusDraft'),
    pending: t('approvals.pending'),
    approved: t('approvals.approved'),
    rejected: t('approvals.rejected'),
    deployed: t('approvals.deployed'),
    rolled_back: t('approvals.statusRolledBack'),
  }
  return map[s] || s
}
const getStatusTag = (s: string) => {
  const map: Record<string, string> = { draft: 'info', pending: 'warning', approved: 'success', rejected: 'danger', deployed: 'primary', rolled_back: 'info' }
  return (map[s] || 'info') as any
}
const formatDate = (d: string | null) => {
  if (!d) return ''
  return new Date(d).toLocaleString(getLocale())
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
