<template>
  <div class="graph-editor-workspace" :style="{ height: workspaceHeight + 'px' }">
    <!-- LEFT: Node Palette (Drag Toolbox) -->
    <aside class="palette-sidebar">
      <div class="palette-header">
        <span class="palette-header-icon">🧩</span>
        <span>算子面板</span>
      </div>

      <div v-for="group in paletteGroups" :key="group.key" class="palette-group">
        <div class="palette-group-title" @click="toggleGroup(group.key)">
          <span>{{ group.icon }} {{ group.label }}</span>
          <span class="caret" :class="{ open: openGroups[group.key] }">▸</span>
        </div>
        <transition name="slide">
          <div v-show="openGroups[group.key]" class="palette-items">
            <div
              v-for="item in group.items"
              :key="item.type"
              class="palette-item"
              :style="{ '--accent': item.borderColor }"
              @click="addNode(item.type)"
            >
              <span class="palette-item-icon">{{ item.icon }}</span>
              <span class="palette-item-label">{{ item.label }}</span>
            </div>
          </div>
        </transition>
      </div>

      <div class="palette-footer">
        <button class="reset-btn" @click="resetGraph">
          <span>🗑️</span> 清空画布
        </button>
      </div>
    </aside>

    <!-- CENTER: Vue Flow Canvas -->
    <main class="canvas-area">
      <VueFlow
        v-if="isInitialized"
        v-model:nodes="nodes"
        v-model:edges="edges"
        :default-zoom="1"
        :min-zoom="0.3"
        :max-zoom="4"
        class="vue-flow-canvas"
        @connect="onConnect"
        @nodeClick="onNodeClick"
        @paneClick="onPaneClick"
        @paneReady="onPaneReady"
      >
        <Background pattern-color="#d1d5db" :gap="20" />
        <Controls position="bottom-left" />
        <MiniMap v-if="nodes.length > 4" />
      </VueFlow>

      <!-- Loading State -->
      <div v-if="!isInitialized" class="canvas-loading-state">
        <div class="loading-spinner"></div>
        <p>加载可视化编辑器...</p>
      </div>

      <!-- Empty State Overlay -->
      <div v-else-if="nodes.length <= 2" class="canvas-empty-hint">
        <div class="hint-content">
          <span class="hint-icon">👈</span>
          <p>从左侧面板点击算子添加到画布</p>
          <p class="hint-sub">拖动节点排列 · 从圆点拉线连接</p>
        </div>
      </div>
    </main>

    <!-- RIGHT: Node Inspector Panel -->
    <aside class="inspector-sidebar" :class="{ open: !!selectedNode }">
      <template v-if="selectedNode">
        <div class="inspector-header">
          <div class="inspector-title-row">
            <span class="inspector-icon" :style="{ background: getNodeMeta(selectedNode.data?.nodeType)?.color }">
              {{ getNodeMeta(selectedNode.data?.nodeType)?.icon || '⚙️' }}
            </span>
            <div class="inspector-title-text">
              <h4>{{ getNodeMeta(selectedNode.data?.nodeType)?.label || '节点配置' }}</h4>
              <span class="inspector-type-badge">{{ selectedNode.data?.nodeType || 'custom' }}</span>
            </div>
          </div>
          <button class="inspector-close" @click="selectedNode = null">✕</button>
        </div>

        <div class="inspector-body">
          <!-- Basic: Node Label -->
          <div class="field-group">
            <label class="field-label" for="node-display-name">显示名称</label>
            <input id="node-display-name" v-model="selectedNode.label" type="text" class="field-input" />
          </div>

          <!-- === Type-Specific Fields === -->

          <!-- LLM Prompt -->
          <div v-if="selectedNode.data?.nodeType === 'text-llm' || selectedNode.data?.nodeType === 'vision-llm'">
            <div class="field-group">
              <label class="field-label" for="node-prompt">
                Prompt 指令
                <span class="field-hint">告诉大模型要检查什么</span>
              </label>
              <textarea id="node-prompt" v-model="selectedNode.data.prompt" class="field-textarea" rows="4" placeholder="请检查该文档是否包含..."></textarea>
            </div>

            <!-- LLM Operation Mode -->
            <div class="field-group">
              <span class="field-label">操作模式</span>
              <div class="node-mode-selector">
                <div
                  class="node-mode-chip"
                  :class="{ active: selectedNode.data.operation_mode === 'verification' }"
                  @click="selectedNode.data.operation_mode = 'verification'"
                >
                  <span class="mode-icon">✓</span>
                  <span class="mode-text">验证</span>
                </div>
                <div
                  class="node-mode-chip"
                  :class="{ active: selectedNode.data.operation_mode === 'extraction' }"
                  @click="selectedNode.data.operation_mode = 'extraction'"
                >
                  <span class="mode-icon">⋮</span>
                  <span class="mode-text">提取</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Keyword -->
          <div class="field-group" v-if="selectedNode.data?.nodeType === 'keyword'">
            <label class="field-label" for="node-keywords">
              关键词列表
              <span class="field-hint">逗号分隔，命中任一即通过</span>
            </label>
            <input id="node-keywords" v-model="selectedNode.data.keywords" type="text" class="field-input" placeholder="华测,CTI,CNAS" />
          </div>

          <!-- Regex -->
          <div class="field-group" v-if="selectedNode.data?.nodeType === 'regex'">
            <label class="field-label" for="node-pattern">
              正则表达式
              <span class="field-hint">匹配内容将写入上下文</span>
            </label>
            <input id="node-pattern" v-model="selectedNode.data.pattern" type="text" class="field-input mono" placeholder="^报告编号[：:]\s*\w+" />
          </div>

          <!-- Signature -->
          <div class="field-group" v-if="selectedNode.data?.nodeType === 'signature'">
            <label class="field-label" for="node-expected-issuer">
              预期签发者
              <span class="field-hint">留空则仅检查签名存在性</span>
            </label>
            <input id="node-expected-issuer" v-model="selectedNode.data.expected_issuer" type="text" class="field-input" placeholder="Centre Testing International" />
          </div>

          <!-- Revision Check -->
          <div v-if="selectedNode.data?.nodeType === 'revision-check'">
            <div class="field-group">
              <label class="field-label" for="node-max-revisions">
                允许最大修订次数
                <span class="field-hint">0 = 使用默认逻辑</span>
              </label>
              <el-input-number id="node-max-revisions" v-model="selectedNode.data.maxRevisions" :min="0" :max="100" :step="1" size="small" style="width: 140px;" />
            </div>
            <div class="field-group">
              <label class="field-label">
                允许合法增量更新
                <span class="field-hint">勾选 = 签名后的非篡改增量更新视为通过</span>
              </label>
              <div class="field-checkbox-group">
                <label class="field-checkbox">
                  <input type="checkbox" v-model="selectedNode.data.allowIncrementalUpdates" />
                  <span>允许增量更新</span>
                </label>
              </div>
            </div>
            <div class="field-hint-card">
              <p>💡 修订版本检测规则：</p>
              <ul class="hint-list">
                <li><strong>Rev=1</strong> — 文档未被修改过 ✅</li>
                <li><strong>Rev&gt;1 + 已签名</strong> — 签名后存在增量更新，可能被篡改 ⚠️</li>
                <li><strong>Rev&gt;1 + 允许增量更新</strong> — 仅警告，不阻断</li>
              </ul>
            </div>
          </div>

          <!-- Condition -->
          <div v-if="selectedNode.data?.nodeType === 'condition'">
            <div class="field-group">
              <label class="field-label" for="node-expression">
                条件表达式
                <span class="field-hint">满足条件走 ✅ 分支</span>
              </label>
              <input id="node-expression" v-model="selectedNode.data.expression" type="text" class="field-input mono" placeholder="institution == 'CTI'" />
            </div>
            <div class="field-hint-card">
              <p>💡 可用变量：<code>institution</code>, <code>has_signature</code>, <code>qr_count</code>, <code>page_count</code>, <code>revision_count</code>, <code>is_tampered</code></p>
            </div>
          </div>

          <!-- HTTP Call -->
          <div v-if="selectedNode.data?.nodeType === 'http-call'">
            <div class="field-group">
              <label class="field-label" for="node-url-template">请求 URL <span class="required-mark">*</span></label>
              <input id="node-url-template" v-model="selectedNode.data.url_template" type="text" class="field-input mono" placeholder="https://verify.example.com/check?code={{qr_content}}" />
              <span class="field-hint">支持变量插值，如 qr_content, extracted_report_id</span>
            </div>
            <div class="field-group">
              <span class="field-label">HTTP 方法</span>
              <div class="field-radio-group">
                <label class="field-radio" :class="{ active: selectedNode.data?.http_method === 'GET' }">
                  <input type="radio" v-model="selectedNode.data.http_method" value="GET" /> GET
                </label>
                <label class="field-radio" :class="{ active: selectedNode.data?.http_method === 'POST' }">
                  <input type="radio" v-model="selectedNode.data.http_method" value="POST" /> POST
                </label>
                <label class="field-radio" :class="{ active: selectedNode.data?.http_method === 'PUT' }">
                  <input type="radio" v-model="selectedNode.data.http_method" value="PUT" /> PUT
                </label>
              </div>
            </div>

            <!-- Advanced Options (Collapsible) -->
            <div class="field-group">
              <div class="collapsible-header" @click="toggleHttpAdvanced">
                <span>高级选项</span>
                <span class="caret" :class="{ open: httpAdvancedExpanded }">▸</span>
              </div>
              <div v-show="httpAdvancedExpanded" class="collapsible-content">
                <!-- Headers -->
                <div class="sub-field-group">
                  <label class="field-label">请求 Headers (可选)</label>
                  <div class="key-value-list">
                    <div v-for="(header, idx) in (selectedNode.data?.headers || [])" :key="header._id || idx" class="key-value-row">
                      <input v-model="header.key" type="text" class="field-input mono key-input" placeholder="Header 名称 (如: Authorization)" />
                      <input v-model="header.value" type="text" class="field-input mono value-input" placeholder="Header 值 (如: Bearer {{token}})" />
                      <button @click.prevent="removeHttpHeader(idx)" class="remove-btn" :disabled="header.key === 'Content-Type' && header.value === 'application/json'">×</button>
                    </div>
                    <button @click.prevent="addHttpHeader" class="add-btn">+ 添加 Header</button>
                  </div>
                </div>

                <!-- Body (for POST/PUT) -->
                <div class="sub-field-group" v-if="selectedNode.data?.http_method === 'POST' || selectedNode.data?.http_method === 'PUT'">
                  <label class="field-label">请求 Body (可选)</label>
                  <textarea v-model="selectedNode.data.body_template" class="field-textarea mono" rows="4" placeholder='{"report_id": "xxx", "code": "xxx"}'></textarea>
                  <span class="field-hint">JSON 格式，支持变量插值</span>
                </div>

                <!-- Timeout -->
                <div class="sub-field-group">
                  <label class="field-label">超时时间 (秒)</label>
                  <input v-model.number="selectedNode.data.timeout" type="number" class="field-input" style="width: 100px;" min="1" max="120" placeholder="30" />
                </div>

                <!-- Success Criteria -->
                <div class="sub-field-group">
                  <label class="field-label">验证通过条件</label>
                  <select v-model="selectedNode.data.success_type" class="field-input">
                    <option value="status_code">状态码等于 200</option>
                    <option value="status_2xx">状态码为 2xx (成功)</option>
                    <option value="json_path">JSON Path 匹配</option>
                    <option value="text_contains">响应文本包含</option>
                  </select>
                  <input v-if="selectedNode.data?.success_type === 'json_path'" v-model="selectedNode.data.json_path" type="text" class="field-input mono" style="margin-top: 6px;" placeholder="$.valid" />
                  <input v-if="selectedNode.data?.success_type === 'json_path'" v-model="selectedNode.data.json_expected" type="text" class="field-input mono" style="margin-top: 6px;" placeholder="true" />
                  <input v-if="selectedNode.data?.success_type === 'text_contains'" v-model="selectedNode.data.text_contains" type="text" class="field-input mono" style="margin-top: 6px;" placeholder="OK" />
                </div>
              </div>
            </div>
          </div>

          <!-- Data Compare -->
          <div v-if="selectedNode.data?.nodeType === 'data-compare'">
            <div class="field-group">
              <label class="field-label" for="node-source-a">比较源 A</label>
              <input id="node-source-a" v-model="selectedNode.data.source_a" type="text" class="field-input mono" placeholder="qr_report_id" />
            </div>
            <div class="compare-arrow">⇅</div>
            <div class="field-group">
              <label class="field-label" for="node-source-b">比较源 B</label>
              <input id="node-source-b" v-model="selectedNode.data.source_b" type="text" class="field-input mono" placeholder="text_report_id" />
            </div>
          </div>

          <!-- Vote -->
          <div class="field-group" v-if="selectedNode.data?.nodeType === 'vote'">
            <label class="field-label" for="node-min-pass">
              最低通过数 (N/M)
              <span class="field-hint">上游连入节点中，至少 N 个通过</span>
            </label>
            <input id="node-min-pass" v-model.number="selectedNode.data.min_pass" type="number" min="1" class="field-input" style="width: 80px;" />
          </div>

          <!-- Human Review -->
          <div class="field-group" v-if="selectedNode.data?.nodeType === 'human-review'">
            <label class="field-label" for="node-review-hint">
              审核提示语
              <span class="field-hint">展示给审核人员的说明</span>
            </label>
            <textarea id="node-review-hint" v-model="selectedNode.data.review_hint" class="field-textarea" rows="3" placeholder="请人工核查签名信息..."></textarea>
          </div>

          <!-- === Common: Severity === -->
          <div class="field-group" v-if="selectedNode.data?.hasSeverity && !isLLMExtractionMode(selectedNode.data)">
            <span class="field-label">不通过时的处理</span>
            <div class="severity-options">
              <label
                v-for="opt in severityOptions"
                :key="opt.value"
                class="severity-chip"
                :class="{ active: selectedNode.data.severity === opt.value, [opt.value]: true }"
              >
                <input type="radio" v-model="selectedNode.data.severity" :value="opt.value" />
                <span class="chip-icon">{{ opt.icon }}</span>
                <span class="chip-label">{{ opt.label }}</span>
              </label>
            </div>
          </div>

          <!-- === Variables Panel (Common) === -->
          <div class="variables-section">
            <div class="variables-header" @click="variablesExpanded = !variablesExpanded">
              <span class="variables-title">📋 可用变量</span>
              <span class="variables-count">{{ getTotalVariablesCount() }} 个</span>
              <span class="caret" :class="{ open: variablesExpanded }">▸</span>
            </div>
            <div v-show="variablesExpanded" class="variables-content">
              <div v-for="group in availableVariables" :key="group.category" class="variable-group">
                <div class="variable-group-title">{{ group.icon }} {{ group.label }}</div>
                <div class="variable-list">
                  <div
                    v-for="variable in group.variables"
                    :key="variable.name"
                    class="variable-item"
                    @click="insertVariable(variable.name)"
                    :title="`点击插入 {{ variable.name }}`"
                  >
                    <span class="variable-syntax">{{ `{{${variable.name}}}` }}</span>
                    <span class="variable-desc">{{ variable.desc }}</span>
                    <span class="variable-insert-hint">→</span>
                  </div>
                </div>
              </div>
              <div class="variables-footer-hint">
                💡 点击变量即可插入到光标位置
              </div>
            </div>
          </div>
        </div>

        <!-- Inspector Footer -->
        <div class="inspector-footer">
          <button class="delete-node-btn" @click="deleteSelectedNode" :disabled="selectedNode.deletable === false">
            🗑️ 删除该节点
          </button>
        </div>
      </template>

      <!-- No Selection -->
      <template v-else>
        <div class="inspector-empty">
          <span class="inspector-empty-icon">🖱️</span>
          <p>点击画布中的节点</p>
          <p class="hint-sub">查看与编辑配置</p>
        </div>
      </template>
    </aside>
  </div>

  <!-- Drag-to-resize handle bar -->
  <div 
    class="editor-resize-bar" 
    @mousedown="startResize" 
    :class="{ 'is-resizing': isResizing }"
  >
    <div class="resize-bar-handle">
      <span class="handle-line"></span>
      <span class="handle-line"></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, nextTick } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

