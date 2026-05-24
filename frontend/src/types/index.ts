// User & Auth
export interface User {
  id: string
  email: string
  full_name: string
  department?: string
  avatar_url?: string
  role: 'ADMIN' | 'MANAGER' | 'USER'
  is_active: boolean
  is_admin: boolean
  email_notifications_enabled: boolean
  created_at: string
  last_login_at?: string
}

export interface LoginRequest {
  email: string
  sso_token?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

// File
export type FileStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'warning'
export type FileType = 'production_plan' | 'quality_report' | 'purchase_order' | 'supplier_qualification' | 'product_specification' | 'other'

export interface File {
  id: string
  filename: string
  original_filename: string
  file_size: number
  file_type: FileType
  page_count?: number
  status: FileStatus
  verification_progress: number
  pass_count: number
  warning_count: number
  fail_count: number
  pass_rate?: number
  uploaded_at: string
  completed_at?: string
  duration_seconds?: number
  verification_result_json?: Record<string, any>
}

export interface FileDetail extends File {
  verification_result?: VerificationResult
  uploaded_by?: string
}

export interface VerificationResult {
  status: 'pass' | 'warning' | 'fail'
  checks: VerificationCheck[]
  summary: {
    total: number
    pass: number
    warning: number
    fail: number
  }
  model_version: string
}

export interface VerificationCheck {
  name: string
  status: 'pass' | 'warning' | 'fail'
  message: string
  page?: number
  details?: Record<string, unknown>
}

export interface FileListResponse {
  total: number
  page: number
  page_size: number
  items: File[]
}

export interface FileFilter {
  status?: FileStatus
  file_type?: FileType
  keyword?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

// Notification
export type NotificationType = 'success' | 'error' | 'warning' | 'info'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message?: string
  link?: string
  is_read: boolean
  created_at: string
}

export interface NotificationListResponse {
  total: number
  unread_count: number
  items: Notification[]
}

// Note
export interface Note {
  id: string
  file_id: string
  author_id: string
  author_name: string
  content: string
  created_at: string
  updated_at: string
}

export interface NoteCreate {
  file_id: string
  content: string
}
