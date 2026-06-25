<template>
  <div class="detail-page-container" v-loading="loading" element-loading-background="rgba(245, 247, 250, 0.8)">
    <!-- Back Button -->
    <div class="navigation-header mb-4">
      <el-button
        :icon="ArrowLeft"
        @click="router.back()"
        class="back-btn glass-btn"
      >
        {{ $t('detail.backToHistory') }}
      </el-button>
    </div>

    <div v-if="file" class="detail-content-layout">
      <!-- File Header Premium Panel -->
      <div class="glass-card header-panel mb-4" :class="statusGlowClass(file.status)">
        <div class="header-main flex-between">
          <div class="file-brand-info">
            <div class="icon-glow-wrapper" :class="file.status">
              <el-icon :size="36"><Document /></el-icon>
            </div>
            <div class="file-details">
              <h2 class="file-title" :title="file.original_filename">{{ file.original_filename }}</h2>
              <div class="file-sub-info" style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <span class="file-type-pill" style="height: 24px; line-height: 24px; display: inline-flex; align-items: center; font-size: 12px;">{{ fileTypeLabel(file.file_type) }}</span>
                <span class="dot-separator">•</span>
                <span class="file-meta-txt" style="font-size: 13px;">{{ formatFileSize(file.file_size) }}</span>
                <span class="dot-separator">•</span>
                <span class="file-meta-txt" style="font-size: 13px;">{{ file.page_count || '-' }} {{ $t('common.page') }}</span>
                <span class="dot-separator">•</span>
                <span class="file-meta-txt" style="font-size: 13px;">{{ $t('detail.trackingId') }}: {{ file.id ? file.id.substring(0, 8) : '-' }}</span>
                
                <template v-if="file.status !== 'pending' && file.status !== 'processing'">
                  <span class="dot-separator">•</span>
                  <el-tag :type="digitalSignatures?.signed ? 'success' : 'danger'" effect="plain" class="feature-tag" style="border-radius: 6px; font-weight: 600; font-size: 13px; height: 32px; line-height: 30px; padding: 0 12px;">
                    {{ digitalSignatures?.signed ? $t('detail.signedDigital') : $t('detail.noValidSignature') }}
                  </el-tag>
                  <el-tag :type="isTextPdf ? 'primary' : 'warning'" effect="plain" class="feature-tag" style="border-radius: 6px; font-weight: 600; font-size: 13px; height: 32px; line-height: 30px; padding: 0 12px;">
                    {{ isTextPdf ? $t('detail.vectorText') : $t('detail.scannedImage') }}
                  </el-tag>
                  <el-tag type="info" effect="plain" class="feature-tag" style="border-radius: 6px; font-weight: 600; font-size: 13px; height: 32px; line-height: 30px; padding: 0 12px;">
                    {{ $t('detail.qrCodeCount', { count: qrCodeCount }) }}
                  </el-tag>
                  <el-tag v-if="stampCount > 0" type="warning" effect="plain" class="feature-tag" style="border-radius: 6px; font-weight: 600; font-size: 13px; height: 32px; line-height: 30px; padding: 0 12px;">
                    {{ $t('detail.stampCount', { count: stampCount }) }}
                  </el-tag>
                </template>
              </div>
            </div>
          </div>
          
          <div class="header-actions" style="display: flex; align-items: center; gap: 12px;">
            <el-tag
              v-if="file.status !== 'pending' && file.status !== 'processing'"
              :type="file.status === 'completed' ? 'success' : (file.status === 'failed' ? 'danger' : 'warning')"
              effect="plain"
              class="risk-level-tag"
              style="font-weight: 700; border-radius: 6px; padding: 0 12px; height: 32px; line-height: 30px; font-size: 13px;"
            >
              {{ riskLevelText }}
            </el-tag>
            <span v-else class="premium-status-badge" :class="file.status" style="font-size: 13px; padding: 4px 12px; border-radius: 6px; height: 32px; display: inline-flex; align-items: center;">
              <span class="pulse-indicator" v-if="file.status === 'processing'"></span>
              {{ statusText(file.status) }}
            </span>
            
            <el-button 
              type="primary" 
              :icon="Download" 
              @click="handleDownload"
              :disabled="file.status === 'pending' || file.status === 'processing'"
              class="download-report-btn"
              style="height: 32px; border-radius: 6px; font-size: 13px; font-weight: 600; display: inline-flex; align-items: center;"
            >
              {{ $t('detail.downloadOriginal') }}
            </el-button>
            <el-button
              @click="trajectoryDrawerVisible = true"
              class="trajectory-btn glass-btn"
              :icon="Tickets"
              style="height: 32px; border-radius: 6px; font-size: 13px; font-weight: 500; display: inline-flex; align-items: center; margin-left: 0 !important;"
            >
              {{ $t('detail.executionLog') }}
            </el-button>
          </div>
        </div>

        <el-divider class="glass-divider" />

        <!-- File Metadata Grid -->
        <el-row :gutter="24" class="file-meta-grid">
          <el-col :xs="12" :sm="8" :md="4" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">{{ $t('detail.institutionAiSniff') }}</span>
              <span class="meta-value text-primary font-bold">{{ sniffedInstitution || $t('detail.unknownAnalyzing') }}</span>
            </div>
          </el-col>
          <el-col :xs="12" :sm="8" :md="4" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">{{ $t('detail.uploadAccount') }}</span>
              <span class="meta-value">{{ file.uploaded_by || '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="12" :sm="8" :md="4" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">{{ $t('file.uploadedAt') }}</span>
              <span class="meta-value">{{ formatDate(file.uploaded_at) }}</span>
            </div>
          </el-col>
          <el-col :xs="12" :sm="8" :md="4" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">{{ $t('file.completedAt') }}</span>
              <span class="meta-value">{{ file.completed_at ? formatDate(file.completed_at) : '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="12" :sm="8" :md="4" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">{{ $t('detail.verificationDuration') }}</span>
              <span class="meta-value">{{ file.duration_seconds !== null && file.duration_seconds !== undefined ? formatDuration(file.duration_seconds) : '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="12" :sm="8" :md="4" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">{{ $t('detail.finalPassRate') }}</span>
              <span class="meta-value pass-rate-highlight" :class="passRateClass(file.pass_rate)">
                {{ file.pass_rate !== null && file.pass_rate !== undefined ? file.pass_rate + '%' : '-' }}
              </span>
            </div>
          </el-col>
        </el-row>

        <!-- Active Processing Progress Tracker -->
        <div v-if="file.status === 'pending' || file.status === 'processing'" class="live-progress-container mt-4">
          <div class="progress-info-row flex-between mb-2">
            <span class="progress-status-title">{{ $t('detail.runningAnalysis') }}</span>
            <span class="progress-percent-val">{{ file.verification_progress }}%</span>
          </div>
          <div class="glowing-progress-track">
            <div class="glowing-progress-fill" :style="{ width: file.verification_progress + '%' }"></div>
          </div>
        </div>
      </div>

      <!-- Main Layout: 2 Columns -->
      <el-row :gutter="24" class="content-row">
        <!-- Left Column: PDF Preview -->
        <el-col :xs="24" :lg="14" class="grid-column" style="display: flex; flex-direction: column;">
          <div class="glass-card section-panel pdf-preview-panel" style="flex: 1; display: flex; flex-direction: column; padding: 0; max-height: 85vh; height: 85vh;">
            <div class="section-title" style="padding: 24px 24px 0 24px;">
              <h3>{{ $t('detail.documentPreview') }}</h3>
            </div>
            <div 
              ref="pdfContainerRef" 
              class="pdf-viewer-container" 
              v-loading="pdfLoading"
              style="flex: 1; overflow-y: auto; background-color: #e5e7eb; position: relative; padding: 20px; display: flex; flex-direction: column; align-items: center;"
            >
              <el-empty
                v-if="!file || ['pending', 'processing'].includes(file.status)"
                :description="$t('detail.waitingPreview')"
                :image-size="80"
              />
            </div>
          </div>
        </el-col>

        <!-- Right Column: Verification Results & Details -->
        <el-col :xs="24" :lg="10" class="grid-column right-scroll-col" style="max-height: 85vh; overflow-y: auto; padding-right: 8px;">
          
          <!-- HITL Review Arbitration Panel -->
          <div class="glass-card section-panel mb-4 arbitration-panel" v-if="file?.status === 'needs_review'">
            <div class="section-title text-warning flex-between" style="color: #E6A23C;">
              <h3 class="flex-align-center"><el-icon class="mr-2"><WarningFilled /></el-icon> {{ $t('detail.needsHumanReview') }}</h3>
            </div>
            <div class="arbitration-content mt-2">
              <p class="text-sm text-gray-600 mb-4" style="line-height: 1.5; margin-bottom: 16px;">
                {{ $t('detail.humanReviewDesc') }}
              </p>
              <div class="arbitration-actions flex gap-4" style="display: flex; gap: 12px;">
                <el-button type="success" :icon="Check" style="flex: 1" @click="handleReviewResolution('approve')">
                  {{ $t('detail.approveAction') }}
                </el-button>
                <el-button type="danger" :icon="Close" style="flex: 1" @click="handleReviewResolution('reject')">
                  {{ $t('detail.rejectAction') }}
                </el-button>
              </div>
            </div>
          </div>

          <!-- Verification Results -->
          <div class="glass-card section-panel mb-4">
            <div class="section-title flex-between">
              <h3>{{ $t('detail.diagnosticReport') }}</h3>
              <div class="checks-counters" v-if="file.verification_result_json?.summary" style="align-items: center;">
                <span 
                  class="counter-badge pass clickable-counter" 
                  :class="{ 'is-active': activeFilter === 'pass' }"
                  @click="toggleFilter('pass')"
                  style="cursor: pointer; transition: all 0.2s; user-select: none;"
                >
                  {{ $t('detail.passLabel', { count: file.pass_count }) }}
                </span>
                <span 
                  class="counter-badge warning clickable-counter"
                  v-if="file.warning_count > 0"
                  :class="{ 'is-active': activeFilter === 'warning' }"
                  @click="toggleFilter('warning')"
                  style="cursor: pointer; transition: all 0.2s; user-select: none;"
                >
                  {{ $t('detail.warningLabel', { count: file.warning_count }) }}
                </span>
                <span 
                  class="counter-badge fail clickable-counter"
                  v-if="file.fail_count > 0"
                  :class="{ 'is-active': activeFilter === 'fail' }"
                  @click="toggleFilter('fail')"
                  style="cursor: pointer; transition: all 0.2s; user-select: none;"
                >
                  {{ $t('detail.failLabel', { count: file.fail_count }) }}
                </span>
                <el-button
                  v-if="activeFilter !== 'all'"
                  size="small"
                  link
                  type="info"
                  class="ml-2"
                  @click="activeFilter = 'all'"
                  style="font-size: 11px;"
                >
                  {{ $t('detail.resetFilter') }}
                </el-button>
                <el-button size="small" type="primary" plain class="ml-3 print-btn hide-on-print" @click="handlePrintReport">
                  {{ $t('detail.exportReportPdf') }}
                </el-button>
              </div>
            </div>

            <el-empty
              v-if="!file.verification_result_json || !file.verification_result_json.checks || file.verification_result_json.checks.length === 0"
              :description="$t('detail.verificationInProgress')"
              :image-size="120"
              class="empty-report-state"
            />

            <div v-else class="diagnostic-checklist">
              <el-empty
                v-if="filteredChecks.length === 0"
                :description="$t('detail.noMatchingFilter')"
                :image-size="60"
                style="padding: 20px 0;"
              />
              <div
                v-else
                v-for="(check, index) in filteredChecks"
                :key="index"
                class="diagnostic-check-card"
                :class="[check.status, check.page ? 'has-page-link' : '']"
                @click="check.page ? scrollToPage(check.page) : null"
              >
                <div class="check-left-indicator" :class="check.status"></div>
                <div class="diagnostic-check-icon" :class="check.status">
                  <el-icon v-if="check.status === 'pass'"><Check /></el-icon>
                  <el-icon v-else-if="check.status === 'warning'"><Warning /></el-icon>
                  <el-icon v-else-if="check.status === 'info'"><InfoFilled /></el-icon>
                  <el-icon v-else><Close /></el-icon>
                </div>
                <div class="diagnostic-check-body" style="width: 100%;">
                  <div class="check-title-row flex-between">
                    <h4 class="flex-align-center">
                      {{ check.name }}
                      <el-tag v-if="check.page" size="small" type="info" effect="plain" class="ml-2 page-tag">
                        {{ $t('detail.pageLabel', { page: check.page }) }} <el-icon class="ml-1"><Position /></el-icon>
                      </el-tag>
                    </h4>
                    <div style="display: flex; align-items: center; gap: 8px;">
                      <span v-if="check.confidence !== undefined && check.confidence !== null" class="check-confidence-badge" :class="{ 'low-confidence': check.confidence < 0.85 }">
                        {{ $t('detail.confidence', { value: (check.confidence * 100).toFixed(0) }) }}
                        <el-icon v-if="check.confidence < 0.85" class="ml-1"><WarningFilled /></el-icon>
                      </span>
                      <span class="check-status-tag" :class="check.status">{{ checkStatusLabel(check.status) }}</span>
                    </div>
                  </div>
                  <p class="check-message">{{ check.message }}</p>
                  
                  <!-- Visual Positioning Hint -->
                  <div v-if="check.page" class="locate-tip-wrapper" style="display: flex; justify-content: flex-end; margin-top: 8px;">
                    <span class="locate-tip" style="font-size: 11px; font-weight: 600; color: #4285f4; display: inline-flex; align-items: center; gap: 4px; opacity: 0.7; transition: all 0.2s;">
                      {{ $t('detail.clickToLocate') }}
                      <el-icon class="arrow-icon-slide"><Right /></el-icon>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Visual PDF Diff Card -->
          <div
            v-if="diffResults && diffResults.changes && diffResults.changes.length > 0"
            class="glass-card section-panel mb-4 diff-panel"
          >
            <div class="section-title flex-between cursor-pointer" @click="diffDetailsCollapsed = !diffDetailsCollapsed" style="user-select: none; margin-bottom: 0;">
              <h3 class="flex-align-center">
                <el-icon class="mr-2"><Tickets /></el-icon> {{ $t('detail.textDiffComparison', { similarity: diffResults.similarity }) }}
              </h3>
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-tag type="danger" size="small">{{ $t('detail.differencesCount', { count: diffResults.changes_count }) }}</el-tag>
                <el-button link type="primary" style="font-size: 13px;">
                  {{ diffDetailsCollapsed ? $t('detail.expand') : $t('detail.collapse') }}
                  <el-icon class="ml-1"><component :is="diffDetailsCollapsed ? ArrowDown : ArrowUp" /></el-icon>
                </el-button>
              </div>
            </div>
            
            <el-collapse-transition>
              <div v-show="!diffDetailsCollapsed" class="mt-4">
                <div class="diff-changes-list">
                  <div
                    v-for="(change, idx) in diffResults.changes"
                    :key="idx"
                    class="diff-change-item"
                  >
                    <div class="diff-change-header flex-between mb-2">
                      <span class="diff-change-index font-bold">{{ $t('detail.differenceLocation', { idx: idx + 1 }) }}</span>
                      <el-tag :type="change.type === 'delete' || change.type === 'replace' ? 'danger' : 'success'" size="small" effect="dark">
                        {{ change.type === 'delete' ? $t('detail.changeTypeDeleted') : (change.type === 'replace' ? $t('detail.changeTypeModified') : $t('detail.changeTypeAdded')) }}
                      </el-tag>
                    </div>
                    
                    <div class="diff-comparison-box">
                      <!-- Removed/Original Fragment -->
                      <div v-if="change.type === 'delete' || change.type === 'replace'" class="diff-line removed">
                        <span class="line-marker">-</span>
                        <div class="line-content" v-html="formatDiffFragment(change.original_fragment, 'removed')"></div>
                      </div>
                      
                      <!-- Added/Current Fragment -->
                      <div v-if="change.type === 'insert' || change.type === 'replace'" class="diff-line added">
                        <span class="line-marker">+</span>
                        <div class="line-content" v-html="formatDiffFragment(change.current_fragment, 'added')"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </el-collapse-transition>
          </div>

          <!-- General Details Card -->
          <div class="glass-card section-panel mb-4 small-card">
            <div class="section-title flex-between cursor-pointer" @click="generalDetailsCollapsed = !generalDetailsCollapsed" style="user-select: none; margin-bottom: 0;">
              <h3>{{ $t('detail.fileDiagnosticDetails') }}</h3>
              <el-button link type="primary" style="font-size: 13px;">
                {{ generalDetailsCollapsed ? $t('detail.expand') : $t('detail.collapse') }}
                <el-icon class="ml-1"><component :is="generalDetailsCollapsed ? ArrowDown : ArrowUp" /></el-icon>
              </el-button>
            </div>
            <el-collapse-transition>
              <div v-show="!generalDetailsCollapsed" class="info-details-list mt-4">
                <div class="info-detail-item">
                  <span class="lbl">{{ $t('detail.verificationId') }}</span>
                  <span class="val text-monospace">#{{ file.id.substring(0, 8) }}</span>
                </div>
                <div class="info-detail-item">
                  <span class="lbl">{{ $t('detail.uploadAccount') }}</span>
                  <span class="val">{{ file.uploaded_by || '-' }}</span>
                </div>
                <div class="info-detail-item">
                  <span class="lbl">{{ $t('detail.verificationModel') }}</span>
                  <span class="val">{{ file.verification_result_json?.model_version || file.verification_model || $t('detail.smartEngine') }}</span>
                </div>
                <div class="info-detail-item">
                  <span class="lbl">{{ $t('file.passCount') }}</span>
                  <span class="val color-pass">{{ $t('detail.passItems', { count: file.pass_count }) }}</span>
                </div>
                <div class="info-detail-item">
                  <span class="lbl">{{ $t('file.warningCount') }}</span>
                  <span class="val color-warning">{{ $t('detail.warningItems', { count: file.warning_count }) }}</span>
                </div>
                <div class="info-detail-item">
                  <span class="lbl">{{ $t('file.failCount') }}</span>
                  <span class="val color-fail">{{ $t('detail.failItems', { count: file.fail_count }) }}</span>
                </div>
              </div>
            </el-collapse-transition>
          </div>

          <!-- Digital Signature Details Card -->
          <div
            v-if="digitalSignatures"
            class="glass-card section-panel mb-4 small-card"
          >
            <div class="section-title flex-between cursor-pointer" @click="signatureDetailsCollapsed = !signatureDetailsCollapsed" style="user-select: none; margin-bottom: 0;">
              <h3>{{ $t('detail.digitalSignatureDetails') }}</h3>
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-tag
                  :type="digitalSignatures.signed ? 'success' : 'info'"
                  size="small"
                >
                  {{ digitalSignatures.signed ? $t('detail.signed') : $t('detail.unsigned') }}
                </el-tag>
                <el-button link type="primary" style="font-size: 13px;">
                  {{ signatureDetailsCollapsed ? $t('detail.expand') : $t('detail.collapse') }}
                  <el-icon class="ml-1"><component :is="signatureDetailsCollapsed ? ArrowDown : ArrowUp" /></el-icon>
                </el-button>
              </div>
            </div>

            <el-collapse-transition>
              <div v-show="!signatureDetailsCollapsed" class="mt-4">
                <!-- No Signatures -->
                <el-empty
                  v-if="!digitalSignatures.signed"
                  :description="$t('detail.noDigitalSignatures')"
                  :image-size="60"
                  class="compact-empty"
                />

                <!-- Signature List -->
                <div v-else class="signatures-list">
                  <div
                    v-for="(sig, index) in digitalSignatures.signatures"
                    :key="index"
                    class="signature-card"
                    :class="{ 'sig-invalid': !sig.integrity || sig.expired }"
                  >
                    <!-- Signature Header -->
                    <div class="sig-header flex-between">
                      <div class="sig-name-group">
                        <el-icon class="sig-icon" :color="sig.integrity && !sig.expired ? '#67C23A' : '#F56C6C'">
                          <Key />
                        </el-icon>
                        <span class="sig-field-name">{{ sig.signature_name }}</span>
                      </div>
                      <div class="sig-badges">
                        <el-tag
                          :type="sig.integrity ? 'success' : 'danger'"
                          size="small"
                          effect="plain"
                        >
                          {{ sig.integrity ? $t('detail.intact') : $t('detail.tampered') }}
                        </el-tag>
                        <el-tag
                          :type="sig.expired ? 'danger' : 'success'"
                          size="small"
                          effect="plain"
                        >
                          {{ sig.expired ? $t('detail.expired') : $t('detail.valid') }}
                        </el-tag>
                      </div>
                    </div>

                    <!-- Signature Details -->
                    <div class="sig-details">
                      <div class="sig-detail-row">
                        <span class="sig-detail-label">{{ $t('detail.signerSubject') }}</span>
                        <span class="sig-detail-value text-bold">{{ sig.signer_cn }}</span>
                      </div>
                      <div class="sig-detail-row" v-if="sig.signing_time">
                        <span class="sig-detail-label">{{ $t('detail.signingTime') }}</span>
                        <span class="sig-detail-value">{{ formatDate(sig.signing_time) }}</span>
                      </div>
                      <div class="sig-detail-row">
                        <span class="sig-detail-label">{{ $t('detail.dataIntegrity') }}</span>
                        <span
                          class="sig-detail-value"
                          :class="sig.integrity ? 'color-pass' : 'color-fail'"
                        >
                          {{ sig.integrity ? $t('detail.notTampered') : $t('detail.dataTampered') }}
                        </span>
                      </div>
                      <div class="sig-detail-row">
                        <span class="sig-detail-label">{{ $t('detail.certificateValidity') }}</span>
                        <span
                          class="sig-detail-value"
                          :class="!sig.expired ? 'color-pass' : 'color-fail'"
                        >
                          {{ sig.expired ? $t('detail.expiredLabel') : $t('detail.validPeriod') }}
                        </span>
                      </div>

                      <!-- Toggle Expansion Button -->
                      <div v-if="sig.cert_info && Object.keys(sig.cert_info).length > 0" class="sig-expand-toggle-row">
                        <el-button 
                          link 
                          type="primary" 
                          size="small" 
                          @click="toggleSigExpand(index)"
                          class="expand-toggle-btn"
                        >
                          {{ expandedSigs[index] ? $t('detail.collapseCertDetails') : $t('detail.expandCertDetails') }}
                          <el-icon class="ml-1">
                            <component :is="expandedSigs[index] ? ArrowUp : ArrowDown" />
                          </el-icon>
                        </el-button>
                      </div>

                      <!-- Expanded Certificate Details (Collapsible) -->
                      <el-collapse-transition>
                        <div v-show="expandedSigs[index]" class="cert-expanded-section mt-2">
                          <el-divider class="compact-divider" />
                          
                          <!-- Subject Details -->
                          <div class="cert-sub-group" v-if="sig.cert_info.subject">
                            <span class="cert-group-title">{{ $t('detail.certSubject') }}</span>
                            <div class="sig-detail-row small-txt" v-if="sig.cert_info.subject.organization_name">
                              <span class="sig-detail-label">{{ $t('detail.organization') }}</span>
                              <span class="sig-detail-value">{{ sig.cert_info.subject.organization_name }}</span>
                            </div>
                            <div class="sig-detail-row small-txt" v-if="sig.cert_info.subject.organizational_unit_name">
                              <span class="sig-detail-label">{{ $t('detail.department') }}</span>
                              <span class="sig-detail-value">{{ sig.cert_info.subject.organizational_unit_name }}</span>
                            </div>
                            <div class="sig-detail-row small-txt" v-if="sig.cert_info.subject.user_id">
                              <span class="sig-detail-label">{{ $t('detail.userId') }}</span>
                              <span class="sig-detail-value text-monospace">{{ sig.cert_info.subject.user_id }}</span>
                            </div>
                            <div class="sig-detail-row small-txt" v-if="sig.cert_info.subject.country_name">
                              <span class="sig-detail-label">{{ $t('detail.country') }}</span>
                              <span class="sig-detail-value">{{ sig.cert_info.subject.country_name }}</span>
                            </div>
                          </div>

                          <!-- Issuer Details -->
                          <div class="cert-sub-group mt-2" v-if="sig.cert_info.issuer">
                            <span class="cert-group-title">{{ $t('detail.certIssuer') }}</span>
                            <div class="sig-detail-row small-txt" v-if="sig.cert_info.issuer.common_name">
                              <span class="sig-detail-label">{{ $t('detail.issuerCn') }}</span>
                              <span class="sig-detail-value">{{ sig.cert_info.issuer.common_name }}</span>
                            </div>
                            <div class="sig-detail-row small-txt" v-if="sig.cert_info.issuer.organization_name">
                              <span class="sig-detail-label">{{ $t('detail.issuerOrg') }}</span>
                              <span class="sig-detail-value">{{ sig.cert_info.issuer.organization_name }}</span>
                            </div>
                          </div>

                          <!-- Validity & Serial Details -->
                          <div class="cert-sub-group mt-2">
                            <span class="cert-group-title">{{ $t('detail.certValidityCredential') }}</span>
                            <div class="sig-detail-row small-txt" v-if="sig.cert_info.validity?.not_before">
                              <span class="sig-detail-label">{{ $t('detail.validFrom') }}</span>
                              <span class="sig-detail-value">{{ formatDate(sig.cert_info.validity.not_before) }}</span>
                            </div>
                            <div class="sig-detail-row small-txt" v-if="sig.cert_info.validity?.not_after">
                              <span class="sig-detail-label">{{ $t('detail.validUntil') }}</span>
                              <span class="sig-detail-value">{{ formatDate(sig.cert_info.validity.not_after) }}</span>
                            </div>
                            <div class="sig-detail-row small-txt" v-if="sig.cert_info.serial_number">
                              <span class="sig-detail-label">{{ $t('detail.serialNumber') }}</span>
                              <span class="sig-detail-value text-monospace word-break-serial">{{ sig.cert_info.serial_number }}</span>
                            </div>
                          </div>
                        </div>
                      </el-collapse-transition>
                    </div>
                  </div>
                </div>
              </div>
            </el-collapse-transition>
          </div>

          <!-- Reviewer Notes Panel -->
          <div class="glass-card section-panel notes-panel">
            <div class="section-title">
              <h3>{{ $t('detail.humanReviewNotes') }}</h3>
            </div>

            <!-- Notes List with smooth scroll -->
            <div class="notes-timeline-container" v-loading="notesLoading">
              <el-empty
                v-if="notes.length === 0"
                :description="$t('detail.noReviewNotes')"
                :image-size="60"
                class="empty-notes-state"
              />
              
              <div v-else class="notes-timeline">
                <div 
                  v-for="note in notes" 
                  :key="note.id" 
                  class="timeline-note-bubble"
                  :class="getNoteBubbleClass(note.content)"
                >
                  <div class="note-meta flex-between">
                    <div class="author-avatar-info">
                      <div class="avatar-circle" :style="getAvatarStyle(note.author_name)">
                        {{ getAvatarText(note.author_name) }}
                      </div>
                      <span class="author-name">{{ note.author_name }}</span>
                    </div>
                    <div class="note-actions">
                      <span class="note-date">{{ formatDate(note.created_at) }}</span>
                      <el-button 
                        v-if="canDeleteNote(note)" 
                        type="danger" 
                        link 
                        :icon="Delete" 
                        class="delete-note-btn"
                        @click="handleDeleteNote(note.id)"
                      />
                    </div>
                  </div>
                  <div class="note-bubble-content">
                    {{ note.content }}
                  </div>
                </div>
              </div>
            </div>

            <el-divider class="glass-divider my-3" />

            <!-- Add Note Form -->
            <div class="add-note-form">
              <el-input
                v-model="newNote"
                type="textarea"
                :rows="3"
                :placeholder="$t('detail.notePlaceholder')"
                maxlength="500"
                show-word-limit
                class="premium-textarea"
                :disabled="submittingNote"
              />
              <div class="flex-between" style="margin-top: 8px;">
                <span class="input-tips">{{ $t('detail.noteHint') }}</span>
                <el-button
                  type="primary"
                  @click="handleAddNote"
                  :loading="submittingNote"
                  :disabled="!newNote.trim()"
                  class="submit-note-btn"
                >
                  {{ $t('detail.submitNote') }}
                </el-button>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Execution Trajectory Drawer -->
    <el-drawer
      v-model="trajectoryDrawerVisible"
      :title="$t('detail.executionLogTitle')"
      size="45%"
      direction="rtl"
      :destroy-on-close="false"
      class="trajectory-drawer"
    >
      <div class="trajectory-container">
        <el-timeline>
          <el-timeline-item
            v-for="(log, idx) in executionLogs"
            :key="idx"
            :type="log.status === 'success' || log.pass_status ? 'success' : (log.status === 'error' || log.pass_status === false ? 'danger' : 'primary')"
            :color="log.status === 'running' ? '#409EFF' : ''"
            :hollow="log.status === 'running'"
            :timestamp="formatDate(log.timestamp)"
            placement="top"
          >
            <el-card shadow="hover" class="log-card">
              <h4 style="margin:0 0 8px 0; font-size:14px;">{{ log.operator }}</h4>
              <p class="log-msg" style="margin:0; font-size:13px; color:#666;">{{ log.message }}</p>
              <el-collapse v-if="log.extracted_data && Object.keys(log.extracted_data).length > 0" class="log-data-collapse mt-2">
                <el-collapse-item :title="$t('detail.extractedData')" name="1">
                  <pre class="log-data-pre">{{ JSON.stringify(log.extracted_data, null, 2) }}</pre>
                </el-collapse-item>
              </el-collapse>
            </el-card>
          </el-timeline-item>
        </el-timeline>
        <el-empty
          v-if="executionLogs.length === 0"
          :description="$t('detail.noExecutionLogs')"
        />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Document, Download, Check, Warning, WarningFilled, Close, Delete, Key, ArrowDown, ArrowUp, Position, Tickets, Right, InfoFilled } from '@element-plus/icons-vue'
import { filesApi } from '@/api/files'
import { notesApi } from '@/api/notes'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'
import { getLocale } from '@/locales'
import type { FileDetail, Note } from '@/types'
import * as pdfjsLib from 'pdfjs-dist'

const { t } = useI18n()

// Use CDN for PDF.js worker to avoid MIME type issues
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const file = ref<FileDetail | null>(null)
const notes = ref<Note[]>([])
const loading = ref(true)
const newNote = ref('')
const notesLoading = ref(false)
const submittingNote = ref(false)
const pdfContainerRef = ref<HTMLElement | null>(null)
const pdfLoading = ref(false)
const expandedSigs = ref<Record<number, boolean>>({})
const diffDetailsCollapsed = ref(true)

const trajectoryDrawerVisible = ref(false)
const liveExecutionLogs = ref<any[]>([])

// ─── 诊断指标微型过滤器 ───
const activeFilter = ref<'all' | 'pass' | 'warning' | 'fail'>('all')

function getNoteBubbleClass(content: string): string {
  if (content.startsWith(t('detail.arbitrationApproved'))) {
    return 'note-arbitration-approved'
  }
  if (content.startsWith(t('detail.arbitrationRejected'))) {
    return 'note-arbitration-rejected'
  }
  return ''
}

function formatDiffFragment(text: string, type: 'removed' | 'added') {
  if (!text) return ''
  // Escape HTML entities to prevent XSS
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  
  const escapedStart = '&gt;&gt;&gt;'
  const escapedEnd = '&lt;&lt;&lt;'
  
  const spanClass = type === 'removed' ? 'diff-text-removed' : 'diff-text-added'
  
  return escaped
    .replace(escapedStart, `<span class="${spanClass}">`)
    .replace(escapedEnd, `</span>`)
}

// ─── 右侧卡片折叠状态管理 ───
const generalDetailsCollapsed = ref(true)
const signatureDetailsCollapsed = ref(true)

function toggleFilter(status: 'pass' | 'warning' | 'fail') {
  activeFilter.value = activeFilter.value === status ? 'all' : status
}

const filteredChecks = computed(() => {
  if (!file.value?.verification_result_json?.checks) return []
  const checks = file.value.verification_result_json.checks
  if (activeFilter.value === 'all') return checks
  return checks.filter((c: any) => c.status === activeFilter.value)
})

const executionLogs = computed(() => {
  let logs: any[] = [...liveExecutionLogs.value]
  
  if (file.value && file.value.verification_result_json) {
    const v = file.value.verification_result_json
    if (v.execution_trajectory && Array.isArray(v.execution_trajectory)) {
      v.execution_trajectory.forEach((traj: any, index: number) => {
        logs.push({
          operator: t('detail.engineFlow'),
          message: traj.message,
          timestamp: traj.time || traj.timestamp,
          status: 'success',
          _order: index
        })
      })
    }
    
    const opLogs = v.operator_logs || {}
    let opIndex = 1000
    Object.entries(opLogs).forEach(([operator, data]: [string, any]) => {
      logs.push({
        operator: operator,
        message: data.message,
        extracted_data: data.extracted_data,
        status: data.pass_status === false ? 'error' : 'success',
        timestamp: file.value?.completed_at,
        _order: opIndex++
      })
    })
  }
  
  logs.sort((a, b) => {
    const timeA = new Date(a.timestamp || 0).getTime()
    const timeB = new Date(b.timestamp || 0).getTime()
    if (timeA === timeB) {
      return (a._order || 0) - (b._order || 0)
    }
    return timeA - timeB
  })
  
  return logs
})

const sniffedInstitution = computed(() => {
  return file.value?.verification_result_json?.operator_logs?.InstitutionSniffer?.extracted_data?.institution || ''
})

const digitalSignatures = computed(() => {
  const v = file.value?.verification_result_json
  return v?.operator_logs?.SignatureVerifier?.extracted_data?.digital_signatures || v?.digital_signatures || null
})

const qrCodes = computed(() => {
  const v = file.value?.verification_result_json
  return v?.operator_logs?.QRScanner?.extracted_data?.qr_codes || v?.qr_codes || null
})

const qrCodeCount = computed(() => {
  return qrCodes.value ? qrCodes.value.length : 0
})

const stampCount = computed(() => {
  const v = file.value?.verification_result_json
  const stamps = v?.operator_logs?.StampDetectionOperator?.extracted_data?.stamps
  return Array.isArray(stamps) ? stamps.length : 0
})

const isTextPdf = computed(() => {
  const v = file.value?.verification_result_json
  return v?.operator_logs?.PDFInfoExtractor?.extracted_data?.pdf_info?.is_text_pdf || false
})

const riskLevelText = computed(() => {
  if (!file.value) return t('detail.analyzing')
  if (file.value.status === 'needs_review') return t('detail.riskHigh')
  if (file.value.status === 'failed') return t('detail.riskDanger')
  if (file.value.status === 'warning') return t('detail.riskWarning')
  if (file.value.status === 'completed') return t('detail.riskSafe')
  return t('detail.riskUnrated')
})

const riskLevelClass = computed(() => {
  if (!file.value) return 'color-info'
  if (file.value.status === 'needs_review') return 'color-warning'
  if (file.value.status === 'failed') return 'color-fail'
  if (file.value.status === 'warning') return 'color-warning'
  if (file.value.status === 'completed') return 'color-pass'
  return 'color-info'
})

function toggleSigExpand(index: number) {
  expandedSigs.value[index] = !expandedSigs.value[index]
}

// ─── 升级版结构化卡片数据提取器 ───
const diffResults = computed(() => {
  return file.value?.verification_result_json?.operator_logs?.DocumentDiff?.extracted_data || null
})

const tableResults = computed(() => {
  return file.value?.verification_result_json?.operator_logs?.TableVerification?.extracted_data || null
})

// ─── 100% 离线自研：彩虹首字母头像系统 ───
const getAvatarText = (name: string | null) => {
  if (!name || name.toLowerCase() === 'system') return 'S'
  return name.charAt(0).toUpperCase()
}

const getAvatarStyle = (name: string | null) => {
  const text = name || 'System'
  let hash = 0
  for (let i = 0; i < text.length; i++) {
    hash = text.charCodeAt(i) + ((hash << 5) - hash)
  }
  
  const colors = [
    '#3b82f6', // 晴空蓝
    '#10b981', // 翡翠绿
    '#f59e0b', // 琥珀黄
    '#ef4444', // 珊瑚红
    '#8b5cf6', // 紫罗兰
    '#ec4899', // 玫瑰粉
    '#06b6d4', // 冰川青
    '#14b8a6', // 薄荷绿
    '#6366f1', // 靛青蓝
    '#f43f5e', // 蔷薇红
    '#64748b'  // 石板灰
  ]
  
  const index = Math.abs(hash) % colors.length
  return {
    backgroundColor: colors[index],
    color: '#ffffff',
    fontWeight: '700',
    fontSize: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'system-ui, sans-serif'
  }
}

let pollTimer: ReturnType<typeof setTimeout> | null = null

async function renderPdf(downloadUrl: string, verificationResult: any) {
  if (!pdfContainerRef.value) return
  pdfLoading.value = true
  try {
    const loadingTask = pdfjsLib.getDocument(downloadUrl)
    const pdf = await loadingTask.promise
    
    pdfContainerRef.value.innerHTML = '' // clear
    
    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
      const page = await pdf.getPage(pageNum)
      const scale = 1.2
      const viewport = page.getViewport({ scale })
      
      const pageWrapper = document.createElement('div')
      pageWrapper.style.position = 'relative'
      pageWrapper.style.marginBottom = '20px'
      pageWrapper.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)'
      pageWrapper.style.width = `${viewport.width}px`
      pageWrapper.style.height = `${viewport.height}px`
      
      const canvas = document.createElement('canvas')
      const context = canvas.getContext('2d')
      if (context) {
        canvas.width = viewport.width
        canvas.height = viewport.height
        canvas.style.display = 'block'
        
        pageWrapper.appendChild(canvas)
        pdfContainerRef.value.appendChild(pageWrapper)
        
        await page.render({ canvasContext: context, viewport }).promise
        
        // QR codes
        const qrs = verificationResult?.operator_logs?.QRScanner?.extracted_data?.qr_codes || verificationResult?.qr_codes || []
        if (qrs && Array.isArray(qrs)) {
          qrs.forEach((qr: any) => {
            if (qr.page === pageNum && qr.rect) {
              drawHighlightBox(pageWrapper, qr.rect, viewport, 'rgba(64, 158, 255, 0.25)', '2px solid #409EFF')
            }
          })
        }
        
        // Signatures
        const sigData = verificationResult?.operator_logs?.SignatureVerifier?.extracted_data?.digital_signatures || verificationResult?.digital_signatures
        if (sigData?.signatures) {
          sigData.signatures.forEach((sig: any) => {
            if (sig.page === pageNum && sig.rect) {
              const color = (sig.integrity && !sig.expired) ? '#67C23A' : '#F56C6C'
              const bg = (sig.integrity && !sig.expired) ? 'rgba(103, 194, 58, 0.25)' : 'rgba(245, 108, 108, 0.25)'
              drawHighlightBox(pageWrapper, sig.rect, viewport, bg, `2px solid ${color}`)
            }
          })
        }

        // Physical stamps / seals (StampDetectionOperator)
        const opLogs = verificationResult?.operator_logs || {}
        if (pageNum === 1) {
          console.log('[PDF Preview] operator_logs keys:', Object.keys(opLogs))
          console.log('[PDF Preview] StampDetectionOperator data:', opLogs.StampDetectionOperator)
        }
        const stampData = opLogs.StampDetectionOperator?.extracted_data?.stamps || []
        if (pageNum === 1) {
          console.log('[PDF Preview] stampData count:', stampData.length, stampData)
        }
        if (Array.isArray(stampData)) {
          stampData.forEach((stamp: any) => {
            if (stamp.page === pageNum && stamp.bounding_box) {
              const [x0, y0, x1, y1] = stamp.bounding_box
              const scale = viewport.scale || 1.5
              console.log(`[Stamp Highlight] page=${pageNum}, bbox=[${x0},${y0},${x1},${y1}], scale=${scale}, cssSize=${(x1-x0)*scale}x${(y1-y0)*scale}, viewportSize=${viewport.width}x${viewport.height}`)
              drawHighlightBox(pageWrapper, stamp.bounding_box, viewport, 'rgba(230, 162, 60, 0.2)', '2px solid #E6A23C')
            }
          })
        }
      }
    }
  } catch (err) {
    console.error('PDF rendering failed:', err)
  } finally {
    pdfLoading.value = false
  }
}

function drawHighlightBox(wrapper: HTMLElement, rect: number[], viewport: any, bg: string, border: string) {
  const [x0, y0, x1, y1] = rect
  const scale = viewport.scale || 1.5

  const left = x0 * scale
  const top = y0 * scale
  const width = (x1 - x0) * scale
  const height = (y1 - y0) * scale

  console.log(`[drawHighlightBox] raw=[${x0},${y0},${x1},${y1}] → CSS: left=${left.toFixed(1)} top=${top.toFixed(1)} w=${width.toFixed(1)} h=${height.toFixed(1)}, wrapper=${wrapper.style.width}x${wrapper.style.height}`)

  const box = document.createElement('div')
  box.style.position = 'absolute'
  box.style.left = `${left}px`
  box.style.top = `${top}px`
  box.style.width = `${width}px`
  box.style.height = `${height}px`
  box.style.backgroundColor = bg
  box.style.border = border
  box.style.pointerEvents = 'none'
  box.style.zIndex = '10'
  box.style.borderRadius = '4px'
  
  wrapper.appendChild(box)
}

function statusText(status: string): string {
  const map: Record<string, string> = {
    pending: t('detail.statusWaiting'),
    processing: t('detail.statusAnalyzing'),
    completed: t('detail.statusPassed'),
    failed: t('detail.statusFailedVerify'),
    warning: t('detail.statusPreWarning'),
    needs_review: t('detail.statusNeedsArbitration'),
  }
  return map[status] || status
}

function checkStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pass: t('detail.checkPass'),
    warning: t('detail.checkWarning'),
    fail: t('detail.checkFail'),
    info: t('detail.checkReference'),
  }
  return map[status] || status
}

function fileTypeLabel(type?: string): string {
  const map: Record<string, string> = {
    production_plan: t('detail.typeProductionPlan'),
    quality_report: t('detail.typeQualityReport'),
    purchase_order: t('detail.typePurchaseOrder'),
    supplier_qualification: t('detail.typeSupplierQualification'),
    product_specification: t('detail.typeProductSpecification'),
    other: t('detail.typeOther'),
  }
  return map[type || ''] || t('detail.typeUncategorized')
}

import { formatFileSize } from '@/utils/formatters'

function formatDuration(seconds?: number): string {
  if (seconds === undefined || seconds === null) return '-'
  if (seconds < 60) return t('detail.seconds', { s: seconds })
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return t('detail.minutesSeconds', { m: min, s: sec })
}

function scrollToPage(page: number) {
  const el = document.getElementById(`pdf-page-${page}`)
  if (el && pdfContainerRef.value) {
    const containerTop = pdfContainerRef.value.getBoundingClientRect().top
    const elTop = el.getBoundingClientRect().top
    const scrollTop = pdfContainerRef.value.scrollTop + (elTop - containerTop) - 20
    
    pdfContainerRef.value.scrollTo({
      top: scrollTop,
      behavior: 'smooth'
    })
  } else {
    ElMessage.warning(t('detail.cannotLocatePage', { page }))
  }
}

function handlePrintReport() {
  window.print()
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString(getLocale(), {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  } catch (e) {
    return dateStr
  }
}

function statusGlowClass(status: string): string {
  return `status-glow-${status}`
}

function passRateClass(rate?: number): string {
  if (rate === undefined || rate === null) return ''
  if (rate >= 90) return 'text-pass'
  if (rate >= 60) return 'text-warning'
  return 'text-fail'
}

function canDeleteNote(note: Note): boolean {
  if (!authStore.user) return false
  return authStore.user.id === note.author_id || authStore.user.is_admin
}

// Fetch file detail
async function fetchFileDetail(silent = false) {
  const fileId = route.params.id as string
  if (!fileId || fileId === 'undefined') return
  if (!silent) loading.value = true
  try {
    const res = await filesApi.getDetail(fileId)
    file.value = res
    
    // Check if we need to poll or connect to WebSocket
    if (res.status === 'pending' || res.status === 'processing') {
      connectWebSocket()
    } else {
      closeWebSocket()
      stopPolling()
      
      if (res.status === 'completed' || res.status === 'warning' || res.status === 'failed') {
        filesApi.getDownloadUrl(fileId).then(urlRes => {
          if (urlRes && urlRes.download_url) {
            nextTick(() => {
              renderPdf(urlRes.download_url, res.verification_result_json || res.verification_result)
            })
          }
        }).catch(err => {
          console.error("Could not fetch download URL for PDF rendering:", err)
        })
      }
    }
  } catch (error) {
    closeWebSocket()
    stopPolling()
    ElMessage.error(t('detail.loadFileFailed'))
  } finally {
    if (!silent) loading.value = false
  }
}

// Fetch Notes
async function fetchNotes(silent = false) {
  const fileId = route.params.id as string
  if (!fileId || fileId === 'undefined') return
  if (!silent) notesLoading.value = true
  try {
    const res = await notesApi.getByFileId(fileId)
    // Notes are already sorted desc by created_at in backend notes.py
    notes.value = res
  } catch (error) {
    ElMessage.error(t('detail.loadNotesFailed'))
  } finally {
    if (!silent) notesLoading.value = false
  }
}

// Download File
async function handleDownload() {
  if (!file.value) return
  try {
    ElMessage.info(t('detail.requestingDownload'))
    const res = await filesApi.getDownloadUrl(file.value.id)
    if (res && res.download_url) {
      window.open(res.download_url, '_blank')
      ElMessage.success(t('detail.downloadOpened'))
    } else {
      ElMessage.error(t('detail.downloadUrlInvalid'))
    }
  } catch (error) {
    ElMessage.error(t('detail.downloadFailed'))
  }
}

// Add Note
async function handleAddNote() {
  if (!file.value || !newNote.value.trim()) return
  
  submittingNote.value = true
  try {
    const payload = {
      file_id: file.value.id,
      content: newNote.value.trim()
    }
    const res = await notesApi.create(payload)
    // Prepend the new note to the top of the local list
    notes.value.unshift(res)
    newNote.value = ''
    ElMessage.success(t('detail.notePublished'))
  } catch (error) {
    ElMessage.error(t('detail.notePublishFailed'))
  } finally {
    submittingNote.value = false
  }
}

// Delete Note
async function handleDeleteNote(noteId: string) {
  try {
    await ElMessageBox.confirm(
      t('detail.deleteNoteConfirm'),
      t('detail.deleteConfirmTitle'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
        buttonSize: 'default'
      }
    )

    await notesApi.delete(noteId)
    notes.value = notes.value.filter(n => n.id !== noteId)
    ElMessage.success(t('detail.noteDeleted'))
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('detail.noteDeleteFailed'))
    }
  }
}