// ─── Node Type Registry ───
interface NodeMeta {
  label: string
  icon: string
  color: string
  borderColor: string
  group: 'ai' | 'detect' | 'flow'
  defaultData: Record<string, any>
}

const NODE_REGISTRY: Record<string, NodeMeta> = {
  'text-llm':            { label: '文本大模型',     icon: '🧠', color: '#dbeafe', borderColor: '#3b82f6', group: 'ai',     defaultData: { prompt: '', operation_mode: 'verification', severity: 'fail', hasSeverity: true } },
  'vision-llm':          { label: '视觉大模型',     icon: '👁️', color: '#ede9fe', borderColor: '#8b5cf6', group: 'ai',     defaultData: { prompt: '', operation_mode: 'verification', severity: 'fail', hasSeverity: true } },
  'institution-sniffer': { label: '机构嗅探',       icon: '🏢', color: '#fef3c7', borderColor: '#f59e0b', group: 'ai',     defaultData: {} },
  'revision-check':      { label: '修订版本检查',   icon: '📋', color: '#e0f2fe', borderColor: '#0284c7', group: 'detect', defaultData: { maxRevisions: 1, allowIncrementalUpdates: false, severity: 'fail', hasSeverity: true } },
  'signature':           { label: '数字签名检查',   icon: '🔐', color: '#dcfce7', borderColor: '#22c55e', group: 'detect', defaultData: { expected_issuer: '', severity: 'fail', hasSeverity: true } },
  'qr-code':             { label: '二维码识别',     icon: '📱', color: '#e0e7ff', borderColor: '#6366f1', group: 'detect', defaultData: { severity: 'fail', hasSeverity: true } },
  'pdf-info':            { label: 'PDF 信息提取',   icon: '📄', color: '#f3e8ff', borderColor: '#a855f7', group: 'detect', defaultData: {} },
  'keyword':             { label: '关键词匹配',     icon: '🔤', color: '#ffedd5', borderColor: '#f97316', group: 'detect', defaultData: { keywords: '', severity: 'fail', hasSeverity: true } },
  'regex':               { label: '正则校验',       icon: '📐', color: '#fef9c3', borderColor: '#eab308', group: 'detect', defaultData: { pattern: '', severity: 'fail', hasSeverity: true } },
  'condition':           { label: '条件分支',       icon: '🔀', color: '#fce7f3', borderColor: '#ec4899', group: 'flow',   defaultData: { expression: '' } },
  'human-review':        { label: '人工审核点',     icon: '🙋', color: '#fff7ed', borderColor: '#ea580c', group: 'flow',   defaultData: { review_hint: '' } },
  'http-call':           { label: 'HTTP 外部验证',  icon: '🌐', color: '#ecfdf5', borderColor: '#059669', group: 'flow',   defaultData: { url_template: '', http_method: 'GET', headers: [{ key: 'Content-Type', value: 'application/json', _id: 1 }], body_template: '', timeout: 30, success_type: 'status_2xx', json_path: '', json_expected: 'true', text_contains: '', severity: 'fail', hasSeverity: true } },
  'data-compare':        { label: '数据比对',       icon: '⚖️', color: '#f0f9ff', borderColor: '#0284c7', group: 'flow',   defaultData: { source_a: '', source_b: '', severity: 'fail', hasSeverity: true } },
  'vote':                { label: '聚合投票',       icon: '🗳️', color: '#faf5ff', borderColor: '#7c3aed', group: 'flow',   defaultData: { min_pass: 2 } },
}

