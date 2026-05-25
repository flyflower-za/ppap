<template>
  <div class="detail-page-container" v-loading="loading" element-loading-background="rgba(245, 247, 250, 0.8)">
    <!-- Back Button -->
    <div class="navigation-header mb-4">
      <el-button 
        :icon="ArrowLeft" 
        @click="router.back()" 
        class="back-btn glass-btn"
      >
        返回历史记录
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
              <div class="file-sub-info">
                <span class="file-type-pill">{{ fileTypeLabel(file.file_type) }}</span>
                <span class="dot-separator">•</span>
                <span class="file-meta-txt">{{ formatFileSize(file.file_size) }}</span>
                <span class="dot-separator">•</span>
                <span class="file-meta-txt">{{ file.page_count || '-' }} 页</span>
              </div>
            </div>
          </div>
          
          <div class="header-actions">
            <span class="premium-status-badge" :class="file.status">
              <span class="pulse-indicator" v-if="file.status === 'processing'"></span>
              {{ statusText(file.status) }}
            </span>
            <el-button 
              type="primary" 
              :icon="Download" 
              @click="handleDownload"
              :disabled="file.status === 'pending' || file.status === 'processing'"
              class="download-report-btn"
            >
              下载原文件
            </el-button>
          </div>
        </div>

        <el-divider class="glass-divider" />

        <!-- File Metadata Grid -->
        <el-row :gutter="24" class="file-meta-grid">
          <el-col :xs="12" :sm="6" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">签发机构 (AI 嗅探)</span>
              <span class="meta-value text-primary font-bold">{{ sniffedInstitution || '未知 / 分析中' }}</span>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">上传时间</span>
              <span class="meta-value">{{ formatDate(file.uploaded_at) }}</span>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">完成时间</span>
              <span class="meta-value">{{ file.completed_at ? formatDate(file.completed_at) : '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">校验耗时</span>
              <span class="meta-value">{{ file.duration_seconds !== null && file.duration_seconds !== undefined ? formatDuration(file.duration_seconds) : '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6" class="meta-col">
            <div class="meta-cell">
              <span class="meta-label">最终通过率</span>
              <span class="meta-value pass-rate-highlight" :class="passRateClass(file.pass_rate)">
                {{ file.pass_rate !== null && file.pass_rate !== undefined ? file.pass_rate + '%' : '-' }}
              </span>
            </div>
          </el-col>
        </el-row>

        <!-- Active Processing Progress Tracker -->
        <div v-if="file.status === 'pending' || file.status === 'processing'" class="live-progress-container mt-4">
          <div class="progress-info-row flex-between mb-2">
            <span class="progress-status-title">正在执行智能校验引擎分析...</span>
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
              <h3>文档在线预览</h3>
            </div>
            <div 
              ref="pdfContainerRef" 
              class="pdf-viewer-container" 
              v-loading="pdfLoading"
              style="flex: 1; overflow-y: auto; background-color: #e5e7eb; position: relative; padding: 20px; display: flex; flex-direction: column; align-items: center;"
            >
              <el-empty 
                v-if="!file || ['pending', 'processing'].includes(file.status)" 
                description="等待处理或暂无预览..." 
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
              <h3 class="flex-align-center"><el-icon class="mr-2"><WarningFilled /></el-icon> 需人工仲裁介入</h3>
            </div>
            <div class="arbitration-content mt-2">
              <p class="text-sm text-gray-600 mb-4" style="line-height: 1.5; margin-bottom: 16px;">
                校验引擎大模型置信度偏低或触发高风险规则拦截，系统已自动挂起此文件。请结合左侧实时预览核实后，在下方作出仲裁决策。
              </p>
              <div class="arbitration-actions flex gap-4" style="display: flex; gap: 12px;">
                <el-button type="success" :icon="Check" style="flex: 1" @click="handleReviewResolution('approve')">
                  人工放行 (Approve)
                </el-button>
                <el-button type="danger" :icon="Close" style="flex: 1" @click="handleReviewResolution('reject')">
                  确认驳回 (Reject)
                </el-button>
              </div>
            </div>
          </div>

          <!-- Verification Results -->
          <div class="glass-card section-panel mb-4">
            <div class="section-title flex-between">
              <h3>校验规则诊断报告</h3>
              <div class="checks-counters" v-if="file.verification_result_json?.summary">
                <span class="counter-badge pass">{{ file.pass_count }} 通过</span>
                <span class="counter-badge warning" v-if="file.warning_count > 0">{{ file.warning_count }} 警告</span>
                <span class="counter-badge fail" v-if="file.fail_count > 0">{{ file.fail_count }} 不合规</span>
                <el-button size="small" type="primary" plain class="ml-3 print-btn hide-on-print" @click="handlePrintReport">
                  导出报告 (PDF)
                </el-button>
              </div>
            </div>

            <el-empty
              v-if="!file.verification_result_json || !file.verification_result_json.checks || file.verification_result_json.checks.length === 0"
              description="校验正在进行中，完成后将自动在此生成详细报告..."
              :image-size="120"
              class="empty-report-state"
            />

            <div v-else class="diagnostic-checklist">
              <div
                v-for="(check, index) in file.verification_result_json.checks"
                :key="index"
                class="diagnostic-check-card"
                :class="[check.status, check.page ? 'has-page-link' : '']"
                @click="check.page ? scrollToPage(check.page) : null"
              >
                <div class="check-left-indicator" :class="check.status"></div>
                <div class="diagnostic-check-icon" :class="check.status">
                  <el-icon v-if="check.status === 'pass'"><Check /></el-icon>
                  <el-icon v-else-if="check.status === 'warning'"><Warning /></el-icon>
                  <el-icon v-else><Close /></el-icon>
                </div>
                <div class="diagnostic-check-body">
                  <div class="check-title-row flex-between">
                    <h4 class="flex-align-center">
                      {{ check.name }}
                      <el-tag v-if="check.page" size="small" type="info" effect="plain" class="ml-2 page-tag">
                        第 {{ check.page }} 页 <el-icon class="ml-1"><Position /></el-icon>
                      </el-tag>
                    </h4>
                    <span class="check-status-tag" :class="check.status">{{ checkStatusLabel(check.status) }}</span>
                  </div>
                  <p class="check-message">{{ check.message }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- General Details Card -->
          <div class="glass-card section-panel mb-4 small-card">
            <div class="section-title">
              <h3>文件诊断详情</h3>
            </div>
            <div class="info-details-list">
              <div class="info-detail-item">
                <span class="lbl">校验ID</span>
                <span class="val text-monospace">#{{ file.id.substring(0, 8) }}</span>
              </div>
              <div class="info-detail-item">
                <span class="lbl">上传账号</span>
                <span class="val">{{ file.uploaded_by || '-' }}</span>
              </div>
              <div class="info-detail-item">
                <span class="lbl">校验模型</span>
                <span class="val">{{ file.verification_result_json?.model_version || file.verification_model || '智能校验引擎 2.0' }}</span>
              </div>
              <div class="info-detail-item">
                <span class="lbl">合规项目</span>
                <span class="val color-pass">{{ file.pass_count }} 项</span>
              </div>
              <div class="info-detail-item">
                <span class="lbl">预警项目</span>
                <span class="val color-warning">{{ file.warning_count }} 项</span>
              </div>
              <div class="info-detail-item">
                <span class="lbl">异常项目</span>
                <span class="val color-fail">{{ file.fail_count }} 项</span>
              </div>
            </div>
          </div>

          <!-- Digital Signature Details Card -->
          <div
            v-if="digitalSignatures"
            class="glass-card section-panel mb-4 small-card"
          >
            <div class="section-title flex-between">
              <h3>数字签名详情</h3>
              <el-tag
                :type="digitalSignatures.signed ? 'success' : 'info'"
                size="small"
              >
                {{ digitalSignatures.signed ? '已签名' : '未签名' }}
              </el-tag>
            </div>

            <!-- No Signatures -->
            <el-empty
              v-if="!digitalSignatures.signed"
              description="该文档未包含数字签名"
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
                      {{ sig.integrity ? '完整' : '已篡改' }}
                    </el-tag>
                    <el-tag
                      :type="sig.expired ? 'danger' : 'success'"
                      size="small"
                      effect="plain"
                    >
                      {{ sig.expired ? '已过期' : '有效' }}
                    </el-tag>
                  </div>
                </div>

                <!-- Signature Details -->
                <div class="sig-details">
                  <div class="sig-detail-row">
                    <span class="sig-detail-label">签署主体</span>
                    <span class="sig-detail-value text-bold">{{ sig.signer_cn }}</span>
                  </div>
                  <div class="sig-detail-row" v-if="sig.signing_time">
                    <span class="sig-detail-label">签署时间</span>
                    <span class="sig-detail-value">{{ formatDate(sig.signing_time) }}</span>
                  </div>
                  <div class="sig-detail-row">
                    <span class="sig-detail-label">数据完整性</span>
                    <span
                      class="sig-detail-value"
                      :class="sig.integrity ? 'color-pass' : 'color-fail'"
                    >
                      {{ sig.integrity ? '未被篡改' : '已遭篡改/损坏' }}
                    </span>
                  </div>
                  <div class="sig-detail-row">
                    <span class="sig-detail-label">证书时效性</span>
                    <span
                      class="sig-detail-value"
                      :class="!sig.expired ? 'color-pass' : 'color-fail'"
                    >
                      {{ sig.expired ? '已过期' : '有效期内' }}
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
                      {{ expandedSigs[index] ? '收起证书详情' : '展开详细证书识别信息' }}
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
                        <span class="cert-group-title">证书主体识别 (Subject)</span>
                        <div class="sig-detail-row small-txt" v-if="sig.cert_info.subject.organization_name">
                          <span class="sig-detail-label">组织 (O)</span>
                          <span class="sig-detail-value">{{ sig.cert_info.subject.organization_name }}</span>
                        </div>
                        <div class="sig-detail-row small-txt" v-if="sig.cert_info.subject.organizational_unit_name">
                          <span class="sig-detail-label">部门 (OU)</span>
                          <span class="sig-detail-value">{{ sig.cert_info.subject.organizational_unit_name }}</span>
                        </div>
                        <div class="sig-detail-row small-txt" v-if="sig.cert_info.subject.user_id">
                          <span class="sig-detail-label">用户 ID</span>
                          <span class="sig-detail-value text-monospace">{{ sig.cert_info.subject.user_id }}</span>
                        </div>
                        <div class="sig-detail-row small-txt" v-if="sig.cert_info.subject.country_name">
                          <span class="sig-detail-label">国家 (C)</span>
                          <span class="sig-detail-value">{{ sig.cert_info.subject.country_name }}</span>
                        </div>
                      </div>

                      <!-- Issuer Details -->
                      <div class="cert-sub-group mt-2" v-if="sig.cert_info.issuer">
                        <span class="cert-group-title">颁发机构 (Issuer CA)</span>
                        <div class="sig-detail-row small-txt" v-if="sig.cert_info.issuer.common_name">
                          <span class="sig-detail-label">机构 CN</span>
                          <span class="sig-detail-value">{{ sig.cert_info.issuer.common_name }}</span>
                        </div>
                        <div class="sig-detail-row small-txt" v-if="sig.cert_info.issuer.organization_name">
                          <span class="sig-detail-label">颁发组织</span>
                          <span class="sig-detail-value">{{ sig.cert_info.issuer.organization_name }}</span>
                        </div>
                      </div>

                      <!-- Validity & Serial Details -->
                      <div class="cert-sub-group mt-2">
                        <span class="cert-group-title">证书有效期与凭证</span>
                        <div class="sig-detail-row small-txt" v-if="sig.cert_info.validity?.not_before">
                          <span class="sig-detail-label">生效时间</span>
                          <span class="sig-detail-value">{{ formatDate(sig.cert_info.validity.not_before) }}</span>
                        </div>
                        <div class="sig-detail-row small-txt" v-if="sig.cert_info.validity?.not_after">
                          <span class="sig-detail-label">失效时间</span>
                          <span class="sig-detail-value">{{ formatDate(sig.cert_info.validity.not_after) }}</span>
                        </div>
                        <div class="sig-detail-row small-txt" v-if="sig.cert_info.serial_number">
                          <span class="sig-detail-label">证书序列号</span>
                          <span class="sig-detail-value text-monospace word-break-serial">{{ sig.cert_info.serial_number }}</span>
                        </div>
                      </div>
                    </div>
                  </el-collapse-transition>
                </div>
              </div>
            </div>
          </div>

          <!-- Reviewer Notes Panel -->
          <div class="glass-card section-panel notes-panel">
            <div class="section-title">
              <h3>人工审核备注</h3>
            </div>

            <!-- Notes List with smooth scroll -->
            <div class="notes-timeline-container" v-loading="notesLoading">
              <el-empty 
                v-if="notes.length === 0" 
                description="暂无审核备注。添加备注以记录文件审查细节。" 
                :image-size="60"
                class="empty-notes-state"
              />
              
              <div v-else class="notes-timeline">
                <div 
                  v-for="note in notes" 
                  :key="note.id" 
                  class="timeline-note-bubble"
                >
                  <div class="note-meta flex-between">
                    <div class="author-avatar-info">
                      <div class="avatar-circle">
                        {{ note.author_name ? note.author_name.charAt(0).toUpperCase() : 'U' }}
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
                placeholder="撰写人工审核意见或异常备注..."
                maxlength="500"
                show-word-limit
                class="premium-textarea"
                :disabled="submittingNote"
              />
              <div class="flex-between" style="margin-top: 8px;">
                <span class="input-tips">请确保记录完整的信息，以便追溯核对</span>
                <el-button 
                  type="primary" 
                  @click="handleAddNote" 
                  :loading="submittingNote"
                  :disabled="!newNote.trim()"
                  class="submit-note-btn"
                >
                  发表备注
                </el-button>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Document, Download, Check, Warning, WarningFilled, Close, Delete, Key, ArrowDown, ArrowUp, Position } from '@element-plus/icons-vue'
import { filesApi } from '@/api/files'
import { notesApi } from '@/api/notes'
import { useAuthStore } from '@/stores/auth'
import type { FileDetail, Note } from '@/types'
import * as pdfjsLib from 'pdfjs-dist'

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

function toggleSigExpand(index: number) {
  expandedSigs.value[index] = !expandedSigs.value[index]
}

let pollTimer: any = null

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
  
  // PyMuPDF returns coordinates in points (72 DPI) with a Top-Left origin.
  // PDF.js viewport.convertToViewportPoint expects standard PDF coordinates (Bottom-Left origin).
  // To avoid flipping or complex viewBox offset math, we can simply scale the Top-Left points
  // directly by the viewport's scale.
  const scale = viewport.scale || 1.5
  
  const left = x0 * scale
  const top = y0 * scale
  const width = (x1 - x0) * scale
  const height = (y1 - y0) * scale
  
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
    pending: '等待校验',
    processing: '智能分析中',
    completed: '校验通过',
    failed: '校验未通过',
    warning: '合规性预警',
    needs_review: '需人工仲裁',
  }
  return map[status] || status
}

function checkStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pass: '通过',
    warning: '预警',
    fail: '不合规',
  }
  return map[status] || status
}

