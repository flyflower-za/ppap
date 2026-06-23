# Changelog

All notable changes to the PPAP project will be documented in this file.

## [2026-06-24] - 在线防伪算子输出增强与预设规则 UX 修复

### 功能描述
- **在线防伪比对算子输出详细化**：`OnlineVerificationOperator` 的执行结果从单行摘要升级为结构化的多维度详细报告，涵盖二维码原始内容、正则提取变量、页数对比、文本长度对比和差异摘要。
- **二维码识别内容可见化**：`QRScannerOperator` 的 message 输出中增加了每个二维码的具体解码内容和类型信息，替代了原先只显示数量的简略输出。
- **文档差异比对算子元数据增强**：`DocumentDiffOperator` 新增返回本地/远程 PDF 页数和文本字符数等元数据，供上游算子组装更加丰富的比对报告。
- **在线防伪提取语法简化**：重构了 `OnlineVerificationOperator` 的正则提取逻辑。现在支持用户友好的 `{report_id}` 和 `{verify_code}` 占位符写法，以及使用 `*` 通配符匹配中间无关参数（例如 `reportno={report_id}*randomno={verify_code}`），并且完全向后兼容原生正则表达式。
- **配置与使用指南文档**：新增了 `ONLINE_VERIFICATION_GUIDE.md` 指南文档，并在项目文档索引 `README.md` 中进行关联。
- **预设规则 Dirty State 提醒**：修复了用户在基础底座配置区切换开关/修改告警级别后不点保存就刷新导致配置丢失的 UX 问题。现在任何未保存的修改都会在保存按钮旁显示醒目的"⚠ 配置已修改，请保存"提示标签。

### 详细修改记录

#### 1. 后端 - 算子输出增强
- **在线防伪比对算子** ([online_verification_operator.py](backend/app/engine/operators/online_verification_operator.py)) [MODIFY]：
  - 执行结果 message 重构为结构化多行输出：
    - 📎 二维码原始内容
    - 🔍 正则提取的命名变量（如 `report_id=A225097188910101C, verify_code=198641334`）
    - 🔗 组装后的目标 URL
    - 📄 页数对比（本地 vs 远程，不一致时标记 ⚠️）
    - 📝 文本长度对比（字符数）
    - 📊 相似度百分比与阈值判定结论
    - 差异摘要（前5处变更的原文→现文对照）
  - `extracted_data` 中新增 `qr_content`、`extracted_vars`、`formatted_url` 字段。
  - 新置 `_convert_simple_pattern` 静态解析方法，支持将 `{report_id}`、`{verify_code}` 占位符和 `*` 通配符转换为标准的命名捕获组正则表达式。

- **文档验证模块 Schema** ([verification_module.py](backend/app/schemas/verification_module.py)) [MODIFY]：
  - 修改 `online_verification` 算子的配置 schema，将其默认的 `regex_pattern` 从原生正则变更为简化占位符格式（`reportno={report_id}&randomno={verify_code}`），以降低用户的学习与使用成本。

- **文档差异比对算子** ([diff_operator.py](backend/app/engine/operators/diff_operator.py)) [MODIFY]：
  - `_extract_text_from_bytes` 方法返回值从 `str` 改为 `tuple[str, int]`，同时返回文本和页数。
  - `extracted_data` 中新增 `current_page_count`、`base_page_count`、`current_text_length`、`base_text_length` 四个字段。

- **二维码识别算子** ([qr_operator.py](backend/app/engine/operators/qr_operator.py)) [MODIFY]：
  - 结果 message 从 `"成功提取到 N 个二维码数据。"` 改为逐条列出每个二维码的解码内容（超过200字符自动截断）和类型信息。