const severityOptions = [
  { value: 'fail', label: '拦截', icon: '🚫' },
  { value: 'warning', label: '警告', icon: '⚠️' },
  { value: 'review', label: '人工复核', icon: '🙋' },
]

// Build palette groups from registry
const paletteGroups = [
  {
    key: 'ai', icon: '🤖', label: 'AI 算子',
    items: Object.entries(NODE_REGISTRY).filter(([, m]) => m.group === 'ai').map(([type, m]) => ({ type, ...m })),
  },
  {
    key: 'detect', icon: '🔍', label: '检测算子',
    items: Object.entries(NODE_REGISTRY).filter(([, m]) => m.group === 'detect').map(([type, m]) => ({ type, ...m })),
  },
  {
    key: 'flow', icon: '🔀', label: '流程控制',
    items: Object.entries(NODE_REGISTRY).filter(([, m]) => m.group === 'flow').map(([type, m]) => ({ type, ...m })),
  },
]

const openGroups = reactive<Record<string, boolean>>({ ai: true, detect: true, flow: true })
function toggleGroup(key: string) { openGroups[key] = !openGroups[key] }
function getNodeMeta(nodeType?: string): NodeMeta | undefined { return nodeType ? NODE_REGISTRY[nodeType] : undefined }

function isLLMExtractionMode(nodeData: any): boolean {
  return (nodeData?.nodeType === 'text-llm' || nodeData?.nodeType === 'vision-llm') &&
         nodeData?.operation_mode === 'extraction'
}