function fileTypeLabel(type?: string): string {
  const map: Record<string, string> = {
    production_plan: '生产计划单',
    quality_report: '质量检测报告',
    purchase_order: '采购订单',
    supplier_qualification: '供应商资质证书',
    product_specification: '产品规格说明书',
    other: '常规文档',
  }
  return map[type || ''] || '未归类文档'
}

function formatFileSize(bytes?: number): string {
  if (bytes === undefined || bytes === null) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatDuration(seconds?: number): string {
  if (seconds === undefined || seconds === null) return '-'
  if (seconds < 60) return `${seconds} 秒`
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return `${min}分${sec}秒`
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
    ElMessage.warning(`无法定位到第 ${page} 页`)
  }
}

function handlePrintReport() {
  window.print()
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
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
    ElMessage.error('无法载入文件详情')
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
    ElMessage.error('无法载入备注记录')
  } finally {
    if (!silent) notesLoading.value = false
  }
}

// Download File
async function handleDownload() {
  if (!file.value) return
  try {
    ElMessage.info('正在请求下载链接...')
    const res = await filesApi.getDownloadUrl(file.value.id)
    if (res && res.download_url) {
      window.open(res.download_url, '_blank')
      ElMessage.success('已打开下载通道')
    } else {
      ElMessage.error('未能获取有效下载链接')
    }
  } catch (error) {
    ElMessage.error('获取下载链接失败，请重试')
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
    ElMessage.success('备注发表成功')
  } catch (error) {
    ElMessage.error('发表备注失败，请重试')
  } finally {
    submittingNote.value = false
  }
}

