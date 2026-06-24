<template>
  <div class="fullscreen-editor">
    <!-- Top Toolbar -->
    <div class="editor-toolbar">
      <div class="toolbar-left">
        <button class="toolbar-btn back-btn" @click="handleBack">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回</span>
        </button>
        <div class="toolbar-title">
          <span>{{ isEditMode ? '编辑规则' : '添加规则' }}</span>
          <span v-if="ruleForm.rule_name" class="rule-name-preview"> - {{ ruleForm.rule_name }}</span>
        </div>
      </div>

      <div class="toolbar-center">
        <button class="toolbar-btn" @click="ruleConfigVisible = true" :class="{ active: ruleConfigVisible }">
          <el-icon><Setting /></el-icon>
          <span>规则配置</span>
        </button>
        <button class="toolbar-btn" @click="saveDraft" :disabled="!hasChanges">
          <el-icon><DocumentCopy /></el-icon>
          <span>保存草稿</span>
        </button>
      </div>

      <div class="toolbar-right">
        <button class="toolbar-btn cancel-btn" @click="handleCancel">
          <span>取消</span>
        </button>
        <button class="toolbar-btn primary-btn" @click="handleSave" :disabled="saving">
          <el-icon><Check /></el-icon>
          <span>{{ saving ? '保存中...' : '保存' }}</span>
        </button>
      </div>
    </div>

    <!-- Main Editor Area -->
    <div class="editor-main">
      <!-- Collapsible Palette Sidebar -->
      <div class="palette-sidebar" :class="{ collapsed: !paletteExpanded }">
        <button class="palette-toggle" @click="paletteExpanded = !paletteExpanded" :title="paletteExpanded ? '收起算子面板' : '展开算子面板'">
          <span>{{ paletteExpanded ? '»' : '«' }}</span>
        </button>

        <div v-show="paletteExpanded" class="palette-content">
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
            <button class="dry-run-btn" @click="triggerDryRun">
              <span>⚡</span> 模拟测试
            </button>
            <button class="reset-btn" @click="resetGraph">
              <span>🗑️</span> 清空画布
            </button>
          </div>
        </div>
      </div>

      <!-- Vue Flow Canvas -->
      <div class="canvas-area" ref="canvasRef">
        <VueFlow
          v-if="isInitialized"
          v-model:nodes="nodes"
          v-model:edges="edges"
          :default-zoom="1"
          :min-zoom="0.1"
          :max-zoom="4"
          class="vue-flow-canvas"
          @connect="onConnect"
          @nodeClick="onNodeClick"
          @paneClick="onPaneClick"
          @paneReady="onPaneReady"
          :style="{ height: canvasHeight + 'px' }"
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
      </div>

      <!-- Right Sidebar (Inspector or Rule Config) -->
      <div class="right-sidebar" :class="{ open: rightPanelOpen }">
        <!-- Inspector Panel -->
        <div v-if="rightPanel === 'inspector' && selectedNode" class="inspector-panel">
          <div class="panel-header">
            <div class="panel-title-row">
              <span class="panel-icon" :style="{ background: getNodeMeta(selectedNode.data?.nodeType)?.color }">
                {{ getNodeMeta(selectedNode.data?.nodeType)?.icon || '⚙️' }}
              </span>
              <div class="panel-title-text">
                <h4>{{ getNodeMeta(selectedNode.data?.nodeType)?.label || '节点配置' }}</h4>
                <span class="panel-type-badge">{{ selectedNode.data?.nodeType || 'custom' }}</span>
              </div>
            </div>
            <button class="panel-close" @click="closeRightPanel">✕</button>
          </div>

          <div class="panel-body">
            <!-- Basic: Node Label -->
            <div class="field-group">
              <label class="field-label">显示名称</label>
              <input v-model="selectedNode.label" type="text" class="field-input" @focus="trackFocusedInput" />
            </div>

            <!-- Type-specific fields will be rendered here -->
            <!-- LLM Prompt -->
            <div v-if="selectedNode.data?.nodeType === 'text-llm' || selectedNode.data?.nodeType === 'vision-llm'">
              <div class="field-group">
                <label class="field-label">
                  Prompt 指令
                  <span class="field-hint">告诉大模型要检查什么</span>
                </label>
                <div class="field-input-with-var">
                  <textarea v-model="selectedNode.data.prompt" class="field-textarea" rows="4" placeholder="请检查该文档是否包含..." @focus="trackFocusedInput"></textarea>
                  <button class="var-trigger-btn" @click="openVarPopover('prompt')" title="插入变量">{x}</button>
                </div>
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

            <!-- Severity -->
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

            <!-- Variables Section -->
            <div class="variables-section">
              <div class="variables-header" @click="variablesExpanded = !variablesExpanded">
                <span class="variables-title">📋 可用变量</span>
                <span class="variables-count">{{ getTotalVariablesCount() }} 个</span>
                <span class="caret" :class="{ open: variablesExpanded }">▸</span>
              </div>
              <div v-show="variablesExpanded" class="variables-content">
                <div class="variables-search">
                  <input
                    v-model="varSearchQuery"
                    type="text"
                    class="variables-search-input"
                    placeholder="🔍 搜索变量..."
                  />
                </div>

                <div v-for="group in filteredVariables" :key="group.category" class="variable-group">
                  <div class="variable-group-title" :class="{ 'is-node-output': group.isNodeOutput }">
                    {{ group.icon }} {{ group.label }}
                    <span v-if="group.isNodeOutput" class="node-output-badge">上游节点</span>
                  </div>
                  <div class="variable-list">
                    <div
                      v-for="variable in group.variables"
                      :key="variable.name"
                      class="variable-item"
                      :class="{ 'is-node-var': group.isNodeOutput }"
                      @click="insertVariable(variable.name, variable)"
                      :title="'点击插入 ' + getVariableSyntax(variable.name, variable)"
                    >
                      <span class="variable-syntax" :class="{ 'node-syntax': group.isNodeOutput }">{{ getVariableSyntax(variable.name, variable) }}</span>
                      <span class="variable-desc">{{ variable.desc }}</span>
                      <span class="variable-insert-hint">→</span>
                    </div>
                  </div>
                </div>

                <div v-if="filteredVariables.length === 0" class="variables-empty">
                  <span>未找到匹配的变量</span>
                </div>

                <div class="variables-footer-hint" v-pre>
                  💡 系统变量: <code>{{var}}</code> · 上游节点: <code>{{#node.key#}}</code>
                </div>
              </div>
            </div>
          </div>

          <div class="panel-footer">
            <button class="delete-node-btn" @click="deleteSelectedNode" :disabled="selectedNode.deletable === false">
              🗑️ 删除该节点
            </button>
          </div>
        </div>

        <!-- Empty Inspector State -->
        <div v-else class="panel-empty">
          <span class="panel-empty-icon">🖱️</span>
          <p>点击画布中的节点</p>
          <p class="hint-sub">查看与编辑配置</p>
        </div>
      </div>
    </div>

    <!-- Rule Config Drawer -->
    <el-drawer
      v-model="ruleConfigVisible"
      title="规则配置"
      direction="rtl"
      size="350px"
      destroy-on-close
    >
      <div class="rule-config-form">
        <div class="form-group">
          <label class="form-label">规则名称</label>
          <el-input v-model="ruleForm.rule_name" placeholder="例如：文档必须包含授权签字" />
        </div>

        <div class="form-group">
          <label class="form-label">规则类型</label>
          <el-select v-model="ruleForm.rule_type" style="width: 100%">
            <el-option label="关键字 (Keyword)" value="keyword" />
            <el-option label="正则表达式 (Regex)" value="regex" />
            <el-option label="大模型分析 (LLM Prompt)" value="llm_prompt" />
            <el-option label="可视化节点图 (Logic Graph)" value="logic_graph" />
          </el-select>
        </div>

        <div class="form-group">
          <label class="form-label">严重级别</label>
          <el-radio-group v-model="ruleForm.severity">
            <el-radio value="fail">拦截</el-radio>
            <el-radio value="warning">警告</el-radio>
            <el-radio value="review">复核</el-radio>
            <el-radio value="reference">参考</el-radio>
          </el-radio-group>
        </div>

        <div class="form-group">
          <label class="form-label">生效条件</label>
          <el-input
            v-model="conditionInstitution"
            placeholder="选填。输入触发校验的机构名（如：CTI）"
          />
        </div>

        <div class="form-actions">
          <el-button @click="ruleConfigVisible = false">取消</el-button>
          <el-button type="primary" @click="ruleConfigVisible = false">确定</el-button>
        </div>
      </div>
    </el-drawer>

    <!-- Dry Run Dialog -->
    <el-dialog
      title="规则沙盒模拟测试 (Dry Run)"
      v-model="dryRunDialogVisible"
      width="650px"
      append-to-body
      destroy-on-close
    >
      <div class="dry-run-workspace" v-loading="dryRunning">
        <el-form label-width="100px">
          <el-form-item label="样例文件" required>
            <el-select
              v-model="selectedSampleFileId"
              placeholder="选择已上传的文件作为测试样例"
              style="width: 100%"
              filterable
              @focus="loadSampleFiles"
            >
              <el-option
                v-for="file in files"
                :key="file.id"
                :label="file.original_filename"
                :value="file.id"
              />
            </el-select>
          </el-form-item>
        </el-form>

        <div class="dry-run-console mt-4" v-if="dryRunLogs.length > 0 || dryRunResult">
          <div class="console-header">
            <span>💻 引擎执行日志</span>
            <el-tag v-if="dryRunResult" :type="dryRunResult.passed ? 'success' : 'danger'" size="small">
              {{ dryRunResult.passed ? '测试通过' : '测试拦截' }}
            </el-tag>
          </div>
          <div class="console-log-box" ref="consoleBoxRef">
            <div v-for="(log, idx) in dryRunLogs" :key="idx" class="console-line">
              <span class="log-time">[{{ formatTime(log.timestamp) }}]</span>
              <span class="log-message">{{ log.message }}</span>
            </div>

            <div v-if="dryRunResult" class="console-result-block" :class="{ passed: dryRunResult.passed }">
              <div class="font-bold">判决报告:</div>
              <div class="result-message">{{ dryRunResult.message }}</div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dryRunDialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="runSimulation" :loading="dryRunning" :disabled="!selectedSampleFileId">
            ⚡ 开始测试
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick, onUnmounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { ArrowLeft, Setting, DocumentCopy, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { filesApi } from '@/api/files'
import { dryRunRule, createRule, updateRule, getRules } from '@/api/rules'
import { getOperators, type OperatorRegistry } from '@/api/operators'
import { getErrorMessage } from '@/utils/formatters'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

// Types
interface NodeMeta {
  label: string
  icon: string
  color: string
  borderColor: string
  group: 'ai' | 'detect' | 'flow'
  defaultData: Record<string, any>
}

// Router
const router = useRouter()
const route = useRoute()

// Props from route
const ruleId = ref<string>(route.query.ruleId as string || '')
const categoryId = ref<string>(route.query.categoryId as string || '')
const isEditMode = computed(() => !!ruleId.value)

// State
const paletteExpanded = ref(true)
const ruleConfigVisible = ref(false)
const rightPanel = ref<'none' | 'inspector' | 'ruleConfig'>('none')
const rightPanelOpen = computed(() => rightPanel.value !== 'none')
const selectedNode = ref<any | null>(null)
const canvasHeight = ref(600)
const canvasRef = ref<HTMLElement | null>(null)

const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const isInitialized = ref(false)
const variablesExpanded = ref(true)
const lastFocusedInput = ref<HTMLInputElement | HTMLTextAreaElement | null>(null)
const saving = ref(false)
const hasChanges = ref(false)

const openGroups = reactive<Record<string, boolean>>({ ai: true, detect: true, flow: true })
const varSearchQuery = ref('')

const dryRunDialogVisible = ref(false)
const selectedSampleFileId = ref<string>('')
const dryRunning = ref(false)
const dryRunLogs = ref<{ timestamp: string; message: string }[]>([])
const dryRunResult = ref<any>(null)
const files = ref<any[]>([])
const consoleBoxRef = ref<HTMLElement | null>(null)

// Rule form
const ruleForm = ref<Record<string, any>>({
  rule_name: '',
  rule_type: 'logic_graph',
  severity: 'fail',
  logic_config: { nodes: [], edges: [] }
})

const conditionInstitution = ref('')

// Node Registry
const DEFAULT_NODE_REGISTRY: Record<string, NodeMeta> = {
  'text-llm':            { label: '文本大模型',     icon: '🧠', color: '#dbeafe', borderColor: '#3b82f6', group: 'ai',     defaultData: { prompt: '', operation_mode: 'verification', severity: 'fail', hasSeverity: true } },
  'vision-llm':          { label: '视觉大模型',     icon: '👁️', color: '#ede9fe', borderColor: '#8b5cf6', group: 'ai',     defaultData: { prompt: '', operation_mode: 'verification', severity: 'fail', hasSeverity: true } },
  'institution-sniffer': { label: '机构嗅探',       icon: '🏢', color: '#fef3c7', borderColor: '#f59e0b', group: 'ai',     defaultData: {} },
  'revision-check':      { label: '修订版本检查',   icon: '📋', color: '#e0f2fe', borderColor: '#0284c7', group: 'detect', defaultData: { maxRevisions: 1, allowIncrementalUpdates: false, severity: 'fail', hasSeverity: true } },
  'signature':           { label: '数字签名检查',   icon: '🔐', color: '#dcfce7', borderColor: '#22c55e', group: 'detect', defaultData: { expected_issuer: '', severity: 'fail', hasSeverity: true } },
  'qr-code':             { label: '二维码识别',     icon: '📱', color: '#e0e7ff', borderColor: '#6366f1', group: 'detect', defaultData: { severity: 'fail', hasSeverity: true } },
  'pdf-info':            { label: 'PDF 信息提取',   icon: '📄', color: '#f3e8ff', borderColor: '#a855f7', group: 'detect', defaultData: {} },
  'keyword':             { label: '关键词匹配',     icon: '🔤', color: '#ffedd5', borderColor: '#f97316', group: 'detect', defaultData: { severity: 'fail', hasSeverity: true } },
  'regex':               { label: '正则校验',       icon: '📐', color: '#fef9c3', borderColor: '#eab308', group: 'detect', defaultData: { severity: 'fail', hasSeverity: true } },
  'condition':           { label: '条件分支',       icon: '🔀', color: '#fce7f3', borderColor: '#ec4899', group: 'flow',   defaultData: {} },
  'http-call':           { label: 'HTTP 外部验证',  icon: '🌐', color: '#ecfdf5', borderColor: '#059669', group: 'flow',   defaultData: { url_template: '', http_method: 'GET', severity: 'fail', hasSeverity: true } },
  'data-compare':        { label: '数据比对',       icon: '⚖️', color: '#f0f9ff', borderColor: '#0284c7', group: 'flow',   defaultData: { severity: 'fail', hasSeverity: true } },
}

const loadedOperators = ref<OperatorRegistry[]>([])
const NODE_REGISTRY = computed<Record<string, NodeMeta>>(() => {
  const registry: Record<string, NodeMeta> = {}
  for (const op of loadedOperators.value) {
    registry[op.operator_key] = {
      label: op.display_name,
      icon: op.icon || DEFAULT_NODE_REGISTRY[op.operator_key]?.icon || '⚙️',
      color: op.color || DEFAULT_NODE_REGISTRY[op.operator_key]?.color || '#f3f4f6',
      borderColor: op.border_color || DEFAULT_NODE_REGISTRY[op.operator_key]?.borderColor || '#d1d5db',
      group: (op.group as 'ai' | 'detect' | 'flow') || DEFAULT_NODE_REGISTRY[op.operator_key]?.group || 'flow',
      defaultData: {
        severity: op.default_severity || 'fail',
        hasSeverity: op.supports_severity !== false,
        ...getDefaultDataForOperator(op.operator_key)
      }
    }
  }
  for (const [key, value] of Object.entries(DEFAULT_NODE_REGISTRY)) {
    if (!registry[key]) {
      registry[key] = value
    }
  }
  return registry
})

const severityOptions = [
  { value: 'fail', label: '拦截', icon: '🚫' },
  { value: 'warning', label: '警告', icon: '⚠️' },
  { value: 'review', label: '复核', icon: '🙋' },
]

const paletteGroups = computed(() => {
  return [
    {
      key: 'ai', icon: '🤖', label: 'AI 算子',
      items: Object.entries(NODE_REGISTRY.value).filter(([, m]) => m.group === 'ai').map(([type, m]) => ({ type, ...m })),
    },
    {
      key: 'detect', icon: '🔍', label: '检测算子',
      items: Object.entries(NODE_REGISTRY.value).filter(([, m]) => m.group === 'detect').map(([type, m]) => ({ type, ...m })),
    },
    {
      key: 'flow', icon: '🔀', label: '流程控制',
      items: Object.entries(NODE_REGISTRY.value).filter(([, m]) => m.group === 'flow').map(([type, m]) => ({ type, ...m })),
    },
  ]
})

// Output schemas
const FALLBACK_OUTPUT_SCHEMAS: Record<string, Record<string, { type: string; desc: string }>> = {
  'signature':           { signer_cn: { type: 'string', desc: '签署人名称' }, signature_valid: { type: 'boolean', desc: '签名是否有效' } },
  'qr-code':             { qr_content: { type: 'string', desc: '首个二维码内容' }, qr_codes: { type: 'array', desc: '所有二维码数据' } },
  'revision-check':      { is_tampered: { type: 'boolean', desc: '是否被篡改' }, revision_count: { type: 'integer', desc: '修订版本数' } },
  'institution-sniffer': { institution: { type: 'string', desc: '识别机构名称' } },
  'text-llm':            { passed: { type: 'boolean', desc: '验证是否通过' }, reason: { type: 'string', desc: '分析结论说明' } },
  'vision-llm':          { passed: { type: 'boolean', desc: '验证是否通过' }, reason: { type: 'string', desc: '分析结论说明' } },
  'http-call':           { status_code: { type: 'integer', desc: 'HTTP 状态码' }, response_json: { type: 'object', desc: 'JSON 响应对象' } },
}

const nodeOutputSchemas = computed(() => {
  const schemas: Record<string, Record<string, { type: string; desc: string }>> = { ...FALLBACK_OUTPUT_SCHEMAS }
  for (const op of loadedOperators.value) {
    const nodeType = op.operator_key
    const backendSchema = op.output_schema?.properties
    if (backendSchema && typeof backendSchema === 'object') {
      schemas[nodeType] = {}
      for (const [key, val] of Object.entries(backendSchema)) {
        const v = val as any
        schemas[nodeType][key] = { type: v.type || 'string', desc: v.description || key }
      }
    }
  }
  return schemas
})

// Methods
function getDefaultDataForOperator(operatorKey: string): Record<string, any> {
  const defaults: Record<string, any> = {
    'text-llm': { prompt: '', operation_mode: 'verification' },
    'vision-llm': { prompt: '', operation_mode: 'verification' },
    'http-call': { url_template: '', http_method: 'GET' },
  }
  return defaults[operatorKey] || {}
}

function getNodeMeta(nodeType?: string): NodeMeta | undefined {
  return nodeType ? NODE_REGISTRY.value[nodeType] : undefined
}

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

function toggleGroup(key: string) {
  openGroups[key] = !openGroups[key]
}

function getUpstreamNodes(nodeId: string): any[] {
  const visited = new Set<string>()
  const queue: string[] = [nodeId]
  const result: any[] = []

  while (queue.length > 0) {
    const currentId = queue.shift()!
    for (const edge of edges.value) {
      if (edge.target === currentId && !visited.has(edge.source)) {
        visited.add(edge.source)
        const sourceNode = nodes.value.find(n => n.id === edge.source)
        if (sourceNode) {
          result.push(sourceNode)
          queue.push(edge.source)
        }
      }
    }
  }
  return result
}

function getNodeOutputsList(node: any): { key: string; type: string; desc: string }[] {
  const nodeType = node.data?.nodeType
  if (!nodeType) return []
  const schema = nodeOutputSchemas.value[nodeType]
  if (!schema) return []
  return Object.entries(schema).map(([key, val]) => ({ key, ...val }))
}

const systemVariableGroups = [
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
]

const availableVariables = computed(() => {
  const groups: any[] = []
  for (const g of systemVariableGroups) {
    groups.push({ ...g })
  }

  if (selectedNode.value) {
    const upstreamNodes = getUpstreamNodes(selectedNode.value.id)
    for (const upNode of upstreamNodes) {
      const outputs = getNodeOutputsList(upNode)
      if (outputs.length === 0) continue

      const meta = getNodeMeta(upNode.data?.nodeType)
      groups.push({
        category: `node_${upNode.id}`,
        icon: meta?.icon || '📦',
        label: upNode.label || meta?.label || upNode.id,
        isNodeOutput: true,
        nodeId: upNode.id,
        variables: outputs.map(o => ({
          name: `${upNode.id}.${o.key}`,
          desc: `${o.desc} (${o.type})`,
          syntax: `{{#${upNode.id}.${o.key}#}}`
        }))
      })
    }
  }
  return groups
})

function getTotalVariablesCount() {
  return availableVariables.value.reduce((sum, group) => sum + group.variables.length, 0)
}

function getVariableSyntax(varName: string, variable?: any) {
  if (variable?.syntax) return variable.syntax
  return `{{${varName}}}`
}

function insertVariable(varName: string, variable?: any) {
  const targetInput = lastFocusedInput.value || document.activeElement as HTMLInputElement | HTMLTextAreaElement

  if (targetInput && (targetInput.tagName === 'INPUT' || targetInput.tagName === 'TEXTAREA')) {
    const variableSyntax = variable?.syntax || `{{${varName}}}`
    const start = targetInput.selectionStart ?? 0
    const end = targetInput.selectionEnd ?? 0
    const value = targetInput.value || ''

    const newValue = value.substring(0, start) + variableSyntax + value.substring(end)
    targetInput.value = newValue

    const newCursorPos = start + variableSyntax.length
    targetInput.setSelectionRange(newCursorPos, newCursorPos)
    targetInput.dispatchEvent(new Event('input', { bubbles: true }))
    targetInput.focus()
  }
}

function trackFocusedInput(event: FocusEvent) {
  const target = event.target as HTMLInputElement | HTMLTextAreaElement
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
    lastFocusedInput.value = target
  }
}

function openVarPopover(fieldName: string) {
  varSearchQuery.value = ''
}

const filteredVariables = computed(() => {
  const q = varSearchQuery.value.toLowerCase().trim()
  if (!q) return availableVariables.value
  return availableVariables.value
    .map(group => ({
      ...group,
      variables: group.variables.filter((v: any) =>
        v.name.toLowerCase().includes(q) || v.desc.toLowerCase().includes(q)
      )
    }))
    .filter((group: any) => group.variables.length > 0)
})

// Node operations
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
    const serialized: any = {
      id: node.id,
      type: node.type,
      label: node.label,
      position: node.position ? { x: Number(node.position.x), y: Number(node.position.y) } : { x: 0, y: 0 },
      data: node.data ? JSON.parse(JSON.stringify(node.data)) : {},
    }
    if (node.style) serialized.style = JSON.parse(JSON.stringify(node.style))
    if (node.class) serialized.class = node.class
    if (node.deletable !== undefined) serialized.deletable = node.deletable
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
    if (edge.animated !== undefined) serialized.animated = edge.animated
    return serialized
  })
}