function updateNodeLabel(node: any) {
  const meta = getNodeMeta(node.data?.nodeType)
  if (!meta) return

  const isExtraction = isLLMExtractionMode(node.data)
  if (isExtraction) {
    node.label = `${meta.icon} ${meta.label} [提取]`
  } else {
    node.label = `${meta.icon} ${meta.label}`
  }
}

// HTTP Headers management
let headerIdCounter = 0

function addHttpHeader() {
  if (!selectedNode.value?.data) return
  if (!selectedNode.value.data.headers) {
    selectedNode.value.data.headers = [{ key: 'Content-Type', value: 'application/json', _id: ++headerIdCounter }]
  }
  selectedNode.value.data.headers.push({ key: '', value: '', _id: ++headerIdCounter })
}

function removeHttpHeader(idx: number | string) {
  if (!selectedNode.value?.data?.headers) return
  const index = typeof idx === 'string' ? parseInt(idx, 10) : idx
  if (selectedNode.value.data.headers.length <= 1) return // Keep at least one
  selectedNode.value.data.headers.splice(index, 1)
}

function toggleHttpAdvanced() {
  httpAdvancedExpanded.value = !httpAdvancedExpanded.value
}

// ─── Variables Management ───
// Available variables from backend shared_state
const availableVariables = [
  {
    category: 'system',
    icon: '⚙️',
    label: '系统变量',
    variables: [
      { name: 'institution', desc: '发证机构名称' },
      { name: 'page_count', desc: 'PDF 页数' },
      { name: 'full_text', desc: '完整文本内容' },
    ]
  },
  {
    category: 'qr',
    icon: '📱',
    label: '二维码',
    variables: [
      { name: 'qr_content', desc: '第一个二维码内容' },
      { name: 'qr_codes', desc: '所有二维码数据数组' },
    ]
  },
  {
    category: 'signature',
    icon: '🔐',
    label: '数字签名',
    variables: [
      { name: 'digital_signatures', desc: '签名完整数据' },
      { name: 'signer_cn', desc: '签署人通用名' },
      { name: 'signature_valid', desc: '签名是否有效' },
    ]
  },
  {
    category: 'pdf',
    icon: '📄',
    label: 'PDF 元数据',
    variables: [
      { name: 'pdf_info', desc: 'PDF 完整信息' },
      { name: 'is_tampered', desc: '是否被篡改' },
      { name: 'revision_count', desc: '修订版本数' },
    ]
  },
  {
    category: 'extract',
    icon: '📤',
    label: '提取数据',
    variables: [
      { name: 'extracted_report_number', desc: '报告编号 (提取模式)' },
      { name: 'extracted_verification_code', desc: '校验码 (提取模式)' },
      { name: 'extracted_tables', desc: '提取的表格数据' },
      { name: 'llm_semantic_analysis', desc: 'LLM 语义分析结果' },
      { name: 'vision_analysis', desc: '视觉分析结果' },
      { name: 'detected_stamps', desc: '检测到的印章' },
      { name: 'diff_results', desc: '文档比对结果' },
    ]
  }
]

