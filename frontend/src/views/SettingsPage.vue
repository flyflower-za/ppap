<template>
  <div>
    <h2 class="mb-4">系统设置</h2>

    <el-row :gutter="32">
      <el-col :span="6">
        <el-menu :default-active="activeMenu" @select="handleMenuSelect">
          <el-menu-item index="profile">
            <el-icon><User /></el-icon>
            <span>个人信息</span>
          </el-menu-item>
          <el-menu-item index="notification">
            <el-icon><Bell /></el-icon>
            <span>通知设置</span>
          </el-menu-item>
          <el-menu-item index="file-retention" v-if="canAccessSettings('file_retention')">
            <el-icon><FolderOpened /></el-icon>
            <span>文件保留设置</span>
          </el-menu-item>
          <el-menu-item index="smtp" v-if="canAccessSettings('smtp')">
            <el-icon><Setting /></el-icon>
            <span>SMTP 配置</span>
          </el-menu-item>
          <el-menu-item index="templates" v-if="canAccessSettings('email_templates')">
            <el-icon><Document /></el-icon>
            <span>邮件模板</span>
          </el-menu-item>
          <el-menu-item index="ldap" v-if="canAccessSettings('ldap')">
            <el-icon><Lock /></el-icon>
            <span>LDAP/SSO配置</span>
          </el-menu-item>
          <el-menu-item index="ai-model" v-if="canAccessSettings('ai_model')">
            <el-icon><Cpu /></el-icon>
            <span>AI 模型配置</span>
          </el-menu-item>
          <el-menu-item index="users" v-if="canAccessSettings('users')">
            <el-icon><UserFilled /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
        </el-menu>
      </el-col>

      <el-col :span="18">
        <!-- Profile Section -->
        <el-card v-if="activeMenu === 'profile'" shadow="never">
          <template #header>
            <span>基本信息</span>
          </template>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="登录名">{{ authStore.user?.email }}</el-descriptions-item>
            <el-descriptions-item label="姓名">{{ authStore.user?.full_name }}</el-descriptions-item>
            <el-descriptions-item label="部门">{{ authStore.user?.department || '-' }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ authStore.user?.email }}</el-descriptions-item>
            <el-descriptions-item label="登录方式">
              <el-tag size="small">SSO</el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <el-alert
            type="info"
            :closable="false"
            class="mt-4"
          >
            个人信息由企业 LDAP/SSO 系统统一管理，如需修改请联系系统管理员。
          </el-alert>
        </el-card>

        <!-- Notification Section -->
        <el-card v-if="activeMenu === 'notification'" shadow="never" v-loading="loadingNotif">
          <template #header>
            <span>邮件通知设置</span>
          </template>

          <div class="notification-setting">
            <div class="setting-item">
              <div class="setting-info">
                <h4>启用邮件通知</h4>
                <p>当文件校验完成时发送邮件通知</p>
              </div>
              <el-switch v-model="emailEnabled" />
            </div>

            <el-divider />

            <div class="setting-item">
              <div class="setting-info">
                <h4>校验失败通知</h4>
                <p>当校验失败时立即发送邮件提醒</p>
              </div>
              <el-switch v-model="notifyOnFailure" />
            </div>

            <el-divider />

            <div class="setting-item">
              <div class="setting-info">
                <h4>每日汇总报告</h4>
                <p>每天发送当日校验任务汇总到邮箱</p>
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
              保存通知设置
            </el-button>
          </div>

          <el-alert
            v-if="notifSaveSuccess"
            type="success"
            title="设置已保存"
            description="通知设置已成功保存"
            :closable="false"
            show-icon
            class="mt-4"
          />
        </el-card>

        <!-- File Retention Settings Section -->
        <el-card v-if="activeMenu === 'file-retention'" shadow="never" v-loading="loadingFileRetention">
          <template #header>
            <div class="flex-between">
              <span>PDF文件保留设置</span>
              <el-tag :type="fileRetentionSettings.auto_cleanup_enabled ? 'success' : 'info'" size="small">
                {{ fileRetentionSettings.auto_cleanup_enabled ? '自动清理已启用' : '自动清理已禁用' }}
              </el-tag>
            </div>
          </template>

          <el-alert
            type="info"
            title="文件自动清理"
            description="系统将自动删除超过保留天数的PDF文件，以释放存储空间。文件删除后无法恢复，请谨慎设置。"
            :closable="false"
            show-icon
            class="mb-4"
          />

          <el-form
            ref="fileRetentionFormRef"
            :model="fileRetentionSettings"
            :rules="fileRetentionRules"
            label-width="180px"
            class="file-retention-form"
          >
            <el-form-item label="启用自动清理" prop="auto_cleanup_enabled">
              <el-switch v-model="fileRetentionSettings.auto_cleanup_enabled" />
              <span class="form-tip">启用后系统将自动清理过期的PDF文件</span>
            </el-form-item>

            <el-form-item label="文件保留天数" prop="retention_days">
              <el-input-number
                v-model="fileRetentionSettings.retention_days"
                :min="1"
                :max="3650"
                :step="1"
                :disabled="!fileRetentionSettings.auto_cleanup_enabled"
                controls-position="right"
                style="width: 200px"
              />
              <span class="form-tip">文件上传后保留的天数（1-3650天，默认30天）</span>
            </el-form-item>

            <el-form-item label="清理执行时间" prop="cleanup_hour">
              <el-select
                v-model="fileRetentionSettings.cleanup_hour"
                :disabled="!fileRetentionSettings.auto_cleanup_enabled"
                placeholder="选择小时"
                style="width: 200px"
              >
                <el-option
                  v-for="hour in 24"
                  :key="hour - 1"
                  :label="`${hour - 1}:00`"
                  :value="hour - 1"
                />
              </el-select>
              <span class="form-tip">每天执行清理任务的时间（0-23点，默认凌晨2点）</span>
            </el-form-item>

            <el-divider />

            <el-form-item>
              <el-button
                type="primary"
                :icon="Check"
                :loading="savingFileRetention"
                @click="handleSaveFileRetention"
              >
                保存设置
              </el-button>
              <el-button
                :icon="Delete"
                :loading="triggeringCleanup"
                :disabled="!fileRetentionSettings.auto_cleanup_enabled"
                @click="handleTriggerCleanup"
              >
                立即执行清理
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="fileRetentionSaveSuccess"
            type="success"
            title="设置已保存"
            description="文件保留设置已成功保存"
            :closable="false"
            show-icon
            class="mt-4"
          />

          <el-alert
            v-if="cleanupTriggerSuccess"
            type="success"
            title="清理任务已启动"
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
              <span>SMTP 邮件服务器配置</span>
              <el-tag :type="smtpConfig.enabled ? 'success' : 'info'" size="small">
                {{ smtpConfig.enabled ? '已启用' : '未启用' }}
              </el-tag>
            </div>
          </template>

          <el-form
            ref="smtpFormRef"
            :model="smtpConfig"
            :rules="smtpRules"
            label-width="140px"
            class="smtp-form"
          >
            <el-form-item label="启用 SMTP" prop="enabled">
              <el-switch
                v-model="smtpConfig.enabled"
              />
              <span class="form-tip">启用后将使用 SMTP 服务器发送邮件通知</span>
            </el-form-item>

            <el-divider content-position="left">服务器配置</el-divider>

            <el-form-item label="SMTP 服务器" prop="host">
              <el-input
                v-model="smtpConfig.host"
                placeholder="例如: smtp.gmail.com"
                :disabled="!smtpConfig.enabled"
                clearable
              />
            </el-form-item>

            <el-form-item label="端口" prop="port">
              <el-input
                v-model="smtpConfig.port"
                type="number"
                placeholder="587"
                :disabled="!smtpConfig.enabled"
                clearable
              />
              <span class="form-tip">常用端口: 25, 465 (SSL), 587 (TLS)</span>
            </el-form-item>

            <el-form-item label="加密方式" prop="encryption">
              <el-radio-group v-model="smtpConfig.encryption" :disabled="!smtpConfig.enabled">
                <el-radio value="none">不加密</el-radio>
                <el-radio value="tls">TLS</el-radio>
                <el-radio value="ssl">SSL</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-divider content-position="left">账户认证</el-divider>

            <el-form-item label="发件人邮箱" prop="username">
              <el-input
                v-model="smtpConfig.username"
                placeholder="例如:noreply@example.com"
                :disabled="!smtpConfig.enabled"
                clearable
              />
            </el-form-item>

            <el-form-item label="发件人名称" prop="from_name">
              <el-input
                v-model="smtpConfig.from_name"
                placeholder="例如:文件校验平台"
                :disabled="!smtpConfig.enabled"
                clearable
              />
            </el-form-item>

            <el-form-item label="密码/授权码" prop="password">
              <el-input
                v-model="smtpConfig.password"
                type="password"
                placeholder="请输入邮箱密码或授权码"
                :disabled="!smtpConfig.enabled"
                show-password
                clearable
              />
              <span class="form-tip">对于 Gmail 等服务，请使用应用专用密码</span>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :icon="MessageBox"
                :loading="testing"
                :disabled="!smtpConfig.enabled"
                @click="handleTestEmail"
              >
                发送测试邮件
              </el-button>
              <el-button
                type="success"
                :icon="Check"
                :loading="saving"
                @click="handleSaveSmtp"
              >
                保存配置
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="saveSuccess"
            type="success"
            title="配置已保存"
            description="SMTP 配置已成功保存，将在下次发送邮件时使用"
            :closable="false"
            show-icon
            class="mt-4"
          />
        </el-card>

        <!-- Email Templates Section -->
        <el-card v-if="activeMenu === 'templates'" shadow="never" v-loading="loadingTemplates">
          <template #header>
            <div class="flex-between">
              <span>邮件模板管理</span>
              <el-button
                type="primary"
                :icon="Plus"
                size="small"
                @click="handleCreateTemplate"
              >
                新建模板
              </el-button>
            </div>
          </template>

          <el-table :data="templates" style="width: 100%">
            <el-table-column prop="name" label="模板名称" width="200" />
            <el-table-column prop="id" label="模板ID" width="180" />
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
            <el-table-column label="变量" width="300">
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
            <el-table-column label="状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.is_active ? 'success' : 'info'" size="small">
                  {{ scope.row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="scope">
                <el-button
                  type="primary"
                  :icon="Edit"
                  size="small"
                  link
                  @click="handleEditTemplate(scope.row)"
                >
                  编辑
                </el-button>
                <el-button
                  type="primary"
                  size="small"
                  link
                  @click="handlePreviewTemplate(scope.row)"
                >
                  预览
                </el-button>
                <el-popconfirm
                  title="确定要删除这个模板吗？"
                  @confirm="handleDeleteTemplate(scope.row.id)"
                >
                  <template #reference>
                    <el-button type="danger" size="small" link>删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- Template Edit Dialog -->
        <el-dialog
          v-model="templateDialogVisible"
          :title="editingTemplate?.id ? '编辑邮件模板' : '新建邮件模板'"
          width="80%"
          :close-on-click-modal="false"
        >
          <el-form
            ref="templateFormRef"
            :model="templateForm"
            :rules="templateRules"
            label-width="120px"
          >
            <el-form-item label="模板ID" prop="id">
              <el-input
                v-model="templateForm.id"
                placeholder="例如: verification_complete"
                :disabled="!!editingTemplate?.id"
                clearable
              />
              <span class="form-tip">唯一标识符，用于系统调用模板</span>
            </el-form-item>

            <el-form-item label="模板名称" prop="name">
              <el-input
                v-model="templateForm.name"
                placeholder="例如: 文件校验完成通知"
                clearable
              />
            </el-form-item>

            <el-form-item label="描述" prop="description">
              <el-input
                v-model="templateForm.description"
                type="textarea"
                :rows="2"
                placeholder="模板用途描述"
              />
            </el-form-item>

            <el-form-item label="邮件主题" prop="subject">
              <el-input
                v-model="templateForm.subject"
                placeholder="例如: 文件校验完成 - {filename}"
                clearable
              />
              <span class="form-tip">可使用变量占位符，如 {filename}</span>
            </el-form-item>

            <el-form-item label="HTML内容" prop="html_content">
              <el-input
                v-model="templateForm.html_content"
                type="textarea"
                :rows="15"
                placeholder="邮件HTML内容，可使用变量占位符"
              />
              <span class="form-tip">可使用变量占位符，如 {filename}, {status} 等</span>
            </el-form-item>

            <el-form-item label="启用状态" prop="is_active">
              <el-switch v-model="templateForm.is_active" />
              <span class="form-tip">启用后，系统将使用此模板发送邮件</span>
            </el-form-item>
          </el-form>

          <template #footer>
            <el-button @click="templateDialogVisible = false">取消</el-button>
            <el-button
              type="primary"
              :icon="Check"
              :loading="savingTemplate"
              @click="handleSaveTemplate"
            >
              保存
            </el-button>
          </template>
        </el-dialog>

        <!-- Template Preview Dialog -->
        <el-dialog
          v-model="previewDialogVisible"
          title="模板预览"
          width="70%"
        >
          <div v-html="previewHtml"></div>
          <template #footer>
            <el-button @click="previewDialogVisible = false">关闭</el-button>
          </template>
        </el-dialog>

        <!-- LDAP/SSO Configuration Section -->
        <el-card v-if="activeMenu === 'ldap'" shadow="never" v-loading="loadingLDAP" class="ldap-config-card">
          <template #header>
            <div class="flex-between">
              <div class="card-header-content">
                <el-icon class="header-icon"><Lock /></el-icon>
                <span>LDAP/SSO 认证配置</span>
              </div>
              <el-tag :type="ldapConfig.ldap_enabled || ldapConfig.sso_enabled ? 'success' : 'info'" size="small">
                {{ ldapConfig.ldap_enabled || ldapConfig.sso_enabled ? '已启用' : '未启用' }}
              </el-tag>
            </div>
          </template>

          <el-form
            ref="ldapFormRef"
            :model="ldapConfig"
            :rules="ldapRules"
            label-width="160px"
            class="ldap-form"
          >
            <!-- LDAP Configuration Block -->
            <el-divider content-position="left">LDAP 目录服务配置</el-divider>

            <el-form-item label="启用 LDAP 认证" prop="ldap_enabled">
              <el-switch
                v-model="ldapConfig.ldap_enabled"
                @change="handleLDAPToggle"
              />
              <span class="form-tip">启用后将使用企业 LDAP/Active Directory 进行用户身份认证</span>
            </el-form-item>

            <template v-if="ldapConfig.ldap_enabled">
              <el-form-item label="服务器地址" prop="ldap_server">
                <el-input
                  v-model="ldapConfig.ldap_server"
                  placeholder="ldap.example.com"
                  clearable
                />
                <span class="form-tip">LDAP 服务器域名或 IP 地址</span>
              </el-form-item>

              <el-form-item label="端口" prop="ldap_port">
                <el-input
                  v-model.number="ldapConfig.ldap_port"
                  type="number"
                  placeholder="389"
                  clearable
                />
                <span class="form-tip">常用端口：389 (标准)、636 (SSL)</span>
              </el-form-item>

              <el-form-item label="加密方式" prop="ldap_use_ssl">
                <el-radio-group v-model="ldapConfig.ldap_use_ssl">
                  <el-radio :value="false">不加密</el-radio>
                  <el-radio :value="true">SSL/TLS 加密</el-radio>
                </el-radio-group>
              </el-form-item>

              <el-form-item label="绑定 DN" prop="ldap_bind_dn">
                <el-input
                  v-model="ldapConfig.ldap_bind_dn"
                  placeholder="cn=admin,dc=example,dc=com"
                  clearable
                />
                <span class="form-tip">管理员 DN，用于绑定 LDAP 服务器</span>
              </el-form-item>

              <el-form-item label="绑定密码" prop="ldap_bind_password">
                <el-input
                  v-model="ldapConfig.ldap_bind_password"
                  type="password"
                  placeholder="请输入绑定密码"
                  show-password
                  clearable
                />
                <span class="form-tip">管理员账户密码</span>
              </el-form-item>

              <el-form-item label="搜索基础 DN" prop="ldap_search_base">
                <el-input
                  v-model="ldapConfig.ldap_search_base"
                  placeholder="dc=example,dc=com"
                  clearable
                />
                <span class="form-tip">用户搜索的根路径</span>
              </el-form-item>

              <!-- Attribute Mapping -->
              <el-divider content-position="left">属性映射配置</el-divider>

              <el-form-item label="邮箱属性" prop="ldap_email_attribute">
                <el-input
                  v-model="ldapConfig.ldap_email_attribute"
                  placeholder="mail"
                  clearable
                />
                <span class="form-tip">LDAP 邮箱属性名，确保用户信息正确同步</span>
              </el-form-item>

              <el-form-item label="姓名属性" prop="ldap_name_attribute">
                <el-input
                  v-model="ldapConfig.ldap_name_attribute"
                  placeholder="cn"
                  clearable
                />
                <span class="form-tip">LDAP 姓名属性名</span>
              </el-form-item>

              <el-form-item label="部门属性" prop="ldap_department_attribute">
                <el-input
                  v-model="ldapConfig.ldap_department_attribute"
                  placeholder="department"
                  clearable
                />
                <span class="form-tip">LDAP 部门属性名</span>
              </el-form-item>

              <!-- AD Group Mapping -->
              <el-divider content-position="left">AD 组权限映射</el-divider>

              <el-form-item label="管理员组" prop="ad_admin_group">
                <el-input
                  v-model="ldapConfig.ad_admin_group"
                  placeholder="cn=PPAP-Admins,ou=groups,dc=example,dc=com"
                  clearable
                />
                <span class="form-tip">该组成员将被分配管理员权限</span>
              </el-form-item>

              <el-form-item label="经理组" prop="ad_manager_group">
                <el-input
                  v-model="ldapConfig.ad_manager_group"
                  placeholder="cn=PPAP-Managers,ou=groups,dc=example,dc=com"
                  clearable
                />
                <span class="form-tip">该组成员将被分配经理权限</span>
              </el-form-item>

              <el-form-item label="普通用户组" prop="ad_user_group">
                <el-input
                  v-model="ldapConfig.ad_user_group"
                  placeholder="cn=PPAP-Users,ou=groups,dc=example,dc=com"
                  clearable
                />
                <span class="form-tip">该组成员将被分配普通用户权限</span>
              </el-form-item>
            </template>

            <!-- SSO Configuration Block -->
            <el-divider content-position="left">SSO 单点登录配置</el-divider>

            <el-form-item label="启用 SSO 单点登录" prop="sso_enabled">
              <el-switch
                v-model="ldapConfig.sso_enabled"
                @change="handleSSOToggle"
              />
              <span class="form-tip">启用后支持第三方 SSO 提供商，支持 OIDC 协议</span>
            </el-form-item>

            <template v-if="ldapConfig.sso_enabled">
              <el-form-item label="提供商类型" prop="sso_provider">
                <el-select
                  v-model="ldapConfig.sso_provider"
                  placeholder="选择提供商"
                  style="width: 100%"
                >
                  <el-option label="Keycloak" value="keycloak" />
                  <el-option label="Azure AD" value="azure" />
                  <el-option label="Okta" value="okta" />
                  <el-option label="Auth0" value="auth0" />
                  <el-option label="其他" value="other" />
                </el-select>
                <span class="form-tip">OIDC 兼容的身份提供商</span>
              </el-form-item>

              <el-form-item label="发现端点" prop="sso_idp_sso_url">
                <el-input
                  v-model="ldapConfig.sso_idp_sso_url"
                  placeholder="https://sso.example.com/.well-known/openid-configuration"
                  clearable
                />
                <span class="form-tip">OIDC 发现文档 URL</span>
              </el-form-item>

              <el-form-item label="客户端 ID" prop="sso_entity_id">
                <el-input
                  v-model="ldapConfig.sso_entity_id"
                  placeholder="ppap-client-id"
                  clearable
                />
                <span class="form-tip">SSO 提供商分配的客户端标识符</span>
              </el-form-item>

              <el-form-item label="客户端密钥" prop="sso_sp_key">
                <el-input
                  v-model="ldapConfig.sso_sp_key"
                  type="password"
                  placeholder="请输入客户端密钥"
                  show-password
                  clearable
                />
                <span class="form-tip">客户端密钥，请妥善保管</span>
              </el-form-item>

              <el-form-item label="回调地址" prop="sso_acs_url">
                <el-input
                  v-model="ldapConfig.sso_acs_url"
                  placeholder="http://localhost:5173/auth/callback"
                  clearable
                />
                <span class="form-tip">认证成功后的回调地址</span>
              </el-form-item>
            </template>

            <!-- General Settings -->
            <el-divider content-position="left">通用用户设置</el-divider>

            <el-form-item label="自动创建用户" prop="auto_create_users">
              <el-switch v-model="ldapConfig.auto_create_users" />
              <span class="form-tip">新用户首次通过 LDAP/SSO 登录时自动创建系统账号</span>
            </el-form-item>

            <el-form-item label="保留本地管理员" prop="local_admin_enabled">
              <el-switch v-model="ldapConfig.local_admin_enabled" />
              <span class="form-tip">保留紧急访问的本地管理员账号以防身份验证服务不可用</span>
            </el-form-item>

            <el-form-item label="默认用户角色" prop="default_role">
              <el-radio-group v-model="ldapConfig.default_role" class="vertical-radio-group">
                <el-radio value="USER">
                  <span>普通用户</span>
                  <span class="radio-tip"> (基本的文件查看和上传权限)</span>
                </el-radio>
                <el-radio value="MANAGER">
                  <span>经理</span>
                  <span class="radio-tip"> (管理任务和查看报表)</span>
                </el-radio>
                <el-radio value="ADMIN">
                  <span>管理员</span>
                  <span class="radio-tip"> (完整的系统管理权限)</span>
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
                测试连接
              </el-button>

              <el-button
                type="success"
                :icon="Check"
                :loading="savingLDAP"
                @click="handleSaveLDAP"
              >
                保存配置
              </el-button>

              <el-button
                :icon="RefreshLeft"
                @click="loadLDAPConfig"
              >
                重置
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="ldapSaveSuccess"
            type="success"
            title="配置已保存"
            description="LDAP/SSO 配置已成功保存"
            :closable="false"
            show-icon
            class="mt-4"
          />
        </el-card>

        <!-- AI Model Configuration Section -->
        <el-card v-if="activeMenu === 'ai-model'" shadow="never" v-loading="loadingProfiles">
          <template #header>
            <div class="flex-between">
              <span>多模型配置（OpenAI 兼容）</span>
              <el-button type="primary" :icon="Plus" @click="handleAddProfile">新增配置</el-button>
            </div>
          </template>

          <el-alert
            type="info"
            title="关于多模型配置"
            description="您可以配置多个模型接入点。通过设为默认，规则执行引擎将自动选择对应的模型进行文本或视觉推理。"
            :closable="false"
            show-icon
            class="mb-4"
          />

          <el-table :data="modelProfiles" style="width: 100%" border>
            <el-table-column prop="name" label="配置名称" width="150" />
            <el-table-column prop="model_name" label="模型" width="150" />
            <el-table-column label="能力" width="100">
              <template #default="{ row }">
                <el-tag size="small" v-if="row.model_type === 'both'">全能</el-tag>
                <el-tag size="small" type="success" v-else-if="row.model_type === 'text'">文本</el-tag>
                <el-tag size="small" type="warning" v-else-if="row.model_type === 'vision'">视觉</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="默认状态" width="180">
              <template #default="{ row }">
                <div style="display: flex; gap: 4px;">
                  <el-tag size="small" effect="dark" type="success" v-if="row.is_default_text">默认文本</el-tag>
                  <el-tag size="small" effect="dark" type="warning" v-if="row.is_default_vision">默认视觉</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
                  {{ row.enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="250">
              <template #default="{ row }">
                <el-button link type="primary" :icon="Edit" @click="handleEditProfile(row)">编辑</el-button>
                <el-button link type="success" :icon="Connection" :loading="testingProfileId === row.id" @click="handleTestProfile(row.id)">测试</el-button>
                <el-dropdown trigger="click" style="margin-left: 12px; margin-right: 12px;">
                  <el-button link type="primary">
                    设为默认<el-icon class="el-icon--right"><arrow-down /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item @click="handleSetDefaultProfile(row.id, 'text')" :disabled="row.model_type === 'vision'">设为默认文本模型</el-dropdown-item>
                      <el-dropdown-item @click="handleSetDefaultProfile(row.id, 'vision')" :disabled="row.model_type === 'text'">设为默认视觉模型</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-popconfirm title="确定要删除此配置吗？" @confirm="handleDeleteProfile(row)">
                  <template #reference>
                    <el-button link type="danger" :icon="Delete">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>

          <el-alert
            v-if="testResult"
            :type="testResult.success ? 'success' : 'error'"
            :title="testResult.success ? '连接测试成功' : '连接测试失败'"
            :description="testResult.message"
            :closable="true"
            @close="testResult = null"
            show-icon
            class="mt-4"
          />
        </el-card>

        <!-- AI Model Profile Dialog -->
        <el-dialog
          :title="editingProfile ? '编辑模型配置' : '新增模型配置'"
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
            <el-form-item label="配置名称" prop="name">
              <el-input v-model="profileForm.name" placeholder="如：GPT-4o 默认接入点" clearable />
            </el-form-item>
            <el-form-item label="Base URL" prop="base_url">
              <el-input v-model="profileForm.base_url" placeholder="https://api.openai.com/v1" clearable />
            </el-form-item>
            <el-form-item label="API Key" prop="api_key">
              <el-input v-model="profileForm.api_key" type="password" show-password placeholder="不修改请留空" clearable />
            </el-form-item>
            <el-form-item label="模型名称" prop="model_name">
              <el-input v-model="profileForm.model_name" placeholder="如：gpt-4o" clearable />
            </el-form-item>
            <el-form-item label="模型能力" prop="model_type">
              <el-radio-group v-model="profileForm.model_type">
                <el-radio label="both">全能 (文本+视觉)</el-radio>
                <el-radio label="text">仅文本</el-radio>
                <el-radio label="vision">仅视觉</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="Max Tokens" prop="max_tokens">
              <el-input-number v-model="profileForm.max_tokens" :min="128" :max="32768" :step="512" />
            </el-form-item>
            <el-form-item label="Temperature" prop="temperature">
              <el-slider v-model="profileForm.temperature" :min="0" :max="2" :step="0.05" show-input style="width: 100%" />
            </el-form-item>
            <el-form-item label="启用状态" prop="enabled">
              <el-switch v-model="profileForm.enabled" />
            </el-form-item>
          </el-form>
          <template #footer>
            <span class="dialog-footer">
              <el-button @click="profileDialogVisible = false">取消</el-button>
              <el-button type="primary" :icon="Check" :loading="savingProfile" @click="handleSaveProfile">
                保存
              </el-button>
            </span>
          </template>
        </el-dialog>

        <!-- User Management Section -->
        <el-card v-if="activeMenu === 'users'" shadow="never" v-loading="loadingUsers">
          <template #header>
            <div class="flex-between">
              <span>用户管理</span>
              <div class="header-actions">
                <el-button :icon="Setting" size="small" @click="activeUserSubTab = 'groups'" v-if="activeUserSubTab === 'list'">权限组管理</el-button>
                <el-button :icon="UserFilled" size="small" @click="activeUserSubTab = 'list'" v-if="activeUserSubTab === 'groups'">用户列表</el-button>
                <el-button type="primary" :icon="Plus" size="small" @click="handleCreateUser" v-if="activeUserSubTab === 'list'">新增用户</el-button>
              </div>
            </div>
          </template>

          <!-- User List View -->
          <template v-if="activeUserSubTab === 'list'">
            <div class="user-search-bar">
              <el-input
                v-model="userSearchQuery"
                placeholder="搜索邮箱、姓名或部门"
                :prefix-icon="Search"
                clearable
                style="width: 300px"
                @input="filterUsers"
              />
            </div>

            <el-table :data="filteredUsers" style="width: 100%">
              <el-table-column prop="email" label="邮箱" min-width="200" />
              <el-table-column prop="full_name" label="姓名" width="120" />
              <el-table-column prop="department" label="部门" width="140" />
              <el-table-column label="权限组" width="140">
                <template #default="scope">
                  <el-tag v-if="scope.row.groups && scope.row.groups.length > 0" size="small" type="info">
                    {{ scope.row.groups.map((g: UserGroup) => g.name).join(', ') }}
                  </el-tag>
                  <span v-else class="text-muted text-sm">-</span>
                </template>
              </el-table-column>
              <el-table-column label="角色" width="110">
                <template #default="scope">
                  <el-select
                    v-model="scope.row.role"
                    size="small"
                    :disabled="scope.row.id === authStore.user?.id"
                    @change="handleRoleChange(scope.row)"
                  >
                    <el-option label="管理员" value="ADMIN" />
                    <el-option label="经理" value="MANAGER" />
                    <el-option label="普通用户" value="USER" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="scope">
                  <el-switch
                    v-model="scope.row.is_active"
                    :disabled="scope.row.id === authStore.user?.id"
                    @change="handleToggleUserStatus(scope.row)"
                  />
                </template>
              </el-table-column>
              <el-table-column label="最后登录" width="140">
                <template #default="scope">
                  {{ scope.row.last_login_at ? formatDate(scope.row.last_login_at) : '-' }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="130" fixed="right">
                <template #default="scope">
                  <el-dropdown trigger="click" @command="(cmd: string) => handleUserCommand(cmd, scope.row)">
                    <el-button link type="primary" size="small">
                      操作 <el-icon class="el-icon--right"><arrow-down /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="edit" :icon="Edit">编辑</el-dropdown-item>
                        <el-dropdown-item command="groups" :icon="UserFilled">设置权限组</el-dropdown-item>
                        <el-dropdown-item command="delete" :icon="Delete" divided v-if="scope.row.id !== authStore.user?.id">删除</el-dropdown-item>
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
                权限组用于 LDAP/SSO 登录后自动分配用户角色。用户登录时会根据其所属的 AD 组自动匹配对应的权限组角色。
              </el-alert>
            </div>

            <el-table :data="userGroups" style="width: 100%" v-loading="loadingGroups">
              <el-table-column prop="name" label="组名称" width="180" />
              <el-table-column prop="description" label="描述" min-width="200" />
              <el-table-column prop="ldap_group_dn" label="LDAP 组 DN" min-width="280">
                <template #default="scope">
                  <code class="text-xs">{{ scope.row.ldap_group_dn || '-' }}</code>
                </template>
              </el-table-column>
              <el-table-column label="分配角色" width="110">
                <template #default="scope">
                  <el-tag :type="getRoleTagType(scope.row.role)" size="small">
                    {{ getRoleLabel(scope.row.role) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="成员数量" width="90" align="center">
                <template #default="scope">
                  <el-badge :value="scope.row.member_count || 0" type="primary" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150" fixed="right">
                <template #default="scope">
                  <el-button link type="primary" :icon="Edit" size="small" @click="handleEditGroup(scope.row)">编辑</el-button>
                  <el-popconfirm
                    title="确定要删除此权限组吗？"
                    @confirm="handleDeleteGroup(scope.row)"
                  >
                    <template #reference>
                      <el-button link type="danger" :icon="Delete" size="small">删除</el-button>
                    </template>
                  </el-popconfirm>
                </template>
              </el-table-column>
            </el-table>

            <div class="mt-4 text-center">
              <el-button type="primary" :icon="Plus" @click="handleCreateGroup">新增权限组</el-button>
            </div>
          </template>
        </el-card>

        <!-- User Edit/Create Dialog -->
        <el-dialog
          v-model="userDialogVisible"
          :title="editingUser?.id ? '编辑用户' : '新增用户'"
          width="500px"
          :close-on-click-modal="false"
        >
          <el-form
            ref="userFormRef"
            :model="userForm"
            :rules="userRules"
            label-width="80px"
          >
            <el-form-item label="邮箱" prop="email">
              <el-input
                v-model="userForm.email"
                placeholder="请输入邮箱"
                :disabled="!!editingUser?.id"
                clearable
              />
            </el-form-item>
            <el-form-item label="姓名" prop="full_name">
              <el-input
                v-model="userForm.full_name"
                placeholder="请输入姓名"
                clearable
              />
            </el-form-item>
            <el-form-item label="部门" prop="department">
              <el-input
                v-model="userForm.department"
                placeholder="请输入部门"
                clearable
              />
            </el-form-item>
            <el-form-item label="角色" prop="role">
              <el-select v-model="userForm.role" placeholder="请选择角色">
                <el-option label="管理员" value="ADMIN" />
                <el-option label="经理" value="MANAGER" />
                <el-option label="普通用户" value="USER" />
              </el-select>
            </el-form-item>
            <el-form-item label="权限组" prop="group_ids">
              <el-select v-model="userForm.group_ids" multiple placeholder="选择权限组" style="width: 100%">
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
            <el-button @click="userDialogVisible = false">取消</el-button>
            <el-button
              type="primary"
              :icon="Check"
              :loading="savingUser"
              @click="handleSaveUser"
            >
              保存
            </el-button>
          </template>
        </el-dialog>

        <!-- User Groups Dialog -->
        <el-dialog
          v-model="groupDialogVisible"
          :title="editingGroup?.id ? '编辑权限组' : '新增权限组'"
          width="600px"
          :close-on-click-modal="false"
        >
          <el-form
            ref="groupFormRef"
            :model="groupForm"
            :rules="groupRules"
            label-width="120px"
          >
            <el-form-item label="组名称" prop="name">
              <el-input v-model="groupForm.name" placeholder="如: PPAP管理员组" clearable />
            </el-form-item>
            <el-form-item label="描述" prop="description">
              <el-input v-model="groupForm.description" type="textarea" :rows="2" placeholder="权限组用途描述" />
            </el-form-item>
            <el-form-item label="LDAP 组 DN" prop="ldap_group_dn">
              <el-input
                v-model="groupForm.ldap_group_dn"
                placeholder="如: cn=PPAP-Admins,ou=groups,dc=example,dc=com"
                clearable
              />
              <span class="form-tip">用户登录时，如果其 AD 组与此 DN 匹配，将自动分配此组设定的角色</span>
            </el-form-item>
            <el-form-item label="分配角色" prop="role">
              <el-select v-model="groupForm.role" placeholder="请选择角色">
                <el-option label="管理员" value="ADMIN" />
                <el-option label="经理" value="MANAGER" />
                <el-option label="普通用户" value="USER" />
              </el-select>
            </el-form-item>
          </el-form>

          <template #footer>
            <el-button @click="groupDialogVisible = false">取消</el-button>
            <el-button type="primary" :icon="Check" :loading="savingGroup" @click="handleSaveGroup">
              保存
            </el-button>
          </template>
        </el-dialog>

        <!-- User Group Assignment Dialog -->
        <el-dialog
          v-model="userGroupAssignDialogVisible"
          title="设置用户权限组"
          width="500px"
          :close-on-click-modal="false"
        >
          <el-form label-width="80px">
            <el-form-item label="用户">
              <span>{{ userForGroupAssign?.full_name }} ({{ userForGroupAssign?.email }})</span>
            </el-form-item>
            <el-form-item label="权限组">
              <el-select v-model="userForGroupAssignGroupIds" multiple placeholder="选择权限组" style="width: 100%">
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
            <el-button @click="userGroupAssignDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="savingUserGroups" @click="handleSaveUserGroups">
              保存
            </el-button>
          </template>
        </el-dialog>

        <!-- User Edit/Create Dialog -->
        <el-dialog
          v-model="userDialogVisible"
          :title="editingUser?.id ? '编辑用户' : '新增用户'"
          width="500px"
          :close-on-click-modal="false"
        >
          <el-form
            ref="userFormRef"
            :model="userForm"
            :rules="userRules"
            label-width="80px"
          >
            <el-form-item label="邮箱" prop="email">
              <el-input
                v-model="userForm.email"
                placeholder="请输入邮箱"
                :disabled="!!editingUser?.id"
                clearable
              />
            </el-form-item>
            <el-form-item label="姓名" prop="full_name">
              <el-input
                v-model="userForm.full_name"
                placeholder="请输入姓名"
                clearable
              />
            </el-form-item>
            <el-form-item label="部门" prop="department">
              <el-input
                v-model="userForm.department"
                placeholder="请输入部门"
                clearable
              />
            </el-form-item>
            <el-form-item label="角色" prop="role">
              <el-select v-model="userForm.role" placeholder="请选择角色">
                <el-option label="管理员" value="ADMIN" />
                <el-option label="经理" value="MANAGER" />
                <el-option label="普通用户" value="USER" />
              </el-select>
            </el-form-item>
          </el-form>

          <template #footer>
            <el-button @click="userDialogVisible = false">取消</el-button>
            <el-button
              type="primary"
              :icon="Check"
              :loading="savingUser"
              @click="handleSaveUser"
            >
              保存
            </el-button>
          </template>
        </el-dialog>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
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

const authStore = useAuthStore()

// Restore active menu from localStorage
const savedMenu = localStorage.getItem('settingsActiveMenu')
const activeMenu = ref(savedMenu || 'profile')

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

const profileRules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  base_url: [{ required: true, message: '请输入 Base URL', trigger: 'blur' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }]
}
const fileRetentionSettings = reactive<FileRetentionSettings>({
  retention_days: 30,
  auto_cleanup_enabled: true,
  cleanup_hour: 2
})

const fileRetentionRules: FormRules = {
  retention_days: [
    { required: true, message: '请输入文件保留天数', trigger: 'blur' },
    { type: 'number', min: 1, max: 3650, message: '保留天数必须在1-3650之间', trigger: 'blur' }
  ],
  cleanup_hour: [
    { required: true, message: '请选择清理执行时间', trigger: 'change' }
  ]
}

const smtpFormRef = ref<FormInstance>()

const smtpConfig = reactive({
  enabled: false,
  host: '',
  port: 587,
  encryption: 'tls',
  username: '',
  from_name: '文件校验平台',
  password: ''
})

const smtpRules: FormRules = {
  host: [
    { required: true, message: '请输入 SMTP 服务器地址', trigger: 'blur' }
  ],
  port: [
    { required: true, message: '请输入端口号', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入发件人邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  from_name: [
    { required: true, message: '请输入发件人名称', trigger: 'blur' }
  ]
}

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

const ldapRules: FormRules = {
  ldap_server: [
    { required: true, message: '请输入 LDAP 服务器地址', trigger: 'blur' }
  ],
  ldap_port: [
    { required: true, message: '请输入端口号', trigger: 'blur' }
  ],
  ldap_bind_dn: [
    { required: true, message: '请输入绑定 DN', trigger: 'blur' }
  ],
  ldap_bind_password: [
    { required: true, message: '请输入绑定密码', trigger: 'blur' }
  ],
  ldap_search_base: [
    { required: true, message: '请输入搜索基础 DN', trigger: 'blur' }
  ],
  ldap_email_attribute: [
    { required: true, message: '请输入邮箱属性', trigger: 'blur' }
  ],
  ldap_name_attribute: [
    { required: true, message: '请输入姓名属性', trigger: 'blur' }
  ],
  ldap_department_attribute: [
    { required: true, message: '请输入部门属性', trigger: 'blur' }
  ],
  sso_provider: [
    { required: true, message: '请选择 SSO 提供商', trigger: 'change' }
  ],
  sso_idp_sso_url: [
    { required: true, message: '请输入发现端点 URL', trigger: 'blur' },
    { type: 'url', message: '请输入正确的 URL 格式', trigger: 'blur' }
  ],
  sso_entity_id: [
    { required: true, message: '请输入客户端 ID', trigger: 'blur' }
  ],
  sso_sp_key: [
    { required: true, message: '请输入客户端密钥', trigger: 'blur' }
  ],
  sso_acs_url: [
    { required: true, message: '请输入回调地址', trigger: 'blur' },
    { type: 'url', message: '请输入正确的 URL 格式', trigger: 'blur' }
  ]
}

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
  email: '',
  full_name: '',
  department: '',
  role: 'USER' as 'ADMIN' | 'MANAGER' | 'USER',
  group_ids: [] as string[]
})

const userRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  full_name: [
    { required: true, message: '请输入姓名', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}

const groupForm = reactive({
  name: '',
  description: '',
  ldap_group_dn: '',
  role: 'USER' as 'ADMIN' | 'MANAGER' | 'USER'
})

const groupRules: FormRules = {
  name: [
    { required: true, message: '请输入组名称', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}

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
    'ADMIN': '管理员',
    'MANAGER': '经理',
    'USER': '普通用户'
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

const templateRules: FormRules = {
  id: [
    { required: true, message: '请输入模板ID', trigger: 'blur' },
    { pattern: /^[a-z_][a-z0-9_]*$/, message: '模板ID只能包含小写字母、数字和下划线，且必须以字母或下划线开头', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入模板名称', trigger: 'blur' }
  ],
  subject: [
    { required: true, message: '请输入邮件主题', trigger: 'blur' }
  ],
  html_content: [
    { required: true, message: '请输入HTML内容', trigger: 'blur' }
  ]
}

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
    ElMessage.success('通知设置已保存')

    setTimeout(() => {
      notifSaveSuccess.value = false
    }, 3000)
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
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
      ElMessage.success('SMTP 配置已保存')

      // 3秒后隐藏成功提示
      setTimeout(() => {
        saveSuccess.value = false
      }, 3000)
    } catch (error: any) {
      ElMessage.error(error.message || '保存失败')
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

      ElMessage.success('测试邮件已发送，请检查收件箱')
    } catch (error: any) {
      ElMessage.error(error.message || '发送失败，请检查配置')
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
    ElMessage.error('加载邮件模板失败')
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
        ElMessage.success('模板更新成功')
      } else {
        // Create new template
        await settingsApi.createEmailTemplate(templateForm)
        ElMessage.success('模板创建成功')
      }

      templateDialogVisible.value = false
      await loadEmailTemplates()
    } catch (error: any) {
      ElMessage.error(error.message || '保存模板失败')
    } finally {
      savingTemplate.value = false
    }
  })
}

async function handleDeleteTemplate(templateId: string) {
  try {
    const { settingsApi } = await import('@/api/settings')
    await settingsApi.deleteEmailTemplate(templateId)
    ElMessage.success('模板删除成功')
    await loadEmailTemplates()
  } catch (error: any) {
    ElMessage.error(error.message || '删除模板失败')
  }
}

async function handlePreviewTemplate(template: EmailTemplate) {
  try {
    const { settingsApi } = await import('@/api/settings')

    // Create sample context based on template variables
    const context: Record<string, any> = {}
    template.variables.forEach(variable => {
      if (variable === 'filename') context[variable] = '示例文件.pdf'
      else if (variable === 'status_emoji') context[variable] = '✅'
      else if (variable === 'status_text') context[variable] = '通过'
      else if (variable === 'pass_rate') context[variable] = '100'
      else if (variable === 'status-class') context[variable] = 'status-completed'
      else if (variable === 'date') context[variable] = '2025年01月15日'
      else if (variable === 'total_count') context[variable] = '50'
      else if (variable === 'completed_count') context[variable] = '45'
      else if (variable === 'warning_count') context[variable] = '3'
      else if (variable === 'failed_count') context[variable] = '2'
      else if (variable === 'file_list_html') context[variable] = '<div>示例文件列表</div>'
      else if (variable === 'from_name') context[variable] = '文件校验平台'
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
  } catch (error: any) {
    ElMessage.error(error.message || '预览模板失败')
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
    ElMessage.success('LDAP/SSO 配置已保存')

    setTimeout(() => {
      ldapSaveSuccess.value = false
    }, 3000)
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    savingLDAP.value = false
  }
}

async function handleTestLDAP() {
  testingLDAP.value = true

  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.testLDAPConnection()
    ElMessage.success('LDAP 连接测试成功')
  } catch (error: any) {
    ElMessage.error(error.message || '连接测试失败')
  } finally {
    testingLDAP.value = false
  }
}

// Handle LDAP toggle
function handleLDAPToggle(value: boolean) {
  if (value) {
    ElMessage.info('LDAP 已启用，请配置连接信息')
  } else {
    ElMessage.warning('LDAP 已禁用，用户无法使用 LDAP 登录')
  }
}

// Handle SSO toggle
function handleSSOToggle(value: boolean) {
  if (value) {
    ElMessage.info('SSO 已启用，请配置第三方登录')
  } else {
    ElMessage.warning('SSO 已禁用，用户无法使用 SSO 登录')
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
    ElMessage.error('加载用户列表失败')
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
    user.full_name.toLowerCase().includes(query) ||
    (user.department && user.department.toLowerCase().includes(query))
  )
}

async function handleRoleChange(user: UserInfo) {
  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.updateUserRole(user.id, user.role as 'ADMIN' | 'MANAGER' | 'USER')
    ElMessage.success(`用户 ${user.full_name} 的角色已更新为 ${user.role}`)
  } catch (error: any) {
    ElMessage.error(error.message || '更新角色失败')
    // Revert the change
    await loadUsers()
  }
}

async function handleToggleUserStatus(user: UserInfo) {
  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.toggleUserStatus(user.id)
    const status = user.is_active ? '启用' : '禁用'
    ElMessage.success(`用户 ${user.full_name} 已${status}`)
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
    // Revert the change
    await loadUsers()
  }
}

function handleCreateUser() {
  editingUser.value = null
  Object.assign(userForm, {
    email: '',
    full_name: '',
    department: '',
    role: 'USER',
    group_ids: []
  })
  userDialogVisible.value = true
}

function handleEditUser(user: UserInfo) {
  editingUser.value = user
  Object.assign(userForm, {
    email: user.email,
    full_name: user.full_name,
    department: user.department || '',
    role: user.role as 'ADMIN' | 'MANAGER' | 'USER',
    group_ids: user.groups?.map((g: UserGroupBasic) => g.id) || []
  })
  userDialogVisible.value = true
}

async function handleSaveUser() {
  if (!userFormRef.value) return

  await userFormRef.value.validate(async (valid) => {
    if (!valid) return

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
        ElMessage.success('用户信息已更新')
      } else {
        // Create new user
        const result = await ldapApi.createUser({
          email: userForm.email,
          full_name: userForm.full_name,
          department: userForm.department || undefined,
          role: userForm.role
        })
        userId = result.user.id
        ElMessage.success('用户创建成功')
      }

      // Update user groups
      await ldapApi.setUserGroups(userId, userForm.group_ids)

      userDialogVisible.value = false
      await loadUsers()
    } catch (error: any) {
      ElMessage.error(error.message || '保存失败')
    } finally {
      savingUser.value = false
    }
  })
}

async function handleDeleteUser(user: UserInfo) {
  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.deleteUser(user.id)
    ElMessage.success('用户已删除')
    await loadUsers()
  } catch (error: any) {
    ElMessage.error(error.message || '删除失败')
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
    ElMessage.error('加载权限组失败')
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
        ElMessage.success('权限组已更新')
      } else {
        // Create new group
        await ldapApi.createUserGroup(groupForm)
        ElMessage.success('权限组创建成功')
      }

      groupDialogVisible.value = false
      await loadUserGroups()
    } catch (error: any) {
      ElMessage.error(error.message || '保存失败')
    } finally {
      savingGroup.value = false
    }
  })
}

