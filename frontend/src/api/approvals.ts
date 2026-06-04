import apiClient from './client'

export interface ChangeRequest {
  id: string
  rule_id: string | null
  change_type: string
  proposed_rule_data: any
  reason: string | null
  impact_assessment: string | null
  status: string
  requested_by: string | null
  requested_at: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  review_comment: string | null
  deployed_by: string | null
  deployed_at: string | null
  category_id: string | null
  priority: string
  test_results: any
  requester_name: string | null
  reviewer_name: string | null
  deployer_name: string | null
}

export interface ApprovalPolicy {
  id: string
  name: string
  description: string | null
  conditions: any
  requires_approval: boolean
  required_approvers: any
  min_approvals_required: number
  is_active: boolean
  created_at: string | null
}

// Change Requests API
export const getChangeRequests = async (status?: string) => {
  const params = status ? { status } : {}
  return await apiClient.get<any, ChangeRequest[]>('/rule-engine/approvals/change-requests', { params })
}

export const createChangeRequest = async (data: {
  rule_id?: string
  change_type: string
  proposed_rule_data: any
  reason: string
  impact_assessment?: string
  priority?: string
  category_id?: string
  test_results?: any
}) => {
  return await apiClient.post<any, ChangeRequest>('/rule-engine/approvals/change-requests', data)
}

export const getChangeRequest = async (id: string) => {
  return await apiClient.get<any, ChangeRequest>(`/rule-engine/approvals/change-requests/${id}`)
}

export const reviewChangeRequest = async (id: string, action: 'approve' | 'reject', comment?: string) => {
  return await apiClient.post<any, ChangeRequest>(`/rule-engine/approvals/change-requests/${id}/review`, {
    action,
    comment
  })
}

export const deployChangeRequest = async (id: string) => {
  return await apiClient.post<any, ChangeRequest>(`/rule-engine/approvals/change-requests/${id}/deploy`)
}

// Policies API
export const getApprovalPolicies = async () => {
  return await apiClient.get<any, ApprovalPolicy[]>('/rule-engine/approvals/policies')
}

export const initApprovalPolicies = async () => {
  return await apiClient.post('/rule-engine/approvals/policies/init')
}
