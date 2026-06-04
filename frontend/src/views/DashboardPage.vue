<template>
  <div class="dashboard-page" v-loading="loading">
    <!-- Header Title -->
    <div class="dashboard-header mb-4">
      <div class="title-section">
        <h2 class="dashboard-title">合规分析控制台</h2>
        <p class="dashboard-subtitle">平台校验质量、运行态势与高风险规则漏洞实时监控</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" plain :icon="Refresh" @click="fetchStats">
          刷新数据
        </el-button>
      </div>
    </div>

    <div v-if="stats" class="dashboard-content">
      <!-- 1. Top Metrics Cards -->
      <el-row :gutter="20" class="metrics-row mb-4">
        <el-col :xs="24" :sm="12" :md="6" :lg="4">
          <div class="glass-card metric-card">
            <div class="metric-icon total">📊</div>
            <div class="metric-info">
              <span class="metric-label">累计校验总量</span>
              <h3 class="metric-value">{{ stats.overview.total }}</h3>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :lg="4">
          <div class="glass-card metric-card">
            <div class="metric-icon completed">✓</div>
            <div class="metric-info">
              <span class="metric-label">合规通过量</span>
              <h3 class="metric-value text-pass">{{ stats.overview.completed }}</h3>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :lg="4">
          <div class="glass-card metric-card">
            <div class="metric-icon warning">⚠</div>
            <div class="metric-info">
              <span class="metric-label">合规预警量</span>
              <h3 class="metric-value text-warn">{{ stats.overview.warning }}</h3>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :lg="4">
          <div class="glass-card metric-card">
            <div class="metric-icon failed">✗</div>
            <div class="metric-info">
              <span class="metric-label">拦截不合规</span>
              <h3 class="metric-value text-fail">{{ stats.overview.failed }}</h3>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="12" :lg="4">
          <div class="glass-card metric-card">
            <div class="metric-icon review">🙋</div>
            <div class="metric-info">
              <span class="metric-label">待人工仲裁</span>
              <h3 class="metric-value text-review">{{ stats.overview.needs_review }}</h3>
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="12" :lg="4">
          <div class="glass-card metric-card pass-rate-card">
            <div class="pass-rate-gauge">
              <svg viewBox="0 0 36 36" class="circular-chart">
                <path class="circle-bg"
                  d="M18 2.0845
                    a 15.9155 15.9155 0 0 1 0 31.831
                    a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path class="circle"
                  :stroke-dasharray="stats.overview.pass_rate + ', 100'"
                  d="M18 2.0845
                    a 15.9155 15.9155 0 0 1 0 31.831
                    a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
              <div class="percentage">{{ stats.overview.pass_rate }}%</div>
            </div>
            <div class="metric-info text-center">
              <span class="metric-label">整体合规通过率</span>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 2. Trend Chart - Full Width -->
      <div class="mb-4">
        <div class="glass-card chart-card trend-full-card">
          <div class="card-header mb-3">
            <h3 class="card-title">📈 近两周校验态势变化趋势</h3>
            <div class="chart-legend">
              <span class="legend-item total"><span class="color-dot"></span>上传总量</span>
              <span class="legend-item passed"><span class="color-dot"></span>合规通过数</span>
            </div>
          </div>
          
          <div class="trend-chart-container">
            <svg viewBox="0 0 1000 280" preserveAspectRatio="xMidYMid meet" class="trend-svg" ref="svgRef">
              <defs>
                <linearGradient id="total-area-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#4285f4" stop-opacity="0.15"></stop>
                  <stop offset="100%" stop-color="#4285f4" stop-opacity="0.0"></stop>
                </linearGradient>
                <linearGradient id="passed-area-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#67c23a" stop-opacity="0.15"></stop>
                  <stop offset="100%" stop-color="#67c23a" stop-opacity="0.0"></stop>
                </linearGradient>
              </defs>

              <!-- Y-axis helper lines -->
              <line v-for="i in 4" :key="i" x1="40" :y1="50 + (i-1) * 60" x2="960" :y2="50 + (i-1) * 60" stroke="rgba(0,0,0,0.05)" stroke-dasharray="4" />

              <!-- Gradients Area Fill -->
              <path :d="totalAreaPath" fill="url(#total-area-grad)"></path>
              <path :d="passedAreaPath" fill="url(#passed-area-grad)"></path>

              <!-- Trend Lines -->
              <path :d="totalLinePath" fill="none" stroke="#4285f4" stroke-width="3" stroke-linecap="round"></path>
              <path :d="passedLinePath" fill="none" stroke="#67c23a" stroke-width="3" stroke-linecap="round"></path>

              <!-- Data Dots -->
              <g v-for="(pt, idx) in trendPoints" :key="'pts-' + idx">
                <circle :cx="pt.x" :cy="pt.totalY" r="4" fill="#ffffff" stroke="#4285f4" stroke-width="2" class="chart-dot" />
                <circle :cx="pt.x" :cy="pt.passedY" r="4" fill="#ffffff" stroke="#67c23a" stroke-width="2" class="chart-dot" />
              </g>

              <!-- X Axis Labels -->
              <text v-for="(pt, idx) in trendPoints" :key="'txt-' + idx" :x="pt.x" y="260" class="axis-label" text-anchor="middle">
                {{ formatDateLabel(pt.date) }}
              </text>
            </svg>
          </div>
        </div>
      </div>

      <!-- 3. Failing Rules - Full Width -->
      <div class="mb-4">
        <div class="glass-card chart-card rules-full-card">
          <div class="card-header mb-3">
            <h3 class="card-title">🔥 高频合规失效规则排行 (Top 5)</h3>
          </div>
          
          <div class="failing-rules-list">
            <div v-if="stats.top_failing_rules.length === 0" class="empty-failing-state">
              <el-empty description="暂无合规失败记录" :image-size="60" />
            </div>
            <div
              v-else
              v-for="(rule, idx) in stats.top_failing_rules"
              :key="idx"
              class="failing-rule-item"
            >
              <div class="rule-ranking-meta mb-1">
                <div class="rank-name-group">
                  <span class="rank-index" :class="'rank-' + (idx + 1)">{{ idx + 1 }}</span>
                  <span class="rule-name" :title="rule.rule_name">{{ rule.rule_name }}</span>
                </div>
                <span class="fail-count font-bold">{{ rule.count }} 次拦截</span>
              </div>
              <div class="progress-track">
                <div 
                  class="progress-fill" 
                  :style="{ width: (rule.count / maxFailCount * 100) + '%' }"
                  :class="'rank-fill-' + (idx + 1)"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { filesApi } from '@/api/files'

