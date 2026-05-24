<template>
  <div class="rule-graph-editor">
    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      :default-zoom="1.2"
      :min-zoom="0.5"
      :max-zoom="4"
      class="vue-flow-container"
      @connect="onConnect"
      @nodeClick="onNodeClick"
      @paneClick="onPaneClick"
    >
      <Background pattern-color="#aaa" gap="16" />
      <Controls />
      <Panel position="top-right" class="controls-panel">
        <button @click.prevent="addNode('text-llm')" class="btn btn-outline btn-sm m-1">
          + 文本大模型
        </button>
        <button @click.prevent="addNode('vision-llm')" class="btn btn-outline btn-sm m-1">
          + 视觉大模型
        </button>
        <button @click.prevent="addNode('keyword')" class="btn btn-outline btn-sm m-1">
          + 关键词提取
        </button>
        <button @click.prevent="resetGraph" class="btn btn-ghost btn-sm m-1">
          清空重置
        </button>
      </Panel>
    </VueFlow>

    <!-- Node Properties Editor Panel -->
    <div v-if="selectedNode" class="node-editor-panel">
      <h3 class="font-bold mb-2">算子配置 ({{ selectedNode.type || 'Custom' }})</h3>
      <div class="form-control w-full">
        <label class="label"><span class="label-text">节点名称</span></label>
        <input v-model="selectedNode.label" type="text" class="input input-bordered input-sm w-full" />
      </div>
      <div v-if="selectedNode.data" class="mt-2">
        <div class="form-control w-full" v-if="'prompt' in selectedNode.data">
          <label class="label"><span class="label-text">Prompt / 校验要求</span></label>
          <textarea v-model="selectedNode.data.prompt" class="textarea textarea-bordered textarea-sm w-full" rows="3"></textarea>
        </div>
        <div class="form-control w-full mt-2" v-if="'severity' in selectedNode.data">
          <label class="label"><span class="label-text">不满足时的严重级</span></label>
          <select v-model="selectedNode.data.severity" class="select select-bordered select-sm w-full">
            <option value="fail">拦截 (Fail)</option>
            <option value="warning">警告 (Warning)</option>
            <option value="review">需人工复核 (Review)</option>
          </select>
        </div>
      </div>
      <button @click="deleteSelectedNode" class="btn btn-error btn-sm w-full mt-4">删除节点</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { Panel } from '@vue-flow/core'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => null
  }
})

const emit = defineEmits(['update:modelValue'])

const { onConnect: onVueFlowConnect, addEdges } = useVueFlow()

const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const selectedNode = ref<any | null>(null)

// Create a generic starting node for the PDF input
const defaultNodes = [
  {
    id: 'node-input',
    type: 'input',
    label: '文档输入 (Document Context)',
    position: { x: 250, y: 50 },
    class: 'bg-primary text-white border-none rounded-lg shadow-lg font-bold p-3',
    deletable: false,
    data: {}
  },
  {
    id: 'node-output',
    type: 'output',
    label: '最终判定结果聚合',
    position: { x: 250, y: 400 },
    class: 'bg-success text-white border-none rounded-lg shadow-lg font-bold p-3',
    deletable: false,
    data: {}
  }
]

onMounted(() => {
  if (props.modelValue && props.modelValue.nodes && props.modelValue.nodes.length > 0) {
    nodes.value = props.modelValue.nodes
    edges.value = props.modelValue.edges || []
  } else {
    nodes.value = [...defaultNodes]
    edges.value = []
  }
})

// Watch for changes to update parent component (AST JSON)
watch(
  [nodes, edges],
  () => {
    emit('update:modelValue', {
      nodes: nodes.value,
      edges: edges.value
    })
  },
  { deep: true }
)

const onConnect = (connection: any) => {
  addEdges([
    {
      id: `e-${connection.source}-${connection.target}`,
      source: connection.source,
      target: connection.target,
      animated: true,
      style: { stroke: '#10b981', strokeWidth: 2 }
    }
  ])
}

const addNode = (type: string) => {
  const id = `node-${type}-${Date.now()}`
  let label = '未定义算子'
  let bgClass = 'bg-base-200'
  
  if (type === 'text-llm') {
    label = 'Text LLM 算子'
    bgClass = 'bg-blue-100 border-blue-500'
  } else if (type === 'vision-llm') {
    label = 'Vision LLM 算子'
    bgClass = 'bg-purple-100 border-purple-500'
  } else if (type === 'keyword') {
    label = '关键词校验'
    bgClass = 'bg-orange-100 border-orange-500'
  }

  nodes.value.push({
    id,
    label,
    position: { x: Math.random() * 200 + 100, y: Math.random() * 200 + 100 },
    class: `${bgClass} border-2 rounded p-2 text-sm shadow-md`,
    data: {
      prompt: '请检查...',
      severity: 'fail'
    }
  })
}

const onNodeClick = (event: any) => {
  selectedNode.value = event.node
}

const onPaneClick = () => {
  selectedNode.value = null
}

const deleteSelectedNode = () => {
  if (selectedNode.value && selectedNode.value.deletable !== false) {
    nodes.value = nodes.value.filter(n => n.id !== selectedNode.value.id)
    edges.value = edges.value.filter(e => e.source !== selectedNode.value.id && e.target !== selectedNode.value.id)
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
.rule-graph-editor {
  position: relative;
  width: 100%;
  height: 500px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background-color: #f9fafb;
}

.controls-panel {
  background: white;
  padding: 8px;
  border-radius: 8px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  max-width: 300px;
}

.node-editor-panel {
  position: absolute;
  bottom: 16px;
  right: 16px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  width: 280px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  z-index: 10;
}
</style>
