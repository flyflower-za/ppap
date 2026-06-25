# PPAP LLM 校验功能说明

## 功能概览

PPAP 项目共有 **5 个功能场景** 调用 LLM，涉及 **2 个核心算子 + 1 个辅助服务**。所有 LLM 调用统一使用 `AsyncOpenAI` 客户端，强制 JSON 响应，具备超时熔断和 Pydantic 输出校验。

---

## 一、核心算子

### 1. TextLLMOperator — 文本语义分析算子

- **文件**: `backend/app/engine/operators/text_llm_operator.py`
- **输入**: PDF 提取的纯文本（`full_text`）
- **输出**: `llm_semantic_analysis`
- **默认模型**: `gpt-4o-mini`

**操作模式**:

| 模式 | 系统角色 | 输出结构 |
|------|---------|---------|
| verification（验证） | 文档审核员 | `{passed, confidence, reason, extracted_data}` |
| extraction（提取） | 信息提取专家 | 字段键值对 |

**关键特性**:
- 文本截断上限 3000 字符，防止超出上下文窗口
- 60 秒超时熔断（`asyncio.wait_for`），超时自动降级返回失败结果
- 未配置 AI 时自动降级为 Mock 响应（confidence=0.95）
- 输出通过 `LLMOutputSchema` Pydantic 模型验证

---

### 2. VisionLLMOperator — 视觉大模型算子

- **文件**: `backend/app/engine/operators/vision_llm_operator.py`
- **输入**: PDF 字节流（`pdf_bytes`）
- **输出**: `vision_analysis`
- **默认模型**: `gpt-4o`

**图像输入策略**:

| 策略 | 条件 | 适用场景 |
|------|------|---------|
| 全页渲染 | 无 `crop_bbox` | 全局布局/签名检查 |
| 区域裁剪 | 提供 `crop_bbox` (x0, y0, x1, y1) | 二维码、角落印章等，大幅降低 token 消耗 |

**关键特性**:
- 使用 PyMuPDF (fitz) 以 2x zoom（~144 DPI）渲染 PDF 页面为 JPEG
- 图像以 base64 编码通过 `image_url` 发送，`detail: "high"`
- 输出通过 `VisionOutputSchema` 验证，额外支持 `bounding_boxes` 字段

---

## 二、LLM 辅助功能

### 3. InstitutionSnifferOperator — 签发机构嗅探

- **文件**: `backend/app/engine/operators/sniffer_operator.py`
- **辅助服务**: `backend/app/services/aliyun_service.py`

**多阶段识别策略**:

| 阶段 | 方法 | 说明 |
|------|------|------|
| Part 0 | 密码学数字签名证书 | 直取签发机构，100% 可信 |
| Part 1 | 提取第一页纯文本 | 为后续阶段准备 |
| Part 2 | 本地正则极速匹配 | 1ms 级，覆盖高频机构（CTI/SGS/TUV 等） |
| **Part 3** | **文本语义 LLM 识别** | 首页前 1200 字符 → LLM 提取机构名称和置信度 |
| **Part 4** | **视觉 LLM Fallback** | 文本无法确定时，渲染首页图像 → Vision LLM 识别 |

**降级链**: LLM 失败后降级为本地正则匹配算法（内置 CTI/SGS/TUV/INTERTEK/BV/UL/CSA/PONY/CCIC/WEIPU 等机构模式库）

---

### 4. 规则引擎调度 — `llm_prompt` 类型规则

- **文件**: `backend/app/engine/core.py`

**规则执行路径**:
- 当 `rule.rule_type == RuleType.llm_prompt` 时：
  - 从 `logic_config` 读取 `llm_model_type`（text/vision）和 `llm_operation_mode`（verification/extraction）
  - 动态实例化 `VisionLLMOperator` 或 `TextLLMOperator`
  - extraction 模式自动通过并将提取数据注入 `shared_state`
  - verification 模式检查 `passed` 字段判定结果

**图节点执行路径**:
- 当节点类型为 `text_llm` / `vision_llm` 时：
  - 从节点 `data` 中读取 `prompt` 和 `operation_mode`
  - 动态实例化对应算子并执行
  - 结果存入 `node_llm_data`，用于后续字段映射和展示

---

### 5. 算子沙盒测试

- **前端文件**: `frontend/src/views/ModuleSandboxPage.vue`
- **后端 API**: `backend/app/api/modules.py`

