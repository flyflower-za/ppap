import client from './client'

export interface VerificationModule {
  id: string
  name: string
  description?: string
  module_type: string
  severity: 'critical' | 'warning' | 'info'
  config: Record<string, any>
  category_id?: string
  is_active: boolean
  is_system: boolean
  sort_order: number
  created_at?: number
  updated_at?: number
  metadata?: {
    label: string
    description: string
    icon: string
    config_fields: Array<{
      key: string
      label: string
      type: string
      default?: any
      options?: string[]
    }>
  }
}

export interface VerificationModuleCreate {
  name: string
  description?: string
  module_type: string
  severity?: 'critical' | 'warning' | 'info'
  config: Record<string, any>
  category_id?: string
  is_active?: boolean
  sort_order?: number
}

export interface VerificationModuleUpdate {
  name?: string
  description?: string
  module_type?: string
  severity?: 'critical' | 'warning' | 'info'
  config?: Record<string, any>
  category_id?: string
  is_active?: boolean
  sort_order?: number
}

export interface ModuleMetadata {
  module_types: Record<string, {
    label: string
    description: string
    icon: string
    config_fields: Array<{
      key: string
      label: string
      type: string
      default?: any
      options?: string[]
    }>
  }>
}

export interface RuleModuleAssign {
  module_ids: string[]
}

export interface RuleModulesResponse {
  rule_id: string
  modules: VerificationModule[]
}

export const verificationModulesApi = {
  // 获取模块元数据（用于前端表单渲染）
  getMetadata(): Promise<ModuleMetadata> {
    return client.get('/rule-engine/modules/metadata')
  },

  // 获取所有校验模块
  listModules(params?: { category_id?: string; is_active?: boolean }): Promise<VerificationModule[]> {
    return client.get('/rule-engine/modules', { params })
  },

  // 获取单个模块详情
  getModule(moduleId: string): Promise<VerificationModule> {
    return client.get(`/rule-engine/modules/${moduleId}`)
  },

  // 创建新模块
  createModule(data: VerificationModuleCreate): Promise<VerificationModule> {
    return client.post('/rule-engine/modules', data)
  },

  // 更新模块
  updateModule(moduleId: string, data: VerificationModuleUpdate): Promise<VerificationModule> {
    return client.put(`/rule-engine/modules/${moduleId}`, data)
  },

  // 删除模块
  deleteModule(moduleId: string): Promise<{ message: string }> {
    return client.delete(`/rule-engine/modules/${moduleId}`)
  },

  // 恢复默认系统模块
  restoreDefaults(): Promise<{ message: string }> {
    return client.post('/rule-engine/modules/restore-defaults')
  },

  // 获取规则关联的模块列表
  getRuleModules(ruleId: string): Promise<RuleModulesResponse> {
    return client.get(`/rule-engine/modules/rule/${ruleId}/modules`)
  },

  // 为规则分配模块（替换现有分配）
  assignRuleModules(ruleId: string, data: RuleModuleAssign): Promise<{ message: string }> {
    return client.put(`/rule-engine/modules/rule/${ruleId}/modules`, data)
  }
}
