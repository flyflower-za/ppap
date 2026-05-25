# 变更记录

> 日期: 2026-05-25
> 范围: P0 Revision 检测 + P1 上传并发控制 + 修复校验规则诊断报告加载失败 + 数字签名检测修复 + 端口优化 & PDF 渲染修复 + 签名验证工具集

---

## 一、P0 — Revision 检测（增量更新/二次修改）

### 问题背景

PDF 规范允许增量更新 (Incremental Update)。一个已签名的 PDF 可以被追加内容（表单填写、添加注释、电子签章平台追加签章外观）**而不破坏原签名的密码学有效性**。因此仅验证签名完整性不足以检测二次修改，必须额外检查 PDF 的 Revision 版本号。

**判定逻辑：** 签名有效 + `Revision > 1` = 签名后内容被修改过，存在篡改风险。

### 实现方案

#### 1. 核心检测模块

**文件:** `backend/app/checkers/revision_checker.py` (新建)

- `count_pdf_revisions(pdf_bytes)` — 通过正则解析 PDF 原始内容的 `xref` 节数量，计数修订版本
- `check_revision_after_signing(pdf_bytes, sig_result)` — 跨引用签名结果，判断签名后是否被修改
- PyMuPDF 补充验证：xref_length、Catalog 对象修改次数

#### 2. 引擎算子

**文件:** `backend/app/engine/operators/revision_operator.py` (新建)

- `RevisionCheckOperator(BaseOperator)` — 封装 revision 检测逻辑
- 自动加入引擎默认算子集合（与 `PDFInfoExtractor`、`InstitutionSniffer` 同级）
- 将 `pdf_revisions` 写入 `shared_state`，供后续规则和条件分支引用

#### 3. 引擎 DAG 节点

**文件:** `backend/app/engine/core.py` (修改)

- 注册 `RevisionCheckOperator` 到 `_available_operators`
- `_determine_required_operators()` 加入 `"RevisionCheck"` 默认算子
- DAG 节点类型 `revision_check` 分支处理：
  - `maxRevisions` 参数：允许最大修订次数（0=使用默认逻辑）
  - `allowIncrementalUpdates` 参数：是否允许合法增量更新
  - `is_tampered_after_sign` 为 true 时阻断

#### 4. 前端规则编辑器

**文件:** `frontend/src/components/RuleGraphEditor.vue` (修改)

- `NODE_REGISTRY` 新增 `revision-check` 节点定义
- 节点属性面板：最大修订次数 (el-input-number)、允许增量更新 (checkbox)
- 条件提示区域新增 `revision_count`、`is_tampered` 变量提示

#### 5. 校验流水线集成

**文件:** `backend/app/tasks/verification_tasks.py` (修改)

- 导入 `check_revision_after_signing` 供校验任务引用

### 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/checkers/revision_checker.py` | 新增 | xref 计数 + 签名交叉引用检测 |
| `backend/app/checkers/__init__.py` | 修改 | 导出 revision_checker 模块 |
| `backend/app/engine/operators/revision_operator.py` | 新增 | RevisionCheckOperator 算子 |
| `backend/app/engine/core.py` | 修改 | 注册算子、DAG 节点处理、默认启用 |
| `backend/app/tasks/verification_tasks.py` | 修改 | 导入 revision_checker |
| `frontend/src/components/RuleGraphEditor.vue` | 修改 | 新增 revision-check 节点 UI |

---

## 二、P1 — 上传并发控制

### 问题背景

前端批量上传多个 PDF 时，原实现使用 `Promise.all(fileList.value.map(...))` 一次性并发所有上传请求。浏览器对同一域名的并发请求有限制（通常 6 个），大量并发会导致浏览器卡死、请求超时。

### 实现方案

**文件:** `frontend/src/views/TaskCenterPage.vue` (修改)

- `handleConfirmUpload()` 改为 **worker 池模式** (bounded concurrency)
- 默认并发上限 **3**（通过 `concurrencyLimit ref` 控制）
- 任务队列使用 `Array.shift()` 动态分配，worker 空闲时自动取下一个任务
- 失败单个文件不影响其他文件上传

### 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/views/TaskCenterPage.vue` | 修改 | 新增 concurrencyLimit ref，重写上传逻辑为 worker 池模式 |

---

## 三、Bug 修复 — 校验规则诊断报告无法加载

### 问题现象

历史记录 → 文件详情页中，右侧"校验规则诊断报告"区域始终显示空状态提示：
> "校验正在进行中，完成后将自动在此生成详细报告..."

即使校验已完成、数据库中有完整结果数据，报告依然为空。

### 根因分析

