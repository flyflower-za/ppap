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

export const settingsApi = {
  /**
   * Get notification settings
   */
  async getNotificationSettings(): Promise<NotificationSettings> {
    const response = await client.get<NotificationSettings>('/settings/notifications')
    return response.data
  },

  /**
   * Update notification settings
   */
  async updateNotificationSettings(settings: NotificationSettings): Promise<{ message: string; settings: NotificationSettings }> {
    const response = await client.post('/settings/notifications', settings)
    return response.data
  },

  /**
   * Get SMTP configuration
   */
  async getSmtpConfig(): Promise<SmtpConfig> {
    const response = await client.get<SmtpConfig>('/settings/smtp')
    return response.data
  },

  /**
   * Update SMTP configuration
   */
  async updateSmtpConfig(config: SmtpConfig): Promise<{ message: string; config: Partial<SmtpConfig> }> {
    const response = await client.post('/settings/smtp', config)
    return response.data
  },

  /**
   * Test SMTP configuration by sending a test email
   */
  async testSmtpConfig(config: SmtpConfig, testEmail?: string): Promise<{ message: string; success: boolean }> {
    const response = await client.post('/settings/smtp/test', {
      config,
      test_email: testEmail
    })
    return response.data
  },

  /**
   * Get all email templates
   */
  async getEmailTemplates(): Promise<EmailTemplate[]> {
    const response = await client.get<EmailTemplate[]>('/settings/email-templates')
    return response.data
  },

  /**
   * Get a specific email template
   */
  async getEmailTemplate(templateId: string): Promise<EmailTemplate> {
    const response = await client.get<EmailTemplate>(`/settings/email-templates/${templateId}`)
    return response.data
  },

  /**
   * Create a new email template
   */
  async createEmailTemplate(template: EmailTemplate): Promise<{ message: string; template: EmailTemplate }> {
    const response = await client.post('/settings/email-templates', template)
    return response.data
  },

  /**
   * Update an existing email template
   */
  async updateEmailTemplate(templateId: string, template: EmailTemplate): Promise<{ message: string }> {
    const response = await client.put(`/settings/email-templates/${templateId}`, template)
    return response.data
  },

  /**
   * Delete an email template
   */
  async deleteEmailTemplate(templateId: string): Promise<{ message: string }> {
    const response = await client.delete(`/settings/email-templates/${templateId}`)
    return response.data
  },

  /**
   * Preview an email template
   */
  async previewEmailTemplate(preview: EmailTemplatePreview): Promise<{ html_content: string }> {
    const response = await client.post('/settings/email-templates/preview', preview)
    return response.data
  }
}
