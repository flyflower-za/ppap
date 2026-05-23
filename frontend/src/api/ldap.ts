/**
 * LDAP/SSO Configuration API client
 */
import client from './client'

export interface LDAPConfig {
  ldap_enabled: boolean
  ldap_server: string | null
  ldap_port: number | null
  ldap_use_ssl: boolean
  ldap_bind_dn: string | null
  ldap_bind_password: string | null
  ldap_search_base: string | null
  ldap_search_filter: string
  ldap_email_attribute: string
  ldap_name_attribute: string
  ldap_department_attribute: string
  ad_admin_group: string | null
  ad_manager_group: string | null
  ad_user_group: string | null
  sso_enabled: boolean
  sso_provider: string | null
  sso_entity_id: string | null
  sso_acs_url: string | null
  sso_slo_url: string | null
  sso_idp_sso_url: string | null
  sso_idp_cert: string | null
  sso_sp_cert: string | null
  sso_sp_key: string | null
  local_admin_enabled: boolean
  auto_create_users: boolean
  default_role: 'ADMIN' | 'MANAGER' | 'USER'
}

export interface UserInfo {
  id: string
  email: string
  full_name: string
  department: string | null
  role: string
  is_active: boolean
  created_at: string | null
  last_login_at: string | null
}

export const ldapApi = {
  /**
   * Get LDAP/SSO configuration
   */
  async getLDAPConfig(): Promise<LDAPConfig> {
    const response = await client.get<LDAPConfig>('/settings/ldap-config')
    return response.data
  },

  /**
   * Update LDAP/SSO configuration
   */
  async updateLDAPConfig(config: LDAPConfig): Promise<{ message: string; config: Partial<LDAPConfig> }> {
    const response = await client.post('/settings/ldap-config', config)
    return response.data
  },

  /**
   * Test LDAP connection
   */
  async testLDAPConnection(): Promise<{ message: string; success: boolean }> {
    const response = await client.post('/settings/ldap-config/test')
    return response.data
  },

  /**
   * Get all users
   */
  async getAllUsers(): Promise<UserInfo[]> {
    const response = await client.get<UserInfo[]>('/settings/users')
    return response.data
  },

  /**
   * Update user role
   */
  async updateUserRole(userId: string, role: 'ADMIN' | 'MANAGER' | 'USER'): Promise<{ message: string; role: string }> {
    const response = await client.put(`/settings/users/${userId}/role`, null, {
      params: { role }
    })
    return response.data
  }
}