// Delete Note
async function handleDeleteNote(noteId: string) {
  try {
    await ElMessageBox.confirm(
      '确定要永久删除这条审核备注吗？此操作无法撤销。',
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
        buttonSize: 'default'
      }
    )
    
    await notesApi.delete(noteId)
    notes.value = notes.value.filter(n => n.id !== noteId)
    ElMessage.success('备注已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除备注失败，请重试')
    }
  }
}

// Handle Review Resolution
async function handleReviewResolution(action: 'approve' | 'reject') {
  if (!file.value) return
  
  const actionText = action === 'approve' ? '放行通过' : '驳回不合规'
  
  try {
    const { value: comment } = await ElMessageBox.prompt(
      `您正在执行【${actionText}】操作。请输入仲裁备注（选填）：`,
      '人工仲裁确认',
      {
        confirmButtonText: '确认提交',
        cancelButtonText: '取消',
        inputPlaceholder: '如：已核对相关条款，确认无误',
        type: action === 'approve' ? 'success' : 'error'
      }
    )
    
    // Call API
    loading.value = true
    const updatedFile = await filesApi.resolveReview(file.value.id, {
      action,
      comment
    })
    
    ElMessage.success(`操作成功：已${actionText}`)
    // Refresh the page data
    await fetchFileDetail(true)
    await fetchNotes(true)
    
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error('仲裁提交失败，请重试')
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
    wsUrl = apiBase.replace(/^http/, 'ws') + `/files/ws/${fileId}?token=${token}`
  } else {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    wsUrl = `${protocol}//${host}${apiBase}/files/ws/${fileId}?token=${token}`
  }
  
  console.log('Connecting to verification progress WebSocket:', wsUrl)
  socket = new WebSocket(wsUrl)
  
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.error) {
      console.error('WebSocket progress channel error:', data.error)
      startPolling() // Fallback
      return
    }
    
    if (file.value) {
      file.value.verification_progress = data.progress
      file.value.status = data.status
      
      if (data.status !== 'pending' && data.status !== 'processing') {
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
  border-radius: 10px;
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
  border-radius: 10px;
  font-weight: 600;
  padding: 10px 20px;
  box-shadow: 0 4px 12px rgba(66, 133, 244, 0.2);
  transition: all 0.25s ease;
}

.download-report-btn:hover:not(:disabled) {
  box-shadow: 0 6px 18px rgba(66, 133, 244, 0.35);
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
  content: '';
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
  content: '';
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
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(0, 0, 0, 0.04);
  border-radius: 12px;
  position: relative;
  overflow: hidden;
  transition: all 0.25s ease;
}

.diagnostic-check-card:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.7);
  box-shadow: 0 6px 15px rgba(0,0,0,0.03);
}

.check-left-indicator {
  position: absolute;
  top: 0; bottom: 0; left: 0;
  width: 4px;
}
.check-left-indicator.pass { background-color: #4caf50; }
.check-left-indicator.warning { background-color: #ff9800; }
.check-left-indicator.fail { background-color: #f44336; }

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
</style>