function getTotalVariablesCount() {
  return availableVariables.reduce((sum, group) => sum + group.variables.length, 0)
}

function insertVariable(varName: string) {
  // Insert variable at cursor position or append to focused input
  const activeElement = document.activeElement as HTMLInputElement | HTMLTextAreaElement
  if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
    const variableSyntax = `{{${varName}}}`
    const start = activeElement.selectionStart ?? 0
    const end = activeElement.selectionEnd ?? 0
    const value = activeElement.value || ''

    const newValue = value.substring(0, start) + variableSyntax + value.substring(end)
    activeElement.value = newValue

    // Set cursor position after inserted variable
    const newCursorPos = start + variableSyntax.length
    activeElement.setSelectionRange(newCursorPos, newCursorPos)

    // Trigger input event to update v-model
    activeElement.dispatchEvent(new Event('input', { bubbles: true }))

    // Flash effect on the input to show insertion happened
    activeElement.classList.add('variable-inserted-flash')
    setTimeout(() => {
      activeElement.classList.remove('variable-inserted-flash')
    }, 300)
  }
}

// ─── Props & Emit ───
const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({ nodes: [], edges: [] })
  }
})
const emit = defineEmits(['update:modelValue'])

const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const selectedNode = ref<any | null>(null)
const isInitialized = ref(false)
const httpAdvancedExpanded = ref(false)
const variablesExpanded = ref(true)

const defaultNodes = [
  {
    id: 'node-input', type: 'input', label: '📥 文档输入',
    position: { x: 280, y: 40 },
    class: 'bg-primary text-white border-none rounded-lg shadow-lg font-bold p-3',
    deletable: false, data: {},
  },
  {
    id: 'node-output', type: 'output', label: '📊 最终判定聚合',
    position: { x: 280, y: 560 },
    class: 'bg-success text-white border-none rounded-lg shadow-lg font-bold p-3',
    deletable: false, data: {},
  },
]

function safeCloneNodes(nodesArray: any[]) {
  if (!Array.isArray(nodesArray)) return []
  return nodesArray.map(node => {
    // Extract only standard serializable properties to avoid VueFlow internal circular references
    const serialized: any = {
      id: node.id,
      type: node.type,
      label: node.label,
      position: node.position ? { x: Number(node.position.x), y: Number(node.position.y) } : { x: 0, y: 0 },
      data: node.data ? JSON.parse(JSON.stringify(node.data)) : {},
    }
    if (node.style) serialized.style = JSON.parse(JSON.stringify(node.style))
    if (node.class) serialized.class = node.class
    if (node.parentId) serialized.parentId = node.parentId
    if (node.draggable !== undefined) serialized.draggable = node.draggable
    if (node.selectable !== undefined) serialized.selectable = node.selectable
    if (node.connectable !== undefined) serialized.connectable = node.connectable
    if (node.deletable !== undefined) serialized.deletable = node.deletable

    // Ensure headers have _id for http-call nodes
    if (serialized.data?.headers && Array.isArray(serialized.data.headers)) {
      serialized.data.headers = serialized.data.headers.map((h: any) => ({
        ...h,
        _id: h._id || ++headerIdCounter
      }))
    }

    return serialized
  })
}