let nodeCounter = 0
function addNode(type: string) {
  nodeCounter++
  const meta = NODE_REGISTRY.value[type]
  if (!meta) return

  const existingCount = nodes.value.filter(n => n.data?.nodeType === type).length
  const col = existingCount % 3
  const row = Math.floor(existingCount / 3)

  const defaultData = JSON.parse(JSON.stringify(meta.defaultData))
  const newNode = {
    id: `node-${type}-${Date.now()}-${nodeCounter}`,
    label: `${meta.icon} ${meta.label}`,
    position: { x: 80 + col * 220, y: 150 + row * 120 },
    class: 'rounded-lg p-2 text-sm shadow-md',
    style: { backgroundColor: meta.color, borderColor: meta.borderColor, borderWidth: '2px', borderStyle: 'solid' },
    data: { nodeType: type, ...defaultData },
  }

  updateNodeLabel(newNode)
  nodes.value.push(newNode)
  hasChanges.value = true
}

const onConnect = (connection: any) => {
  edges.value.push({
    id: `e-${connection.source}-${connection.target}`,
    source: connection.source,
    target: connection.target,
    animated: true,
    style: { stroke: '#10b981', strokeWidth: 2 },
  })
  hasChanges.value = true
}

const onNodeClick = (event: any) => {
  selectedNode.value = event.node
  rightPanel.value = 'inspector'
  lastFocusedInput.value = null
}

