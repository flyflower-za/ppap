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

export interface AiModelConfig {
  enabled: boolean
  base_url: string
  api_key: string | null
  text_model: string
  vision_model: string
  max_tokens: number
  temperature: number
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
  },

  // ==================== AI Model Configuration ====================

  /**
   * Get AI model configuration
   */
  getAiModelConfig(): Promise<AiModelConfig> {
    return client.get<any, AiModelConfig>('/settings/ai-model')
  },

  /**
   * Update AI model configuration
   */
  updateAiModelConfig(config: AiModelConfig): Promise<{ message: string }> {
    return client.post<any, { message: string }>('/settings/ai-model', config)
  },

  /**
   * Test AI model connection
   */
  testAiModelConfig(config: AiModelConfig): Promise<{ success: boolean; message: string }> {
    return client.post<any, { success: boolean; message: string }>('/settings/ai-model/test', config)
  },

  // ==================== Multi-Model Profiles ====================

  /** List enabled model profiles for all users */
  listPublicModelProfiles(): Promise<PublicModelProfile[]> {
    return client.get<any, PublicModelProfile[]>('/settings/ai-models/public')
  },

  /** List all model profiles (admin only) */
  listModelProfiles(): Promise<ModelProfile[]> {
    return client.get<any, ModelProfile[]>('/settings/ai-models')
  },

  /** Create a new model profile */
  createModelProfile(profile: Omit<ModelProfile, 'id'>): Promise<{ message: string; profile: ModelProfile }> {
    return client.post<any, { message: string; profile: ModelProfile }>('/settings/ai-models', profile)
  },

  /** Update a model profile */
  updateModelProfile(id: string, profile: ModelProfile): Promise<{ message: string; profile: ModelProfile }> {
    return client.put<any, { message: string; profile: ModelProfile }>(`/settings/ai-models/${id}`, profile)
  },

  /** Delete a model profile */
  deleteModelProfile(id: string): Promise<{ message: string }> {
    return client.delete<any, { message: string }>(`/settings/ai-models/${id}`)
  },

  /** Test a model profile by ID */
  testModelProfile(id: string): Promise<{ success: boolean; message: string }> {
    return client.post<any, { success: boolean; message: string }>(`/settings/ai-models/${id}/test`)
  },

  /** Set a profile as default for text or vision */
  setDefaultModelProfile(id: string, forType: 'text' | 'vision'): Promise<{ message: string }> {
    return client.post<any, { message: string }>(`/settings/ai-models/${id}/set-default`, { for_type: forType })
  }
}

export interface PublicModelProfile {
  id: string
  name: string
  model_name: string
  model_type: 'text' | 'vision' | 'both'
}

export interface ModelProfile {
  id: string
  name: string
  base_url: string
  api_key: string | null
  model_name: string
  model_type: 'text' | 'vision' | 'both'
  max_tokens: number
  temperature: number
  enabled: boolean
  is_default_text: boolean
  is_default_vision: boolean
}