`backend/app/schemas/file.py` 的 `FileResponse.extract_json` validator 存在 dict vs ORM 对象处理顺序错误。

**数据流：**
```
verify_pdf → DB: file.verification_result = JSON string
file_service.get_file_detail() → json.loads(verification_result) → parsed dict
FileDetailResponse(id=..., verification_result=parsed_dict, ...) → kwargs → dict
extract_json(mode='before') → 接收 dict
```

**Bug：** validator 顶层的条件判断使用 `getattr()` / `hasattr()` 检查 `data`：
```python
if getattr(data, 'verification_result_json', None) is not None:  # ①
   return data
if hasattr(data, 'verification_result') and data.verification_result:  # ②
```

当 `data` 是 **dict** 时（从 keyword-arg 构造而来）：
- ① `getattr(dict_instance, 'verification_result_json')` → `None`（dict 没有这个属性！）
- ② `hasattr(dict_instance, 'verification_result')` → `False`（同样不识别 key）
- → 整个 validator 跳过转换，`verification_result` 被 Pydantic 忽略为 extra field
- → `verification_result_json` 保持默认值 `None` → 前端显示空状态

只有当 `data` 是 SQLAlchemy ORM 对象时才走对了分支（Path B），但 `FileDetailResponse` 是通过 keyword-arg 构造的，收到的总是 dict。

### 修复

重构 `extract_json` validator，先判断 `isinstance(data, dict)` 再处理：

```
Is data a dict?
  ├─ Yes → Path A: 用 .get() / 下标访问 verification_result → 转为 verification_result_json
  └─ No  → Path B: 用 getattr/hasattr (SQLAlchemy ORM 对象路径)
```

| 文件 | 操作 | 关键变化 |
|------|------|----------|
| `backend/app/schemas/file.py` | 修改 | `extract_json` 改为 dict-first，先 `isinstance(data, dict)` 再用 `.get()` 访问 key |

---

## 四、数字签名检测与显示修复

### 问题现象

数字签名被检测到但未在前端 UI 中正确显示。

### 根因分析

1. **签名验证器未处理加密 PDF**：原始 `sig_verifier.py` 在遇到加密 PDF 时直接失败，无法自动解密后验证
2. **pyHanko 兼容性问题**：某些国密签名或特殊格式的 PDF 与 pyHanko 不完全兼容
3. **API Schema 校验不匹配**：`verification_result` 字段在前端期望的是 JSON 对象，但后端返回的是字符串
4. **前端字段路径错误**：`FileDetailPage.vue` 使用 `verification_result` 而非 `verification_result_json` 读取数据

### 修复

| 文件 | 操作 | 关键变化 |
|------|------|----------|
| `backend/app/checkers/sig_verifier.py` | 修改 | 增加加密 PDF 自动解密逻辑，失败时 fallback 到手动检查器 |
| `backend/app/checkers/sig_verifier_manual.py` | 新增 | 独立的手动签名检查器，处理 pyHanko 不兼容的情况 |
| `backend/app/schemas/file.py` | 修改 | 修正 `extract_json` validator 的 dict/ORM 对象处理顺序 |
| `frontend/src/views/FileDetailPage.vue` | 修改 | 修正字段路径为 `verification_result_json`，更新签名显示逻辑 |

---

## 五、端口配置优化与 PDF 渲染修复

### 问题背景

1. **端口冲突**：后端默认 8000 端口与其他服务冲突
2. **PDF.js worker 加载失败**：本地 worker 文件因 MIME 类型检查被浏览器拒绝
3. **nginx MIME 类型配置缺失**：`.mjs` 文件返回错误的 Content-Type

### 修复

| 文件 | 操作 | 关键变化 |
|------|------|----------|
| `frontend/vite.config.ts` | 修改 | 代理端口改为 31234 |
| `frontend/src/views/FileDetailPage.vue` | 修改 | PDF.js worker 改用 CDN 加载 |
| `deploy/docker-compose.yml` | 修改 | 环境变量和端口映射更新为 31234 |
| `deploy/nginx.conf` | 修改 | 新增 `.mjs` MIME 类型配置，优化 location 规则 |
| `deploy.sh` | 修改 | API 文档地址更新 |
| `CHANGELOG.md` | 新增 | 详细变更日志 |
| `setup_firewall.sh` | 新增 | 防火墙配置脚本 |

---

## 六、已更新文档

| 文件 | 说明 |
|------|------|
| `check.md` | 差距分析中的 Revision 检测、上传并发控制、数字签名验证状态已更新为 ✅ |
| `FEATURES.md` | 新增功能特性文档 |