async function handleDeleteGroup(group: UserGroup) {
  try {
    const { ldapApi } = await import('@/api/ldap')
    await ldapApi.deleteUserGroup(group.id)
    ElMessage.success('权限组已删除')
    await loadUserGroups()
  } catch (error: any) {
    ElMessage.error(error.message || '删除失败')
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
    ElMessage.success('用户权限组已更新')
    userGroupAssignDialogVisible.value = false
    await loadUsers()
  } catch (error: any) {
    ElMessage.error(error.message || '更新失败')
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
    ElMessage.error('加载文件保留设置失败')
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
      ElMessage.success('文件保留设置已保存')

      setTimeout(() => {
        fileRetentionSaveSuccess.value = false
      }, 3000)
    } catch (error: any) {
      ElMessage.error(error.message || '保存失败')
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

    cleanupTriggerMessage.value = `任务ID: ${response.task_id}`
    cleanupTriggerSuccess.value = true
    ElMessage.success('清理任务已启动，请稍后查看结果')

    setTimeout(() => {
      cleanupTriggerSuccess.value = false
    }, 5000)
  } catch (error: any) {
    ElMessage.error(error.message || '启动清理任务失败')
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
    ElMessage.error('加载模型配置失败')
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
        ElMessage.success('配置已更新')
      } else {
        await settingsApi.createModelProfile(submitData)
        ElMessage.success('配置已创建')
      }
      profileDialogVisible.value = false
      await loadModelProfiles()
    } catch (error: any) {
      ElMessage.error(error.message || '保存失败')
    } finally {
      savingProfile.value = false
    }
  })
}

async function handleDeleteProfile(profile: ModelProfile) {
  try {
    const { settingsApi } = await import('@/api/settings')
    await settingsApi.deleteModelProfile(profile.id)
    ElMessage.success('配置已删除')
    await loadModelProfiles()
  } catch (error: any) {
    ElMessage.error(error.message || '删除失败')
  }
}

async function handleSetDefaultProfile(profileId: string, forType: 'text' | 'vision') {
  try {
    const { settingsApi } = await import('@/api/settings')
    await settingsApi.setDefaultModelProfile(profileId, forType)
    ElMessage.success(`已设为默认${forType}模型`)
    await loadModelProfiles()
  } catch (error: any) {
    ElMessage.error(error.message || '设置失败')
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
      ElMessage.success('连接测试成功')
    } else {
      ElMessage.warning('连接测试失败')
    }
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    const message = detail || error?.message || '连接测试失败，请检查网络或配置'
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
  max-width: 600px;
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
  max-width: 700px;
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
  max-width: 1200px;
  margin: 0 auto;
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
</style>
