/**
 * Settings API client
 */
import client from './client'

export interface SmtpConfig {
  enabled: boolean
  host: string | null
  port: number
  encryption: 'none' | 'tls' | 'ssl'
  username: string | null
  from_name: string
  password?: string | null
}

export interface NotificationSettings {
  email_enabled: boolean
  notify_on_failure: boolean
  daily_summary: boolean
}

export interface EmailTemplate {
  id: string
  name: string
  subject: string
  html_content: string
  description?: string
  variables: string[]
  is_active: boolean
}

export interface EmailTemplatePreview {
  template_id: string
  context: Record<string, any>
}

export interface FileRetentionSettings {
  retention_days: number
  auto_cleanup_enabled: boolean
  cleanup_hour: number
}

export const settingsApi = {
  /**
   * Get notification settings
   */
  getNotificationSettings(): Promise<NotificationSettings> {
    return client.get<any, NotificationSettings>('/settings/notifications')
  },

  /**
   * Update notification settings
   */
  updateNotificationSettings(settings: NotificationSettings): Promise<{ message: string; settings: NotificationSettings }> {
    return client.post<any, { message: string; settings: NotificationSettings }>('/settings/notifications', settings)
  },

  /**
   * Get SMTP configuration
   */
  getSmtpConfig(): Promise<SmtpConfig> {
    return client.get<any, SmtpConfig>('/settings/smtp')
  },

  /**
   * Update SMTP configuration
   */
  updateSmtpConfig(config: SmtpConfig): Promise<{ message: string; config: Partial<SmtpConfig> }> {
    return client.post<any, { message: string; config: Partial<SmtpConfig> }>('/settings/smtp', config)
  },

  /**
   * Test SMTP configuration by sending a test email
   */
  testSmtpConfig(config: SmtpConfig, testEmail?: string): Promise<{ message: string; success: boolean }> {
    return client.post<any, { message: string; success: boolean }>('/settings/smtp/test', {
      config,
      test_email: testEmail
    })
  },

  /**
   * Get all email templates
   */
  getEmailTemplates(): Promise<EmailTemplate[]> {
    return client.get<any, EmailTemplate[]>('/settings/email-templates')
  },

  /**
   * Get a specific email template
   */
  getEmailTemplate(templateId: string): Promise<EmailTemplate> {
    return client.get<any, EmailTemplate>(`/settings/email-templates/${templateId}`)
  },

  /**
   * Create a new email template
   */
  createEmailTemplate(template: EmailTemplate): Promise<{ message: string; template: EmailTemplate }> {
    return client.post<any, { message: string; template: EmailTemplate }>('/settings/email-templates', template)
  },

  /**
   * Update an existing email template
   */
  updateEmailTemplate(templateId: string, template: EmailTemplate): Promise<{ message: string }> {
    return client.put<any, { message: string }>(`/settings/email-templates/${templateId}`, template)
  },

  /**
   * Delete an email template
   */
  deleteEmailTemplate(templateId: string): Promise<{ message: string }> {
    return client.delete<any, { message: string }>(`/settings/email-templates/${templateId}`)
  },

  /**
   * Preview an email template
   */
  previewEmailTemplate(preview: EmailTemplatePreview): Promise<{ html_content: string }> {
    return client.post<any, { html_content: string }>('/settings/email-templates/preview', preview)
  },

  /**
   * Get file retention settings
   */
  getFileRetentionSettings(): Promise<FileRetentionSettings> {
    return client.get<any, FileRetentionSettings>('/settings/file-retention')
  },

  /**
   * Update file retention settings
   */
  updateFileRetentionSettings(settings: FileRetentionSettings): Promise<{ message: string; settings: FileRetentionSettings }> {
    return client.post<any, { message: string; settings: FileRetentionSettings }>('/settings/file-retention', settings)
  },

  /**
   * Trigger immediate file cleanup
   */
  triggerCleanupNow(): Promise<{ message: string; task_id: string }> {
    return client.post<any, { message: string; task_id: string }>('/settings/file-retention/cleanup-now')
  }
}