管理员可在沙盒页面单独测试 TextLLM / VisionLLM 算子：
- 支持选择具体底座模型（从已配置的 `aiModelProfiles` 列表中选择）
- 超时设置为 120 秒，适配 LLM 视觉推理的长耗时

---

## 三、配置层

### AI 模型配置管理

| 组件 | 文件 | 说明 |
|------|------|------|
| ai_config_service | `backend/app/services/ai_config_service.py` | 统一配置加载器，按 model_type 匹配默认配置 |
| Settings API | `backend/app/api/settings.py` | 模型档案 CRUD + 连接测试 REST API |
| Settings 页面 | `frontend/src/views/SettingsPage.vue` | 管理员 UI：CRUD 模型档案、测试连接、设默认模型 |

### 配置降级链

```
数据库 ai_model_profiles（多模型档案）
  → 数据库 ai_model_config（遗留单配置）
    → 环境变量（已废弃，保留向后兼容）
      → Mock 响应
```

### 模型档案（ModelProfile）字段

| 字段 | 说明 |
|------|------|
| name | 档案名称 |
| base_url | OpenAI 兼容 API 地址 |
| api_key | API 密钥（脱敏存储） |
| model_name | 模型名称（如 gpt-4o、gpt-4o-mini） |
| model_type | 能力类型：text / vision / both |
| max_tokens | 最大输出 token 数 |
| temperature | 采样温度 |
| enabled | 是否启用 |
| is_default_text | 是否为默认文本模型 |
| is_default_vision | 是否为默认视觉模型 |

### API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/settings/ai-model` | 获取遗留单配置 |
| POST | `/api/settings/ai-model` | 更新遗留单配置 |
| POST | `/api/settings/ai-model/test` | 测试遗留配置连接 |
| GET | `/api/settings/ai-models` | 列出所有模型档案 |
| POST | `/api/settings/ai-models` | 创建新模型档案 |
| PUT | `/api/settings/ai-models/{id}` | 更新模型档案 |
| DELETE | `/api/settings/ai-models/{id}` | 删除模型档案 |
| POST | `/api/settings/ai-models/{id}/test` | 测试指定档案连接 |
| GET | `/api/settings/ai-models/public` | 列出启用档案（普通用户，无敏感数据） |

---

## 四、数据模型

| 模型文件 | LLM 相关内容 |
|---------|-------------|
| `models/rule.py` | `RuleType.llm_prompt` 枚举；`logic_config` JSONB 存储 `llm_model_type` 和 `llm_operation_mode` |
| `models/verification_module.py` | `ModuleType.text_llm` 和 `ModuleType.vision_llm` 枚举 |
| `models/operator_registry.py` | `operator_type` 支持 `"llm"` 类型；预置 `text_llm` 算子注册数据 |
| `schemas/verification_module.py` | LLM 模块元数据（label, description, icon, config_fields） |

---

## 五、前端 LLM 相关页面

| 页面 | 文件 | LLM 功能 |
|------|------|---------|
| 系统设置 | `views/SettingsPage.vue` | 多模型档案 CRUD、连接测试、设默认模型 |
| 规则管理 | `views/RulesPage.vue` | 创建 `llm_prompt` 类型规则，选择文本/视觉 LLM，切换验证/提取模式 |
| 规则图编辑器 | `components/RuleGraphEditor.vue` | 可视化添加 `text-llm` / `vision-llm` 节点，配置 prompt 和操作模式 |
| 全屏规则编辑器 | `views/FullscreenRuleEditor.vue` | 同上，全屏版 |
| 算子沙盒 | `views/ModuleSandboxPage.vue` | 单独测试 LLM 算子，选择底座模型 |

---

## 六、功能全景图

```
┌─────────────────────────────────────────────────────┐
│                    前端 (Vue 3)                      │
│  SettingsPage  RulesPage  RuleGraphEditor  Sandbox   │
└──────────────────────┬──────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────┐
│              配置层 (ai_config_service)               │
│  多模型档案 → 遗留单配置 → 环境变量 → Mock 降级        │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              调度层 (engine/core.py)                  │
│  规则类型 llm_prompt / 图节点 text-llm|vision-llm     │
└───────┬──────────────┬──────────────┬───────────────┘
        │              │              │
┌───────▼───┐  ┌───────▼───┐  ┌──────▼──────────┐
│ TextLLM   │  │ VisionLLM │  │ SnifferOperator │
│ Operator  │  │ Operator  │  │  (LLM 辅助)     │
└───────────┘  └───────────┘  └─────────────────┘
```
