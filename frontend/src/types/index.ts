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
export type FileStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'warning' | 'needs_review'
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
  institution?: string
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

// Audit
export interface AuditLogEntry {
  id: string
  user_id: string
  user_email: string
  action: string
  resource_type: string
  resource_id?: string
  details?: Record<string, unknown>
  ip_address?: string
  created_at: string
}

export interface AuditLogResponse {
  total: number
  page: number
  page_size: number
  items: AuditLogEntry[]
}

// Approval
export interface ApprovalItem {
  id: string
  file_id: string
  filename: string
  rule_name: string
  proposed_rule_data?: Record<string, unknown>
  status: 'pending' | 'approved' | 'rejected'
  reviewer_id?: string
  reviewer_comment?: string
  test_results?: Record<string, unknown>
  created_at: string
  reviewed_at?: string
}

export interface ApprovalListResponse {
  total: number
  items: ApprovalItem[]
}

// Verification execution
export interface ExecutionTrajectoryEntry {
  operator: string
  status: string
  duration_ms?: number
  message?: string
  result?: Record<string, unknown>
}

export interface ExecutionLog {
  timestamp: string
  message: string
  level?: string
}

// Stats / Dashboard
export interface DashboardStats {
  total_files: number
  completed_files: number
  failed_files: number
  pending_files: number
  avg_processing_time: number
  top_failing_rules: { rule_name: string; count: number }[]
  daily_trend: { date: string; total: number; passed: number; failed: number }[]
}

// Task (file with verification progress)
export interface TaskFile extends File {
  institution?: string
  ref_count?: number
  failed_checks?: { title?: string; rule_name?: string; message?: string; severity?: string }[]
}
