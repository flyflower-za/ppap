<template>
  <div class="graph-editor-workspace">
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
        v-model:nodes="nodes"
        v-model:edges="edges"
        :default-zoom="1"
        :min-zoom="0.3"
        :max-zoom="4"
        class="vue-flow-canvas"
        @connect="onConnect"
        @nodeClick="onNodeClick"
        @paneClick="onPaneClick"
      >
        <Background pattern-color="#d1d5db" gap="20" />
        <Controls position="bottom-left" />
        <MiniMap v-if="nodes.length > 4" />
      </VueFlow>

      <!-- Empty State Overlay -->
      <div v-if="nodes.length <= 2" class="canvas-empty-hint">
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
            <label class="field-label">显示名称</label>
            <input v-model="selectedNode.label" type="text" class="field-input" />
          </div>

          <!-- === Type-Specific Fields === -->

          <!-- LLM Prompt -->
          <div class="field-group" v-if="selectedNode.data?.nodeType === 'text-llm' || selectedNode.data?.nodeType === 'vision-llm'">
            <label class="field-label">
              Prompt 指令
              <span class="field-hint">告诉大模型要检查什么</span>
            </label>
            <textarea v-model="selectedNode.data.prompt" class="field-textarea" rows="5" placeholder="请检查该文档是否包含..."></textarea>
          </div>

          <!-- Keyword -->
          <div class="field-group" v-if="selectedNode.data?.nodeType === 'keyword'">
            <label class="field-label">
              关键词列表
              <span class="field-hint">逗号分隔，命中任一即通过</span>
            </label>
            <input v-model="selectedNode.data.keywords" type="text" class="field-input" placeholder="华测,CTI,CNAS" />
          </div>

          <!-- Regex -->
          <div class="field-group" v-if="selectedNode.data?.nodeType === 'regex'">
            <label class="field-label">
              正则表达式
              <span class="field-hint">匹配内容将写入上下文</span>
            </label>
            <input v-model="selectedNode.data.pattern" type="text" class="field-input mono" placeholder="^报告编号[：:]\s*\w+" />
          </div>

          <!-- Signature -->
          <div class="field-group" v-if="selectedNode.data?.nodeType === 'signature'">
            <label class="field-label">
              预期签发者
              <span class="field-hint">留空则仅检查签名存在性</span>
            </label>
            <input v-model="selectedNode.data.expected_issuer" type="text" class="field-input" placeholder="Centre Testing International" />
          </div>

          <!-- Condition -->
          <div v-if="selectedNode.data?.nodeType === 'condition'">
            <div class="field-group">
              <label class="field-label">
                条件表达式
                <span class="field-hint">满足条件走 ✅ 分支</span>
              </label>
              <input v-model="selectedNode.data.expression" type="text" class="field-input mono" placeholder="institution == 'CTI'" />
            </div>
            <div class="field-hint-card">
              <p>💡 可用变量：<code>institution</code>, <code>has_signature</code>, <code>qr_count</code>, <code>page_count</code></p>
            </div>
          </div>

          <!-- HTTP Call -->
          <div v-if="selectedNode.data?.nodeType === 'http-call'">
            <div class="field-group">
              <label class="field-label">请求 URL 模板</label>
              <input v-model="selectedNode.data.url_template" type="text" class="field-input mono" placeholder="https://verify.example.com/check?code={{qr_content}}" />
            </div>
            <div class="field-group">
              <label class="field-label">HTTP 方法</label>
              <div class="field-radio-group">
                <label class="field-radio" :class="{ active: selectedNode.data.http_method === 'GET' }">
                  <input type="radio" v-model="selectedNode.data.http_method" value="GET" /> GET
                </label>
                <label class="field-radio" :class="{ active: selectedNode.data.http_method === 'POST' }">
                  <input type="radio" v-model="selectedNode.data.http_method" value="POST" /> POST
                </label>
              </div>
            </div>
          </div>

          <!-- Data Compare -->
          <div v-if="selectedNode.data?.nodeType === 'data-compare'">
            <div class="field-group">
              <label class="field-label">比较源 A</label>
              <input v-model="selectedNode.data.source_a" type="text" class="field-input mono" placeholder="qr_report_id" />
            </div>
            <div class="compare-arrow">⇅</div>
            <div class="field-group">
              <label class="field-label">比较源 B</label>
              <input v-model="selectedNode.data.source_b" type="text" class="field-input mono" placeholder="text_report_id" />
            </div>
          </div>

          <!-- Vote -->
          <div class="field-group" v-if="selectedNode.data?.nodeType === 'vote'">
            <label class="field-label">
              最低通过数 (N/M)
              <span class="field-hint">上游连入节点中，至少 N 个通过</span>
            </label>
            <input v-model.number="selectedNode.data.min_pass" type="number" min="1" class="field-input" style="width: 80px;" />
          </div>

          <!-- Human Review -->
          <div class="field-group" v-if="selectedNode.data?.nodeType === 'human-review'">
            <label class="field-label">
              审核提示语
              <span class="field-hint">展示给审核人员的说明</span>
            </label>
            <textarea v-model="selectedNode.data.review_hint" class="field-textarea" rows="3" placeholder="请人工核查签名信息..."></textarea>
          </div>

          <!-- === Common: Severity === -->
          <div class="field-group" v-if="selectedNode.data?.hasSeverity">
            <label class="field-label">不通过时的处理</label>
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
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { Panel } from '@vue-flow/core'

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
  'text-llm':            { label: '文本大模型',     icon: '🧠', color: '#dbeafe', borderColor: '#3b82f6', group: 'ai',     defaultData: { prompt: '', severity: 'fail', hasSeverity: true } },
  'vision-llm':          { label: '视觉大模型',     icon: '👁️', color: '#ede9fe', borderColor: '#8b5cf6', group: 'ai',     defaultData: { prompt: '', severity: 'fail', hasSeverity: true } },
  'institution-sniffer': { label: '机构嗅探',       icon: '🏢', color: '#fef3c7', borderColor: '#f59e0b', group: 'ai',     defaultData: {} },
  'signature':           { label: '数字签名检查',   icon: '🔐', color: '#dcfce7', borderColor: '#22c55e', group: 'detect', defaultData: { expected_issuer: '', severity: 'fail', hasSeverity: true } },
  'qr-code':             { label: '二维码识别',     icon: '📱', color: '#e0e7ff', borderColor: '#6366f1', group: 'detect', defaultData: { severity: 'fail', hasSeverity: true } },
  'pdf-info':            { label: 'PDF 信息提取',   icon: '📄', color: '#f3e8ff', borderColor: '#a855f7', group: 'detect', defaultData: {} },
  'keyword':             { label: '关键词匹配',     icon: '🔤', color: '#ffedd5', borderColor: '#f97316', group: 'detect', defaultData: { keywords: '', severity: 'fail', hasSeverity: true } },
  'regex':               { label: '正则校验',       icon: '📐', color: '#fef9c3', borderColor: '#eab308', group: 'detect', defaultData: { pattern: '', severity: 'fail', hasSeverity: true } },
  'condition':           { label: '条件分支',       icon: '🔀', color: '#fce7f3', borderColor: '#ec4899', group: 'flow',   defaultData: { expression: '' } },
  'human-review':        { label: '人工审核点',     icon: '🙋', color: '#fff7ed', borderColor: '#ea580c', group: 'flow',   defaultData: { review_hint: '' } },
  'http-call':           { label: 'HTTP 外部验证',  icon: '🌐', color: '#ecfdf5', borderColor: '#059669', group: 'flow',   defaultData: { url_template: '', http_method: 'GET', severity: 'fail', hasSeverity: true } },
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