function safeCloneEdges(edgesArray: any[]) {
  if (!Array.isArray(edgesArray)) return []
  return edgesArray.map(edge => {
    const serialized: any = {
      id: edge.id,
      source: edge.source,
      target: edge.target,
    }
    if (edge.type) serialized.type = edge.type
    if (edge.label) serialized.label = edge.label
    if (edge.animated !== undefined) serialized.animated = edge.animated
    if (edge.style) serialized.style = JSON.parse(JSON.stringify(edge.style))
    if (edge.class) serialized.class = edge.class
    if (edge.data) serialized.data = JSON.parse(JSON.stringify(edge.data))
    return serialized
  })
}

onMounted(() => {
  try {
    if (props.modelValue?.nodes?.length > 0) {
      // Load existing graph data with safe cloning
      nodes.value = safeCloneNodes(props.modelValue.nodes)
      edges.value = safeCloneEdges(props.modelValue.edges || [])

      // Ensure default nodes exist
      const hasInput = nodes.value.some(n => n.id === 'node-input')
      const hasOutput = nodes.value.some(n => n.id === 'node-output')

      if (!hasInput) {
        nodes.value.unshift(...safeCloneNodes(defaultNodes.filter(n => n.id === 'node-input')))
      }
      if (!hasOutput) {
        nodes.value.push(...safeCloneNodes(defaultNodes.filter(n => n.id === 'node-output')))
      }
    } else {
      // Initialize with default nodes
      nodes.value = safeCloneNodes(defaultNodes)
      edges.value = []
    }

    // Delay initialization to allow CSS transitions (like el-dialog fullscreen) to finish
    // so VueFlow can accurately measure container dimensions.
    setTimeout(() => {
      isInitialized.value = true
    }, 350)
  } catch (error) {
    console.error('[RuleGraphEditor] Failed to initialize graph:', error)
    // Fallback to default
    nodes.value = safeCloneNodes(defaultNodes)
    edges.value = []
    isInitialized.value = true
  }
})

watch([nodes, edges], () => {
  nextTick(() => {
    emit('update:modelValue', {
      nodes: safeCloneNodes(nodes.value),
      edges: safeCloneEdges(edges.value)
    })
  })
}, { deep: true })

// Watch selected node operation mode changes to update label
watch(() => selectedNode.value?.data?.operation_mode, () => {
  if (selectedNode.value) {
    updateNodeLabel(selectedNode.value)
  }
})

const onConnect = (connection: any) => {
  edges.value.push({
    id: `e-${connection.source}-${connection.target}`,
    source: connection.source,
    target: connection.target,
    animated: true,
    style: { stroke: '#10b981', strokeWidth: 2 },
  })
}

let nodeCounter = 0
const addNode = (type: string) => {
  nodeCounter++
  const meta = NODE_REGISTRY[type]
  if (!meta) return

  const existingCount = nodes.value.filter(n => n.data?.nodeType === type).length
  const col = existingCount % 3
  const row = Math.floor(existingCount / 3)

  // Deep clone default data and regenerate IDs for headers
  const defaultData = JSON.parse(JSON.stringify(meta.defaultData))
  if (defaultData.headers) {
    defaultData.headers = defaultData.headers.map((h: any) => ({
      ...h,
      _id: ++headerIdCounter
    }))
  }

  const newNode = {
    id: `node-${type}-${Date.now()}-${nodeCounter}`,
    label: `${meta.icon} ${meta.label}`,
    position: { x: 80 + col * 220, y: 150 + row * 120 },
    class: 'rounded-lg p-2 text-sm shadow-md',
    style: { backgroundColor: meta.color, borderColor: meta.borderColor, borderWidth: '2px', borderStyle: 'solid' },
    data: { nodeType: type, ...defaultData },
  }

  // Update label based on operation mode
  updateNodeLabel(newNode)

  nodes.value.push(newNode)
}

const onNodeClick = (event: any) => {
  selectedNode.value = event.node
  // Reset advanced options expansion when switching nodes
  if (event.node?.data?.nodeType !== 'http-call') {
    httpAdvancedExpanded.value = false
  }
}
const onPaneClick = () => { selectedNode.value = null }
const onPaneReady = (vueFlowInstance: any) => {
  // Ensure the view is fitted properly once the canvas is fully ready
  setTimeout(() => {
    vueFlowInstance.fitView()
  }, 50)
}

const deleteSelectedNode = () => {
  if (selectedNode.value && selectedNode.value.deletable !== false) {
    const id = selectedNode.value.id
    nodes.value = nodes.value.filter(n => n.id !== id)
    edges.value = edges.value.filter(e => e.source !== id && e.target !== id)
    selectedNode.value = null
  }
}

const resetGraph = () => {
  nodes.value = safeCloneNodes(defaultNodes)
  edges.value = []
  selectedNode.value = null
}

// Height resizing logic
const workspaceHeight = ref(600)
const isResizing = ref(false)

function startResize(e: MouseEvent) {
  isResizing.value = true
  const startY = e.clientY
  const startHeight = workspaceHeight.value
  
  const onMouseMove = (moveEvent: MouseEvent) => {
    if (!isResizing.value) return
    const deltaY = moveEvent.clientY - startY
    workspaceHeight.value = Math.max(400, Math.min(1200, startHeight + deltaY))
  }
  
  const onMouseUp = () => {
    isResizing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }
  
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}
</script>

<style scoped>
/* ─── Layout ─── */
.graph-editor-workspace {
  display: flex;
  width: 100%;
  height: 600px;
  border: 1px solid #e5e7eb;
  border-radius: 12px 12px 0 0;
  overflow: hidden;
  background: #f8fafc;
  transition: height 0.1s ease;
}

:global(.el-dialog.is-fullscreen) .graph-editor-workspace {
  height: calc(100vh - 170px) !important;
  border-radius: 12px !important;
}