const loading = ref(true)
const stats = ref<any>(null)

const fetchStats = async () => {
  loading.value = true
  try {
    stats.value = await filesApi.getStatistics()
  } catch (e) {
    ElMessage.error('无法载入合规大屏统计数据')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStats()
})

// Max fail count for ranking progress bars normalization
const maxFailCount = computed(() => {
  if (!stats.value?.top_failing_rules || stats.value.top_failing_rules.length === 0) return 1
  return Math.max(...stats.value.top_failing_rules.map((r: any) => r.count), 1)
})

// Trend coordinates mapping (SVG dimensions: 600 width, 280 height)
const trendPoints = computed(() => {
  if (!stats.value?.trend || stats.value.trend.length === 0) return []
  const trend = stats.value.trend
  const paddingLeft = 40
  const paddingRight = 40
  const graphWidth = 1000 - paddingLeft - paddingRight
  const maxVal = Math.max(...trend.map((t: any) => t.total), 10)
  
  return trend.map((t: any, index: number) => {
    const x = paddingLeft + (index * (graphWidth / (trend.length - 1)))
    // Y points: height is 280, max y-height is 220, leaving 50px top padding, 60px bottom padding
    const totalY = 220 - (t.total / maxVal) * 170
    const passedY = 220 - (t.passed / maxVal) * 170
    return {
      date: t.date,
      total: t.total,
      passed: t.passed,
      x,
      totalY,
      passedY
    }
  })
})

const totalLinePath = computed(() => {
  const pts = trendPoints.value
  if (pts.length === 0) return ''
  return `M ${pts[0].x} ${pts[0].totalY} ` + pts.slice(1).map(p => `L ${p.x} ${p.totalY}`).join(' ')
})

const passedLinePath = computed(() => {
  const pts = trendPoints.value
  if (pts.length === 0) return ''
  return `M ${pts[0].x} ${pts[0].passedY} ` + pts.slice(1).map(p => `L ${p.x} ${p.passedY}`).join(' ')
})

const totalAreaPath = computed(() => {
  const pts = trendPoints.value
  if (pts.length === 0) return ''
  const first = pts[0]
  const last = pts[pts.length - 1]
  // Down to X axis (y = 230)
  return `M ${first.x} 230 L ${first.x} ${first.totalY} ` + pts.slice(1).map(p => `L ${p.x} ${p.totalY}`).join(' ') + ` L ${last.x} 230 Z`
})

const passedAreaPath = computed(() => {
  const pts = trendPoints.value
  if (pts.length === 0) return ''
  const first = pts[0]
  const last = pts[pts.length - 1]
  return `M ${first.x} 230 L ${first.x} ${first.passedY} ` + pts.slice(1).map(p => `L ${p.x} ${p.passedY}`).join(' ') + ` L ${last.x} 230 Z`
})