// Handle Review Resolution
async function handleReviewResolution(action: 'approve' | 'reject') {
  if (!file.value) return
  
  const actionText = action === 'approve' ? t('detail.approveText') : t('detail.rejectText')

  try {
    const { value: comment } = await ElMessageBox.prompt(
      t('detail.reviewPrompt', { action: actionText }),
      t('detail.reviewConfirmTitle'),
      {
        confirmButtonText: t('detail.confirmSubmit'),
        cancelButtonText: t('common.cancel'),
        inputPlaceholder: t('detail.reviewPlaceholder'),
        type: action === 'approve' ? 'success' : 'error'
      }
    )

    // Call API
    loading.value = true
    const updatedFile = await filesApi.resolveReview(file.value.id, {
      action,
      comment
    })

    ElMessage.success(t('detail.reviewSuccess', { action: actionText }))
    // Refresh the page data
    await fetchFileDetail(true)
    await fetchNotes(true)

  } catch (e: unknown) {
    if (e !== 'cancel') {
      ElMessage.error(t('detail.reviewFailed'))
    }
  } finally {
    loading.value = false
  }
}

// WebSocket Connection Management
let socket: WebSocket | null = null

function connectWebSocket() {
  if (socket) return

  const token = localStorage.getItem('token') || ''
  const fileId = route.params.id as string
  if (!fileId || fileId === 'undefined') return

  let wsUrl = ''
  const apiBase = import.meta.env.VITE_API_BASE_URL || '/api/v1'

  if (apiBase.startsWith('http')) {
    wsUrl = apiBase.replace(/^http/, 'ws') + `/files/ws/${fileId}`
  } else {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    wsUrl = `${protocol}//${host}${apiBase}/files/ws/${fileId}`
  }

  console.log('Connecting to verification progress WebSocket:', wsUrl)
  socket = new WebSocket(wsUrl)

  // Send auth message as first message (token not in URL to avoid logging)
  socket.onopen = () => {
    socket!.send(JSON.stringify({ type: 'auth', token }))
  }

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.error) {
      console.error('WebSocket progress channel error:', data.error)
      startPolling() // Fallback
      return
    }
    
    if (data.current_step) {
      liveExecutionLogs.value.push({
        operator: t('detail.realtimeAnalysis'),
        message: data.current_step,
        timestamp: new Date().toISOString(),
        status: 'running'
      })
    }
    
    if (file.value) {
      file.value.verification_progress = data.progress
      file.value.status = data.status
      
      if (data.status !== 'pending' && data.status !== 'processing') {
        liveExecutionLogs.value = []
        fetchFileDetail(true)
        fetchNotes(true)
        closeWebSocket()
      }
    }
  }
  
  socket.onerror = (err) => {
    console.error('WebSocket encountered an error:', err)
    startPolling() // Fallback to HTTP Polling
  }
  
  socket.onclose = () => {
    socket = null
  }
}

