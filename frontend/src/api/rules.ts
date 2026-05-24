import apiClient from './client'

export interface Category {
  id: string
  name: string
  keywords: string[]
  is_active: boolean
}

export interface Rule {
  id: string
  category_id: string | null
  rule_name: string
  rule_type: string
  rule_content: string
  severity: string
  is_active: boolean
}

// Categories API
export const getCategories = async () => {
  return await apiClient.get<any, Category[]>('/rule-engine/categories')
}

export const createCategory = async (data: Partial<Category>) => {
  return await apiClient.post<any, Category>('/rule-engine/categories', data)
}

export const updateCategory = async (id: string, data: Partial<Category>) => {
  return await apiClient.put<any, Category>(`/rule-engine/categories/${id}`, data)
}

export const deleteCategory = async (id: string) => {
  return await apiClient.delete(`/rule-engine/categories/${id}`)
}

// Rules API
export const getRules = async (categoryId?: string) => {
  const params = categoryId ? { category_id: categoryId } : {}
  return await apiClient.get<any, Rule[]>('/rule-engine/rules', { params })
}

export const createRule = async (data: Partial<Rule>) => {
  return await apiClient.post<any, Rule>('/rule-engine/rules', data)
}

export const updateRule = async (id: string, data: Partial<Rule>) => {
  return await apiClient.put<any, Rule>(`/rule-engine/rules/${id}`, data)
}

export const deleteRule = async (id: string) => {
  return await apiClient.delete(`/rule-engine/rules/${id}`)
}
