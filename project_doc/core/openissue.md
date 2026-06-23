# 算子引擎变量传递问题分析

> **版本**: v2.0 待优化项
> **状态**: 问题识别中
> **优先级**: 高

---

## 一、问题描述

当前算子引擎 (Verification Engine) 在执行 **logic_graph** 类型规则时，节点间的变量传递存在不稳定的情况。具体表现为：

1. **上游节点提取的变量**（如 `variable_extractor` 节点）无法被 **下游节点** 正确引用
2. **HTTP 节点** 的响应数据无法被后续节点使用
3. **LLM 节点** 的提取数据在 `extraction` 模式下无法正确传递
4. **节点间数据传递** 依赖于 `{{#node_id.key#}}` 语法，但执行时可能找不到对应的值

---

## 二、代码位置

| 文件 | 行号范围 | 功能描述 |
|------|----------|----------|
| `backend/app/engine/core.py` | 40-73 | `_flatten_shared_state` - 扁平化嵌套变量 |
| `backend/app/engine/core.py` | 417-445 | `interpolate_vars` - 变量插值解析 |
| `backend/app/engine/core.py` | 779-812 | `variable_extractor` 节点处理 |
| `backend/app/engine/core.py` | 666-777 | `http_call` 节点处理 |
| `backend/app/engine/core.py` | 851-904 | `node_outputs` 缓存填充 |

---

## 三、问题根因分析

### 3.1 变量作用域混乱

**问题**: 代码中存在两个变量存储位置，使用场景不清晰：

```python
# 1. 全局共享状态 (shared_state)
context.shared_state[key] = value

# 2. 节点输出缓存 (node_outputs)
context.node_outputs[node_id] = {...}
```

**现状分析**:
- `shared_state` 用于存储全局变量 (如 `institution`, `qr_content`, `page_count`)
- `node_outputs` 用于存储节点执行结果
- 但 `interpolate_vars` 需要同时查询两个地方，容易产生歧义

### 3.2 变量插值顺序问题

**问题**: 节点执行时，上游节点的输出可能尚未写入 `node_outputs`

**当前流程**:
```
1. 节点 A 执行 → 产生输出
2. 节点 A 的输出写入 node_outputs (line 905)
3. 节点 B 执行 → 读取 node_outputs (line 495 的 interpolate_vars)
```

**潜在风险**:
- 如果节点 B 执行时节点 A 的输出尚未写入，变量将为空
- `_flatten_shared_state` 的调用时机 (lines 182, 265, 541, 664) 可能晚于某些节点对变量的访问

### 3.3 嵌套路径解析不完整

**问题**: `get_nested_val` 函数 (lines 406-414) 只支持简单的 `.` 分隔路径

```python
def get_nested_val(d: dict, path: str):
    parts = path.split('.')
    # 只支持 . 分隔，不支持数组索引 [0]
```

**场景不匹配**:
- `qr_codes[0].data` 这种数组索引路径无法正确解析
- HTTP 响应的嵌套 JSON 结构可能无法正确访问

### 3.4 变量提取节点存储位置错误

**问题**: `variable_extractor` 节点将提取的变量直接写入 `shared_state` (line 798)

```python
for k, v in extracted.items():
    context.shared_state[k] = v  # 直接写入 shared_state
```

**正确行为应该是**:
- 将提取的变量写入当前节点的 `node_outputs`
- 下游节点通过 `{{#node_id.key#}}` 引用

---

## 四、解决方案建议

### 方案 A: 明确变量作用域 (推荐)

**核心思想**: 分清全局变量和节点局部变量的用途

| 变量类型 | 存储位置 | 引用语法 | 示例 |
|----------|----------|----------|------|
| 全局变量 | `shared_state` | `{{variable_name}}` | `{{institution}}`, `{{qr_content}}` |
| 节点输出 | `node_outputs` | `{{#node_id.key#}}` | `{{#node_1.extracted_id#}}` |

**修改点**:

1. **在执行开始时初始化**:
```python
async def run(self, context: DocumentContext, ...):
    # 确保初始化
    if not hasattr(context, "node_outputs"):
        context.node_outputs = {}
    if not hasattr(context, "shared_state"):
        context.shared_state = {}
```

2. **variable_extractor 节点修改**:
```python
# 当前 (错误)
context.shared_state[k] = v

# 修改为 (正确)
context.node_outputs[node_id][k] = v
```

3. **LLM extraction 模式修改**:
```python
# 当前
context.shared_state[f"extracted_{key}"] = value

# 修改为
context.node_outputs[node_id][key] = value
```

---

### 方案 B: 增强 `interpolate_vars` 函数

**核心思想**: 让变量插值更智能、更健壮

**增强功能**:

1. **支持数组索引语法**:
```python
def get_nested_val(d: dict, path: str):
    # 支持 qr_codes[0].data 语法
    # 支持 data.items[0].name 语法
    pass
```

2. **添加调试日志**:
```python
def interpolate_vars(val: any, state: dict, node_outputs: dict = None) -> any:
    # 记录每个变量的解析过程
    logger.debug(f"[VariableInterpolation] Interpolating: {val}")
    # ... 解析过程
    logger.debug(f"[VariableInterpolation] Result: {val}")
    return val
```

3. **添加变量未找到警告**:
```python
# 当 {{#node_id.key#}} 找不到时，记录警告而非静默返回空
if replacement == "" and original_var.startswith('#'):
    logger.warning(f"Variable not found: {{#{match}#}}}}")
```

---

### 方案 C: 统一节点输出 Schema

**核心思想**: 每个节点的输出结构标准化

**标准输出结构**:
```python
node_output = {
    "passed": bool,           # 节点是否通过
    "message": str,           # 执行消息
    "data": dict,             # 节点提取的数据 (供下游使用)
    "error": str | None       # 错误信息
}
```

**修改点**:

1. **所有节点统一输出格式**:
```python
# HTTP 节点
context.node_outputs[node_id] = {
    "passed": node_passed,
    "message": node_msg,
    "data": {
        "status_code": status_code,
        "response_json": resp_json,
        "response_text": response.text
    },
    "error": None
}

# LLM 节点
context.node_outputs[node_id] = {
    "passed": node_passed,
    "message": node_msg,
    "data": llm_data,  # 直接使用提取的数据
    "error": None
}

# Variable Extractor 节点
context.node_outputs[node_id] = {
    "passed": node_passed,
    "message": node_msg,
    "data": extracted_groups,
    "error": None
}
```

2. **插值时统一从 `.data` 字段获取**:
```python
# {{#http_node.data.response_json.status#}}
replacement = get_nested_val(
    node_outputs.get("http_node", {}).get("data", {}),
    "response_json.status"
)
```

---

## 五、测试用例

### 用例 1: 变量提取 → 下游引用

```yaml
节点 1 (variable_extractor):
  pattern: "ID:(?P<report_id>[A-Z0-9]+)"
  source_field: "qr_content"

节点 2 (http_call):
  url_template: "https://api.example.com/verify?id={{#node_1.data.report_id#}}"
  预期: URL 正确填充 report_id
```

### 用例 2: LLM 提取 → 下游引用

```yaml
节点 1 (text_llm):
  operation_mode: "extraction"
  prompt: "提取报告编号和校验码"

节点 2 (http_call):
  url_template: "https://api.example.com/verify?sn={{#node_1.data.报告编号#}}"
  预期: URL 正确填充报告编号
```

### 用例 3: HTTP 响应 → 下游引用

```yaml
节点 1 (http_call):
  url_template: "https://api.example.com/get"
  json_path: "$.data.status"

节点 2 (comparison):
  field_a: "{{#node_1.data.response_json.data.status#}}"
  field_b: "active"
  预期: 正确比较 HTTP 响应中的状态值
```

---

## 六、实施计划

### 阶段 1: 问题诊断 (1-2 天)

- [ ] 添加详细的调试日志到 `interpolate_vars`
- [ ] 创建测试用例验证当前变量传递行为
- [ ] 确认哪些场景下变量传递失败

### 阶段 2: 核心修复 (3-5 天)

- [ ] 实施**方案 A** (明确变量作用域)
- [ ] 修改 `variable_extractor` 节点
- [ ] 修改 LLM extraction 模式
- [ ] 修改 HTTP 节点输出结构

### 阶段 3: 功能增强 (2-3 天)

- [ ] 实施**方案 B** (增强插值函数)
- [ ] 支持数组索引语法
- [ ] 添加变量未找到警告

### 阶段 4: 测试验证 (2-3 天)

- [ ] 运行上述测试用例
- [ ] 回归测试现有规则
- [ ] 性能测试

---

## 七、技术风险

| 风险项 | 影响 | 缓解措施 |
|--------|------|----------|
| 破坏现有规则 | 高 | 添加兼容层，同时支持新旧两种语法 |
| 性能下降 | 中 | 优化 `interpolate_vars` 函数 |
| 调试困难 | 中 | 添加详细日志，便于排查 |

---

## 八、相关文件清单

需要修改的文件：

1. `backend/app/engine/core.py` - 核心引擎逻辑
2. `backend/app/engine/base.py` - 基础类定义
3. `backend/tests/engine/test_engine.py` - 测试用例
4. `frontend/src/components/RuleGraphEditor.vue` - 前端变量面板

---

*文档创建时间: 2026-06-23*
*预计修复版本: v2.0.0*
