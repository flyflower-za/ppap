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
        <el-card v-if="activeMenu === 'ldap'" shadow="never" v-loading="loadingLDAP">
          <template #header>
            <div class="flex-between">
              <span>LDAP/SSO 认证配置</span>
              <el-tag :type="ldapConfig.ldap_enabled || ldapConfig.sso_enabled ? 'success' : 'info'" size="small">
                {{ ldapConfig.ldap_enabled || ldapConfig.sso_enabled ? '已启用' : '未启用' }}
              </el-tag>
            </div>
          </template>

          <el-form
            ref="ldapFormRef"
            :model="ldapConfig"
            label-width="200px"
            class="ldap-form"
          >
            <el-divider content-position="left">基本设置</el-divider>

            <el-form-item label="保留本地管理员账号" prop="local_admin_enabled">
              <el-switch v-model="ldapConfig.local_admin_enabled" />
              <span class="form-tip">保留本地管理员账号，用于紧急访问</span>
            </el-form-item>

            <el-form-item label="自动创建用户" prop="auto_create_users">
              <el-switch v-model="ldapConfig.auto_create_users" />
              <span class="form-tip">用户首次登录时自动创建账号</span>
            </el-form-item>

            <el-form-item label="默认用户角色" prop="default_role">
              <el-radio-group v-model="ldapConfig.default_role">
                <el-radio value="USER">普通用户</el-radio>
                <el-radio value="MANAGER">经理</el-radio>
                <el-radio value="ADMIN">管理员</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-divider content-position="left">LDAP 配置</el-divider>

            <el-form-item label="启用 LDAP" prop="ldap_enabled">
              <el-switch v-model="ldapConfig.ldap_enabled" />
            </el-form-item>

            <el-form-item label="LDAP 服务器" v-if="ldapConfig.ldap_enabled" prop="ldap_server">
              <el-input
                v-model="ldapConfig.ldap_server"
                placeholder="例如: ldap.example.com"
                clearable
              />
            </el-form-item>

            <el-form-item label="端口" v-if="ldapConfig.ldap_enabled" prop="ldap_port">
              <el-input
                v-model.number="ldapConfig.ldap_port"
                type="number"
                placeholder="389"
                clearable
              />
              <span class="form-tip">常用端口: 389 (标准), 636 (SSL)</span>
            </el-form-item>

            <el-form-item label="使用 SSL/TLS" v-if="ldapConfig.ldap_enabled" prop="ldap_use_ssl">
              <el-switch v-model="ldapConfig.ldap_use_ssl" />
            </el-form-item>

            <el-form-item label="绑定 DN" v-if="ldapConfig.ldap_enabled" prop="ldap_bind_dn">
              <el-input
                v-model="ldapConfig.ldap_bind_dn"
                placeholder="例如: cn=admin,dc=example,dc=com"
                clearable
              />
            </el-form-item>

            <el-form-item label="绑定密码" v-if="ldapConfig.ldap_enabled" prop="ldap_bind_password">
              <el-input
                v-model="ldapConfig.ldap_bind_password"
                type="password"
                placeholder="请输入绑定密码"
                show-password
                clearable
              />
            </el-form-item>

            <el-form-item label="搜索基础 DN" v-if="ldapConfig.ldap_enabled" prop="ldap_search_base">
              <el-input
                v-model="ldapConfig.ldap_search_base"
                placeholder="例如: dc=example,dc=com"
                clearable
              />
            </el-form-item>

            <el-form-item label="邮箱属性" v-if="ldapConfig.ldap_enabled" prop="ldap_email_attribute">
              <el-input
                v-model="ldapConfig.ldap_email_attribute"
                placeholder="mail"
                clearable
              />
            </el-form-item>

            <el-form-item label="姓名属性" v-if="ldapConfig.ldap_enabled" prop="ldap_name_attribute">
              <el-input
                v-model="ldapConfig.ldap_name_attribute"
                placeholder="cn"
                clearable
              />
            </el-form-item>

            <el-form-item label="部门属性" v-if="ldapConfig.ldap_enabled" prop="ldap_department_attribute">
              <el-input
                v-model="ldapConfig.ldap_department_attribute"
                placeholder="department"
                clearable
              />
            </el-form-item>

            <el-divider content-position="left">AD 组映射（权限分配）</el-divider>

            <el-form-item label="管理员组 DN" v-if="ldapConfig.ldap_enabled" prop="ad_admin_group">
              <el-input
                v-model="ldapConfig.ad_admin_group"
                placeholder="例如: cn=PPAP-Admins,ou=groups,dc=example,dc=com"
                clearable
              />
              <span class="form-tip">该组成员将被分配管理员权限</span>
            </el-form-item>

            <el-form-item label="经理组 DN" v-if="ldapConfig.ldap_enabled" prop="ad_manager_group">
              <el-input
                v-model="ldapConfig.ad_manager_group"
                placeholder="例如: cn=PPAP-Managers,ou=groups,dc=example,dc=com"
                clearable
              />
              <span class="form-tip">该组成员将被分配经理权限</span>
            </el-form-item>

            <el-form-item label="用户组 DN" v-if="ldapConfig.ldap_enabled" prop="ad_user_group">
              <el-input
                v-model="ldapConfig.ad_user_group"
                placeholder="例如: cn=PPAP-Users,ou=groups,dc=example,dc=com"
                clearable
              />
              <span class="form-tip">该组成员将被分配普通用户权限</span>
            </el-form-item>

            <el-divider content-position="left">SSO 配置（SAML）</el-divider>

            <el-form-item label="启用 SSO" prop="sso_enabled">
              <el-switch v-model="ldapConfig.sso_enabled" />
            </el-form-item>

            <el-form-item label="SSO 提供商" v-if="ldapConfig.sso_enabled" prop="sso_provider">
              <el-input
                v-model="ldapConfig.sso_provider"
                placeholder="例如: AzureAD, Okta"
                clearable
              />
            </el-form-item>

            <el-form-item label="实体 ID" v-if="ldapConfig.sso_enabled" prop="sso_entity_id">
              <el-input
                v-model="ldapConfig.sso_entity_id"
                placeholder="例如: https://ppap.example.com"
                clearable
              />
            </el-form-item>

            <el-form-item label="ACS URL" v-if="ldapConfig.sso_enabled" prop="sso_acs_url">
              <el-input
                v-model="ldapConfig.sso_acs_url"
                placeholder="断言消费服务 URL"
                clearable
              />
            </el-form-item>

            <el-form-item label="IdP SSO URL" v-if="ldapConfig.sso_enabled" prop="sso_idp_sso_url">
              <el-input
                v-model="ldapConfig.sso_idp_sso_url"
                placeholder="身份提供者登录 URL"
                clearable
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :icon="Check"
                :loading="savingLDAP"
                @click="handleSaveLDAP"
              >
                保存配置
              </el-button>
              <el-button
                v-if="ldapConfig.ldap_enabled"
                :icon="MessageBox"
                :loading="testingLDAP"
                @click="handleTestLDAP"
              >
                测试 LDAP 连接
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

        <!-- User Management Section -->
        <el-card v-if="activeMenu === 'users'" shadow="never" v-loading="loadingUsers">
          <template #header>
            <span>用户管理</span>
          </template>

          <el-table :data="users" style="width: 100%">
            <el-table-column prop="email" label="邮箱" width="250" />
            <el-table-column prop="full_name" label="姓名" width="150" />
            <el-table-column prop="department" label="部门" />
            <el-table-column label="角色" width="120">
              <template #default="scope">
                <el-select
                  v-model="scope.row.role"
                  size="small"
                  @change="handleRoleChange(scope.row)"
                >
                  <el-option label="管理员" value="ADMIN" />
                  <el-option label="经理" value="MANAGER" />
                  <el-option label="普通用户" value="USER" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.is_active ? 'success' : 'info'" size="small">
                  {{ scope.row.is_active ? '激活' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="最后登录" width="180">
              <template #default="scope">
                {{ scope.row.last_login_at ? new Date(scope.row.last_login_at).toLocaleString() : '-' }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Bell, Setting, Document, MessageBox, Check, Plus, Edit, Lock, UserFilled, FolderOpened, Delete } from '@element-plus/icons-vue'
import type { EmailTemplate, FileRetentionSettings } from '@/api/settings'
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
const users = ref<UserInfo[]>([])
const loadingUsers = ref(false)

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

async function loadUsers() {
  loadingUsers.value = true
  try {
    const { ldapApi } = await import('@/api/ldap')
    users.value = await ldapApi.getAllUsers()
  } catch (error) {
    console.error('Failed to load users:', error)
    ElMessage.error('加载用户列表失败')
  } finally {
    loadingUsers.value = false
  }
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

.mb-4 {
  margin-bottom: 16px;
}
</style>
