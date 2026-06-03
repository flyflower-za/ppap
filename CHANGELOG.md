# Changelog

All notable changes to the PPAP project will be documented in this file.

## [2026-06-03] - 平台核心功能升级与响应式文件列表优化

### 功能描述
- **AI置信度与人机协同审核（HITL）**：当智能校验引擎的大模型置信度偏低（< 85%）或触发高风险拦截时，系统自动将文件状态挂起为“需人工仲裁”。在文件详情页提供显眼的警告 Banner、置信度徽章，并允许管理员一键“人工放行”或“确认驳回”，同时在执行流水中记录带有决策人和备注的完整仲裁审计链。
- **可视化文档差异比对高亮**：对 `DocumentDiffOperator` 算子输出的文本变化，提供类似 GitHub 的红绿差异高亮卡片。清晰显示文本的删除线（红色背景）与新增项（绿色背景），并支持差异位置一键定位及折叠。
- **规则版本控制与沙盒模拟测试**：
  - 规则保存与编辑时自动快照版本历史，在规则配置页新增“版本历史”抽屉，支持将规则一键回滚至任意历史版本。
  - 在可视化流程图编辑器中集成“沙盒模拟测试（Dry Run）”，允许选择已上传的 PDF 样例文件并在内存中触发临时校验，在底部的虚拟控制台中实时打印算子执行日志与拦截判定结果，而不对数据库产生实质修改。
- **合规分析仪表盘（业务大屏）**：新增“业务大屏（Dashboard）”，集成合规概览、待办工单、趋势图表及高频失败规则统计。通过流畅 of SVG 仪表盘和极简的玻璃微动特效，直观呈现平台处理性能与通过率。
- **文件列表与附件响应式截断优化**：针对任务中心、历史审计中心、沙盒页面的超长 PDF 文件名，移除硬编码的限宽限制，采用弹性 Flex 挤压配合 `text-overflow: ellipsis` 方式进行自适应截断，保障大屏下的美观与文字完整性。

### 详细修改记录

