<template>
  <div class="settings-container">
    <h2 class="mb-4">{{ $t('settings.title') }}</h2>

    <el-row :gutter="32" type="flex" class="settings-row">
      <el-col :span="5" class="settings-menu-col">
        <el-menu :default-active="activeMenu" @select="handleMenuSelect" class="settings-menu">
          <!-- 个人设置组 -->
          <el-menu-item-group title="个人设置">
            <el-menu-item index="profile">
              <el-icon><User /></el-icon>
              <span>{{ $t('settings.menuProfile') }}</span>
            </el-menu-item>
            <el-menu-item index="notification">
              <el-icon><Bell /></el-icon>
              <span>{{ $t('settings.menuNotification') }}</span>
            </el-menu-item>
          </el-menu-item-group>

          <!-- 系统配置组 -->
          <el-menu-item-group title="系统配置" v-if="canAccessSettings('file_retention') || canAccessSettings('smtp') || canAccessSettings('email_templates') || canAccessSettings('ldap') || canAccessSettings('ai_model')">
            <el-menu-item index="file-retention" v-if="canAccessSettings('file_retention')">
              <el-icon><FolderOpened /></el-icon>
              <span>{{ $t('settings.menuFileRetention') }}</span>
            </el-menu-item>
            <el-menu-item index="smtp" v-if="canAccessSettings('smtp')">
              <el-icon><Setting /></el-icon>
              <span>{{ $t('settings.menuSmtp') }}</span>
            </el-menu-item>
            <el-menu-item index="templates" v-if="canAccessSettings('email_templates')">
              <el-icon><Document /></el-icon>
              <span>{{ $t('settings.menuTemplates') }}</span>
            </el-menu-item>
            <el-menu-item index="ldap" v-if="canAccessSettings('ldap')">
              <el-icon><Lock /></el-icon>
              <span>{{ $t('settings.menuLdap') }}</span>
            </el-menu-item>
            <el-menu-item index="ai-model" v-if="canAccessSettings('ai_model')">
              <el-icon><Cpu /></el-icon>
              <span>{{ $t('settings.menuAiModel') }}</span>
            </el-menu-item>
          </el-menu-item-group>

          <!-- 用户管理组 -->
          <el-menu-item-group title="用户管理" v-if="canAccessSettings('users')">
            <el-menu-item index="users" v-if="canAccessSettings('users')">
              <el-icon><UserFilled /></el-icon>
              <span>{{ $t('settings.menuUsers') }}</span>
            </el-menu-item>
          </el-menu-item-group>
        </el-menu>
      </el-col>

      <el-col :span="19">
        <!-- Profile Section -->
        <el-card v-if="activeMenu === 'profile'" shadow="never">
          <template #header>
            <span>{{ $t('settings.profileTitle') }}</span>
          </template>

          <el-descriptions :column="1" border>
            <el-descriptions-item :label="$t('settings.loginName')">{{ authStore.user?.email }}</el-descriptions-item>
            <el-descriptions-item :label="$t('settings.username')">{{ authStore.user?.username || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('settings.fullName')">{{ authStore.user?.full_name }}</el-descriptions-item>
            <el-descriptions-item :label="$t('settings.department')">{{ authStore.user?.department || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('settings.email')">{{ authStore.user?.email }}</el-descriptions-item>
            <el-descriptions-item :label="$t('settings.loginMethod')">
              <el-tag size="small">{{ authStore.user?.sso_id ? $t('settings.loginMethodSso') : $t('settings.loginMethodPassword') }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <el-alert
            type="info"
            :closable="false"
            class="mt-4"
          >
            {{ $t('settings.profileLdapHint') }}
          </el-alert>

          <div class="mt-4">
            <el-button type="primary" :icon="Key" @click="openChangePasswordDialog">{{ $t('settings.changePassword') }}</el-button>
          </div>
        </el-card>

        <!-- Notification Section -->
        <el-card v-if="activeMenu === 'notification'" shadow="never" v-loading="loadingNotif">
          <template #header>
            <span>{{ $t('settings.notificationTitle') }}</span>
          </template>

          <div class="notification-setting">
            <div class="setting-item">
              <div class="setting-info">
                <h4>{{ $t('settings.enableEmailNotification') }}</h4>
                <p>{{ $t('settings.enableEmailNotificationDesc') }}</p>
              </div>
              <el-switch v-model="emailEnabled" />
            </div>

            <el-divider />

            <div class="setting-item">
              <div class="setting-info">
                <h4>{{ $t('settings.failureNotification') }}</h4>
                <p>{{ $t('settings.failureNotificationDesc') }}</p>
              </div>
              <el-switch v-model="notifyOnFailure" />
            </div>

            <el-divider />

            <div class="setting-item">
              <div class="setting-info">
                <h4>{{ $t('settings.dailySummary') }}</h4>
                <p>{{ $t('settings.dailySummaryDesc') }}</p>
              </div>
              <el-switch v-model="dailySummary" />
            </div>
          </div>

          <el-divider class="my-4" />

          <div class="notification-actions">
            <el-button
              type="primary"
              :icon="Check"
              :loading="savingNotif"
              @click="handleSaveNotification"
            >
              {{ $t('settings.saveNotificationSettings') }}
            </el-button>
          </div>

          <el-alert
            v-if="notifSaveSuccess"
            type="success"
            :title="$t('settings.notificationSaved')"
            :description="$t('settings.notificationSavedDesc')"
            :closable="false"
            show-icon
            class="mt-4"
          />
        </el-card>

        <!-- File Retention Settings Section -->
        <el-card v-if="activeMenu === 'file-retention'" shadow="never" v-loading="loadingFileRetention">
          <template #header>
            <div class="flex-between">
              <span>{{ $t('settings.fileRetentionTitle') }}</span>
              <el-tag :type="fileRetentionSettings.auto_cleanup_enabled ? 'success' : 'info'" size="small">
                {{ fileRetentionSettings.auto_cleanup_enabled ? $t('settings.autoCleanupEnabled') : $t('settings.autoCleanupDisabled') }}
              </el-tag>
            </div>
          </template>

          <el-alert
            type="info"
            :title="$t('settings.fileAutoCleanupTitle')"
            :description="$t('settings.fileAutoCleanupDesc')"
            :closable="false"
            show-icon
            class="mb-4"
          />

          <el-form
            ref="fileRetentionFormRef"
            :model="fileRetentionSettings"
            :rules="fileRetentionRules"
            label-width="200px"
            class="file-retention-form"
          >
            <el-form-item :label="$t('settings.enableAutoCleanup')" prop="auto_cleanup_enabled">
              <el-switch v-model="fileRetentionSettings.auto_cleanup_enabled" />
              <span class="form-tip">{{ $t('settings.enableAutoCleanupTip') }}</span>
            </el-form-item>

            <el-form-item :label="$t('settings.retentionDays')" prop="retention_days">
              <el-input-number
                v-model="fileRetentionSettings.retention_days"
                :min="1"
                :max="3650"
                :step="1"
                :disabled="!fileRetentionSettings.auto_cleanup_enabled"
                controls-position="right"
                style="width: 200px"
              />
              <span class="form-tip">{{ $t('settings.retentionDaysTip') }}</span>
            </el-form-item>

            <el-form-item :label="$t('settings.cleanupHour')" prop="cleanup_hour">
              <el-select
                v-model="fileRetentionSettings.cleanup_hour"
                :disabled="!fileRetentionSettings.auto_cleanup_enabled"
                :placeholder="$t('settings.cleanupHourPlaceholder')"
                style="width: 200px"
              >
                <el-option
                  v-for="hour in 24"
                  :key="hour - 1"
                  :label="`${hour - 1}:00`"
                  :value="hour - 1"
                />
              </el-select>
              <span class="form-tip">{{ $t('settings.cleanupHourTip') }}</span>
            </el-form-item>

            <el-divider />

            <el-form-item>
              <el-button
                type="primary"
                :icon="Check"
                :loading="savingFileRetention"
                @click="handleSaveFileRetention"
              >
                {{ $t('settings.saveSettings') }}
              </el-button>
              <el-button
                :icon="Delete"
                :loading="triggeringCleanup"
                :disabled="!fileRetentionSettings.auto_cleanup_enabled"
                @click="handleTriggerCleanup"
              >
                {{ $t('settings.executeCleanupNow') }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="fileRetentionSaveSuccess"
            type="success"
            :title="$t('settings.fileRetentionSaved')"
            :description="$t('settings.fileRetentionSavedDesc')"
            :closable="false"
            show-icon
            class="mt-4"
          />

          <el-alert
            v-if="cleanupTriggerSuccess"
            type="success"
            :title="$t('settings.cleanupStarted')"
            :description="cleanupTriggerMessage"
            :closable="false"
            show-icon
            class="mt-4"
          />
        </el-card>

        <!-- SMTP Configuration Section -->
        <el-card v-if="activeMenu === 'smtp'" shadow="never" v-loading="loading">
          <template #header>
            <div class="flex-between">
              <span>{{ $t('settings.smtpTitle') }}</span>
              <el-tag :type="smtpConfig.enabled ? 'success' : 'info'" size="small">
                {{ smtpConfig.enabled ? $t('settings.enabled') : $t('settings.notEnabled') }}
              </el-tag>
            </div>
          </template>

          <el-form
            ref="smtpFormRef"
            :model="smtpConfig"
            :rules="smtpRules"
            label-width="180px"
            class="smtp-form"
          >
            <el-form-item :label="$t('settings.enableSmtp')" prop="enabled">
              <el-switch
                v-model="smtpConfig.enabled"
              />
              <span class="form-tip">{{ $t('settings.enableSmtpTip') }}</span>
            </el-form-item>

            <el-divider content-position="left">{{ $t('settings.serverConfig') }}</el-divider>

            <el-form-item :label="$t('settings.smtpServer')" prop="host">
              <el-input
                v-model="smtpConfig.host"
                :placeholder="$t('settings.smtpServerPlaceholder')"
                :disabled="!smtpConfig.enabled"
                clearable
              />
            </el-form-item>

            <el-form-item :label="$t('settings.port')" prop="port">
              <el-input
                v-model="smtpConfig.port"
                type="number"
                placeholder="587"
                :disabled="!smtpConfig.enabled"
                clearable
              />
              <span class="form-tip">{{ $t('settings.portTip') }}</span>
            </el-form-item>

            <el-form-item :label="$t('settings.encryption')" prop="encryption">
              <el-radio-group v-model="smtpConfig.encryption" :disabled="!smtpConfig.enabled">
                <el-radio value="none">{{ $t('settings.encryptionNone') }}</el-radio>
                <el-radio value="tls">TLS</el-radio>
                <el-radio value="ssl">SSL</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-divider content-position="left">{{ $t('settings.accountAuth') }}</el-divider>

            <el-form-item :label="$t('settings.senderEmail')" prop="username">
              <el-input
                v-model="smtpConfig.username"
                :placeholder="$t('settings.senderEmailPlaceholder')"
                :disabled="!smtpConfig.enabled"
                clearable
              />
            </el-form-item>

            <el-form-item :label="$t('settings.senderName')" prop="from_name">
              <el-input
                v-model="smtpConfig.from_name"
                :placeholder="$t('settings.senderNamePlaceholder')"
                :disabled="!smtpConfig.enabled"
                clearable
              />
            </el-form-item>

            <el-form-item :label="$t('settings.passwordOrAuthCode')" prop="password">
              <el-input
                v-model="smtpConfig.password"
                type="password"
                :placeholder="$t('settings.passwordPlaceholder')"
                :disabled="!smtpConfig.enabled"
                show-password
                clearable
              />
              <span class="form-tip">{{ $t('settings.passwordTip') }}</span>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :icon="MessageBox"
                :loading="testing"
                :disabled="!smtpConfig.enabled"
                @click="handleTestEmail"
              >
                {{ $t('settings.sendTestEmail') }}
              </el-button>
              <el-button
                type="success"
                :icon="Check"
                :loading="saving"
                @click="handleSaveSmtp"
              >
                {{ $t('settings.saveConfig') }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="saveSuccess"
            type="success"
            :title="$t('settings.smtpSaved')"
            :description="$t('settings.smtpSavedDesc')"
            :closable="false"
            show-icon
            class="mt-4"
          />
        </el-card>

        <!-- Email Templates Section -->
        <el-card v-if="activeMenu === 'templates'" shadow="never" v-loading="loadingTemplates">
          <template #header>
            <div class="flex-between">
              <span>{{ $t('settings.templateTitle') }}</span>
              <el-button
                type="primary"
                :icon="Plus"
                size="small"
                @click="handleCreateTemplate"
              >
                {{ $t('settings.createTemplate') }}
              </el-button>
            </div>
          </template>

          <el-table :data="templates" style="width: 100%">
            <el-table-column prop="name" :label="$t('settings.templateName')" width="200" />
            <el-table-column prop="id" :label="$t('settings.templateId')" width="180" />
            <el-table-column prop="description" :label="$t('settings.description')" show-overflow-tooltip />
            <el-table-column :label="$t('settings.variables')" width="300">
              <template #default="scope">
                <el-tag
                  v-for="variable in scope.row.variables"
                  :key="variable"
                  size="small"
                  class="mr-1"
                >
                  {{ formatVariable(variable) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('settings.status')" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.is_active ? 'success' : 'info'" size="small">
                  {{ scope.row.is_active ? $t('settings.statusEnabled') : $t('settings.statusDisabled') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('settings.actions')" width="180" fixed="right">
              <template #default="scope">
                <el-button
                  type="primary"
                  :icon="Edit"
                  size="small"
                  link
                  @click="handleEditTemplate(scope.row)"
                >
                  {{ $t('settings.edit') }}
                </el-button>
                <el-button
                  type="primary"
                  size="small"
                  link
                  @click="handlePreviewTemplate(scope.row)"
                >
                  {{ $t('settings.preview') }}
                </el-button>
                <el-popconfirm
                  :title="$t('settings.deleteTemplateConfirm')"
                  @confirm="handleDeleteTemplate(scope.row.id)"
                >
                  <template #reference>
                    <el-button type="danger" size="small" link>{{ $t('settings.delete') }}</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- Template Edit Dialog -->
        <el-dialog
          v-model="templateDialogVisible"
          :title="editingTemplate?.id ? $t('settings.editTemplate') : $t('settings.createNewTemplate')"
          width="80%"
          :close-on-click-modal="false"
        >
          <el-form
            ref="templateFormRef"
            :model="templateForm"
            :rules="templateRules"
            label-width="120px"
          >
            <el-form-item :label="$t('settings.templateId')" prop="id">
              <el-input
                v-model="templateForm.id"
                :placeholder="$t('settings.templateIdPlaceholder')"
                :disabled="!!editingTemplate?.id"
                clearable
              />
              <span class="form-tip">{{ $t('settings.templateIdTip') }}</span>
            </el-form-item>

            <el-form-item :label="$t('settings.templateName')" prop="name">
              <el-input
                v-model="templateForm.name"
                :placeholder="$t('settings.templateNamePlaceholder')"
                clearable
              />
            </el-form-item>

            <el-form-item :label="$t('settings.description')" prop="description">
              <el-input
                v-model="templateForm.description"
                type="textarea"
                :rows="2"
                :placeholder="$t('settings.descriptionPlaceholder')"
              />
            </el-form-item>

            <el-form-item :label="$t('settings.emailSubject')" prop="subject">
              <el-input
                v-model="templateForm.subject"
                :placeholder="$t('settings.emailSubjectPlaceholder')"
                clearable
              />
              <span class="form-tip">{{ $t('settings.emailSubjectTip') }}</span>
            </el-form-item>

            <el-form-item :label="$t('settings.htmlContent')" prop="html_content">
              <el-input
                v-model="templateForm.html_content"
                type="textarea"
                :rows="15"
                :placeholder="$t('settings.htmlContentPlaceholder')"
              />
              <span class="form-tip">{{ $t('settings.htmlContentTip') }}</span>
            </el-form-item>

            <el-form-item :label="$t('settings.isActive')" prop="is_active">
              <el-switch v-model="templateForm.is_active" />
              <span class="form-tip">{{ $t('settings.isActiveTip') }}</span>
            </el-form-item>
          </el-form>

          <template #footer>
            <el-button @click="templateDialogVisible = false">{{ $t('settings.cancel') }}</el-button>
            <el-button
              type="primary"
              :icon="Check"
              :loading="savingTemplate"
              @click="handleSaveTemplate"
            >
              {{ $t('settings.save') }}
            </el-button>
          </template>
        </el-dialog>

        <!-- Template Preview Dialog -->
        <el-dialog
          v-model="previewDialogVisible"
          :title="$t('settings.templatePreview')"
          width="70%"
        >
          <div v-html="previewHtml"></div>
          <template #footer>
            <el-button @click="previewDialogVisible = false">{{ $t('settings.close') }}</el-button>
          </template>
        </el-dialog>

        <!-- LDAP/SSO Configuration Section -->
        <el-card v-if="activeMenu === 'ldap'" shadow="never" v-loading="loadingLDAP" class="ldap-config-card">
          <template #header>
            <div class="flex-between">
              <div class="card-header-content">
                <el-icon class="header-icon"><Lock /></el-icon>
                <span>{{ $t('settings.ldapTitle') }}</span>
              </div>
              <el-tag :type="ldapConfig.ldap_enabled || ldapConfig.sso_enabled ? 'success' : 'info'" size="small">
                {{ ldapConfig.ldap_enabled || ldapConfig.sso_enabled ? $t('settings.enabled') : $t('settings.notEnabled') }}
              </el-tag>
            </div>
          </template>

          <el-form
            ref="ldapFormRef"
            :model="ldapConfig"
            :rules="ldapRules"
            label-width="220px"
            class="ldap-form"
          >
            <!-- LDAP Configuration Block -->
            <el-divider content-position="left">{{ $t('settings.ldapSectionTitle') }}</el-divider>

            <el-form-item :label="$t('settings.enableLdap')" prop="ldap_enabled">
              <el-switch
                v-model="ldapConfig.ldap_enabled"
                @change="handleLDAPToggle"
              />
              <span class="form-tip">{{ $t('settings.enableLdapTip') }}</span>
            </el-form-item>

            <template v-if="ldapConfig.ldap_enabled">
              <el-form-item :label="$t('settings.serverAddress')" prop="ldap_server">
                <el-input
                  v-model="ldapConfig.ldap_server"
                  placeholder="ldap.example.com"
                  clearable
                />
                <span class="form-tip">{{ $t('settings.serverAddressTip') }}</span>
              </el-form-item>

              <el-form-item :label="$t('settings.port')" prop="ldap_port">
                <el-input
                  v-model.number="ldapConfig.ldap_port"
                  type="number"
                  placeholder="389"
                  clearable
                />
                <span class="form-tip">{{ $t('settings.ldapPortTip') }}</span>
              </el-form-item>

              <el-form-item :label="$t('settings.ldapEncryption')" prop="ldap_use_ssl">
                <el-radio-group v-model="ldapConfig.ldap_use_ssl">
                  <el-radio :value="false">{{ $t('settings.encryptionNone') }}</el-radio>
                  <el-radio :value="true">{{ $t('settings.encryptionSsl') }}</el-radio>
                </el-radio-group>
              </el-form-item>

              <el-form-item :label="$t('settings.bindDn')" prop="ldap_bind_dn">
                <el-input
                  v-model="ldapConfig.ldap_bind_dn"
                  placeholder="cn=admin,dc=example,dc=com"
                  clearable
                />
                <span class="form-tip">{{ $t('settings.bindDnTip') }}</span>
              </el-form-item>

              <el-form-item :label="$t('settings.bindPassword')" prop="ldap_bind_password">
                <el-input
                  v-model="ldapConfig.ldap_bind_password"
                  type="password"
                  :placeholder="$t('settings.bindPasswordPlaceholder')"
                  show-password
                  clearable
                />
                <span class="form-tip">{{ $t('settings.bindPasswordTip') }}</span>
              </el-form-item>

              <el-form-item :label="$t('settings.searchBaseDn')" prop="ldap_search_base">
                <el-input
                  v-model="ldapConfig.ldap_search_base"
                  placeholder="dc=example,dc=com"
                  clearable
                />
                <span class="form-tip">{{ $t('settings.searchBaseDnTip') }}</span>
              </el-form-item>

              <!-- Attribute Mapping -->
              <el-divider content-position="left">{{ $t('settings.attributeMapping') }}</el-divider>

              <el-form-item :label="$t('settings.emailAttribute')" prop="ldap_email_attribute">
                <el-input
                  v-model="ldapConfig.ldap_email_attribute"
                  placeholder="mail"
                  clearable
                />
                <span class="form-tip">{{ $t('settings.emailAttributeTip') }}</span>
              </el-form-item>

              <el-form-item :label="$t('settings.nameAttribute')" prop="ldap_name_attribute">
                <el-input
                  v-model="ldapConfig.ldap_name_attribute"
                  placeholder="cn"
                  clearable
                />
                <span class="form-tip">{{ $t('settings.nameAttributeTip') }}</span>
              </el-form-item>

              <el-form-item :label="$t('settings.departmentAttribute')" prop="ldap_department_attribute">
                <el-input
                  v-model="ldapConfig.ldap_department_attribute"
                  placeholder="department"
                  clearable
                />
                <span class="form-tip">{{ $t('settings.departmentAttributeTip') }}</span>
              </el-form-item>

              <!-- AD Group Mapping -->
              <el-divider content-position="left">{{ $t('settings.adGroupMapping') }}</el-divider>

              <el-form-item :label="$t('settings.adminGroup')" prop="ad_admin_group">
                <el-input
                  v-model="ldapConfig.ad_admin_group"
                  placeholder="cn=PPAP-Admins,ou=groups,dc=example,dc=com"
                  clearable
                />
                <span class="form-tip">{{ $t('settings.adminGroupTip') }}</span>
              </el-form-item>

              <!-- Manager group field hidden as MANAGER role is enabled -->
              <el-form-item :label="$t('settings.userGroup')" prop="ad_user_group">
                <el-input
                  v-model="ldapConfig.ad_user_group"
                  placeholder="cn=PPAP-Users,ou=groups,dc=example,dc=com"
                  clearable
                />
                <span class="form-tip">{{ $t('settings.userGroupTip') }}</span>
              </el-form-item>
            </template>

            <!-- SSO Configuration Block -->
            <el-divider content-position="left">{{ $t('settings.ssoSectionTitle') }}</el-divider>

            <el-form-item :label="$t('settings.enableSso')" prop="sso_enabled">
              <el-switch
                v-model="ldapConfig.sso_enabled"
                @change="handleSSOToggle"
              />
              <span class="form-tip">{{ $t('settings.enableSsoTip') }}</span>
            </el-form-item>

            <template v-if="ldapConfig.sso_enabled">
              <el-form-item :label="$t('settings.providerType')" prop="sso_provider">
                <el-select
                  v-model="ldapConfig.sso_provider"
                  :placeholder="$t('settings.providerPlaceholder')"
                  style="width: 100%"
                >
                  <el-option label="Keycloak" value="keycloak" />
                  <el-option label="Azure AD" value="azure" />
                  <el-option label="Okta" value="okta" />
                  <el-option label="Auth0" value="auth0" />
                  <el-option :label="$t('settings.providerOther')" value="other" />
                </el-select>
                <span class="form-tip">{{ $t('settings.providerTip') }}</span>
              </el-form-item>

              <el-form-item :label="$t('settings.discoveryEndpoint')" prop="sso_idp_sso_url">
                <el-input
                  v-model="ldapConfig.sso_idp_sso_url"
                  placeholder="https://sso.example.com/.well-known/openid-configuration"
                  clearable
                />
                <span class="form-tip">{{ $t('settings.discoveryEndpointTip') }}</span>
              </el-form-item>

              <el-form-item :label="$t('settings.clientId')" prop="sso_entity_id">
                <el-input
                  v-model="ldapConfig.sso_entity_id"
                  placeholder="ppap-client-id"
                  clearable
                />
                <span class="form-tip">{{ $t('settings.clientIdTip') }}</span>
              </el-form-item>

              <el-form-item :label="$t('settings.clientSecret')" prop="sso_sp_key">
                <el-input
                  v-model="ldapConfig.sso_sp_key"
                  type="password"
                  :placeholder="$t('settings.clientSecretPlaceholder')"
                  show-password
                  clearable
                />
                <span class="form-tip">{{ $t('settings.clientSecretTip') }}</span>
              </el-form-item>

              <el-form-item :label="$t('settings.callbackUrl')" prop="sso_acs_url">
                <el-input
                  v-model="ldapConfig.sso_acs_url"
                  placeholder="http://localhost:5173/auth/callback"
                  clearable
                />
                <span class="form-tip">{{ $t('settings.callbackUrlTip') }}</span>
              </el-form-item>
            </template>

            <!-- General Settings -->
            <el-divider content-position="left">{{ $t('settings.generalUserSettings') }}</el-divider>

            <el-form-item :label="$t('settings.autoCreateUsers')" prop="auto_create_users">
              <el-switch v-model="ldapConfig.auto_create_users" />
              <span class="form-tip">{{ $t('settings.autoCreateUsersTip') }}</span>
            </el-form-item>

            <el-form-item :label="$t('settings.keepLocalAdmin')" prop="local_admin_enabled">
              <el-switch v-model="ldapConfig.local_admin_enabled" />
              <span class="form-tip">{{ $t('settings.keepLocalAdminTip') }}</span>
            </el-form-item>

            <el-form-item :label="$t('settings.defaultUserRole')" prop="default_role">
              <el-radio-group v-model="ldapConfig.default_role" class="vertical-radio-group">
                <el-radio value="USER">
                  <span>{{ $t('settings.roleUser') }}</span>
                  <span class="radio-tip"> {{ $t('settings.roleUserDesc') }}</span>
                </el-radio>
                <el-radio value="ADMIN">
                  <span>{{ $t('settings.roleAdmin') }}</span>
                  <span class="radio-tip"> {{ $t('settings.roleAdminDesc') }}</span>
                </el-radio>
              </el-radio-group>
            </el-form-item>

            <!-- Action Buttons -->
            <el-form-item>
              <el-button
                type="primary"
                :icon="MessageBox"
                :loading="testingLDAP"
                :disabled="!ldapConfig.ldap_enabled"
                @click="handleTestLDAP"
              >
                {{ $t('settings.testConnection') }}
              </el-button>

              <el-button
                type="success"
                :icon="Check"
                :loading="savingLDAP"
                @click="handleSaveLDAP"
              >
                {{ $t('settings.saveConfig') }}
              </el-button>

              <el-button
                :icon="RefreshLeft"
                @click="loadLDAPConfig"
              >
                {{ $t('settings.reset') }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="ldapSaveSuccess"
            type="success"
            :title="$t('settings.ldapSaved')"
            :description="$t('settings.ldapSavedDesc')"
            :closable="false"
            show-icon
            class="mt-4"
          />
        </el-card>

        <!-- AI Model Configuration Section -->
        <el-card v-if="activeMenu === 'ai-model'" shadow="never" v-loading="loadingProfiles">
          <template #header>
            <div class="flex-between">
              <span>{{ $t('settings.aiModelTitle') }}</span>
              <el-button type="primary" :icon="Plus" @click="handleAddProfile">{{ $t('settings.addProfile') }}</el-button>
            </div>
          </template>

          <el-alert
            type="info"
            :title="$t('settings.aiModelAboutTitle')"
            :description="$t('settings.aiModelAboutDesc')"
            :closable="false"
            show-icon
            class="mb-4"
          />

          <el-table :data="modelProfiles" style="width: 100%" border>
            <el-table-column prop="name" :label="$t('settings.profileName')" width="150" />
            <el-table-column prop="model_name" :label="$t('settings.model')" width="150" />
            <el-table-column :label="$t('settings.capability')" width="100">
              <template #default="{ row }">
                <el-tag size="small" v-if="row.model_type === 'both'">{{ $t('settings.capabilityBoth') }}</el-tag>
                <el-tag size="small" type="success" v-else-if="row.model_type === 'text'">{{ $t('settings.capabilityText') }}</el-tag>
                <el-tag size="small" type="warning" v-else-if="row.model_type === 'vision'">{{ $t('settings.capabilityVision') }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('settings.defaultStatus')" width="180">
              <template #default="{ row }">
                <div style="display: flex; gap: 4px;">
                  <el-tag size="small" effect="dark" type="success" v-if="row.is_default_text">{{ $t('settings.defaultText') }}</el-tag>
                  <el-tag size="small" effect="dark" type="warning" v-if="row.is_default_vision">{{ $t('settings.defaultVision') }}</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column :label="$t('settings.status')" width="80">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
                  {{ row.enabled ? $t('settings.enabled') : $t('settings.notEnabled') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('settings.actions')" min-width="250">
              <template #default="{ row }">
                <el-button link type="primary" :icon="Edit" @click="handleEditProfile(row)">{{ $t('settings.edit') }}</el-button>
                <el-button link type="success" :icon="Connection" :loading="testingProfileId === row.id" @click="handleTestProfile(row.id)">{{ $t('common.test') }}</el-button>
                <el-dropdown trigger="click" style="margin-left: 12px; margin-right: 12px;">
                  <el-button link type="primary">
                    {{ $t('settings.setAsDefault') }}<el-icon class="el-icon--right"><arrow-down /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item @click="handleSetDefaultProfile(row.id, 'text')" :disabled="row.model_type === 'vision'">{{ $t('settings.setDefaultSuccessText') }}</el-dropdown-item>
                      <el-dropdown-item @click="handleSetDefaultProfile(row.id, 'vision')" :disabled="row.model_type === 'text'">{{ $t('settings.setDefaultSuccessVision') }}</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-popconfirm :title="$t('settings.deleteProfileConfirm')" @confirm="handleDeleteProfile(row)">
                  <template #reference>
                    <el-button link type="danger" :icon="Delete">{{ $t('settings.delete') }}</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>

          <el-alert
            v-if="testResult"
            :type="testResult.success ? 'success' : 'error'"
            :title="testResult.success ? $t('settings.testSuccess') : $t('settings.testFailed')"
            :description="testResult.message"
            :closable="true"
            @close="testResult = null"
            show-icon
            class="mt-4"
          />
        </el-card>

        <!-- AI Model Profile Dialog -->
        <el-dialog
          :title="editingProfile ? $t('settings.editProfile') : $t('settings.addNewProfile')"
          v-model="profileDialogVisible"
          width="600px"
          destroy-on-close
        >
          <el-form
            ref="profileFormRef"
            :model="profileForm"
            :rules="profileRules"
            label-width="120px"
          >
            <el-form-item :label="$t('settings.profileName')" prop="name">
              <el-input v-model="profileForm.name" :placeholder="$t('settings.profileNamePlaceholder')" clearable />
            </el-form-item>
            <el-form-item label="Base URL" prop="base_url">
              <el-input v-model="profileForm.base_url" placeholder="https://api.openai.com/v1" clearable />
            </el-form-item>
            <el-form-item label="API Key" prop="api_key">
              <el-input v-model="profileForm.api_key" type="password" show-password :placeholder="$t('settings.apiKeyPlaceholder')" clearable />
            </el-form-item>
            <el-form-item :label="$t('settings.model')" prop="model_name">
              <el-input v-model="profileForm.model_name" :placeholder="$t('settings.modelNamePlaceholder')" clearable />
            </el-form-item>
            <el-form-item :label="$t('settings.modelCapability')" prop="model_type">
              <el-radio-group v-model="profileForm.model_type">
                <el-radio label="both">{{ $t('settings.capabilityBothLabel') }}</el-radio>
                <el-radio label="text">{{ $t('settings.capabilityTextLabel') }}</el-radio>
                <el-radio label="vision">{{ $t('settings.capabilityVisionLabel') }}</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="Max Tokens" prop="max_tokens">
              <el-input-number v-model="profileForm.max_tokens" :min="128" :max="32768" :step="512" />
            </el-form-item>
            <el-form-item label="Temperature" prop="temperature">
              <el-slider v-model="profileForm.temperature" :min="0" :max="2" :step="0.05" show-input style="width: 100%" />
            </el-form-item>
            <el-form-item :label="$t('settings.enabledStatus')" prop="enabled">
              <el-switch v-model="profileForm.enabled" />
            </el-form-item>
          </el-form>
          <template #footer>
            <span class="dialog-footer">
              <el-button @click="profileDialogVisible = false">{{ $t('settings.cancel') }}</el-button>
              <el-button type="primary" :icon="Check" :loading="savingProfile" @click="handleSaveProfile">
                {{ $t('settings.save') }}
              </el-button>
            </span>
          </template>
        </el-dialog>

        <!-- User Management Section -->
        <el-card v-if="activeMenu === 'users'" shadow="never" v-loading="loadingUsers">
          <template #header>
            <div class="flex-between">
              <span>{{ $t('settings.userManagement') }}</span>
              <div class="header-actions">
                <el-button :icon="Setting" size="small" @click="activeUserSubTab = 'groups'" v-if="activeUserSubTab === 'list'">{{ $t('settings.groupManagement') }}</el-button>
                <el-button :icon="UserFilled" size="small" @click="activeUserSubTab = 'list'" v-if="activeUserSubTab === 'groups'">{{ $t('settings.userList') }}</el-button>
                <el-button type="primary" :icon="Plus" size="small" @click="handleCreateUser" v-if="activeUserSubTab === 'list'">{{ $t('settings.addUser') }}</el-button>
              </div>
            </div>
          </template>

          <!-- User List View -->
          <template v-if="activeUserSubTab === 'list'">
            <div class="user-search-bar">
              <el-input
                v-model="userSearchQuery"
                :placeholder="$t('settings.searchUserPlaceholder')"
                :prefix-icon="Search"
                clearable
                style="width: 300px"
                @input="filterUsers"
              />
            </div>

            <el-table :data="filteredUsers" style="width: 100%">
              <el-table-column prop="email" :label="$t('settings.email')" min-width="200" />
              <el-table-column prop="username" :label="$t('settings.username')" width="130" />
              <el-table-column prop="full_name" :label="$t('settings.fullName')" width="120" />
              <el-table-column prop="department" :label="$t('settings.department')" width="140" />
              <el-table-column :label="$t('settings.userGroups')" width="140">
                <template #default="scope">
                  <el-tag v-if="scope.row.groups && scope.row.groups.length > 0" size="small" type="info">
                    {{ scope.row.groups.map((g: UserGroup) => g.name).join(', ') }}
                  </el-tag>
                  <span v-else class="text-muted text-sm">-</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('settings.role')" width="110">
                <template #default="scope">
                  <el-select
                    v-model="scope.row.role"
                    size="small"
                    :disabled="scope.row.id === authStore.user?.id"
                    @change="handleRoleChange(scope.row)"
                  >
                    <el-option :label="$t('settings.roleAdmin')" value="ADMIN" />
                    <el-option :label="$t('settings.roleManager')" value="MANAGER" />
                    <el-option :label="$t('settings.roleUser')" value="USER" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column :label="$t('settings.status')" width="90">
                <template #default="scope">
                  <el-switch
                    v-model="scope.row.is_active"
                    :disabled="scope.row.id === authStore.user?.id"
                    @change="handleToggleUserStatus(scope.row)"
                  />
                </template>
              </el-table-column>
              <el-table-column :label="$t('settings.lastLogin')" width="140">
                <template #default="scope">
                  {{ scope.row.last_login_at ? formatDate(scope.row.last_login_at) : '-' }}
                </template>
              </el-table-column>
              <el-table-column :label="$t('settings.operation')" width="130" fixed="right">
                <template #default="scope">
                  <el-dropdown trigger="click" @command="(cmd: string) => handleUserCommand(cmd, scope.row)">
                    <el-button link type="primary" size="small">
                      {{ $t('settings.operation') }} <el-icon class="el-icon--right"><arrow-down /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="edit" :icon="Edit">{{ $t('settings.editUser') }}</el-dropdown-item>
                        <el-dropdown-item command="groups" :icon="UserFilled">{{ $t('settings.setUserGroups') }}</el-dropdown-item>
                        <el-dropdown-item command="resetPassword" :icon="Key">{{ $t('settings.resetPassword') }}</el-dropdown-item>
                        <el-dropdown-item command="delete" :icon="Delete" divided v-if="scope.row.id !== authStore.user?.id">{{ $t('settings.deleteUser') }}</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </template>
              </el-table-column>
            </el-table>
          </template>

          <!-- Permission Groups View -->
          <template v-if="activeUserSubTab === 'groups'">
            <div class="groups-header">
              <el-alert
                type="info"
                :closable="false"
                show-icon
                class="mb-4"
              >
                {{ $t('settings.groupAlert') }}
              </el-alert>
            </div>

            <el-table :data="userGroups" style="width: 100%" v-loading="loadingGroups">
              <el-table-column prop="name" :label="$t('settings.groupName')" width="180" />
              <el-table-column prop="description" :label="$t('settings.description')" min-width="200" />
              <el-table-column prop="ldap_group_dn" :label="$t('settings.ldapGroupDn')" min-width="280">
                <template #default="scope">
                  <code class="text-xs">{{ scope.row.ldap_group_dn || '-' }}</code>
                </template>
              </el-table-column>
              <el-table-column :label="$t('settings.assignedRole')" width="110">
                <template #default="scope">
                  <el-tag :type="getRoleTagType(scope.row.role)" size="small">
                    {{ getRoleLabel(scope.row.role) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column :label="$t('settings.memberCount')" width="90" align="center">
                <template #default="scope">
                  <el-badge :value="scope.row.member_count || 0" type="primary" />
                </template>
              </el-table-column>
              <el-table-column :label="$t('settings.operation')" width="150" fixed="right">
                <template #default="scope">
                  <el-button link type="primary" :icon="Edit" size="small" @click="handleEditGroup(scope.row)">{{ $t('settings.edit') }}</el-button>
                  <el-popconfirm
                    :title="$t('settings.deleteGroupConfirm')"
                    @confirm="handleDeleteGroup(scope.row)"
                  >
                    <template #reference>
                      <el-button link type="danger" :icon="Delete" size="small">{{ $t('settings.delete') }}</el-button>
                    </template>
                  </el-popconfirm>
                </template>
              </el-table-column>
            </el-table>

            <div class="mt-4 text-center">
              <el-button type="primary" :icon="Plus" @click="handleCreateGroup">{{ $t('settings.addGroup') }}</el-button>
            </div>
          </template>
        </el-card>

        <!-- User Edit/Create Dialog -->
        <el-dialog
          v-model="userDialogVisible"
          :title="editingUser?.id ? $t('settings.editUserTitle') : $t('settings.addUserTitle')"
          width="500px"
          :close-on-click-modal="false"
        >
          <el-form
            ref="userFormRef"
            :model="userForm"
            :rules="userRules"
            label-width="80px"
          >
            <el-form-item label="用户名" prop="username">
              <el-input
                v-model="userForm.username"
                placeholder="留空则从邮箱前缀自动生成"
                :disabled="!!editingUser?.id"
                clearable
              />
            </el-form-item>
            <el-form-item :label="$t('settings.email')" prop="email">
              <el-input
                v-model="userForm.email"
                :placeholder="$t('settings.enterEmail')"
                :disabled="!!editingUser?.id"
                clearable
              />
            </el-form-item>
            <el-form-item :label="$t('settings.fullName')" prop="full_name">
              <el-input
                v-model="userForm.full_name"
                :placeholder="$t('settings.enterName')"
                clearable
              />
            </el-form-item>
            <el-form-item :label="$t('settings.department')" prop="department">
              <el-input
                v-model="userForm.department"
                :placeholder="$t('settings.enterDepartment')"
                clearable
              />
            </el-form-item>
            <el-form-item v-if="!editingUser?.id" :label="$t('auth.password')" prop="password" required>
              <el-input
                v-model="userForm.password"
                type="password"
                :placeholder="$t('settings.enterInitialPassword')"
                show-password
                clearable
              />
            </el-form-item>
            <el-form-item :label="$t('settings.role')" prop="role">
              <el-select v-model="userForm.role" :placeholder="$t('settings.selectRole')">
                <el-option :label="$t('settings.roleAdmin')" value="ADMIN" />
                <el-option :label="$t('settings.roleUser')" value="USER" />
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('settings.permissionGroups')" prop="group_ids">
              <el-select v-model="userForm.group_ids" multiple :placeholder="$t('settings.selectGroups')" style="width: 100%">
                <el-option
                  v-for="group in userGroups"
                  :key="group.id"
                  :label="group.name"
                  :value="group.id"
                />
              </el-select>
            </el-form-item>
          </el-form>

          <template #footer>
            <el-button @click="userDialogVisible = false">{{ $t('common.cancel') }}</el-button>
            <el-button
              type="primary"
              :icon="Check"
              :loading="savingUser"
              @click="handleSaveUser"
            >
              {{ $t('common.save') }}
            </el-button>
          </template>
        </el-dialog>

        <!-- User Groups Dialog -->
        <el-dialog
          v-model="groupDialogVisible"
          :title="editingGroup?.id ? $t('settings.editGroupTitle') : $t('settings.addGroupTitle')"
          width="600px"
          :close-on-click-modal="false"
        >
          <el-form
            ref="groupFormRef"
            :model="groupForm"
            :rules="groupRules"
            label-width="120px"
          >
            <el-form-item :label="$t('settings.groupName')" prop="name">
              <el-input v-model="groupForm.name" :placeholder="$t('settings.groupNamePlaceholder')" clearable />
            </el-form-item>
            <el-form-item :label="$t('settings.description')" prop="description">
              <el-input v-model="groupForm.description" type="textarea" :rows="2" :placeholder="$t('settings.groupDescriptionPlaceholder')" />
            </el-form-item>
            <el-form-item :label="$t('settings.ldapGroupDn')" prop="ldap_group_dn">
              <el-input
                v-model="groupForm.ldap_group_dn"
                :placeholder="$t('settings.ldapGroupDnPlaceholder')"
                clearable
              />
              <span class="form-tip">{{ $t('settings.ldapGroupDnTip') }}</span>
            </el-form-item>
            <el-form-item :label="$t('settings.assignedRole')" prop="role">
              <el-select v-model="groupForm.role" :placeholder="$t('settings.selectRole')">
                <el-option :label="$t('settings.roleAdmin')" value="ADMIN" />
                <el-option :label="$t('settings.roleManager')" value="MANAGER" />
                <el-option :label="$t('settings.roleUser')" value="USER" />
              </el-select>
            </el-form-item>
          </el-form>

          <template #footer>
            <el-button @click="groupDialogVisible = false">{{ $t('common.cancel') }}</el-button>
            <el-button type="primary" :icon="Check" :loading="savingGroup" @click="handleSaveGroup">
              {{ $t('common.save') }}
            </el-button>
          </template>
        </el-dialog>

        <!-- User Group Assignment Dialog -->
        <el-dialog
          v-model="userGroupAssignDialogVisible"
          :title="$t('settings.setUserGroupsTitle')"
          width="500px"
          :close-on-click-modal="false"
        >
          <el-form label-width="80px">
            <el-form-item :label="$t('settings.user')">
              <span>{{ userForGroupAssign?.full_name }} ({{ userForGroupAssign?.email }})</span>
            </el-form-item>
            <el-form-item :label="$t('settings.permissionGroups')">
              <el-select v-model="userForGroupAssignGroupIds" multiple :placeholder="$t('settings.selectGroups')" style="width: 100%">
                <el-option
                  v-for="group in userGroups"
                  :key="group.id"
                  :label="`${group.name} (${getRoleLabel(group.role)})`"
                  :value="group.id"
                />
              </el-select>
            </el-form-item>
          </el-form>

          <template #footer>
            <el-button @click="userGroupAssignDialogVisible = false">{{ $t('common.cancel') }}</el-button>
            <el-button type="primary" :loading="savingUserGroups" @click="handleSaveUserGroups">
              {{ $t('common.save') }}
            </el-button>
          </template>
        </el-dialog>

        <!-- Reset Password Dialog (Admin) -->
        <el-dialog
          v-model="resetPasswordDialogVisible"
          :title="$t('settings.resetPasswordTitle')"
          width="450px"
          :close-on-click-modal="false"
        >
          <el-form label-width="100px">
            <el-form-item :label="$t('settings.user')">
              <span>{{ resetPasswordUser?.full_name }} ({{ resetPasswordUser?.email }})</span>
            </el-form-item>
            <el-form-item :label="$t('settings.newPassword')" required>
              <el-input
                v-model="resetPasswordForm.password"
                type="password"
                :placeholder="$t('settings.newPasswordPlaceholder')"
                show-password
              />
            </el-form-item>
            <el-form-item :label="$t('settings.confirmPassword')" required>
              <el-input
                v-model="resetPasswordForm.confirmPassword"
                type="password"
                :placeholder="$t('settings.confirmPasswordPlaceholder')"
                show-password
              />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="resetPasswordDialogVisible = false">{{ $t('common.cancel') }}</el-button>
            <el-button type="primary" :loading="resettingPassword" @click="handleResetPassword">{{ $t('settings.confirmReset') }}</el-button>
          </template>
        </el-dialog>

        <!-- Change Password Dialog (Self-service) -->
        <el-dialog
          v-model="changePasswordDialogVisible"
          :title="$t('settings.changePasswordTitle')"
          width="450px"
          :close-on-click-modal="false"
        >
          <el-form label-width="100px">
            <el-form-item :label="$t('settings.oldPassword')" required>
              <el-input
                v-model="changePasswordForm.oldPassword"
                type="password"
                :placeholder="$t('settings.oldPasswordPlaceholder')"
                show-password
              />
            </el-form-item>
            <el-form-item :label="$t('settings.changePasswordNew')" required>
              <el-input
                v-model="changePasswordForm.newPassword"
                type="password"
                :placeholder="$t('settings.changePasswordNewPlaceholder')"
                show-password
              />
            </el-form-item>
            <el-form-item :label="$t('settings.confirmNewPassword')" required>
              <el-input
                v-model="changePasswordForm.confirmNewPassword"
                type="password"
                :placeholder="$t('settings.confirmNewPasswordPlaceholder')"
                show-password
              />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="changePasswordDialogVisible = false">{{ $t('common.cancel') }}</el-button>
            <el-button type="primary" :loading="changingPassword" @click="handleChangePassword">{{ $t('settings.confirmChange') }}</el-button>
          </template>
        </el-dialog>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { getLocale } from '@/locales'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  User,
  Bell,
  Setting,
  Document,
  MessageBox,
  Check,
  Plus,
  Edit,
  Lock,
  UserFilled,
  FolderOpened,
  Delete,
  Cpu,
  Connection,
  Search,
  ArrowDown,
  OfficeBuilding,
  Key,
  RefreshLeft,
  Message,
  Star
} from '@element-plus/icons-vue'
import type { EmailTemplate, FileRetentionSettings, AiModelConfig, ModelProfile } from '@/api/settings'
import type { LDAPConfig, UserInfo } from '@/api/ldap'
import { getErrorMessage } from '@/utils/formatters'

const authStore = useAuthStore()
const { t } = useI18n()

// Restore active menu from localStorage (with permission check)
const savedMenu = localStorage.getItem('settingsActiveMenu')

// Helper to check if user can access a setting section (inline version for init)
function canAccessMenuSection(section: string): boolean {
  const user = authStore.user
  const role = user?.role || 'USER'
  const adminSections = ['file-retention', 'smtp', 'templates', 'ldap', 'ai-model', 'users']
  return !adminSections.includes(section) || role === 'ADMIN'
}

// Use saved menu only if user has access, otherwise default to 'profile'
const activeMenu = ref((savedMenu && canAccessMenuSection(savedMenu)) ? savedMenu : 'profile')

// Auto-fix user role on mount (in case of stale data)
async function ensureUserRole() {
  try {
    await authStore.fetchMe()
    console.log('[Settings] User info refreshed:', authStore.user)
  } catch (error) {
    console.error('[Settings] Failed to refresh user info:', error)
  }
}

// Call refresh on mount
ensureUserRole()

// Check if user can access specific settings
function canAccessSettings(setting: string): boolean {
  const user = authStore.user
  const role = user?.role || 'USER'

  // Debug logging
  console.log('[Settings] Checking permission:', {
    setting,
    userRole: role,
    userEmail: user?.email,
    isAdmin: user?.is_admin,
    rawUser: user
  })

  // Define which roles can access which settings
  const permissions: Record<string, string[]> = {
    profile: ['USER', 'MANAGER', 'ADMIN'],
    notification: ['USER', 'MANAGER', 'ADMIN'],
    file_retention: ['ADMIN'],
    smtp: ['ADMIN'],
    email_templates: ['ADMIN'],
    ldap: ['ADMIN'],
    ai_model: ['ADMIN'],
    users: ['ADMIN'],
  }

  const hasAccess = permissions[setting]?.includes(role) || false
  console.log('[Settings] Permission check result:', { setting, hasAccess })

  return hasAccess
}

const loading = ref(false)
const loadingNotif = ref(false)
const saving = ref(false)
const savingNotif = ref(false)
const testing = ref(false)
const saveSuccess = ref(false)
const notifSaveSuccess = ref(false)

// File Retention Settings
const loadingFileRetention = ref(false)
const savingFileRetention = ref(false)
const triggeringCleanup = ref(false)
const fileRetentionSaveSuccess = ref(false)
const cleanupTriggerSuccess = ref(false)
const cleanupTriggerMessage = ref('')
const fileRetentionFormRef = ref<FormInstance>()

// AI Model Profiles
const modelProfiles = ref<ModelProfile[]>([])
const loadingProfiles = ref(false)
const profileDialogVisible = ref(false)
const savingProfile = ref(false)
const profileFormRef = ref<FormInstance>()
const editingProfile = ref<ModelProfile | null>(null)
const testingProfileId = ref<string | null>(null)
const testResult = ref<{ id: string; success: boolean; message: string } | null>(null)

const profileForm = reactive<Omit<ModelProfile, 'id'> & { id?: string }>({
  name: '',
  base_url: 'https://api.openai.com/v1',
  api_key: '',
  model_name: '',
  model_type: 'both',
  max_tokens: 2048,
  temperature: 0.1,
  enabled: true,
  is_default_text: false,
  is_default_vision: false
})

const profileRules = computed<FormRules>(() => ({
  name: [{ required: true, message: t('settings.enterProfileName'), trigger: 'blur' }],
  base_url: [{ required: true, message: t('settings.enterBaseUrl'), trigger: 'blur' }],
  model_name: [{ required: true, message: t('settings.enterModelName'), trigger: 'blur' }]
}))
const fileRetentionSettings = reactive<FileRetentionSettings>({
  retention_days: 30,
  auto_cleanup_enabled: true,
  cleanup_hour: 2
})

const fileRetentionRules = computed<FormRules>(() => ({
  retention_days: [
    { required: true, message: t('settings.enterRetentionDays'), trigger: 'blur' },
    { type: 'number', min: 1, max: 3650, message: t('settings.retentionDaysRange'), trigger: 'blur' }
  ],
  cleanup_hour: [
    { required: true, message: t('settings.selectCleanupHour'), trigger: 'change' }
  ]
}))

const smtpFormRef = ref<FormInstance>()

const smtpConfig = reactive({
  enabled: false,
  host: '',
  port: 587,
  encryption: 'tls',
  username: '',
  from_name: '',
  password: ''
})

const smtpRules = computed<FormRules>(() => ({
  host: [
    { required: true, message: t('settings.enterSmtpServer'), trigger: 'blur' }
  ],
  port: [
    { required: true, message: t('settings.enterPort'), trigger: 'blur' }
  ],
  username: [
    { required: true, message: t('settings.enterSenderEmail'), trigger: 'blur' },
    { type: 'email', message: t('settings.invalidEmail'), trigger: 'blur' }
  ],
  from_name: [
    { required: true, message: t('settings.enterSenderName'), trigger: 'blur' }
  ]
}))

const emailEnabled = ref(true)
const notifyOnFailure = ref(true)
const dailySummary = ref(false)

// Helper function to format variable display
function formatVariable(variable: string) {
  return `{${variable}}`
}

// Email templates
const templates = ref<EmailTemplate[]>([])
const loadingTemplates = ref(false)
const templateDialogVisible = ref(false)
const previewDialogVisible = ref(false)
const editingTemplate = ref<EmailTemplate | null>(null)
const savingTemplate = ref(false)
const templateFormRef = ref<FormInstance>()
const previewHtml = ref('')

// LDAP/SSO Configuration
const loadingLDAP = ref(false)
const savingLDAP = ref(false)
const testingLDAP = ref(false)
const ldapSaveSuccess = ref(false)
const ldapFormRef = ref<FormInstance>()

const ldapRules = computed<FormRules>(() => ({
  ldap_server: [
    { required: true, message: t('settings.enterLdapServer'), trigger: 'blur' }
  ],
  ldap_port: [
    { required: true, message: t('settings.enterPort'), trigger: 'blur' }
  ],
  ldap_bind_dn: [
    { required: true, message: t('settings.enterBindDn'), trigger: 'blur' }
  ],
  ldap_bind_password: [
    { required: true, message: t('settings.enterBindPassword'), trigger: 'blur' }
  ],
  ldap_search_base: [
    { required: true, message: t('settings.enterSearchBaseDn'), trigger: 'blur' }
  ],
  ldap_email_attribute: [
    { required: true, message: t('settings.enterEmailAttribute'), trigger: 'blur' }
  ],
  ldap_name_attribute: [
    { required: true, message: t('settings.enterNameAttribute'), trigger: 'blur' }
  ],
  ldap_department_attribute: [
    { required: true, message: t('settings.enterDepartmentAttribute'), trigger: 'blur' }
  ],
  sso_provider: [
    { required: true, message: t('settings.selectSsoProvider'), trigger: 'change' }
  ],
  sso_idp_sso_url: [
    { required: true, message: t('settings.enterDiscoveryEndpoint'), trigger: 'blur' },
    { type: 'url', message: t('settings.invalidUrl'), trigger: 'blur' }
  ],
  sso_entity_id: [
    { required: true, message: t('settings.enterClientId'), trigger: 'blur' }
  ],
  sso_sp_key: [
    { required: true, message: t('settings.enterClientSecret'), trigger: 'blur' }
  ],
  sso_acs_url: [
    { required: true, message: t('settings.enterCallbackUrl'), trigger: 'blur' },
    { type: 'url', message: t('settings.invalidUrl'), trigger: 'blur' }
  ]
}))

const ldapConfig = reactive<LDAPConfig>({
  ldap_enabled: false,
  ldap_server: null,
  ldap_port: null,
  ldap_use_ssl: false,
  ldap_bind_dn: null,
  ldap_bind_password: null,
  ldap_search_base: null,
  ldap_search_filter: '(sAMAccountName={username})',
  ldap_email_attribute: 'mail',
  ldap_name_attribute: 'cn',
  ldap_department_attribute: 'department',
  ad_admin_group: null,
  ad_manager_group: null,
  ad_user_group: null,
  sso_enabled: false,
  sso_provider: null,
  sso_entity_id: null,
  sso_acs_url: null,
  sso_slo_url: null,
  sso_idp_sso_url: null,
  sso_idp_cert: null,
  sso_sp_cert: null,
  sso_sp_key: null,
  local_admin_enabled: true,
  auto_create_users: true,
  default_role: 'USER'
})

// User Management
const activeUserSubTab = ref('list') // 'list' or 'groups'
const users = ref<UserInfo[]>([])
const filteredUsers = ref<UserInfo[]>([])
const loadingUsers = ref(false)
const userSearchQuery = ref('')
const userDialogVisible = ref(false)
const savingUser = ref(false)
const userFormRef = ref<FormInstance>()
const editingUser = ref<UserInfo | null>(null)

// User Groups
const userGroups = ref<UserGroup[]>([])
const loadingGroups = ref(false)
const groupDialogVisible = ref(false)
const savingGroup = ref(false)
const groupFormRef = ref<FormInstance>()
const editingGroup = ref<UserGroup | null>(null)
const userGroupAssignDialogVisible = ref(false)
const userForGroupAssign = ref<UserInfo | null>(null)
const userForGroupAssignGroupIds = ref<string[]>([])
const savingUserGroups = ref(false)

interface UserGroup {
  id: string
  name: string
  description: string | null
  ldap_group_dn: string | null
  role: 'ADMIN' | 'MANAGER' | 'USER'
  member_count?: number
}

const userForm = reactive({
  username: '',
  email: '',
  full_name: '',
  department: '',
  password: '',
  role: 'USER' as 'ADMIN' | 'MANAGER' | 'USER',
  group_ids: [] as string[]
})

const userRules = computed<FormRules>(() => ({
  email: [
    { required: true, message: t('settings.enterEmail'), trigger: 'blur' },
    { type: 'email', message: t('settings.invalidEmail'), trigger: 'blur' }
  ],
  full_name: [
    { required: true, message: t('settings.enterName'), trigger: 'blur' }
  ],
  role: [
    { required: true, message: t('settings.selectRole'), trigger: 'change' }
  ]
}))

const groupForm = reactive({
  name: '',
  description: '',
  ldap_group_dn: '',
  role: 'USER' as 'ADMIN' | 'MANAGER' | 'USER'
})

const groupRules = computed<FormRules>(() => ({
  name: [
    { required: true, message: t('settings.enterGroupName'), trigger: 'blur' }
  ],
  role: [
    { required: true, message: t('settings.selectRole'), trigger: 'change' }
  ]
}))

// Helper functions
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getRoleLabel(role: string): string {
  const labels: Record<string, string> = {
    'ADMIN': t('settings.roleAdmin'),
    'MANAGER': t('settings.roleManager'),
    'USER': t('settings.roleUser')
  }
  return labels[role] || role
}

function getRoleTagType(role: string): 'success' | 'warning' | 'info' | 'danger' {
  const types: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
    'ADMIN': 'danger',
    'MANAGER': 'warning',
    'USER': 'info'
  }
  return types[role] || 'info'
}

const templateForm = reactive({
  id: '',
  name: '',
  subject: '',
  html_content: '',
  description: '',
  variables: [] as string[],
  is_active: true
})

const templateRules = computed<FormRules>(() => ({
  id: [
    { required: true, message: t('settings.enterTemplateId'), trigger: 'blur' },
    { pattern: /^[a-z_][a-z0-9_]*$/, message: t('settings.templateIdPattern'), trigger: 'blur' }
  ],
  name: [
    { required: true, message: t('settings.enterTemplateName'), trigger: 'blur' }
  ],
  subject: [
    { required: true, message: t('settings.enterEmailSubject'), trigger: 'blur' }
  ],
  html_content: [
    { required: true, message: t('settings.enterHtmlContent'), trigger: 'blur' }
  ]
}))

function handleMenuSelect(index: string) {
  activeMenu.value = index
}

async function loadNotificationSettings() {
  loadingNotif.value = true
  try {
    const { settingsApi } = await import('@/api/settings')
    const response = await settingsApi.getNotificationSettings()
    emailEnabled.value = response.email_enabled
    notifyOnFailure.value = response.notify_on_failure
    dailySummary.value = response.daily_summary
  } catch (error) {
    console.error('Failed to load notification settings:', error)
  } finally {
    loadingNotif.value = false
  }
}

async function loadSmtpConfig() {
  loading.value = true
  try {
    const { settingsApi } = await import('@/api/settings')
    const response = await settingsApi.getSmtpConfig()
    Object.assign(smtpConfig, response)
  } catch (error) {
    console.error('Failed to load SMTP config:', error)
  } finally {
    loading.value = false
  }
}

async function handleSaveNotification() {
  savingNotif.value = true
  notifSaveSuccess.value = false

  try {
    const { settingsApi } = await import('@/api/settings')
    await settingsApi.updateNotificationSettings({
      email_enabled: emailEnabled.value,
      notify_on_failure: notifyOnFailure.value,
      daily_summary: dailySummary.value
    })

    notifSaveSuccess.value = true
    ElMessage.success(t('settings.notificationSavedMsg'))

    setTimeout(() => {
      notifSaveSuccess.value = false
    }, 3000)
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.operationFailed')))
  } finally {
    savingNotif.value = false
  }
}

async function handleSaveSmtp() {
  if (!smtpFormRef.value) return

  await smtpFormRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    saveSuccess.value = false

    try {
      const { settingsApi } = await import('@/api/settings')
      await settingsApi.updateSmtpConfig(smtpConfig)

      saveSuccess.value = true
      ElMessage.success(t('settings.smtpSavedMsg'))

      // 3秒后隐藏成功提示
      setTimeout(() => {
        saveSuccess.value = false
      }, 3000)
    } catch (error: unknown) {
      ElMessage.error(getErrorMessage(error, t('settings.operationFailed')))
    } finally {
      saving.value = false
    }
  })
}

async function handleTestEmail() {
  if (!smtpFormRef.value) return

  await smtpFormRef.value.validate(async (valid) => {
    if (!valid) return

    testing.value = true

    try {
      const { settingsApi } = await import('@/api/settings')
      await settingsApi.testSmtpConfig(smtpConfig)

      ElMessage.success(t('settings.testEmailSent'))
    } catch (error: unknown) {
      ElMessage.error(getErrorMessage(error, t('settings.sendFailed')))
    } finally {
      testing.value = false
    }
  })
}

async function loadEmailTemplates() {
  loadingTemplates.value = true
  try {
    const { settingsApi } = await import('@/api/settings')
    templates.value = await settingsApi.getEmailTemplates()
  } catch (error) {
    console.error('Failed to load email templates:', error)
    ElMessage.error(t('settings.loadTemplatesFailed'))
  } finally {
    loadingTemplates.value = false
  }
}

function handleCreateTemplate() {
  editingTemplate.value = null
  Object.assign(templateForm, {
    id: '',
    name: '',
    subject: '',
    html_content: '',
    description: '',
    variables: [],
    is_active: true
  })
  templateDialogVisible.value = true
}

async function handleEditTemplate(template: EmailTemplate) {
  editingTemplate.value = template
  Object.assign(templateForm, template)
  templateDialogVisible.value = true
}

async function handleSaveTemplate() {
  if (!templateFormRef.value) return

  await templateFormRef.value.validate(async (valid) => {
    if (!valid) return

    savingTemplate.value = true

    try {
      const { settingsApi } = await import('@/api/settings')

      if (editingTemplate.value?.id) {
        // Update existing template
        await settingsApi.updateEmailTemplate(editingTemplate.value.id, templateForm)
        ElMessage.success(t('settings.templateUpdated'))
      } else {
        // Create new template
        await settingsApi.createEmailTemplate(templateForm)
        ElMessage.success(t('settings.templateCreated'))
      }

      templateDialogVisible.value = false
      await loadEmailTemplates()
    } catch (error: unknown) {
      ElMessage.error(getErrorMessage(error, t('settings.saveTemplateFailed')))
    } finally {
      savingTemplate.value = false
    }
  })
}

async function handleDeleteTemplate(templateId: string) {
  try {
    const { settingsApi } = await import('@/api/settings')
    await settingsApi.deleteEmailTemplate(templateId)
    ElMessage.success(t('settings.templateDeleted'))
    await loadEmailTemplates()
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.deleteTemplateFailed')))
  }
}

async function handlePreviewTemplate(template: EmailTemplate) {
  try {
    const { settingsApi } = await import('@/api/settings')

    // Create sample context based on template variables
    const context: Record<string, any> = {}
    template.variables.forEach(variable => {
      if (variable === 'filename') context[variable] = t('settings.sampleFilename')
      else if (variable === 'status_emoji') context[variable] = '✅'
      else if (variable === 'status_text') context[variable] = t('settings.sampleStatusText')
      else if (variable === 'pass_rate') context[variable] = '100'
      else if (variable === 'status-class') context[variable] = 'status-completed'
      else if (variable === 'date') context[variable] = t('settings.sampleDate')
      else if (variable === 'total_count') context[variable] = '50'
      else if (variable === 'completed_count') context[variable] = '45'
      else if (variable === 'warning_count') context[variable] = '3'
      else if (variable === 'failed_count') context[variable] = '2'
      else if (variable === 'file_list_html') context[variable] = `<div>${t('settings.sampleFileList')}</div>`
      else if (variable === 'from_name') context[variable] = t('settings.sampleFromName')
      else if (variable === 'smtp_host') context[variable] = 'smtp.example.com'
      else if (variable === 'smtp_port') context[variable] = '587'
      else if (variable === 'encryption') context[variable] = 'TLS'
      else if (variable === 'username') context[variable] = 'noreply@example.com'
      else context[variable] = `[${variable}]`
    })

    const result = await settingsApi.previewEmailTemplate({
      template_id: template.id,
      context
    })

    previewHtml.value = result.html_content
    previewDialogVisible.value = true
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.previewTemplateFailed')))
  }
}

// Watch for menu changes and load corresponding data (must be after function definitions)
watch(activeMenu, (newIndex) => {
  // Save to localStorage
  localStorage.setItem('settingsActiveMenu', newIndex)

  // Load corresponding data
  if (newIndex === 'smtp') {
    loadSmtpConfig()
  } else if (newIndex === 'notification') {
    loadNotificationSettings()
  } else if (newIndex === 'file-retention') {
    loadFileRetentionSettings()
  } else if (newIndex === 'templates') {
    loadEmailTemplates()
  } else if (newIndex === 'ldap') {
    loadLDAPConfig()
  } else if (newIndex === 'users') {
    loadUsers()
    loadUserGroups()
  } else if (newIndex === 'ai-model') {
    loadModelProfiles()
  }
}, { immediate: true })

async function loadLDAPConfig() {
  loadingLDAP.value = true
  try {
    const { ldapApi } = await import('@/api/ldap')
    const config = await ldapApi.getLDAPConfig()
    Object.assign(ldapConfig, config)
  } catch (error) {
    console.error('Failed to load LDAP config:', error)
  } finally {
    loadingLDAP.value = false
  }
}

async function handleSaveLDAP() {
  savingLDAP.value = true
  ldapSaveSuccess.value = false

  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.updateLDAPConfig(ldapConfig)

    ldapSaveSuccess.value = true
    ElMessage.success(t('settings.ldapSavedMsg'))

    setTimeout(() => {
      ldapSaveSuccess.value = false
    }, 3000)
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.operationFailed')))
  } finally {
    savingLDAP.value = false
  }
}

async function handleTestLDAP() {
  testingLDAP.value = true

  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.testLDAPConnection()
    ElMessage.success(t('settings.ldapTestSuccess'))
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.connectionTestFailed')))
  } finally {
    testingLDAP.value = false
  }
}

// Handle LDAP toggle
function handleLDAPToggle(value: boolean) {
  if (value) {
    ElMessage.info(t('settings.ldapEnabledMsg'))
  } else {
    ElMessage.warning(t('settings.ldapDisabledMsg'))
  }
}

// Handle SSO toggle
function handleSSOToggle(value: boolean) {
  if (value) {
    ElMessage.info(t('settings.ssoEnabledMsg'))
  } else {
    ElMessage.warning(t('settings.ssoDisabledMsg'))
  }
}

async function loadUsers() {
  loadingUsers.value = true
  try {
    const { ldapApi } = await import('@/api/ldap')
    users.value = await ldapApi.getAllUsers()
    filterUsers()
  } catch (error) {
    console.error('Failed to load users:', error)
    ElMessage.error(t('settings.loadUsersFailed'))
  } finally {
    loadingUsers.value = false
  }
}

function filterUsers() {
  const query = userSearchQuery.value.toLowerCase().trim()
  if (!query) {
    filteredUsers.value = users.value
    return
  }
  filteredUsers.value = users.value.filter(user =>
    user.email.toLowerCase().includes(query) ||
    (user.username && user.username.toLowerCase().includes(query)) ||
    user.full_name.toLowerCase().includes(query) ||
    (user.department && user.department.toLowerCase().includes(query))
  )
}

async function handleRoleChange(user: UserInfo) {
  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.updateUserRole(user.id, user.role as 'ADMIN' | 'MANAGER' | 'USER')
    ElMessage.success(t('settings.roleUpdated', { name: user.full_name, role: user.role }))
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.updateRoleFailed')))
    // Revert the change
    await loadUsers()
  }
}

async function handleToggleUserStatus(user: UserInfo) {
  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.toggleUserStatus(user.id)
    const status = user.is_active ? t('settings.userEnabled') : t('settings.userDisabled')
    ElMessage.success(t('settings.userStatusChanged', { name: user.full_name, status }))
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.operationFailed')))
    // Revert the change
    await loadUsers()
  }
}

function handleCreateUser() {
  editingUser.value = null
  Object.assign(userForm, {
    username: '',
    email: '',
    full_name: '',
    department: '',
    password: '',
    role: 'USER',
    group_ids: []
  })
  userDialogVisible.value = true
}

function handleEditUser(user: UserInfo) {
  editingUser.value = user
  Object.assign(userForm, {
    username: user.username || '',
    email: user.email,
    full_name: user.full_name,
    department: user.department || '',
    password: '',
    role: user.role as 'ADMIN' | 'MANAGER' | 'USER',
    group_ids: user.groups?.map((g: UserGroupBasic) => g.id) || []
  })
  userDialogVisible.value = true
}

async function handleSaveUser() {
  if (!userFormRef.value) return

  await userFormRef.value.validate(async (valid) => {
    if (!valid) return

    // For new users, password is required
    if (!editingUser.value?.id && !userForm.password) {
      ElMessage.error(t('settings.enterInitialPassword'))
      return
    }

    savingUser.value = true

    try {
      const { ldapApi } = await import('@/api/ldap')

      let userId: string

      if (editingUser.value?.id) {
        // Update existing user
        userId = editingUser.value.id
        await ldapApi.updateUser(userId, {
          full_name: userForm.full_name,
          department: userForm.department || undefined,
          role: userForm.role
        })
        ElMessage.success(t('settings.userUpdated'))
      } else {
        // Create new user
        const result = await ldapApi.createUser({
          username: userForm.username || undefined,
          email: userForm.email,
          full_name: userForm.full_name,
          department: userForm.department || undefined,
          role: userForm.role,
          password: userForm.password
        })
        userId = result.user.id
        ElMessage.success(t('settings.userCreated'))
      }

      // Update user groups
      await ldapApi.setUserGroups(userId, userForm.group_ids)

      userDialogVisible.value = false
      await loadUsers()
    } catch (error: unknown) {
      ElMessage.error(getErrorMessage(error, t('settings.operationFailed')))
    } finally {
      savingUser.value = false
    }
  })
}

async function handleDeleteUser(user: UserInfo) {
  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.deleteUser(user.id)
    ElMessage.success(t('settings.userDeleted'))
    await loadUsers()
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.deleteFailed')))
  }
}

// ==================== Password Management ====================

// Admin reset password
const resetPasswordDialogVisible = ref(false)
const resetPasswordUser = ref<UserInfo | null>(null)
const resetPasswordForm = reactive({ password: '', confirmPassword: '' })
const resettingPassword = ref(false)

function openResetPasswordDialog(user: UserInfo) {
  resetPasswordUser.value = user
  resetPasswordForm.password = ''
  resetPasswordForm.confirmPassword = ''
  resetPasswordDialogVisible.value = true
}

async function handleResetPassword() {
  if (!resetPasswordUser.value) return
  if (resetPasswordForm.password.length < 6) {
    ElMessage.warning(t('settings.passwordMinLength'))
    return
  }
  if (resetPasswordForm.password !== resetPasswordForm.confirmPassword) {
    ElMessage.warning(t('settings.passwordsMismatch'))
    return
  }
  resettingPassword.value = true
  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.resetUserPassword(resetPasswordUser.value.id, resetPasswordForm.password)
    ElMessage.success(t('settings.passwordResetSuccess', { email: resetPasswordUser.value.email }))
    resetPasswordDialogVisible.value = false
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.resetPasswordFailed')))
  } finally {
    resettingPassword.value = false
  }
}

// Self-service change password
const changePasswordDialogVisible = ref(false)
const changePasswordForm = reactive({ oldPassword: '', newPassword: '', confirmNewPassword: '' })
const changingPassword = ref(false)

function openChangePasswordDialog() {
  changePasswordForm.oldPassword = ''
  changePasswordForm.newPassword = ''
  changePasswordForm.confirmNewPassword = ''
  changePasswordDialogVisible.value = true
}

async function handleChangePassword() {
  if (changePasswordForm.newPassword.length < 6) {
    ElMessage.warning(t('settings.newPasswordMinLength'))
    return
  }
  if (changePasswordForm.newPassword !== changePasswordForm.confirmNewPassword) {
    ElMessage.warning(t('settings.newPasswordsMismatch'))
    return
  }
  changingPassword.value = true
  try {
    const { authApi } = await import('@/api/auth')
    await authApi.changePassword(changePasswordForm.oldPassword, changePasswordForm.newPassword)
    ElMessage.success(t('settings.changePasswordSuccess'))
    changePasswordDialogVisible.value = false
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.changePasswordFailed')))
  } finally {
    changingPassword.value = false
  }
}

// User command handler (for dropdown menu)
async function handleUserCommand(command: string, user: UserInfo) {
  switch (command) {
    case 'edit':
      handleEditUser(user)
      break
    case 'groups':
      handleSetUserGroups(user)
      break
    case 'resetPassword':
      openResetPasswordDialog(user)
      break
    case 'delete':
      await handleDeleteUser(user)
      break
  }
}

// User Groups Functions
async function loadUserGroups() {
  loadingGroups.value = true
  try {
    const { ldapApi } = await import('@/api/ldap')
    userGroups.value = await ldapApi.getUserGroups()
  } catch (error) {
    console.error('Failed to load user groups:', error)
    ElMessage.error(t('settings.loadGroupsFailed'))
  } finally {
    loadingGroups.value = false
  }
}

function handleCreateGroup() {
  editingGroup.value = null
  Object.assign(groupForm, {
    name: '',
    description: '',
    ldap_group_dn: '',
    role: 'USER'
  })
  groupDialogVisible.value = true
}

function handleEditGroup(group: UserGroup) {
  editingGroup.value = group
  Object.assign(groupForm, {
    name: group.name,
    description: group.description || '',
    ldap_group_dn: group.ldap_group_dn || '',
    role: group.role
  })
  groupDialogVisible.value = true
}

async function handleSaveGroup() {
  if (!groupFormRef.value) return

  await groupFormRef.value.validate(async (valid) => {
    if (!valid) return

    savingGroup.value = true

    try {
      const { ldapApi } = await import('@/api/ldap')

      if (editingGroup.value?.id) {
        // Update existing group
        await ldapApi.updateUserGroup(editingGroup.value.id, groupForm)
        ElMessage.success(t('settings.groupUpdated'))
      } else {
        // Create new group
        await ldapApi.createUserGroup(groupForm)
        ElMessage.success(t('settings.groupCreated'))
      }

      groupDialogVisible.value = false
      await loadUserGroups()
    } catch (error: unknown) {
      ElMessage.error(getErrorMessage(error, t('settings.saveGroupFailed')))
    } finally {
      savingGroup.value = false
    }
  })
}

async function handleDeleteGroup(group: UserGroup) {
  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.deleteUserGroup(group.id)
    ElMessage.success(t('settings.groupDeleted'))
    await loadUserGroups()
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.deleteFailed')))
  }
}

function handleSetUserGroups(user: UserInfo) {
  userForGroupAssign.value = user
  userForGroupAssignGroupIds.value = user.groups?.map((g: UserGroupBasic) => g.id) || []
  userGroupAssignDialogVisible.value = true
}

async function handleSaveUserGroups() {
  savingUserGroups.value = true

  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.setUserGroups(userForGroupAssign.value!.id, userForGroupAssignGroupIds.value)
    ElMessage.success(t('settings.userGroupsUpdated'))
    userGroupAssignDialogVisible.value = false
    await loadUsers()
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.updateFailed')))
  } finally {
    savingUserGroups.value = false
  }
}

// File Retention Settings Functions
async function loadFileRetentionSettings() {
  loadingFileRetention.value = true
  try {
    const { settingsApi } = await import('@/api/settings')
    const response = await settingsApi.getFileRetentionSettings()
    Object.assign(fileRetentionSettings, response)
  } catch (error) {
    console.error('Failed to load file retention settings:', error)
    ElMessage.error(t('settings.loadFileRetentionFailed'))
  } finally {
    loadingFileRetention.value = false
  }
}

async function handleSaveFileRetention() {
  if (!fileRetentionFormRef.value) return

  await fileRetentionFormRef.value.validate(async (valid) => {
    if (!valid) return

    savingFileRetention.value = true
    fileRetentionSaveSuccess.value = false

    try {
      const { settingsApi } = await import('@/api/settings')
      await settingsApi.updateFileRetentionSettings(fileRetentionSettings)

      fileRetentionSaveSuccess.value = true
      ElMessage.success(t('settings.fileRetentionSavedMsg'))

      setTimeout(() => {
        fileRetentionSaveSuccess.value = false
      }, 3000)
    } catch (error: unknown) {
      ElMessage.error(getErrorMessage(error, t('settings.operationFailed')))
    } finally {
      savingFileRetention.value = false
    }
  })
}

async function handleTriggerCleanup() {
  triggeringCleanup.value = true
  cleanupTriggerSuccess.value = false

  try {
    const { settingsApi } = await import('@/api/settings')
    const response = await settingsApi.triggerCleanupNow()

    cleanupTriggerMessage.value = `Task ID: ${response.task_id}`
    cleanupTriggerSuccess.value = true
    ElMessage.success(t('settings.cleanupStartedMsg'))

    setTimeout(() => {
      cleanupTriggerSuccess.value = false
    }, 5000)
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.startCleanupFailed')))
  } finally {
    triggeringCleanup.value = false
  }
}

// AI Model Profile Functions
async function loadModelProfiles() {
  loadingProfiles.value = true
  try {
    const { settingsApi } = await import('@/api/settings')
    modelProfiles.value = await settingsApi.listModelProfiles()
  } catch (error) {
    console.error('Failed to load model profiles:', error)
    ElMessage.error(t('settings.loadProfilesFailed'))
  } finally {
    loadingProfiles.value = false
  }
}

function handleAddProfile() {
  editingProfile.value = null
  Object.assign(profileForm, {
    name: '',
    base_url: 'https://api.openai.com/v1',
    api_key: '',
    model_name: '',
    model_type: 'both',
    max_tokens: 2048,
    temperature: 0.1,
    enabled: true,
    is_default_text: false,
    is_default_vision: false
  })
  delete profileForm.id
  profileDialogVisible.value = true
}

function handleEditProfile(profile: ModelProfile) {
  editingProfile.value = profile
  Object.assign(profileForm, { ...profile })
  if (profileForm.api_key === '***') {
    profileForm.api_key = '' // Clear placeholder in edit mode so it isn't accidentally modified to literal '***'
  }
  profileDialogVisible.value = true
}

async function handleSaveProfile() {
  if (!profileFormRef.value) return
  await profileFormRef.value.validate(async (valid) => {
    if (!valid) return

    savingProfile.value = true
    try {
      const { settingsApi } = await import('@/api/settings')
      // If editing and key left blank, send '***' to preserve
      const submitData = { ...profileForm }
      if (editingProfile.value && !submitData.api_key) {
        submitData.api_key = '***'
      }

      if (editingProfile.value?.id) {
        await settingsApi.updateModelProfile(editingProfile.value.id, submitData as ModelProfile)
        ElMessage.success(t('settings.profileUpdated'))
      } else {
        await settingsApi.createModelProfile(submitData)
        ElMessage.success(t('settings.profileCreated'))
      }
      profileDialogVisible.value = false
      await loadModelProfiles()
    } catch (error: unknown) {
      ElMessage.error(getErrorMessage(error, t('settings.operationFailed')))
    } finally {
      savingProfile.value = false
    }
  })
}

async function handleDeleteProfile(profile: ModelProfile) {
  try {
    const { settingsApi } = await import('@/api/settings')
    await settingsApi.deleteModelProfile(profile.id)
    ElMessage.success(t('settings.profileDeleted'))
    await loadModelProfiles()
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.deleteFailed')))
  }
}

async function handleSetDefaultProfile(profileId: string, forType: 'text' | 'vision') {
  try {
    const { settingsApi } = await import('@/api/settings')
    await settingsApi.setDefaultModelProfile(profileId, forType)
    ElMessage.success(t('settings.setDefaultSuccess', { type: forType === 'text' ? t('settings.setDefaultSuccessText') : t('settings.setDefaultSuccessVision') }))
    await loadModelProfiles()
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, t('settings.setDefaultFailed')))
  }
}

async function handleTestProfile(profileId: string) {
  testingProfileId.value = profileId
  testResult.value = null

  try {
    const { settingsApi } = await import('@/api/settings')
    const result = await settingsApi.testModelProfile(profileId)
    testResult.value = { id: profileId, ...result }
    if (result.success) {
      ElMessage.success(t('settings.connectionTestSuccessMsg'))
    } else {
      ElMessage.warning(t('settings.connectionTestFailedMsg'))
    }
  } catch (error: unknown) {
    const message = getErrorMessage(error, t('settings.connectionTestFailedDetail'))
    testResult.value = { id: profileId, success: false, message }
    ElMessage.error(message)
  } finally {
    testingProfileId.value = null
  }
}


onMounted(() => {
  // Data loading is handled by watch with immediate: true
})
</script>

<style scoped>
/* Page container */
.settings-container {
  min-width: 900px;
  overflow-x: auto;
}

/* Layout container */
.settings-row {
  flex-wrap: nowrap !important;
  min-width: 900px;
  align-items: stretch;
}

.settings-row > .el-col {
  display: flex;
  flex-direction: column;
}

.settings-row > .el-col:first-child {
  flex-shrink: 0;
}

.settings-row > .el-col:last-child {
  flex-shrink: 1;
  overflow: auto;
}

/* Make menu stretch to fill column height */
.settings-menu {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.notification-setting {
  padding: 16px 0;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.setting-info h4 {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.setting-info p {
  font-size: 13px;
  color: #999;
}

.smtp-form {
  max-width: 720px;
}

.form-tip {
  display: block;
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.form-tip-group {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.full-width {
  width: 100%;
}

.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.notification-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}

.my-4 {
  margin: 16px 0;
}

.mr-1 {
  margin-right: 4px;
}

.file-retention-form {
  max-width: 800px;
}

.ai-model-form {
  max-width: 680px;
}

.mb-4 {
  margin-bottom: 16px;
}

.mt-4 {
  margin-top: 16px;
}

.mt-6 {
  margin-top: 24px;
}

.text-center {
  text-align: center;
}

.text-muted {
  color: #909399;
}

.text-sm {
  font-size: 13px;
}

.text-xs {
  font-size: 12px;
}

.p-4 {
  padding: 16px;
}

.bg-gray-50 {
  background-color: #f5f7fa;
}

.bg-gray-900 {
  background-color: #1f2937;
}

.text-gray-100 {
  color: #f3f4f6;
}

.text-gray-700 {
  color: #374151;
}

.border {
  border: 1px solid #dcdfe6;
}

.rounded-lg {
  border-radius: 8px;
}

.border-success {
  border-color: #67c23a;
}

.border-danger {
  border-color: #f56c6c;
}

.bg-success-light {
  background-color: #f0f9eb;
}

.bg-danger-light {
  background-color: #fef0f0;
}

.text-green-600 {
  color: #67c23a;
}

.text-red-600 {
  color: #f56c6c;
}

.user-search-bar {
  margin-bottom: 16px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.groups-header {
  margin-bottom: 16px;
}

code {
  background-color: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}

/* LDAP/SSO Configuration Styles */
.ldap-config-card {
  max-width: 100%;
  overflow: hidden;
}

.card-header-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  font-size: 20px;
  color: #409eff;
}

.vertical-radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-start;
  margin-top: 6px;
}

.radio-tip {
  font-size: 12px;
  color: #909399;
  margin-left: 4px;
}

/* Form overrides */
.ldap-config-card :deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

.ldap-config-card :deep(.el-input__wrapper) {
  transition: all 0.3s ease;
}

.ldap-config-card :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

.ldap-config-card :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}

.ldap-config-card :deep(.el-switch.is-checked .el-switch__core) {
  background-color: #409eff;
}

/* Card rounded corners */
:deep(.el-card) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.el-card__header) {
  border-radius: 12px 12px 0 0;
}

/* Settings menu styling */
.settings-menu-col {
  min-width: 200px;
  flex-shrink: 0;
}

.settings-menu {
  min-width: 180px;
  border-radius: 12px;
  overflow: hidden;
  background-color: #ffffff;
  border: 1px solid #e4e7ed;
}

.settings-menu :deep(.el-menu-item) {
  height: 48px;
  line-height: 48px;
  padding: 0 16px;
  white-space: nowrap;
}

.settings-menu :deep(.el-menu-item span) {
  display: inline;
  opacity: 1 !important;
  visibility: visible !important;
}

.settings-menu :deep(.el-menu-item-group__title) {
  padding: 12px 16px;
  font-size: 13px;
  font-weight: 600;
  color: #909399;
}

.settings-menu :deep(.el-icon) {
  margin-right: 8px;
  width: 18px;
  height: 18px;
}
</style>