const onPaneClick = () => {
  selectedNode.value = null
  rightPanel.value = 'none'
  lastFocusedInput.value = null
}

const onPaneReady = (vueFlowInstance: any) => {
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
    rightPanel.value = 'none'
    hasChanges.value = true
  }
}

const resetGraph = () => {
  nodes.value = safeCloneNodes(defaultNodes)
  edges.value = []
  selectedNode.value = null
  rightPanel.value = 'none'
  hasChanges.value = true
}

function closeRightPanel() {
  selectedNode.value = null
  rightPanel.value = 'none'
}

// Toolbar actions
function handleBack() {
  if (hasChanges.value) {
    ElMessage.warning('您有未保存的更改，请先保存或取消')
    return
  }
  router.push({ name: 'Rules' })
}

function handleCancel() {
  router.push({ name: 'Rules' })
}

async function handleSave() {
  console.log('[FullscreenEditor] handleSave called', {
    rule_name: ruleForm.value.rule_name,
    nodes_count: nodes.value.length,
    edges_count: edges.value.length,
    category_id: categoryId.value
  })

  if (!ruleForm.value.rule_name) {
    console.warn('[FullscreenEditor] Missing rule_name')
    ElMessage.warning('请输入规则名称')
    ruleConfigVisible.value = true
    return
  }

  // Validate logic graph
  if (nodes.value.length <= 2) {
    console.warn('[FullscreenEditor] Not enough nodes:', nodes.value.length)
    ElMessage.warning('请至少添加一个算子节点')
    return
  }

  if (!categoryId.value) {
    console.error('[FullscreenEditor] Missing category_id')
    ElMessage.error('缺少分类信息，无法保存规则')
    return
  }

  saving.value = true
  try {
    // Build logic_config
    const logicConfig = {
      nodes: safeCloneNodes(nodes.value),
      edges: safeCloneEdges(edges.value)
    }

    if (conditionInstitution.value) {
      logicConfig.conditions = { institution: conditionInstitution.value }
    }

    // Prepare payload
    const payload: any = {
      category_id: categoryId.value,
      rule_name: ruleForm.value.rule_name,
      rule_type: 'logic_graph',
      rule_content: '', // Empty string for logic_graph type (required by backend)
      severity: ruleForm.value.severity || 'fail',
      logic_config: logicConfig,
      is_active: true
    }

    // Include id for updates
    if (ruleForm.value.id) {
      payload.id = ruleForm.value.id
    }

    console.log('[FullscreenEditor] Saving rule with payload:', payload)

    // Call API
    console.log('[FullscreenEditor] Calling API:', ruleForm.value.id ? 'updateRule' : 'createRule')
    if (ruleForm.value.id) {
      const result = await updateRule(ruleForm.value.id, payload)
      console.log('[FullscreenEditor] Update successful:', result)
      ElMessage.success('规则更新成功')
    } else {
      const result = await createRule(payload as any)
      console.log('[FullscreenEditor] Create successful:', result)
      ElMessage.success('规则创建成功')
    }

    hasChanges.value = false
    // Navigate back with refresh flag to trigger rules list reload
    console.log('[FullscreenEditor] Navigating back to rules page')
    router.push({ name: 'Rules', query: { refresh: 'true' } })
  } catch (error: unknown) {
    console.error('[FullscreenEditor] Save failed:', error)
    ElMessage.error(getErrorMessage(error, '保存失败'))
  } finally {
    saving.value = false
  }
}