/* ─── Resize Bar ─── */
.editor-resize-bar {
  width: 100%;
  height: 10px;
  background: #f1f5f9;
  border: 1px solid #e5e7eb;
  border-top: none;
  border-radius: 0 0 12px 12px;
  cursor: ns-resize;
  display: flex;
  justify-content: center;
  align-items: center;
  user-select: none;
  transition: background 0.15s, height 0.15s;
  z-index: 10;
}

.editor-resize-bar:hover,
.editor-resize-bar.is-resizing {
  background: #cbd5e1;
  height: 12px;
}

.resize-bar-handle {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: center;
}

.handle-line {
  width: 32px;
  height: 2px;
  background: #94a3b8;
  border-radius: 1px;
  transition: background 0.15s;
}

.editor-resize-bar:hover .handle-line,
.editor-resize-bar.is-resizing .handle-line {
  background: #64748b;
}

:global(.el-dialog.is-fullscreen) .editor-resize-bar {
  display: none !important;
}

/* ─── Palette Sidebar ─── */
.palette-sidebar {
  width: 200px;
  min-width: 200px;
  background: #ffffff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.palette-header {
  padding: 14px 16px;
  font-weight: 700;
  font-size: 14px;
  color: #1e293b;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  gap: 8px;
  position: sticky;
  top: 0;
  background: white;
  z-index: 1;
}

.palette-header-icon {
  font-size: 18px;
}

.palette-group {
  border-bottom: 1px solid #f1f5f9;
}

.palette-group-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}

.palette-group-title:hover {
  background: #f8fafc;
}

.caret {
  transition: transform 0.2s;
  font-size: 10px;
}

.caret.open {
  transform: rotate(90deg);
}

.palette-items {
  padding: 0 8px 8px;
}

.palette-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  margin-bottom: 3px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  border-left: 3px solid var(--accent, #e5e7eb);
  background: #fafbfc;
  font-size: 12px;
}

.palette-item:hover {
  background: #f0f4ff;
  transform: translateX(3px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.palette-item-icon {
  font-size: 15px;
  flex-shrink: 0;
}

.palette-item-label {
  color: #334155;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.palette-footer {
  margin-top: auto;
  padding: 12px;
  border-top: 1px solid #f1f5f9;
}

.reset-btn {
  width: 100%;
  padding: 8px;
  font-size: 12px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fff5f5;
  color: #ef4444;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.reset-btn:hover {
  background: #fee2e2;
}

/* ─── Canvas ─── */
.canvas-area {
  flex: 1;
  position: relative;
  background: #f1f5f9;
}

.vue-flow-canvas {
  width: 100%;
  height: 100%;
}

.canvas-empty-hint {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 1;
}

.hint-content {
  text-align: center;
  color: #94a3b8;
}

.hint-icon {
  font-size: 36px;
  display: block;
  margin-bottom: 8px;
}

.hint-content p {
  margin: 0;
  font-size: 14px;
}

.hint-sub {
  font-size: 12px !important;
  color: #cbd5e1;
  margin-top: 4px !important;
}

/* ─── Loading State ─── */
.canvas-loading-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  z-index: 10;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.canvas-loading-state p {
  margin-top: 16px;
  font-size: 14px;
  color: #64748b;
}

/* ─── Inspector Sidebar ─── */
.inspector-sidebar {
  width: 0;
  min-width: 0;
  background: #ffffff;
  border-left: 1px solid #e5e7eb;
  transition: width 0.25s ease, min-width 0.25s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.inspector-sidebar.open {
  width: 300px;
  min-width: 300px;
}

.inspector-header {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.inspector-title-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.inspector-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.inspector-title-text h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.inspector-type-badge {
  font-size: 10px;
  color: #94a3b8;
  font-family: 'SF Mono', monospace;
}

.inspector-close {
  background: none;
  border: none;
  font-size: 16px;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.inspector-close:hover {
  background: #f1f5f9;
  color: #64748b;
}

.inspector-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

/* ─── Field Styles ─── */
.field-group {
  margin-bottom: 14px;
}

.field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 6px;
}

.field-hint {
  display: block;
  font-weight: 400;
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.field-input {
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}

.field-input:focus {
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.15);
}

.field-input.mono, .mono {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
}

.field-textarea {
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  outline: none;
  resize: vertical;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
  line-height: 1.5;
}

.field-textarea:focus {
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.15);
}

.field-hint-card {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 11px;
  color: #92400e;
  margin-bottom: 14px;
}

.field-hint-card code {
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: 'SF Mono', monospace;
  font-size: 11px;
}

.field-hint-card p {
  margin: 0;
}

.field-radio-group {
  display: flex;
  gap: 8px;
}

.field-radio {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  color: #64748b;
}

.field-radio input { display: none; }

.field-radio.active {
  border-color: #818cf8;
  background: #eef2ff;
  color: #4338ca;
}

.compare-arrow {
  text-align: center;
  font-size: 20px;
  color: #94a3b8;
  padding: 4px 0;
}

/* ─── Severity Chips ─── */
.severity-options {
  display: flex;
  gap: 6px;
}

.severity-chip {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 10px 4px;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s;
  background: white;
}

.severity-chip input { display: none; }

.chip-icon { font-size: 18px; }
.chip-label { font-size: 11px; font-weight: 600; color: #64748b; }

.severity-chip.active.fail {
  border-color: #ef4444;
  background: #fef2f2;
}
.severity-chip.active.fail .chip-label { color: #dc2626; }

.severity-chip.active.warning {
  border-color: #f59e0b;
  background: #fffbeb;
}
.severity-chip.active.warning .chip-label { color: #d97706; }

.severity-chip.active.review {
  border-color: #8b5cf6;
  background: #f5f3ff;
}
.severity-chip.active.review .chip-label { color: #7c3aed; }

/* ─── Node Mode Selector ─── */
.node-mode-selector {
  display: flex;
  gap: 8px;
}

.node-mode-chip {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  border: 2px solid var(--el-border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.node-mode-chip:hover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.node-mode-chip.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.node-mode-chip .mode-icon {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-secondary);
}

.node-mode-chip.active .mode-icon {
  color: var(--el-color-primary);
}

.node-mode-chip .mode-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-regular);
}

.node-mode-chip.active .mode-text {
  color: var(--el-color-primary);
}

/* ─── Inspector Footer ─── */
.inspector-footer {
  padding: 12px 16px;
  border-top: 1px solid #f1f5f9;
}

.delete-node-btn {
  width: 100%;
  padding: 8px;
  font-size: 12px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: white;
  color: #ef4444;
  cursor: pointer;
  transition: all 0.15s;
}

.delete-node-btn:hover:not(:disabled) {
  background: #fef2f2;
}

.delete-node-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* ─── Empty Inspector ─── */
.inspector-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  padding: 24px;
}

.inspector-empty-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.inspector-empty p {
  margin: 0;
  font-size: 13px;
}

/* ─── HTTP Advanced Options ─── */
.collapsible-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  transition: background 0.15s;
}

.collapsible-header:hover {
  background: var(--el-fill-color);
}

.collapsible-header .caret {
  transition: transform 0.2s;
  font-size: 10px;
  color: var(--el-text-color-secondary);
}

.collapsible-header .caret.open {
  transform: rotate(90deg);
}

.collapsible-content {
  margin-top: 12px;
  padding-left: 8px;
}

.sub-field-group {
  margin-bottom: 16px;
}

.sub-field-group:last-child {
  margin-bottom: 0;
}

.key-value-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.key-value-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.key-value-row .key-input {
  flex: 1;
  min-width: 120px;
}

.key-value-row .value-input {
  flex: 2;
}

.key-value-row .remove-btn {
  width: 24px;
  height: 24px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: white;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  line-height: 1;
  transition: all 0.15s;
}

.key-value-row .remove-btn:hover:not(:disabled) {
  background: var(--el-color-danger-light-9);
  border-color: var(--el-color-danger-light-5);
  color: var(--el-color-danger);
}

.key-value-row .remove-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.add-btn {
  padding: 6px 12px;
  font-size: 12px;
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--el-color-primary);
  cursor: pointer;
  transition: all 0.15s;
  width: 100%;
}

.add-btn:hover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.required-mark {
  color: var(--el-color-danger);
  margin-left: 2px;
}

/* ─── Variables Panel ─── */
.variables-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.variables-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-fill-color-light) 100%);
  border-radius: 8px;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  transition: all 0.15s;
  border: 1px solid transparent;
}