const formatDateLabel = (dateStr: string) => {
  if (!dateStr) return ''
  // Return MM-DD
  const parts = dateStr.split('-')
  if (parts.length >= 3) {
    return `${parts[1]}-${parts[2]}`
  }
  return dateStr
}
</script>

<style scoped>
.dashboard-page {
  padding: 8px 4px;
  min-height: calc(100vh - 120px);
}

.dashboard-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1f36;
  margin: 0 0 6px 0;
}

.dashboard-subtitle {
  font-size: 13px;
  color: #697386;
  margin: 0;
}

/* Glassmorphism layouts */
.glass-card {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.04);
  border-radius: 16px;
  padding: 20px;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.glass-card:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
}

/* Metric Card Layouts */
.metric-card {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 100px;
  padding: 16px 20px;
  margin-bottom: 12px;
}

.metric-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: bold;
  flex-shrink: 0;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}

.metric-icon.total { background: rgba(66, 133, 244, 0.1); color: #4285f4; }
.metric-icon.completed { background: rgba(76, 175, 80, 0.1); color: #4caf50; font-size: 24px; }
.metric-icon.warning { background: rgba(255, 152, 0, 0.1); color: #ff9800; }
.metric-icon.failed { background: rgba(244, 67, 54, 0.1); color: #f44336; }
.metric-icon.review { background: rgba(144, 164, 174, 0.15); color: #78909c; }

.metric-info {
  display: flex;
  flex-direction: column;
}

.metric-label {
  font-size: 11px;
  color: #8792a2;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  color: #1a1f36;
}

.text-pass { color: #67c23a; }
.text-warn { color: #e6a23c; }
.text-fail { color: #f56c6c; }
.text-review { color: #909399; }

/* Pass Rate dial circular animation */
.pass-rate-card {
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 12px 16px;
  min-height: 100px;
  margin-bottom: 12px;
}

.pass-rate-gauge {
  width: 50px;
  height: 50px;
  position: relative;
  margin-bottom: 6px;
}

.circular-chart {
  display: block;
  max-width: 100%;
  max-height: 100%;
}

.circle-bg {
  fill: none;
  stroke: rgba(0, 0, 0, 0.05);
  stroke-width: 3.2;
}

.circle {
  fill: none;
  stroke-width: 3.2;
  stroke-linecap: round;
  stroke: #67c23a;
  animation: progress 1.2s ease-out forwards;
}

@keyframes progress {
  0% { stroke-dasharray: 0 100; }
}

.pass-rate-gauge .percentage {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  font-weight: 700;
  color: #1a1f36;
}

/* Charts Panel Layouts */
.chart-card {
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.trend-full-card {
  height: 380px;
}

.rules-full-card {
  height: auto;
  min-height: 200px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: #1a1f36;
  margin: 0;
}

.chart-legend {
  display: flex;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  font-size: 11px;
  color: #697386;
  font-weight: 600;
}

.legend-item .color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  display: inline-block;
}

.legend-item.total .color-dot { background-color: #4285f4; }
.legend-item.passed .color-dot { background-color: #67c23a; }

/* SVG Graph styles */
.trend-chart-container {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.trend-svg {
  width: 100%;
  height: 100%;
  max-height: 300px;
}

.axis-label {
  font-size: 9px;
  fill: #8792a2;
  font-weight: 600;
}

.chart-dot {
  transition: r 0.15s ease;
  cursor: pointer;
}

.chart-dot:hover {
  r: 6;
}

/* Ranking progress list styles */
.failing-rules-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.failing-rules-list::-webkit-scrollbar {
  width: 4px;
}
.failing-rules-list::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.08);
  border-radius: 2px;
}

.failing-rule-item {
  display: flex;
  flex-direction: column;
}

.rule-ranking-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.rank-name-group {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 75%;
}

.rank-index {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  background: #f1f3f9;
  color: #697386;
  flex-shrink: 0;
}

.rank-index.rank-1 { background: rgba(244, 67, 54, 0.1); color: #f44336; }
.rank-index.rank-2 { background: rgba(255, 152, 0, 0.1); color: #ff9800; }
.rank-index.rank-3 { background: rgba(255, 193, 7, 0.1); color: #ffc107; }

.rule-name {
  color: #3c4257;
  font-weight: 600;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}

.fail-count {
  color: #697386;
  font-size: 12px;
}

.progress-track {
  width: 100%;
  height: 6px;
  background: rgba(0,0,0,0.03);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 4px;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.8s ease-out;
  background-color: #90a4ae;
}

.progress-fill.rank-fill-1 {
  background: linear-gradient(90deg, #e57373, #f44336);
}
.progress-fill.rank-fill-2 {
  background: linear-gradient(90deg, #ffb74d, #ff9800);
}
.progress-fill.rank-fill-3 {
  background: linear-gradient(90deg, #ffd54f, #ffc107);
}

.empty-failing-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
</style>
