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
  getLDAPConfig(): Promise<LDAPConfig> {
    return client.get<any, LDAPConfig>('/settings/ldap-config')
  },

  /**
   * Update LDAP/SSO configuration
   */
  updateLDAPConfig(config: LDAPConfig): Promise<{ message: string; config: Partial<LDAPConfig> }> {
    return client.post<any, { message: string; config: Partial<LDAPConfig> }>('/settings/ldap-config', config)
  },

  /**
   * Test LDAP connection
   */
  testLDAPConnection(): Promise<{ message: string; success: boolean }> {
    return client.post<any, { message: string; success: boolean }>('/settings/ldap-config/test')
  },

  /**
   * Get all users
   */
  getAllUsers(): Promise<UserInfo[]> {
    return client.get<any, UserInfo[]>('/settings/users')
  },

  /**
   * Update user role
   */
  updateUserRole(userId: string, role: 'ADMIN' | 'MANAGER' | 'USER'): Promise<{ message: string; role: string }> {
    return client.put<any, { message: string; role: string }>(`/settings/users/${userId}/role`, null, {
      params: { role }
    })
  }
}