function closeWebSocket() {
  if (socket) {
    socket.close()
    socket = null
  }
}

// Live Polling Scheduler (Fallback)
function startPolling() {
  if (pollTimer) return
  console.log('Falling back to standard HTTP short polling...')
  pollTimer = setInterval(async () => {
    await fetchFileDetail(true)
    if (file.value && file.value.status !== 'pending' && file.value.status !== 'processing') {
      fetchNotes(true)
    }
  }, 1500)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(async () => {
  // Parallel load
  await Promise.all([
    fetchFileDetail(),
    fetchNotes()
  ])
})

onUnmounted(() => {
  closeWebSocket()
  stopPolling()
})
</script>

<style scoped>
.detail-page-container {
  min-height: calc(100vh - 120px);
  padding: 8px 4px;
}

/* Glassmorphism card default styles */
.glass-card {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.04);
  border-radius: 16px;
  padding: 24px;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.glass-card:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
}

/* Back Button Style */
.glass-btn {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 6px;
  color: #555;
  font-weight: 500;
  transition: all 0.25s ease;
}

.glass-btn:hover {
  background: #fff;
  border-color: #4285f4;
  color: #4285f4;
  transform: translateX(-2px);
}

/* Premium Status Glow Borders */
.header-panel {
  border-left: 6px solid rgba(0, 0, 0, 0.08);
}
.header-panel.status-glow-completed {
  border-left-color: #4caf50;
  background: linear-gradient(to right, rgba(76, 175, 80, 0.04), rgba(255, 255, 255, 0.75));
}
.header-panel.status-glow-warning {
  border-left-color: #ff9800;
  background: linear-gradient(to right, rgba(255, 152, 0, 0.04), rgba(255, 255, 255, 0.75));
}
.header-panel.status-glow-failed {
  border-left-color: #f44336;
  background: linear-gradient(to right, rgba(244, 67, 54, 0.04), rgba(255, 255, 255, 0.75));
}
.header-panel.status-glow-processing {
  border-left-color: #2196f3;
  background: linear-gradient(to right, rgba(33, 150, 243, 0.04), rgba(255, 255, 255, 0.75));
}

