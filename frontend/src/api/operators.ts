import apiClient from './client'

export interface OperatorRegistry {
  id: string
  operator_key: string
  display_name: string
  category: string
  description?: string
  operator_type: string
  parameters_schema: Record<string, any>
  output_schema: Record<string, any>
  supports_severity: boolean
  default_severity: string
  priority: number
  is_heavy: boolean
  is_active: boolean
  is_deprecated: boolean
  deprecated_by?: string
  version: string
  created_at: string
  updated_at: string
  // UI rendering fields
  icon?: string
  color?: string
  border_color?: string
  group?: string
}

export interface OperatorTemplate {
  id: string
  name: string
  operator_key: string
  preset_parameters: Record<string, any>
  use_case_description?: string
  is_system: boolean
  created_at: string
}

export interface RuleTemplate {
  id: string
  name: string
  description?: string
  category_suggestions: string[]
  is_system: boolean
  template_rules: Record<string, any>[]
  created_by?: string
  created_at: string
  is_public: boolean
  tags?: string[]
  thumbnail_url?: string
  usage_count?: number
}

// Operator Registry APIs
export const getOperators = async (isActive: boolean = true) => {
  return await apiClient.get<any, OperatorRegistry[]>('/rule-engine/operators/registry', {
    params: { is_active: isActive }
  })
}

export const getOperator = async (operatorKey: string) => {
  return await apiClient.get<any, OperatorRegistry>(`/rule-engine/operators/registry/${operatorKey}`)
}

export const createOperator = async (data: Partial<OperatorRegistry>) => {
  return await apiClient.post<any, OperatorRegistry>('/rule-engine/operators/registry', data)
}

export const updateOperator = async (operatorKey: string, data: Partial<OperatorRegistry>) => {
  return await apiClient.put<any, OperatorRegistry>(`/rule-engine/operators/registry/${operatorKey}`, data)
}

export const deleteOperator = async (operatorKey: string) => {
  return await apiClient.delete(`/rule-engine/operators/registry/${operatorKey}`)
}

// Operator Template APIs
export const getOperatorTemplates = async (operatorKey?: string) => {
  const params = operatorKey ? { operator_key: operatorKey } : {}
  return await apiClient.get<any, OperatorTemplate[]>('/rule-engine/operators/templates', { params })
}

export const createOperatorTemplate = async (data: Partial<OperatorTemplate>) => {
  return await apiClient.post<any, OperatorTemplate>('/rule-engine/operators/templates', data)
}

// Rule Template APIs
export const getRuleTemplates = async (params?: { category?: string; tag?: string; is_public?: boolean }) => {
  return await apiClient.get<any, RuleTemplate[]>('/rule-engine/operators/rule-templates', { params })
}

export const getRuleTemplate = async (templateId: string) => {
  return await apiClient.get<any, RuleTemplate>(`/rule-engine/operators/rule-templates/${templateId}`)
}

export const createRuleTemplate = async (data: Partial<RuleTemplate>) => {
  return await apiClient.post<any, RuleTemplate>('/rule-engine/operators/rule-templates', data)
}

export const updateRuleTemplate = async (templateId: string, data: Partial<RuleTemplate>) => {
  return await apiClient.put<any, RuleTemplate>(`/rule-engine/operators/rule-templates/${templateId}`, data)
}

export const deleteRuleTemplate = async (templateId: string) => {
  return await apiClient.delete(`/rule-engine/operators/rule-templates/${templateId}`)
}

export const applyRuleTemplate = async (templateId: string, categoryId: string) => {
  return await apiClient.post<any, {
    message: string
    category_id: string
    category_name: string
    rules_created: number
    rules: Array<{ id: string; name: string }>
  }>(`/rule-engine/operators/rule-templates/${templateId}/apply`, null, {
    params: { category_id: categoryId }
  })
}

// Initialization APIs
export const initializeRegistry = async () => {
  return await apiClient.get<any, { message: string; initialized: number; updated: number; total: number }>('/rule-engine/operators/init-registry')
}

export const initializeRuleTemplates = async () => {
  return await apiClient.get<any, { message: string; initialized: number; updated: number; total: number }>('/rule-engine/operators/init-rule-templates')
}
