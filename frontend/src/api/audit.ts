import apiClient from './client'

export interface AuditLog {
  id: string
  user_id: string | null
  user_email: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  details: Record<string, any>
  ip_address: string | null
  created_at: string
}

export interface GetAuditLogsParams {
  skip?: number
  limit?: number
  action?: string
  resource_type?: string
  days?: number
}

export const getAuditLogs = (params: GetAuditLogsParams) => {
  return apiClient.get<any, AuditLog[]>('/audit-logs/', { params })
}