.variables-header:hover {
  background: linear-gradient(135deg, var(--el-color-primary-light-8) 0%, var(--el-fill-color) 100%);
  border-color: var(--el-color-primary-light-5);
}

.variables-title {
  display: flex;
  align-items: center;
  gap: 6px;
}

.variables-count {
  font-size: 10px;
  background: var(--el-color-primary);
  color: white;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 500;
}

.variables-header .caret {
  transition: transform 0.2s;
  font-size: 10px;
  color: var(--el-text-color-secondary);
}

.variables-header .caret.open {
  transform: rotate(90deg);
}

.variables-content {
  margin-top: 12px;
  max-height: 300px;
  overflow-y: auto;
  padding: 2px;
}

.variable-group {
  margin-bottom: 16px;
}

.variable-group:last-child {
  margin-bottom: 0;
}

.variable-group-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--el-text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
  padding: 4px 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  display: inline-block;
}

.variable-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.variable-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
  border: 1px solid var(--el-border-color-lighter);
  position: relative;
  overflow: hidden;
}

.variable-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--el-color-primary-light-5);
  transition: width 0.2s ease;
}

.variable-item:hover {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
  transform: translateX(2px);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.variable-item:hover::before {
  width: 4px;
  background: var(--el-color-primary);
}

.variable-item:active {
  transform: translateX(3px) scale(0.99);
}

.variable-syntax {
  font-family: 'SF Mono', 'Fira Code', Consolas, monospace;
  font-size: 11px;
  color: var(--el-color-primary);
  font-weight: 600;
  background: var(--el-color-primary-light-9);
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid var(--el-color-primary-light-5);
  white-space: nowrap;
}

.variable-desc {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  flex: 1;
  line-height: 1.4;
}

.variable-insert-hint {
  font-size: 14px;
  color: var(--el-color-primary-light-3);
  opacity: 0;
  transition: opacity 0.2s;
}

.variable-item:hover .variable-insert-hint {
  opacity: 1;
}

.variables-footer-hint {
  margin-top: 12px;
  padding: 8px 12px;
  background: var(--el-color-success-light-9);
  border: 1px solid var(--el-color-success-light-5);
  border-radius: 6px;
  font-size: 11px;
  color: var(--el-color-success-dark-2);
  text-align: center;
}

/* Flash effect for variable insertion */
.variable-inserted-flash {
  animation: flashHighlight 0.3s ease;
}

@keyframes flashHighlight {
  0% {
    box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.7);
    border-color: var(--el-color-primary);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.3);
    border-color: var(--el-color-primary);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(64, 158, 255, 0);
  }
}

/* ─── Transitions ─── */
.slide-enter-active, .slide-leave-active {
  transition: all 0.2s ease;
  max-height: 500px;
  overflow: hidden;
}

.slide-enter-from, .slide-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