function saveDraft() {
  // Save to localStorage as draft
  const draftData = {
    ruleForm: ruleForm.value,
    nodes: nodes.value,
    edges: edges.value,
    conditionInstitution: conditionInstitution.value,
    categoryId: categoryId.value,
    timestamp: new Date().toISOString()
  }
  localStorage.setItem('rule_draft_' + (ruleForm.value.id || 'new'), JSON.stringify(draftData))
  hasChanges.value = false
  ElMessage.success('草稿已保存到本地')
}

// Dry run
const loadSampleFiles = async () => {
  try {
    const res = await filesApi.list({ page: 1, page_size: 50 })
    files.value = res.items || []
  } catch (e) {
    console.error('Failed to load sample files:', e)
  }
}

const triggerDryRun = () => {
  dryRunDialogVisible.value = true
  selectedSampleFileId.value = ''
  dryRunLogs.value = []
  dryRunResult.value = null
  loadSampleFiles()
}

const runSimulation = async () => {
  if (!selectedSampleFileId.value) return

  dryRunning.value = true
  dryRunLogs.value = []
  dryRunResult.value = null

  try {
    const logicConfig = {
      nodes: safeCloneNodes(nodes.value),
      edges: safeCloneEdges(edges.value)
    }

    const res = await dryRunRule({
      file_id: selectedSampleFileId.value,
      rule_name: '可视化流程沙盒测试',
      rule_type: 'logic_graph',
      rule_content: '',
      severity: 'fail',
      logic_config: logicConfig
    })

    dryRunLogs.value = res.logs || []
    dryRunResult.value = res.result || null

    nextTick(() => {
      if (consoleBoxRef.value) {
        consoleBoxRef.value.scrollTop = consoleBoxRef.value.scrollHeight
      }
    })
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '模拟测试运行失败'))
  } finally {
    dryRunning.value = false
  }
}