#### 2. 前端 - 预设规则 UX 改进
- **规则配置页面** ([RulesPage.vue](frontend/src/views/RulesPage.vue)) [MODIFY]：
  - 新增 `presetDirty` ref 状态变量，追踪基础底座配置区是否有未保存的修改。
  - 预设规则开关 `<el-switch>` 绑定 `@change="presetDirty = true"` 事件。
  - 告警级别下拉框 `<el-select>` 同样绑定 `@change="presetDirty = true"` 事件。
  - 保存按钮旁新增 `<el-tag>` 未保存提示标签（带 pulse 动画），dirty 状态时自动显示。
  - `savePresetRules` 成功后重置 `presetDirty = false`。
  - 新增 `@keyframes pulse` CSS 动画。

### 影响范围
- ✅ 在线防伪比对引擎输出
- ✅ 二维码识别引擎输出
- ✅ 文档差异比对引擎输出
- ✅ 前端预设规则配置 UX

---

## [2026-06-23] - 极简预置规则自初始化与规则管理界面优化

### 功能描述
- **分类自动初始化底座规则**：重构了文档分类创建与重置机制。在新建任何分类时，系统会自动将所有活动的系统校验模块（如二维码、数字签名、印章检测等）自动克隆并初始化为该分类下的预置规则（默认不启用）。
- **底座预置规则配置极简化**：在规则配置页面中重排了布局。右侧校验区划分为“基础配置（预置规则卡片）”与“高级自定义配置（表格）”两部分。基础规则以网格 Switch 卡片形式平铺呈现，用户无需进入复杂表单，直接通过开关与严重级别下拉框进行修改，一键批量保存。
- **规则-模块外键直连重构**：数据库层面重构了 `VerificationRule` 与 `VerificationModule` 的一对一关系，废除了冗余的 `rule_modules` Junction 关系表，简化了后端的映射解析，并消除了 `is_system` 标记不同步导致规则未初始化的缺陷。
- **修复级联删除与 NameError 缺陷**：
  - 修复了删除分类时由于 `rule_modules` 关系表外键约束导致的 `ForeignKeyViolationError` (500 Error)。
  - 修复了规则引擎在大项校验时由于未引入 `Severity` 产生的 `NameError` 导致分析卡死在“正在分析中”的缺陷。

### 详细修改记录