/* File Brand Block */
.file-brand-info {
  display: flex;
  align-items: center;
  gap: 20px;
  max-width: 70%;
}

.icon-glow-wrapper {
  width: 60px;
  height: 60px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  background: #90a4ae;
}

.icon-glow-wrapper.completed {
  background: linear-gradient(135deg, #81c784, #4caf50);
  box-shadow: 0 6px 20px rgba(76, 175, 80, 0.3);
}
.icon-glow-wrapper.warning {
  background: linear-gradient(135deg, #ffb74d, #ff9800);
  box-shadow: 0 6px 20px rgba(255, 152, 0, 0.3);
}
.icon-glow-wrapper.failed {
  background: linear-gradient(135deg, #e57373, #f44336);
  box-shadow: 0 6px 20px rgba(244, 67, 54, 0.3);
}
.icon-glow-wrapper.processing {
  background: linear-gradient(135deg, #64b5f6, #2196f3);
  box-shadow: 0 6px 20px rgba(33, 150, 243, 0.3);
  animation: pulse-glow 2s infinite ease-in-out;
}

@keyframes pulse-glow {
  0% { transform: scale(1); box-shadow: 0 6px 15px rgba(33, 150, 243, 0.3); }
  50% { transform: scale(1.04); box-shadow: 0 6px 25px rgba(33, 150, 243, 0.5); }
  100% { transform: scale(1); box-shadow: 0 6px 15px rgba(33, 150, 243, 0.3); }
}

.file-details {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.file-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a1f36;
  margin: 0 0 8px 0;
  text-overflow: ellipsis;
  white-space: nowrap;
  overflow: hidden;
}

.file-sub-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.file-type-pill {
  background: rgba(66, 133, 244, 0.1);
  color: #4285f4;
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.dot-separator {
  color: #ccc;
  font-size: 12px;
}

.file-meta-txt {
  font-size: 13px;
  color: #697386;
  font-weight: 500;
}

/* Header Action Pill */
.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.premium-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.premium-status-badge.pending {
  background: rgba(255, 152, 0, 0.1);
  color: #ff9800;
}
.premium-status-badge.processing {
  background: rgba(33, 150, 243, 0.1);
  color: #2196f3;
}
.premium-status-badge.completed {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
}
.premium-status-badge.failed {
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
}
.premium-status-badge.warning {
  background: rgba(255, 152, 0, 0.1);
  color: #ff9800;
}

.pulse-indicator {
  width: 8px;
  height: 8px;
  background-color: #2196f3;
  border-radius: 50%;
  animation: scale-pulse 1.4s infinite ease-in-out;
}

@keyframes scale-pulse {
  0% { transform: scale(0.6); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.4; }
  100% { transform: scale(0.6); opacity: 1; }
}

.download-report-btn {
  background: linear-gradient(135deg, #4285f4, #2b6de0);
  border: none;
  border-radius: 6px;
  font-weight: 600;
  box-shadow: 0 4px 10px rgba(66, 133, 244, 0.2);
  transition: all 0.25s ease;
}

.download-report-btn:hover:not(:disabled) {
  box-shadow: 0 6px 14px rgba(66, 133, 244, 0.3);
  transform: translateY(-1px);
}

.glass-divider {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  margin: 20px 0;
}

/* Metadata Grid styling */
.file-meta-grid {
  margin-bottom: 4px;
}

.meta-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 6px 12px;
}

.meta-label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  color: #8792a2;
  letter-spacing: 0.5px;
}

.meta-value {
  font-size: 15px;
  font-weight: 600;
  color: #3c4257;
}

.pass-rate-highlight {
  font-size: 20px;
  font-weight: 800;
}

.text-pass {
  color: #4caf50;
}
.text-warning {
  color: #ff9800;
}
.text-fail {
  color: #f44336;
}

/* Glowing Progress bar under analyzing */
.live-progress-container {
  background: rgba(0, 0, 0, 0.02);
  padding: 16px;
  border-radius: 12px;
  border: 1px dashed rgba(0, 0, 0, 0.06);
}

.progress-status-title {
  font-size: 13px;
  font-weight: 600;
  color: #4f5b66;
}

.progress-percent-val {
  font-size: 14px;
  font-weight: 700;
  color: #2196f3;
}

.glowing-progress-track {
  width: 100%;
  height: 8px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}

.glowing-progress-fill {
  height: 100%;
  border-radius: 6px;
  background: linear-gradient(90deg, #64b5f6, #2196f3, #00c853);
  box-shadow: 0 0 10px rgba(33, 150, 243, 0.6);
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.glowing-progress-fill::after {
  /* Using non-empty content to avoid AV false positive (BehavesLike.PS.Downloader) */
  content: '\00a0';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(
    90deg,
    rgba(255,255,255,0) 0%,
    rgba(255,255,255,0.4) 50%,
    rgba(255,255,255,0) 100%
  );
  animation: shine-bar 1.5s infinite linear;
}

@keyframes shine-bar {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* Two-column dashboard row */
.content-row {
  align-items: stretch;
}

.grid-column {
  display: flex;
  flex-direction: column;
}

.section-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-bottom: 24px;
}

.section-panel.small-card {
  flex: 0 0 auto;
}

.section-title {
  margin-bottom: 20px;
}

.section-title h3 {
  font-size: 16px;
  font-weight: 700;
  color: #1a1f36;
  margin: 0;
  position: relative;
  padding-left: 12px;
}

.section-title h3::before {
  /* Using non-empty content to avoid AV false positive (BehavesLike.PS.Downloader) */
  content: '\00a0';
  position: absolute;
  left: 0;
  top: 3px;
  bottom: 3px;
  width: 4px;
  border-radius: 2px;
  background-color: #4285f4;
}

/* Diagnostic checklist items */
.diagnostic-checklist {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.diagnostic-check-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  border-radius: 12px;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.04);
  background: rgba(255, 255, 255, 0.4);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.diagnostic-check-card.pass {
  background: rgba(76, 175, 80, 0.02);
  border-color: rgba(76, 175, 80, 0.1);
}
.diagnostic-check-card.pass:hover {
  background: rgba(76, 175, 80, 0.05);
  border-color: rgba(76, 175, 80, 0.25);
  box-shadow: 0 4px 15px rgba(76, 175, 80, 0.06);
}

.diagnostic-check-card.warning {
  background: rgba(255, 152, 0, 0.025);
  border-color: rgba(255, 152, 0, 0.1);
}
.diagnostic-check-card.warning:hover {
  background: rgba(255, 152, 0, 0.06);
  border-color: rgba(255, 152, 0, 0.25);
  box-shadow: 0 4px 15px rgba(255, 152, 0, 0.06);
}

.diagnostic-check-card.fail {
  background: rgba(244, 67, 54, 0.025);
  border-color: rgba(244, 67, 54, 0.1);
}
.diagnostic-check-card.fail:hover {
  background: rgba(244, 67, 54, 0.06);
  border-color: rgba(244, 67, 54, 0.25);
  box-shadow: 0 4px 15px rgba(244, 67, 54, 0.06);
}

.diagnostic-check-card:hover {
  transform: translateY(-2px);
}

/* Clicking locator cues style */
.locate-tip {
  font-size: 11px;
  font-weight: 600;
  color: #4285f4;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  opacity: 0.65;
  transition: all 0.2s ease;
}

.diagnostic-check-card:hover .locate-tip {
  opacity: 1 !important;
  color: #2b6de0 !important;
}

.arrow-icon-slide {
  transition: transform 0.2s ease;
}

.diagnostic-check-card:hover .arrow-icon-slide {
  transform: translateX(4px);
}

/* Clickable micro-filters */
.clickable-counter {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1.5px solid transparent !important;
}

.clickable-counter:hover {
  transform: scale(1.05);
  filter: brightness(0.95);
}

.clickable-counter.is-active {
  border-color: currentColor !important;
  box-shadow: 0 0 8px rgba(0, 0, 0, 0.08);
  transform: scale(1.06);
}

.check-left-indicator {
  position: absolute;
  top: 0; bottom: 0; left: 0;
  width: 4px;
}
.check-left-indicator.pass { background-color: #4caf50; }
.check-left-indicator.warning { background-color: #ff9800; }
.check-left-indicator.fail { background-color: #f44336; }
.check-left-indicator.info { background-color: #64b5f6; }

.diagnostic-check-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.diagnostic-check-icon.pass {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
}
.diagnostic-check-icon.warning {
  background: rgba(255, 152, 0, 0.1);
  color: #ff9800;
}
.diagnostic-check-icon.fail {
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
}
.diagnostic-check-icon.info {
  background: rgba(33, 150, 243, 0.1);
  color: #1976d2;
}

.diagnostic-check-body {
  flex: 1;
}

.check-title-row h4 {
  font-size: 14px;
  font-weight: 700;
  color: #3c4257;
  margin: 0;
}

.check-status-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.check-status-tag.pass { background: rgba(76, 175, 80, 0.1); color: #4caf50; }
.check-status-tag.warning { background: rgba(255, 152, 0, 0.1); color: #ff9800; }
.check-status-tag.fail { background: rgba(244, 67, 54, 0.1); color: #f44336; }
.check-status-tag.info { background: rgba(33, 150, 243, 0.08); color: #1976d2; letter-spacing: 0; }

.check-message {
  font-size: 13px;
  color: #697386;
  margin: 6px 0 0 0;
  line-height: 1.5;
}

.checks-counters {
  display: flex;
  gap: 8px;
}

.counter-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
}

.counter-badge.pass { background: rgba(76, 175, 80, 0.1); color: #4caf50; }
.counter-badge.warning { background: rgba(255, 152, 0, 0.1); color: #ff9800; }
.counter-badge.fail { background: rgba(244, 67, 54, 0.1); color: #f44336; }

.empty-report-state {
  margin: auto;
  padding: 40px 0;
}

/* Info detail items list */
.info-details-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.info-detail-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.info-detail-item .lbl {
  font-size: 13px;
  font-weight: 500;
  color: #8792a2;
}

.info-detail-item .val {
  font-size: 13px;
  font-weight: 600;
  color: #3c4257;
}

.text-monospace {
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
}

.color-pass { color: #4caf50; }
.color-warning { color: #ff9800; }
.color-fail { color: #f44336; }

/* Reviewer Notes timeline and bubbles */
.notes-panel {
  display: flex;
  flex-direction: column;
  max-height: 500px;
}

.notes-timeline-container {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
  max-height: 250px;
  margin-bottom: 12px;
}

/* Custom scrollbar for notes */
.notes-timeline-container::-webkit-scrollbar {
  width: 5px;
}
.notes-timeline-container::-webkit-scrollbar-track {
  background: rgba(0,0,0,0.02);
}
.notes-timeline-container::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.1);
  border-radius: 3px;
}

.empty-notes-state {
  padding: 20px 0;
}

.notes-timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.timeline-note-bubble {
  background: rgba(0, 0, 0, 0.025);
  border: 1px solid rgba(0, 0, 0, 0.02);
  border-radius: 12px;
  padding: 12px;
  transition: background 0.2s ease;
}

.timeline-note-bubble:hover {
  background: rgba(0, 0, 0, 0.04);
}

.note-meta {
  margin-bottom: 8px;
}

.author-avatar-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.avatar-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #4285f4;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.author-name {
  font-size: 12px;
  font-weight: 700;
  color: #3c4257;
}

.note-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.note-date {
  font-size: 11px;
  color: #8792a2;
}

.delete-note-btn {
  padding: 0;
  height: auto;
  font-size: 14px;
  color: #8792a2;
}
.delete-note-btn:hover {
  color: #f44336 !important;
}

.note-bubble-content {
  font-size: 13px;
  line-height: 1.5;
  color: #4f5b66;
  word-break: break-all;
  white-space: pre-wrap;
}

/* Premium Textarea fields */
.premium-textarea :deep(.el-textarea__inner) {
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: rgba(255,255,255,0.6);
  font-size: 13px;
  padding: 10px 12px;
  transition: all 0.25s ease;
}

.premium-textarea :deep(.el-textarea__inner:focus) {
  background: #fff;
  border-color: #4285f4;
  box-shadow: 0 0 0 2px rgba(66,133,244,0.1);
}

.input-tips {
  font-size: 11px;
  color: #8792a2;
}

.submit-note-btn {
  background: #4285f4;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  padding: 8px 16px;
}

.submit-note-btn:hover:not(:disabled) {
  background: #3367d6;
}

/* ==================== Digital Signature Card Styles ==================== */
.signatures-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.signature-card {
  background: rgba(255, 255, 255, 0.6);
  border: 1.5px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.25s ease;
}

.signature-card:hover {
  background: rgba(255, 255, 255, 0.85);
  border-color: rgba(66, 133, 244, 0.2);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.signature-card.sig-invalid {
  background: rgba(255, 243, 235, 0.5);
  border-color: rgba(245, 63, 54, 0.2);
}

.signature-card.sig-invalid:hover {
  background: rgba(255, 243, 235, 0.75);
  border-color: rgba(245, 63, 54, 0.3);
}

.sig-header {
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.sig-name-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sig-icon {
  flex-shrink: 0;
  font-size: 18px;
}

.sig-field-name {
  font-size: 14px;
  font-weight: 700;
  color: #2c3e50;
}

.sig-badges {
  display: flex;
  gap: 6px;
}

.sig-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sig-detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.sig-detail-label {
  color: #8792a2;
  font-weight: 500;
}

.sig-detail-value {
  font-weight: 600;
  color: #2c3e50;
  text-align: right;
  max-width: 60%;
  word-break: break-word;
}

.compact-empty {
  padding: 12px 0;
}

.compact-empty :deep(.el-empty__description) {
  font-size: 13px;
  color: #8792a2;
}

.my-3 {
  margin: 12px 0;
}

/* Enhanced Digital Signature styles */
.text-bold {
  font-weight: 700;
}

.compact-divider {
  margin: 10px 0;
  border-top: 1px dashed rgba(0, 0, 0, 0.08);
}

.cert-expanded-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cert-sub-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: rgba(0, 0, 0, 0.015);
  border-radius: 8px;
  padding: 8px 10px;
  border: 1px solid rgba(0, 0, 0, 0.02);
}

.cert-group-title {
  font-size: 11px;
  font-weight: 700;
  color: #7d8b99;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
  display: block;
}

.small-txt {
  font-size: 12px !important;
}

.word-break-serial {
  word-break: break-all;
  font-size: 11px;
  max-width: 70%;
  color: #64748b;
}

.mt-2 {
  margin-top: 8px;
}

.sig-expand-toggle-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.expand-toggle-btn {
  font-size: 12px;
  font-weight: 600;
  color: #4285f4;
  transition: all 0.2s ease;
  padding: 4px 0;
}

.expand-toggle-btn:hover {
  color: #3367d6;
  text-decoration: none;
  transform: translateY(-0.5px);
}

.ml-1 {
  margin-left: 4px;
}

.has-page-link {
  cursor: pointer;
  transition: all 0.2s ease;
}

.has-page-link:hover {
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.page-tag {
  font-weight: 600;
  cursor: pointer;
}

@media print {
  /* Hide unnecessary elements during print */
  .navigation-header,
  .live-progress-container,
  .pdf-preview-panel,
  .hide-on-print,
  .notes-panel .add-note-form,
  .notes-panel .delete-note-btn {
    display: none !important;
  }
  
  /* Reset max-height and scrolling for the right column to allow full print */
  .right-scroll-col {
    max-height: none !important;
    overflow: visible !important;
    width: 100% !important;
    flex: 0 0 100% !important;
    max-width: 100% !important;
    padding: 0 !important;
  }
  
  .content-row {
    display: block !important;
  }
  
  body {
    background: white !important;
  }
  
  .glass-card {
    box-shadow: none !important;
    border: 1px solid #ddd !important;
    break-inside: avoid;
    background: white !important;
  }
  
  /* Make sure background colors for tags and badges print */
  * {
    -webkit-print-color-adjust: exact !important;
    color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
}

/* Timeline log cards */
.log-card {
  border-radius: 8px;
}

/* Check confidence styles */
.check-confidence-badge {
  font-size: 12px;
  font-weight: 600;
  color: #67C23A;
  background: rgba(103, 194, 58, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
}
.check-confidence-badge.low-confidence {
  color: #E6A23C;
  background: rgba(230, 162, 60, 0.1);
}

/* Timeline arbitration notes custom styles */
.timeline-note-bubble.note-arbitration-approved {
  background: rgba(103, 194, 58, 0.05);
  border-left: 4px solid #67C23A;
  border-color: rgba(103, 194, 58, 0.15) rgba(103, 194, 58, 0.15) rgba(103, 194, 58, 0.15) #67C23A;
}
.timeline-note-bubble.note-arbitration-rejected {
  background: rgba(245, 108, 108, 0.05);
  border-left: 4px solid #F56C6C;
  border-color: rgba(245, 108, 108, 0.15) rgba(245, 108, 108, 0.15) rgba(245, 108, 108, 0.15) #F56C6C;
}

/* Document Diff Panel Styles */
.diff-panel {
  display: flex;
  flex-direction: column;
}

.diff-changes-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 4px;
}

.diff-changes-list::-webkit-scrollbar {
  width: 5px;
}
.diff-changes-list::-webkit-scrollbar-track {
  background: rgba(0,0,0,0.02);
}
.diff-changes-list::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.1);
  border-radius: 3px;
}

.diff-change-item {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  padding: 12px;
}

.diff-change-header {
  font-size: 13px;
}

.diff-comparison-box {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 6px;
  overflow: hidden;
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 12px;
}

.diff-line {
  display: flex;
  padding: 8px 12px;
  line-height: 1.5;
}

.diff-line.removed {
  background-color: rgba(244, 67, 54, 0.02);
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.diff-line.added {
  background-color: rgba(76, 175, 80, 0.02);
}

.diff-line .line-marker {
  width: 20px;
  user-select: none;
  font-weight: bold;
}

.diff-line.removed .line-marker {
  color: #F56C6C;
}

.diff-line.added .line-marker {
  color: #67C23A;
}

.diff-line .line-content {
  flex: 1;
  word-break: break-all;
  white-space: pre-wrap;
}

/* Format diff fragments highlighted inside spans */
:deep(.diff-text-removed) {
  background-color: rgba(245, 108, 108, 0.2);
  color: #c45656;
  text-decoration: line-through;
  padding: 2px 4px;
  border-radius: 2px;
  font-weight: 600;
}

:deep(.diff-text-added) {
  background-color: rgba(103, 194, 58, 0.2);
  color: #5daf34;
  padding: 2px 4px;
  border-radius: 2px;
  font-weight: 600;
}
</style>