#### 1. 前端 - 核心功能页面与组件开发
- **文件详情页** ([FileDetailPage.vue](file:///c:/Projects/git/ppap/frontend/src/views/FileDetailPage.vue)):
  - 引入了人工仲裁（HITL）看板，支持直接触发 `approve` 或 `reject` 手工审计逻辑。
  - 对低置信度（< 85%）的规则卡片在右侧置信度徽章处进行高亮预警并关联警告图标。
  - 增加了基于红绿背景和删除/新增标识的文档文本差异比对（Diff）可视化渲染面板，支持折叠与自适应换行。
- **规则图编辑器** ([RuleGraphEditor.vue](file:///c:/Projects/git/ppap/frontend/src/components/RuleGraphEditor.vue)):
  - 增加了“沙盒模拟测试（Dry Run）”按钮与对话框，支持从历史上传中选择样例文件并触发内存级沙盒模拟。
  - 增加了仿终端控制台，配合微动画实时输出节点执行轨迹、置信度以及最终判定日志。
- **规则列表与分类** ([RulesPage.vue](file:///c:/Projects/git/ppap/frontend/src/views/RulesPage.vue)):
  - 添加了“历史”版本按钮，点击可唤出规则版本轨迹抽屉。
  - 渲染了时间线列表，支持选择任一快照将当前规则一键回滚。
- **合规大屏** ([DashboardPage.vue](file:///c:/Projects/git/ppap/frontend/src/views/DashboardPage.vue)):
  - 新增合规分析页面，包含总文件数、平均通过率、待审核人工工单及规则拦截 Top 排行榜。
  - 使用自适应 SVG 渲染通过率环形图、周校验趋势折线图以及异常排行柱状图，添加极简科技感卡片阴影。
- **响应式文件列表样式优化**:
  - [TaskCenterPage.vue](file:///c:/Projects/git/ppap/frontend/src/views/TaskCenterPage.vue)：修改 `.item-name-info` 为自适应宽度，完美支持任意超长文件名，并移除硬编码的 200px 限制。
  - [HistoryPage.vue](file:///c:/Projects/git/ppap/frontend/src/views/HistoryPage.vue)：为 `.file-name-cell` 增加弹性缩放限制，并允许 `.file-title-text` 进行 ellipsis 截断。
  - [ModuleSandboxPage.vue](file:///c:/Projects/git/ppap/frontend/src/views/ModuleSandboxPage.vue)：修改 `el-upload-list__item-name` 的 `max-width` 为 `100%`，防止长文件名溢出。

#### 2. 后端 - API 接口与版本回滚引擎
- **规则版本控制系统** ([rule_version.py](file:///c:/Projects/git/ppap/backend/app/models/rule_version.py)):
  - 建立了 `RuleVersion` 的 SQLAlchemy 映射模型，对名称、类型、严重性、逻辑图配置及内容进行多版本归档。
  - 编写并执行了 Alembic 迁移脚本 `10dd2dcf16f5`，安全在 PostgreSQL 中创建版本数据表。
- **规则相关 API 路由** ([rules.py](file:///c:/Projects/git/ppap/backend/app/api/rules.py)):
  - 实现了 `GET /api/v1/rules/{id}/versions` 路由获取特定规则的版本树。
  - 实现了 `POST /api/v1/rules/{id}/rollback` 进行指定的历史版本回滚。
  - 实现了 `POST /api/v1/rules/dry-run` 内存沙盒计算接口，执行无痕化模拟校验并按日志节点形式向前端返回运行堆栈。
- **合规统计 API 路由** ([files.py](file:///c:/Projects/git/ppap/backend/app/api/files.py)):
  - 实现了 `GET /api/v1/files/statistics`，提供全局统计和各指标曲线的基础数据。

---

## [2026-06-03] - 统一设置页面样式与按钮布局优化

### 功能描述
- 统一 LDAP/SSO 配置选项页与 SMTP 配置选项页的视觉风格，将表单对齐方式统一调整为左侧对齐（`label-width="160px"`）。
- 移除自定义的渐变色嵌套卡片（`config-section`）风格，改用标准的 `<el-divider>` 进行区域分隔，简化表单结构。
- 修复“默认用户角色”（Default User Role）单选按钮组在垂直方向排列时的边框重叠及挤压遮挡缺陷。
- 对齐 LDAP/SSO 操作按钮的配色与排列顺序至 SMTP 风格：测试连接（Primary 蓝色，在 LDAP 禁用时置灰）位于最左侧，保存配置（Success 绿色）位于中间，重置位于最右侧。
- 优化本地前端开发与部署流程，在 `docker-compose.yml` 中新增本地 `frontend/dist` 静态资源目录映射挂载，实现本地秒级构建热部署，并解决 Docker 官方源拉取超时的部署阻碍。

### 详细修改记录

#### 1. 前端 - 页面布局与样式重构
**文件路径**: [SettingsPage.vue](file:///c:/Projects/git/ppap/frontend/src/views/SettingsPage.vue)
- 将表单标签属性由 `label-position="top"` 改为 `label-width="160px"`。
- 将 nested `config-section` card blocks 替换为标准的 `<el-divider>`。
- 将自定义 `role-selector` 单选卡片重构为带有 `.vertical-radio-group` 的标准 `el-radio-group`。
- 重排底部按钮顺序及配色：
  - 测试连接：`type="primary"`，`:disabled="!ldapConfig.ldap_enabled"`
  - 保存配置：`type="success"`
  - 重置：普通按钮
- 清理 CSS 中已废弃的自定义 LDAP 卡片样式、表格栅格等，添加 `.vertical-radio-group` 与 `.radio-tip` 样式。

---

#### 2. 部署 - 本地静态目录挂载优化
**文件路径**: [docker-compose.yml](file:///c:/Projects/git/ppap/deploy/docker-compose.yml)
- 在 `frontend` 容器服务中新增挂载卷映射 `- ../frontend/dist:/usr/share/nginx/html:ro`。
- 允许前端在宿主机使用 `npm run build` 产出静态包后，容器实时挂载更新，从而规避拉取基础镜像可能导致的网络报错。

---

### 影响范围
- ✅ 前端设置页面
- ✅ 部署服务（Docker 挂载配置）
- ❌ 无数据库变更
- ❌ 无破坏性变更

---

## [2026-05-27] - 变量面板功能

### 功能描述
- 在规则图编辑器中添加变量面板，显示所有可用的数据源变量
- 支持点击变量自动插入到输入框光标位置
- 按节点类型分组显示变量，便于查找

### 详细修改记录

#### 1. 后端 - 数据扁平化支持
**文件路径**: `/Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/app/engine/core.py`
**修改时间**: 2026-05-27

**新增方法**: `_flatten_shared_state(context)`
```python
def _flatten_shared_state(self, context: DocumentContext) -> None:
    """
    Flatten commonly used nested values from shared_state for easier variable access.
    This makes it simpler to reference things like signer_cn without full path.
    """
```

**扁平化的变量**:
- `signer_cn` - 从 `digital_signatures.signatures[0].signer_cn` 提取
- `signature_valid` - 从 `digital_signatures.signatures[0].integrity` 提取
- `signature_expired` - 从 `digital_signatures.signatures[0].expired` 提取
- `is_tampered` - 从 `pdf_revisions.is_tampered_after_sign` 提取
- `revision_count` - 从 `pdf_revisions.revision_count` 提取

**调用时机**:
- Stage 1 预分类算子执行后
- Stage 2 深度算子执行后
- 签名验证节点执行后
- 修订检查节点执行后

---

#### 2. 前端 - 变量面板 UI
**文件路径**: `/Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/frontend/src/components/RuleGraphEditor.vue`
**修改时间**: 2026-05-27

**新增数据结构**:
```typescript
const availableVariables = [
  { category: 'system', icon: '⚙️', label: '系统变量', variables: [...] },
  { category: 'qr', icon: '📱', label: '二维码', variables: [...] },
  { category: 'signature', icon: '🔐', label: '数字签名', variables: [...] },
  { category: 'pdf', icon: '📄', label: 'PDF 元数据', variables: [...] },
  { category: 'extract', icon: '📤', label: '提取数据', variables: [...] },
]
```

**新增方法**:
- `getTotalVariablesCount()` - 计算变量总数
- `insertVariable(varName)` - 点击插入变量到输入框，支持光标位置插入和闪烁动画反馈

**UI 特性**:
- 可折叠面板，默认展开
- 显示变量总数统计
- 悬停效果和点击动画
- 变量语法显示为 `{{variable_name}}`

**可用变量列表** (共18个):

| 分类 | 变量名 | 描述 |
|-----|-------|------|
| ⚙️ 系统变量 | `institution` | 发证机构名称 |
| | `page_count` | PDF 页数 |
| | `full_text` | 完整文本内容 |
| 📱 二维码 | `qr_content` | 第一个二维码内容 |
| | `qr_codes` | 所有二维码数据数组 |
| 🔐 数字签名 | `digital_signatures` | 签名完整数据 |
| | `signer_cn` | 签署人通用名 |
| | `signature_valid` | 签名是否有效 |
| 📄 PDF 元数据 | `pdf_info` | PDF 完整信息 |
| | `is_tampered` | 是否被篡改 |
| | `revision_count` | 修订版本数 |
| 📤 提取数据 | `extracted_report_number` | 报告编号 (提取模式) |
| | `extracted_verification_code` | 校验码 (提取模式) |
| | `extracted_tables` | 提取的表格数据 |
| | `llm_semantic_analysis` | LLM 语义分析结果 |
| | `vision_analysis` | 视觉分析结果 |
| | `detected_stamps` | 检测到的印章 |
| | `diff_results` | 文档比对结果 |

### 使用方法
1. 在规则图编辑器中选中一个节点
2. 在右侧配置面板底部找到"📋 可用变量"区域
3. 点击任意变量即可插入到当前焦点输入框
4. 变量以 `{{变量名}}` 的格式插入

### 影响范围
- ✅ 前端规则图编辑器
- ✅ 后端数据流处理
- ❌ 无数据库变更
- ❌ 无破坏性变更

---

## [2026-05-25] - 端口配置优化

### 问题描述
- 系统中存在端口冲突，8000端口已被其他服务占用
- 需要调整PPAP项目的端口配置以避免冲突

### 详细修改记录

#### 1. 前端开发服务器代理配置
**文件路径**: `/home/zhouao2/ppap/frontend/vite.config.ts`
**修改位置**: 第17行，proxy配置段
**修改时间**: 2026-05-25 10:30

**代码对比**:
```diff
server: {
  port: 5173,
  proxy: {
    '/api': {
-     target: 'http://localhost:8000',
+     target: 'http://localhost:31234',
      changeOrigin: true,
      ws: true,
    },
  },
}
```

**原因**: 将前端代理指向新的后端端口，避免与占用的8000端口冲突

---

#### 2. Docker端口映射配置
**文件路径**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
**修改位置**: 第74行，backend服务配置段
**修改时间**: 2026-05-25 10:39

**代码对比**:
```diff
backend:
  build:
    context: ../backend
    dockerfile: Dockerfile
  container_name: ppap-backend
  restart: unless-stopped
  environment:
    DATABASE_URL: postgresql+asyncpg://ppap:ppap123@postgres:5432/ppap
    REDIS_URL: redis://redis:6379/0
    MINIO_ENDPOINT: minio:9000
    MINIO_SECURE: "false"
    SECRET_KEY: ${SECRET_KEY:-change-this-in-production}
    CORS_ORIGINS: '["http://localhost:3000","http://localhost:5173"]'
  ports:
-   - "31234:8000"
+   - "31234:31234"
  depends_on:
```

**原因**: 保持Docker容器内外端口一致，与应用配置中的PORT=31234匹配

---

#### 3. 部署脚本端口配置
**文件路径**: `/home/zhouao2/ppap/deploy.sh`
**修改位置**: 第88行，部署完成提示信息段
**修改时间**: 2026-05-25 10:45

**代码对比**:
```diff
echo -e "=== Deployment Completed Successfully ===${NC}"
echo -e "Access the services at:"
echo -e "  - Frontend UI:   http://localhost"
- echo -e "  - Backend API:   http://localhost:8000/docs"
+ echo -e "  - Backend API:   http://localhost:31234/docs"
echo -e "  - MinIO Console: http://localhost:9001 (minioadmin / minioadmin)"
```

**原因**: 更新部署脚本中的API文档地址，确保显示正确的后端端口

---

#### 4. Docker容器环境变量配置 (修复)
**文件路径**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
**修改位置**: 第67行，backend服务environment配置段
**修改时间**: 2026-05-25 10:50
**问题**: Docker容器缺少PORT环境变量，导致后端服务仍监听8000端口

**代码对比**:
```diff
backend:
  build:
    context: ../backend
    dockerfile: Dockerfile
  container_name: ppap-backend
  restart: unless-stopped
  environment:
+   PORT: "31234"
    DATABASE_URL: postgresql+asyncpg://ppap:ppap123@postgres:5432/ppap
    REDIS_URL: redis://redis:6379/0
    MINIO_ENDPOINT: minio:9000
    MINIO_SECURE: "false"
    SECRET_KEY: ${SECRET_KEY:-change-this-in-production}
    CORS_ORIGINS: '["http://localhost:3000","http://localhost:5173"]'
```

**原因**: 确保Docker容器内的后端服务使用正确的PORT环境变量，解决外部访问31234端口失败的问题

---

#### 5. Docker容器启动命令配置 (修复)
**文件路径**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
**修改位置**: 第75行后，backend服务配置段
**修改时间**: 2026-05-25 10:55
**问题**: Dockerfile中硬编码了8000端口，导致环境变量无效

**代码对比**:
```diff
backend:
  build:
    context: ../backend
    dockerfile: Dockerfile
  container_name: ppap-backend
  restart: unless-stopped
  environment:
    PORT: "31234"
    DATABASE_URL: postgresql+asyncpg://ppap:ppap123@postgres:5432/ppap
    REDIS_URL: redis://redis:6379/0
    MINIO_ENDPOINT: minio:9000
    MINIO_SECURE: "false"
    SECRET_KEY: ${SECRET_KEY:-change-this-in-production}
    CORS_ORIGINS: '["http://localhost:3000","http://localhost:5173"]'
  ports:
    - "31234:31234"
+  command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "31234"]
```

**原因**: 覆盖Dockerfile中的硬编码端口，确保后端服务监听31234端口

---

#### 6. 防火墙端口配置
**文件路径**: `/home/zhouao2/ppap/setup_firewall.sh`
**修改位置**: 第37-38行，防火墙规则配置段
**修改时间**: 2026-05-25 10:58

**代码对比**:
```diff
# Backend API
- echo -e "Allowing Backend API (Port 8000)..."
- ufw allow 8000/tcp
+ echo -e "Allowing Backend API (Port 31234)..."
+ ufw allow 31234/tcp
```

**原因**: 更新防火墙规则，允许外部访问31234端口

---

#### 7. Nginx MIME类型配置 (修复PDF渲染问题)
**文件路径**: `/home/zhouao2/ppap/deploy/nginx.conf`
**修改位置**: 第28行后，server配置段
**修改时间**: 2026-05-25 10:52
**问题**: .mjs文件的MIME类型设置为application/octet-stream，导致PDF.js worker加载失败

**代码对比**:
```diff
# Frontend static files
location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}

+ # Fix MIME type for .mjs files (PDF.js worker)
+ location ~* \.mjs$ {
+     root /usr/share/nginx/html;
+     add_header Content-Type application/javascript always;
+ }
```

**原因**: 使用专门的location块和add_header指令强制设置.mjs文件的MIME类型为application/javascript，解决PDF.js worker加载失败的问题

---

#### 8. PDF.js Worker加载方式修复 (彻底解决PDF渲染问题)
**文件路径**: `/home/zhouao2/ppap/frontend/src/views/FileDetailPage.vue`
**修改位置**: 第485-488行，PDF.js导入和配置段
**修改时间**: 2026-05-25 10:54
**问题**: 本地.mjs worker文件在nginx环境下的MIME类型和加载路径问题

**代码对比**:
```diff
- import * as pdfjsLib from 'pdfjs-dist'
- import pdfWorker from 'pdfjs-dist/build/pdf.worker.mjs?url'
- 
- pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker
+ import * as pdfjsLib from 'pdfjs-dist'
+ 
+ // Use CDN for PDF.js worker to avoid MIME type issues
+ pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`
```

**原因**: 使用CDN版本的PDF.js worker来避免本地文件的MIME类型和路径问题，确保PDF渲染功能稳定可靠

**附加修复**: 重新安装前端依赖并重新构建前端，解决了rollup构建依赖问题

---

### 相关配置文件

#### 无需修改的配置文件
以下文件已正确配置，无需修改：

1. **后端环境配置**: `/home/zhouao2/ppap/backend/.env`
   - 第9行: `PORT=31234` ✅

2. **后端默认配置**: `/home/zhouao2/ppap/backend/app/core/config.py`
   - 第15行: `PORT: int = 8000` (默认值，被.env覆盖) ✅

3. **数据库配置**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
   - 第16行: `"5435:5432"` (PostgreSQL端口映射) ✅

4. **Redis配置**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
   - 第32行: `"6379:6379"` (Redis端口映射) ✅

5. **MinIO配置**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
   - 第51行: `"9000:9000"` (MinIO API端口) ✅
   - 第52行: `"9001:9001"` (MinIO控制台端口) ✅

### 端口分配总结

#### 主要服务端口
- **后端API服务器**: 31234 (原8000，已迁移)
- **前端开发服务器**: 5173
- **前端生产服务器**: 80

#### 数据存储端口
- **PostgreSQL**: 5435 (外部) → 5432 (容器内部)
- **Redis**: 6379
- **MinIO API**: 9000
- **MinIO 控制台**: 9001

#### 其他端口
- **SMTP**: 465 (默认未启用)

### 部署说明
由于配置变更，需要重新创建Docker容器：

```bash
# 停止并删除现有容器
cd /home/zhouao2/ppap/deploy
docker compose down

# 重新构建并启动
docker compose up -d --build
```

### 验证步骤
1. 确认后端服务在31234端口正常运行
2. 测试前端开发服务器代理功能
3. 验证API接口访问: `http://localhost:31234/api/v1/docs`
4. 检查各服务间通信正常

### 影响范围
- ✅ 本地开发环境配置
- ✅ Docker容器化部署
- ✅ 前后端连接配置
- ❌ 无数据库迁移需求
- ❌ 无代码逻辑变更

---

## 版本历史

| 日期 | 版本 | 描述 |
|------|------|------|
| 2026-06-03 | 1.0.3 | 数据库初始化自动化与Windows部署支持 |
| 2026-05-27 | 1.0.2 | 变量面板功能，支持快捷插入数据源变量 |
| 2026-05-25 | 1.0.1 | 端口配置优化，解决8000端口冲突 |
| 2026-05-24 | 1.0.0 | PPAP项目初始版本 |