// ─── Props & Emit ───
const props = defineProps({ modelValue: { type: Object, default: () => null } })
const emit = defineEmits(['update:modelValue'])
const { addEdges } = useVueFlow()

const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const selectedNode = ref<any | null>(null)

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

onMounted(() => {
  if (props.modelValue?.nodes?.length > 0) {
    nodes.value = props.modelValue.nodes
    edges.value = props.modelValue.edges || []
  } else {
    nodes.value = [...defaultNodes]
    edges.value = []
  }
})

watch([nodes, edges], () => {
  emit('update:modelValue', { nodes: nodes.value, edges: edges.value })
}, { deep: true })

const onConnect = (connection: any) => {
  addEdges([{
    id: `e-${connection.source}-${connection.target}`,
    source: connection.source, target: connection.target,
    animated: true, style: { stroke: '#10b981', strokeWidth: 2 },
  }])
}

let nodeCounter = 0
const addNode = (type: string) => {
  nodeCounter++
  const meta = NODE_REGISTRY[type]
  if (!meta) return

  const existingCount = nodes.value.filter(n => n.data?.nodeType === type).length
  const col = existingCount % 3
  const row = Math.floor(existingCount / 3)

  nodes.value.push({
    id: `node-${type}-${Date.now()}-${nodeCounter}`,
    label: `${meta.icon} ${meta.label}`,
    position: { x: 80 + col * 220, y: 150 + row * 120 },
    class: 'rounded-lg p-2 text-sm shadow-md',
    style: { backgroundColor: meta.color, borderColor: meta.borderColor, borderWidth: '2px', borderStyle: 'solid' },
    data: { nodeType: type, ...JSON.parse(JSON.stringify(meta.defaultData)) },
  })
}

const onNodeClick = (event: any) => { selectedNode.value = event.node }
const onPaneClick = () => { selectedNode.value = null }

const deleteSelectedNode = () => {
  if (selectedNode.value && selectedNode.value.deletable !== false) {
    const id = selectedNode.value.id
    nodes.value = nodes.value.filter(n => n.id !== id)
    edges.value = edges.value.filter(e => e.source !== id && e.target !== id)
    selectedNode.value = null
  }
}

const resetGraph = () => {
  nodes.value = [...defaultNodes]
  edges.value = []
  selectedNode.value = null
}
</script>

<style scoped>
/* ─── Layout ─── */
.graph-editor-workspace {
  display: flex;
  width: 100%;
  height: 600px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
  background: #f8fafc;
  transition: height 0.3s ease;
}

:global(.el-dialog.is-fullscreen) .graph-editor-workspace {
  height: calc(100vh - 170px);
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