#### 1. 后端 - 数据模型与 API 逻辑重构
- **数据库模型** ([rule.py](file:///c:/Projects/git/ppap/backend/app/models/rule.py)) [MODIFY]：
  - 新增 `module_id` 列并与 `VerificationModule` 建立外键直连关系。
- **分类与重置接口** ([rules.py](file:///c:/Projects/git/ppap/backend/app/api/rules.py)) [MODIFY]：
  - 修改 `create_category`，在分类创建时自动加载所有活动验证模块并生成其对应的默认预置规则。
  - 修改 `delete_category`，在执行分类删除前主动清空 `rule_modules` 以防级联删除外键冲突报错。
- **校验调度引擎** ([core.py](file:///c:/Projects/git/ppap/backend/app/engine/core.py)) [MODIFY]：
  - 引入缺失的 `Severity` 枚举，修复大项校验报错问题。
- **校验异步任务** ([verification_tasks.py](file:///c:/Projects/git/ppap/backend/app/tasks/verification_tasks.py)) [MODIFY]：
  - 弃用 junction 表，直接从 rules 对象的 `module_id` 列提取对应关联的 VerificationModule 传入执行器。

#### 2. 前端 - 极简多模块展示与提交
- **规则配置页面** ([RulesPage.vue](file:///c:/Projects/git/ppap/frontend/src/views/RulesPage.vue)) [MODIFY]：
  - 将当前分类下的规则划分出基础配置卡片区域与高级自定义列表区域。
  - 基础规则区域绑定 `presetRules` 计算属性，支持多卡片 Switch 绑定及告警级别修改，并开发 `savePresetRules` 提交逻辑。

### 影响范围
- ✅ 规则引擎校验逻辑
- ✅ 数据库关系表（添加 `module_id` 并修复级联约束）
- ✅ 前端规则配置界面
- ✅ 20 个单元测试通过

---

## [2026-06-23] - 校验模块联动与引擎比对功能增强

### 功能描述
- **引擎机构归一化比对修复**：在规则引擎中增加了 `normalize_institution_name` 归一化清洗函数，统一比对中英文、简称（如 "华测检测", "华测", "CTI" 都归一化为 "cti"），修复了因为归一化差异导致的规则被跳过、进而检测项为 0 的严重 Bug。
- **自定义规则的关联模块配置功能**：在规则配置中心的规则编辑与新建对话框中，为非逻辑图类型的标准规则添加了「关联校验模块」的多选勾选框，用户可以为自定义规则勾选需要触发的底层校验模块（如：二维码识别检查、数字签名验证、文档篡改检查、发证机构识别等），并能够将关联的模块成功同步保存至后端。
- **添加 Docker 构建忽略文件以提速构建**：在前端和后端目录中分别补充了 `.dockerignore` 配置文件，彻底排除了本地 `node_modules`、`dist`、`__pycache__` 等无用缓存对 Docker 上下文的干扰，显著提升了常规部署和热更新的构建效率。

### 详细修改记录

#### 1. 后端 - 引擎归一化与 Docker 忽略
- **规则引擎核心** ([core.py](file:///c:/Projects/git/ppap/backend/app/engine/core.py)) [MODIFY]：
  - 新增 `normalize_institution_name` 归一化清洗函数。
  - 修改引擎两处生效条件校验逻辑，由直接比对 `lower()` 改为基于归一化结果进行比对，防止 "CTI" 与 "华测检测" 等拼写差异导致规则失效。
- **后端 Docker 忽略** ([.dockerignore](file:///c:/Projects/git/ppap/backend/.dockerignore)) [NEW]：
  - 忽略 `__pycache__`, `.pytest_cache`, `.venv` 等临时目录，加速构建上下文传输。

#### 2. 前端 - 关联校验模块多选与 Docker 忽略
- **规则管理页面** ([RulesPage.vue](file:///c:/Projects/git/ppap/frontend/src/views/RulesPage.vue)) [MODIFY]：
  - 在新建/编辑标准规则的表单中，添加了「关联校验模块」复选框组。
  - 弹窗打开时自动异步加载活动校验模块列表及规则已绑定的模块列表。
  - 保存规则时自动调用 `assignRuleModules` 接口保存绑定的校验模块。
- **前端 Docker 忽略** ([.dockerignore](file:///c:/Projects/git/ppap/frontend/.dockerignore)) [NEW]：
  - 忽略 `node_modules`, `dist` 等本地开发残留资源。

### 影响范围
- ✅ 规则引擎校验逻辑
- ✅ 前端规则配置页面
- ✅ Docker 构建速度提升
- ❌ 无数据库变更

---

## [2026-06-23] - Windows 部署脚本修复

### 功能描述
- **修复 PowerShell 部署脚本与 Bash 脚本功能一致性**：修复 `deploy.ps1` 中的语法错误和缺失功能，使其与 `deploy.sh` 保持完全一致。
- **解决 PowerShell 语法兼容问题**：将 Bash 专用的 `until` 循环改为 PowerShell 兼容的 `while` 循环结构。
- **添加完整的健康检查流程**：补充后端 API 健康检查、MinIO bucket 创建重试逻辑等关键功能。

### 详细修改记录

#### 部署脚本修复
**文件路径**: [deploy.ps1](deploy.ps1) [MODIFY]

- **参数简化**：移除无用的 `-SkipEnvCheck` 和 `-SkipMinIO` 参数，仅保留 `-ForceRebuild`
- **添加 `--remove-orphans`**：在 `docker compose up` 命令中添加此参数以清理孤立容器
- **强制重建使用 `--no-cache`**：与 Bash 脚本保持一致，确保完全重建
- **添加后端 API 健康检查**：检查 `http://localhost:31234/docs` 端点
- **MinIO bucket 创建重试**：5 次重试，每次等待 3 秒
- **添加最终状态检查**：显示 `docker compose ps` 输出
- **语法错误修复**：
  - 修复第 115 行 here-string 语法错误
  - 将所有 `until` 循环改为 `while (-not $condition -and $retries -gt 0)` 结构
- **输出格式统一**：使用表情符号和颜色代码，与 Bash 脚本输出风格一致

### 影响范围
- ✅ Windows 部署脚本
- ❌ 无数据库变更
- ❌ 无后端/前端代码变更

---

## [2026-06-04] - 规则页面全面检查与优化

### 功能描述
- **修复规则保存功能**：解决了 `logic_graph` 类型规则保存时缺少 `rule_content` 字段的问题，确保规则能够正确保存到后端。
- **修复全屏可视化编辑器保存功能**：解决了保存后规则列表不刷新、payload 构建错误等多个问题，确保规则能够正确保存并显示在列表中。
- **添加规则列表自动刷新**：从全屏编辑器返回时自动刷新规则列表，确保新创建/更新的规则立即可见。
- **优化规则列表显示**：为 `logic_graph` 类型规则添加了专门的显示格式，显示节点和连线数量。
- **清理不支持的字段**：移除了全屏编辑器和规则页面中所有后端不支持的 `description` 字段。
- **修复按钮状态显示**：将原生按钮的 `:loading` 属性改为 `:disabled`，并添加动态文本显示保存状态。
- **添加调试日志**：增加详细的控制台日志，便于诊断保存问题。

### 详细修改记录

#### 1. 前端 - 规则页面优化
- **规则页面** ([RulesPage.vue](frontend/src/views/RulesPage.vue)) [MODIFY]：
  - 修复 `saveRule` 函数，为 `logic_graph` 类型规则添加 `rule_content` 字段（空字符串）
  - 优化规则列表中的 `rule_content` 列，为 `logic_graph` 类型显示节点和连线数量
  - 添加路由查询参数监听，从全屏编辑器返回时自动刷新规则列表

#### 2. 前端 - 全屏编辑器保存修复
- **全屏编辑器** ([FullscreenRuleEditor.vue](frontend/src/views/FullscreenRuleEditor.vue)) [MODIFY]：
  - 修复 payload 构建逻辑，添加后端要求的 `rule_content` 字段（对于 `logic_graph` 类型使用空字符串）
  - 移除后端不支持的 `description` 字段（规则配置表单、`ruleForm` 初始化、加载现有规则时的引用）
  - 修改保存成功后的导航逻辑，使用 `router.push({ name: 'Rules', query: { refresh: 'true' } })` 替代 `router.back()`
  - 修复按钮的 `:loading` 属性问题，改用 `:disabled` 和动态文本（"保存中..."）
  - 添加详细的调试日志，包括 payload 内容和 API 响应
  - 添加 `categoryId` 验证，确保规则有分类归属

### 影响范围
- ✅ 前端规则页面
- ✅ 前端全屏可视化编辑器
- ❌ 无数据库变更
- ❌ 无后端变更

---

## [2026-06-04] - 自主规则配置与逻辑图数据流优化

### 功能描述
- **算子注册表去重与前后端命名对准**：彻底排除了前端可视化节点编辑器中由于 kebab-case 和 snake-case 命名不统一造成的“二维码识别”、“数字签名验证”等节点的冗余重复显示，消除了后端 API 路由双重 prefix 的 `/operators/operators` 重复挂载 Bug，修复了 API 获取算子定义时的 404 错误。
- **属性配置面板变量数据流联动 (Variable Flow)**：在属性面板中，新增了可折叠/自适应渲染的“节点数据流 (Variable Flow)”面板。通过分析用户填写的字段和正则表达式（包含 (?P<name>...) 命名捕获组和 {{name}} 模板变量插值），动态计算并实时渲染出当前节点对上游变量的“输入依赖 (Requires)”以及向全局上下文注入的“输出变量 (Produces)”。
- **全量算子及逻辑图测试套件**：重构了 `test_engine.py` 用例中的逻辑图 BFS 执行逻辑，增加了订单无关性验证以抵御多测试路径的影响；并新增了 `test_rule_execution.py` 集成测试，验证了从 `qr_scanner` 到 `variable_extractor` 再到 `document_diff` 的端到端 DAG 流程。

### 详细修改记录

#### 1. 前端 - 算子去重与变量数据流展示
- **编辑器组件** ([RuleGraphEditor.vue](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/frontend/src/components/RuleGraphEditor.vue)) [MODIFY]：
  - 更新了 `DEFAULT_NODE_REGISTRY` 全局硬编码列表，将所有 kebab-case 格式的键名对齐为后端统一返回的 snake-case 格式（如 `text_llm`, `digital_signature`, `qr_scanner`, `revision_check` 等）。
  - 新增 `getNodeVariableInfo` 工具函数，用于动态计算并解析节点表单中的变量字段依赖（支持正则捕获组提取和 `{{var}}` 占位符解析）。
  - 在 HTML 中添加 `variable-flow-card` 结构，并使用 vanilla CSS 样式规范化 Requires 依赖和 Produces 变量。
  - 为所有配置子面板增加了 snake-case 与 kebab-case 节点类型的双向条件兼容（如 `text_llm` || `text-llm`）。

#### 2. 后端 - API 路由挂载修正与测试套件完善
- **算子路由挂载修复** ([operators.py](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/app/api/operators.py)) [MODIFY]：
  - 移除了 `router = APIRouter(prefix="/operators")` 中的重复 `/operators` 路径前缀，确保后端路由通过 `__init__.py` 统一注册后接口地址为标准的 `/api/v1/rule-engine/operators/registry`。
- **嗅探器返回类型对准** ([sniffer_operator.py](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/app/engine/operators/sniffer_operator.py)) [MODIFY]：
  - 重构了 `InstitutionSnifferOperator`，将其识别归纳的机构返回全称（"华测检测", "SGS通标"）统一校准为全系统和测试用例预置的标准编码简称（"CTI", "SGS"），避免分类规则条件匹配失效。
- **测试断言优化与集成测试添加**：
  - [test_engine.py](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/tests/engine/test_engine.py) [MODIFY]：修改了 `test_logic_graph_rule_evaluation` 和 `test_logic_graph_dag_and_interpolation` 的测试断言，改为对 `checks` 数组元素进行顺序无关的包含性判定（`any(...)`），以规避 BFS 遍历中对无依赖同级节点的排布顺序干扰。

## [2026-06-04] - P2&P3 规则变更审批流程与版本管理增强

### 功能描述
- **P2: 规则变更审批流程**：基于审批策略（ApprovalPolicy）与规则变更请求（RuleChangeRequest）模型，构建了完整的规则审批生命周期。支持创建、更新、停用及删除操作的在线审批流，非 ADMIN/MANAGER 角色需要经过审批批准后方可将变更部署生效，而普通/低风险规则依据预置审批策略可触发“免审批”快速部署通道。
- **P3: 版本管理与变更日志增强**：在现有的规则多版本历史记录上进行了字段扩展，新增了 `change_log`（变更说明）与 `change_request_id`（关联的审批请求），支持在规则版本历史抽屉中清晰比对多版本配置差异，并高亮标记其差异项。
- **审批中心 UI 与功能开发**：全新上线“审批中心”仪表盘，包含待审批、已批准、已拒绝等关键工单的卡片式展示与按角色快速审批、拒绝、一键部署生效等功能。

### 详细修改记录

#### 1. 前端 - 审批中心开发与版本差异高亮
- **审批中心页面** [ApprovalsPage.vue](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/frontend/src/views/ApprovalsPage.vue) [NEW]：
  - 新增统计卡片区，展示待审批数、已审批数、已驳回数等。
  - 支持分栏切换（待审批 / 全部 / 我发起的）工单卡片列表。
  - 支持工单详情预览、填写审批意见、执行通过/驳回以及一键部署生效等操作。
- **规则配置页面优化** [RulesPage.vue](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/frontend/src/views/RulesPage.vue) [MODIFY]：
  - 在操作列增加“提交审批”按钮与审批请求填写弹窗。
  - 增强版本历史抽屉以渲染显示 `change_log` 字段，并新增高亮 diff 标签展示版本间修改的字段差异。
- **导航与路由配置**：
  - [MainLayout.vue](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/frontend/src/layouts/MainLayout.vue) [MODIFY]：新增“审批中心”导航栏图标与跳转链接。
  - [router/index.ts](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/frontend/src/router/index.ts) [MODIFY]：添加 `/approvals` 页面的异步组件懒加载路由。
- **审批 API 客户端** [approvals.ts](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/frontend/src/api/approvals.ts) [NEW]：封装与后端接口交互的变更工单、审批策略列表及处理操作。

#### 2. 后端 - 审批工作流与版本日志存储
- **数据库表结构扩展与迁移**：
  - [rule_version.py](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/app/models/rule_version.py) [MODIFY]：为 `RuleVersion` 数据库模型添加 `change_log` 与 `change_request_id` 关联字段。
  - [p2p3_approval_workflow.py](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/migrations/versions/p2p3_approval_workflow.py) [NEW]：编写 Alembic 数据库迁移脚本，并手动校准外键关系，通过 `alembic stamp head` 命令使其成功与现有基于 SQLAlchemy 初始化生成的 `rule_change_requests` 和 `approval_policies` 数据库表完成校准和升级。
- **数据结构定义** [approval.py](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/app/schemas/approval.py) [NEW]：新建 Pydantic schemas，对 `RuleChangeRequestCreate`、`RuleChangeRequestResponse`、`ReviewAction` 和 `ApprovalPolicyResponse` 提供全方位的输入/输出校验。
- **审批流接口开发** [approvals.py](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/app/api/approvals.py) [NEW]：
  - `GET /change-requests` & `POST /change-requests`：列表过滤展示以及新建规则变更工单。
  - `POST /change-requests/{id}/review` & `POST /change-requests/{id}/deploy`：管理员/经理的评审表决及审核通过规则的一键合并发布与版本快照自动保存。
  - `GET /policies` & `POST /policies/init`：获取审批策略及默认测试审批规则初始化。
- **路由注册** [__init__.py](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/app/api/__init__.py) [MODIFY]：将审批中心路由挂载至全局 API 前缀 `/rule-engine/approvals`。

#### 3. 单元测试 - 稳定性保证
- **单元测试套件** [test_approvals.py](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/tests/api/test_approvals.py) [NEW]：
  - 编写了完整的覆盖测试，对自动放行、待审批挂起、越权访问拦截、管理员确认授权、一键部署以及审计日志记录等核心逻辑进行了全覆盖验证。
- **全局测试配置** [conftest.py](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/tests/conftest.py) [MODIFY]：
  - 增加 Session-scoped 的 `event_loop` 共享夹具，完美规避多测试用例并发下，异步连接池由于 event loop 重建产生的 `RuntimeError` 错误。

---

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
| 2026-06-23 | 1.1.2 | 校验模块联动与引擎机构归一化比对修复 |
| 2026-06-23 | 1.1.1 | Windows 部署脚本修复，功能对齐 deploy.sh |
| 2026-06-04 | 1.1.0 | P2 规则变更审批流程与 P3 版本管理增强 |
| 2026-06-03 | 1.0.3 | 数据库初始化自动化与Windows部署支持 |
| 2026-05-27 | 1.0.2 | 变量面板功能，支持快捷插入 data-source 变量 |
| 2026-05-25 | 1.0.1 | 端口配置优化，解决8000端口冲突 |
| 2026-05-24 | 1.0.0 | PPAP项目初始版本 |