const formatTime = (isoStr: string) => {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString('zh-CN', { hour12: false })
  } catch (e) {
    return isoStr
  }
}

// Keyboard shortcuts
const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    if (ruleConfigVisible.value) {
      ruleConfigVisible.value = false
    } else if (rightPanel.value !== 'none') {
      closeRightPanel()
    } else {
      handleCancel()
    }
  }
  if ((e.metaKey || e.ctrlKey) && e.key === 's') {
    e.preventDefault()
    handleSave()
  }
}

// Lifecycle
onMounted(async () => {
  try {
    const operators = await getOperators()
    loadedOperators.value = operators
    console.log('[FullscreenEditor] Loaded operators:', operators.length)
  } catch (error) {
    console.warn('[FullscreenEditor] Failed to load operators:', error)
  }

  try {
    if (ruleId.value) {
      // Load existing rule
      const rules = await getRules(categoryId.value)
      const existingRule = rules.find(r => r.id === ruleId.value)
      if (existingRule) {
        ruleForm.value = {
          id: existingRule.id,
          rule_name: existingRule.rule_name,
          rule_type: existingRule.rule_type,
          severity: existingRule.severity,
          logic_config: existingRule.logic_config || { nodes: [], edges: [] }
        }
        conditionInstitution.value = existingRule.logic_config?.conditions?.institution || ''

        if (existingRule.logic_config?.nodes) {
          nodes.value = safeCloneNodes(existingRule.logic_config.nodes)
        }
        if (existingRule.logic_config?.edges) {
          edges.value = safeCloneEdges(existingRule.logic_config.edges)
        }
      }
    } else {
      nodes.value = safeCloneNodes(defaultNodes)
      edges.value = []
    }

    setTimeout(() => {
      isInitialized.value = true
    }, 350)
  } catch (error) {
    console.error('[FullscreenEditor] Failed to initialize:', error)
    nodes.value = safeCloneNodes(defaultNodes)
    edges.value = []
    isInitialized.value = true
  }

  // Calculate canvas height
  if (canvasRef.value) {
    canvasHeight.value = canvasRef.value.clientHeight
  }

  // Add keyboard listener
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

watch([nodes, edges], () => {
  hasChanges.value = true
}, { deep: true })

watch(() => selectedNode.value?.data?.operation_mode, () => {
  if (selectedNode.value) {
    updateNodeLabel(selectedNode.value)
  }
})
</script>

<style scoped>
/* Fullscreen Editor Layout */
.fullscreen-editor {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  z-index: 9999;
}

/* Toolbar */
.editor-toolbar {
  height: 50px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
  gap: 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  color: #64748b;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.toolbar-btn:hover:not(:disabled) {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.toolbar-btn.active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #3b82f6;
}

.toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.primary-btn {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.primary-btn:hover:not(:disabled) {
  background: #2563eb;
}

.cancel-btn {
  color: #64748b;
}

.toolbar-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.rule-name-preview {
  font-weight: 400;
  color: #64748b;
}

/* Main Editor Area */
.editor-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* Palette Sidebar */
.palette-sidebar {
  width: 250px;
  min-width: 250px;
  background: white;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
  position: relative;
}

.palette-sidebar.collapsed {
  width: 40px;
  min-width: 40px;
}

.palette-toggle {
  position: absolute;
  top: 50%;
  right: -12px;
  transform: translateY(-50%);
  width: 24px;
  height: 48px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0 8px 8px 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #94a3b8;
  transition: all 0.2s;
  z-index: 10;
}

.palette-toggle:hover {
  color: #3b82f6;
  background: #f8fafc;
}

.palette-content {
  flex: 1;
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
  white-space: nowrap;
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
  white-space: nowrap;
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
  white-space: nowrap;
}

.palette-item:hover {
  background: #f0f4ff;
  transform: translateX(3px);
}

.palette-footer {
  margin-top: auto;
  padding: 12px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dry-run-btn, .reset-btn {
  padding: 8px;
  font-size: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.15s;
}

.dry-run-btn {
  background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
  border-color: #7dd3fc;
  color: #0369a1;
}

.dry-run-btn:hover {
  transform: translateY(-1px);
}

.reset-btn:hover {
  background: #fef2f2;
  border-color: #fecaca;
  color: #ef4444;
}

/* Canvas Area */
.canvas-area {
  flex: 1;
  position: relative;
  background: #f1f5f9;
  overflow: hidden;
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

/* Right Sidebar */
.right-sidebar {
  width: 0;
  min-width: 0;
  background: white;
  border-left: 1px solid #e5e7eb;
  transition: width 0.2s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.right-sidebar.open {
  width: 300px;
  min-width: 300px;
}

.panel-header {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.panel-title-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.panel-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.panel-title-text h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.panel-type-badge {
  font-size: 10px;
  color: #94a3b8;
  font-family: 'SF Mono', monospace;
}

.panel-close {
  background: none;
  border: none;
  font-size: 16px;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.panel-close:hover {
  background: #f1f5f9;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.panel-footer {
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
}

.delete-node-btn:hover:not(:disabled) {
  background: #fef2f2;
}

.panel-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  padding: 24px;
}

.panel-empty-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

/* Field Styles */
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
  transition: border-color 0.15s;
  box-sizing: border-box;
}

.field-input:focus {
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.15);
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
  transition: border-color 0.15s;
  box-sizing: border-box;
  line-height: 1.5;
}

.field-textarea:focus {
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.15);
}

.field-input-with-var {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.field-input-with-var .field-textarea {
  flex: 1;
}

.var-trigger-btn {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid #e0e7ff;
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
  color: #4f46e5;
  font-weight: 700;
  font-size: 12px;
  font-family: monospace;
  cursor: pointer;
  transition: all 0.2s ease;
}

.var-trigger-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(79, 70, 229, 0.2);
}

/* Severity Options */
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

.severity-chip.active.warning {
  border-color: #f59e0b;
  background: #fffbeb;
}

.severity-chip.active.review {
  border-color: #8b5cf6;
  background: #f5f3ff;
}

/* Node Mode Selector */
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

/* Variables Section */
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

.variable-group-title.is-node-output {
  color: #6366f1;
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.06) 0%, transparent 100%);
  border-left: 3px solid #818cf8;
  padding-left: 9px;
}

.node-output-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
  color: #4f46e5;
  font-weight: 600;
  margin-left: auto;
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

.variables-empty {
  padding: 16px;
  text-align: center;
  color: #9ca3af;
  font-size: 12px;
}

.variables-search {
  padding: 8px 12px 4px;
}

.variables-search-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 12px;
  background: #f9fafb;
  outline: none;
  box-sizing: border-box;
}

.variables-search-input:focus {
  border-color: #a5b4fc;
  background: white;
}

/* Rule Config Form */
.rule-config-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.form-actions {
  margin-top: auto;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* Dry Run Console */
.dry-run-console {
  background: #181818;
  border-radius: 12px;
  padding: 16px;
  color: #f8f8f2;
  font-family: monospace;
  font-size: 13px;
  border: 1px solid #282828;
}

.console-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #444;
  padding-bottom: 8px;
  margin-bottom: 12px;
  font-weight: bold;
}

.console-log-box {
  max-height: 250px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.console-line {
  line-height: 1.6;
}

.console-result-block {
  border-top: 1px solid #333;
  padding-top: 12px;
  margin-top: 12px;
}

.console-result-block.passed {
  color: #a6e22e;
}

.console-result-block:not(.passed) {
  color: #f92672;
}

.log-time {
  color: #75715e;
  margin-right: 8px;
}

/* Transitions */
.slide-enter-active, .slide-leave-active {
  transition: all 0.2s ease;
  max-height: 500px;
  overflow: hidden;
}

.slide-enter-from, .slide-leave-to {
  max-height: 0;
  opacity: 0;
}

.caret {
  transition: transform 0.2s;
  font-size: 10px;
}

.caret.open {
  transform: rotate(90deg);
}
</style>
