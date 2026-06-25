# PPAP 算子精准度审计报告

> 审计日期: 2026-06-25
> 审计范围: 13 个算子 + 4 个内联逻辑类型

---

## 一、使用 AI 的算子

### 1. InstitutionSnifferOperator

**文件**: [sniffer_operator.py](../../backend/app/engine/operators/sniffer_operator.py)
**使用 AI**: 是 — Stage 2 调用 `aliyun_service.call_qwen_async()`（文本 LLM），Stage 3 调用 VisionLLM（视觉 fallback）

#### 算法架构

| Stage | 方法 | 速度 | 精度 | 说明 |
|-------|------|------|------|------|
| 0 | 密码学证书直取 | 亚毫秒 | 100% | 从 PDF 数字签名证书提取组织名称 |
| 1 | 本地正则匹配 | 1ms | 高 | 硬编码高频机构正则（CTI/SGS/CCIC/TUV 等） |
| 2 | LLM 语义提取 | 1-5s | 中高 | 调用 Qwen 模型从第一页文本提取机构名 |
| 3 | Vision Fallback | 3-10s | 中 | 扫描件无文本时用 VLM 识别页眉 LOGO |

#### 精准度问题

**1. LLM JSON 解析脆弱（中风险）**

当前代码用 `re.search(r'\{.*\}', llm_res.replace('\n', ''))` 贪婪匹配 JSON。当 LLM 返回 markdown 代码块时（```json...```），正则可能截断或匹配到错误内容。

```python
# 当前脆弱写法
json_match = re.search(r'\{.*\}', llm_res.replace('\n', ''))
```

改进方案：先剥离 markdown 代码块标记，再用 `json.loads()` 直接解析：

```python
import json
cleaned = llm_res.strip()
if cleaned.startswith("```"):
    cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]
data = json.loads(cleaned)
```

**2. 证书机构归一化不全（低风险）**

Stage 0 只处理了 8 个知名机构（CTI/SGS/CCIC/TUV/Intertek/WEIPU/BV/PONY），遇到其他机构的数字证书时直接返回原始组织名（`clean_name`），不做标准归一化。

**3. Vision fallback 未复用全局 AI 配置（中风险）**

```python
# sniffer 中直接硬编码创建 AsyncOpenAI
client = AsyncOpenAI(
    api_key=ai_config["api_key"],
    base_url=ai_config.get("base_url", "https://api.openai.com/v1")
)
```

没有通过 `ai_config_service` 获取 `ModelProfile` 中的视觉模型配置，导致前端配置的视觉模型在此处不生效。

**4. 文本长度固定 1200 字符（低风险）**

`text_to_analyze = first_page_text[:1200]` 在大段文字场景可能截断关键信息。建议提升到 3000 或根据页面布局动态提取页眉区域。

---

### 2. TextLLMOperator

**文件**: [text_llm_operator.py](../../backend/app/engine/operators/text_llm_operator.py)
**使用 AI**: 是 — OpenAI-compatible API 调用文本 LLM（默认 `gpt-4o-mini`）

#### 算法架构

- 通过 `ai_config_service` 获取多 profile 模型配置
- 支持两种模式：`verification`（通过/不通过）和 `extraction`（提取任意字段）
- 60 秒超时熔断机制
- 无 API key 时 fallback 到 mock 响应

#### 精准度问题

**1. 上下文窗口固定 3000 字符（中风险）**

`max_chars = 3000` 硬编码，不根据模型实际上下文窗口调整。不同模型（如 `gpt-4o-mini` 128K vs `gpt-3.5-turbo` 16K）的上下文能力差异大。

改进方案：从 `ModelProfile` 读取 `max_tokens` 字段推算可用文本长度，或做成可配置参数。

**2. Mock fallback 置信度不真实（中风险）**

无 API key 时返回：

```python
{
    "passed": True,
    "confidence": 0.95,  # 过高！模拟数据不应带高置信度
    "reason": "[Mock] 通过大模型语义分析，提取到了符合要求的信息。"
}
```

模拟数据建议设 `confidence=0.5`（不确定），或显式标记 `skipped=true` 让下游知晓未执行真实分析。

**3. 缺少防幻觉 prompt 指令（中风险）**

当前 verification 模式的 system prompt 没有要求 LLM 必须引用原文证据。容易产生幻觉。

改进：system prompt 末尾添加：

```
你必须基于文档文本中的具体语句来做出判断，不能凭空推断。
如果文档中没有明确提及，返回 {"passed": False, "confidence": 0.0, "reason": "文档中未提及相关信息"}
```

**4. 缺少重试机制（低风险）**

60s 超时后直接返回降级结果。建议对 `TimeoutError` 和 `APIError` 增加 1-2 次自动重试（指数退避）。

---

### 3. VisionLLMOperator

**文件**: [vision_llm_operator.py](../../backend/app/engine/operators/vision_llm_operator.py)
**使用 AI**: 是 — Vision-Language Model 分析文档图像（默认 `gpt-4o`）

#### 算法架构

- 支持全页渲染和裁剪区域（`crop_bbox`）两种模式
- 2x zoom 渲染（~144 DPI），平衡成本和质量
- 通过 `ai_config_service` 获取视觉模型配置
- 无 API key 时 fallback 到 mock 响应

#### 精准度问题

**1. 缺少 60s 超时熔断（高风险）**

对比 TextLLM 的 `asyncio.wait_for(..., 60.0)`，VisionLLM **没有设置超时**。视觉模型通常更慢，大分辨率图片可能超过 120s，导致请求永久挂起。

**2. zoom 固定为 2.0（中风险）**

144 DPI 对全页足够，但对小区域文字（如 `crop_bbox` 中提取的印章文字）分辨率不足。建议对有 `crop_bbox` 的区域使用 3.0-4.0 zoom。

**3. 同样缺少重试机制（低风险）**

与 TextLLM 相同，建议增加网络重试。

---

## 二、不使用 AI 的算子

### 4. StampDetectionOperator

**文件**: [stamp_operator.py](../../backend/app/engine/operators/stamp_operator.py)
**算法**: OpenCV HSV 红色掩膜 → 膨胀 → 轮廓检测 → 圆度过滤 → 邻近合并

#### 精准度问题

**1. HSV 红色阈值偏宽，误检率高（高风险）**

```python
lower_red1 = np.array([0, 50, 50])   # 饱和度下限 50 偏低
```

饱和度 50 会把红色页眉、表格线、红色文字都检测为印章候选。建议提纯：

```python
lower_red1 = np.array([0, 80, 80])   # 提高饱和度/明度下限
lower_red2 = np.array([160, 80, 80])
```

**2. 跨页骑缝章未关联（中风险）**

`_merge_nearby(page_candidates)` 仅在单页内合并。骑缝章跨页的两半各自为独立条目，无法识别为同一印章。

改进方案：添加跨页距离判断，相同 X 坐标范围的上下相邻页面候选进行跨页合并。

**3. 小印章检测精度不足（低风险）**

2x zoom 对 1-2cm 小印章像素不足。建议对候选区域像素面积 < 10000 的自动提升 zoom 到 3.0 重新检测。

**4. 没有反光/阴影预处理（低风险）**

扫描件常有反光导致红色通道偏移。建议添加高斯模糊预处理。

**5. 没有 OCR 验证印章文字（低风险）**

仅靠几何特征可能把红色圆形贴纸误检为章。改进方向：候选区域用 OCR 验证是否包含机构文字。

---

### 5. TableVerificationOperator

**文件**: [table_operator.py](../../backend/app/engine/operators/table_verification_operator.py)
**算法**: pdfplumber 提取表格 → 清洗 → Decimal 高精度汇总

#### 精准度问题

**1. 复杂表格提取不稳定（中风险）**

pdfplumber 在以下场景准确率下降：合并单元格、无边框表格、旋转文本。建议加兜底：检测到合并单元格时尝试 Camelot 或基于规则的二次提取。

**2. 会计格式解析不够完整（低风险）**

`_parse_financial_number` 处理了 `(123.45)` 和 `-123.45` 格式，但中文金额 `100.00元` 格式需要确认 `元` 字外的其他中文单位覆盖。

**3. 表头判断硬编码（中风险）**

```python
# 跳过表头 row[0]
for row in cleaned_table[1:]:
```

如果表格无表头（纯数据表），跳过第一行会导致漏算。建议：检测第一行是否含非数字文本来自动识别表头。

**4. 没有列类型推断（低风险）**

所有列都尝试解析为数字，但有些列是文本描述。建议先识别数字列再汇总。

---

### 6. DocumentDiffOperator

**文件**: [diff_operator.py](../../backend/app/engine/operators/diff_operator.py)
**算法**: PyMuPDF 提取文本 → whitespace 归一化 → difflib.SequenceMatcher

#### 精准度问题

**1. Whitespace 归一化过度，段落结构丢失（中风险）**

```python
current_text_clean = re.sub(r'\s+', ' ', current_text).strip()
```

把所有换行符压缩为空格，无法区分「甲乙丙」和分行排列的「甲\n乙\n丙」。建议保留换行符用于段落级比对：

```python
# 保留段落结构
paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
```

**2. 差异上下文仅 20 字符（低风险）**

对中文文档，20 个字符可能不足以理解差异的语义上下文。建议改为可配置（默认 50）。

**3. 大文本分句逻辑有 bug（中风险）**

```python
re.split(r'([。；;!?！？\n])', ...)
```

保留分隔符会导致句子列表长度翻倍且含空字符串，影响 SequenceMatcher 准确率。

改进：改为 `re.split(r'[。；;!?！？\n]+', text)`（不保留分隔符）并过滤空串。

**4. 相似度计算公式不带权重（低风险）**

`sm.ratio()` 对所有操作一视同仁。文档比对中 delete/insert 应获得更高权重。建议使用加权相似度。

**5. 浮点精度风险（低风险）**

`similarity_pct >= threshold` 在 threshold=100.0 时可能出现 99.999999 被判定不通过。建议：

```python
if round(similarity_pct, 2) >= threshold:
```

---

### 7. QRScannerOperator

**文件**: [qr_operator.py](../../backend/app/engine/operators/qr_operator.py)
**算法**: OpenCV QRCodeDetector 三层策略（detectAndDecodeMulti → detectAndDecode → 增强灰度）

#### 精准度: 基本成熟

三层 fallback 策略设计合理。改进建议：

1. **小二维码检出率** — 200 DPI 对密集排版的小二维码不够。建议：对未解码页面用 300 DPI 重试一次。
2. **多二维码场景优先级** — `qr_data[0]` 取第一个二维码，但页面可能同时有追溯码和防伪码。建议允许按位置优先级选择。

---

### 8. SignatureOperator

**文件**: [signature_operator.py](../../backend/app/engine/operators/signature_operator.py)
**算法**: pyHanko 解析 PDF 数字签名 → 验证完整性

#### 精准度: 理论 100%（基于密码学）

改进建议：
1. **证书吊销检查** — 当前未检查 CRL/OCSP，已吊销证书仍可能通过验证。建议添加可选吊销检查。
2. **签名时间戳验证** — 未验证 RFC 3161 时间戳。建议添加时间戳合法性校验。
3. **签名策略分析** — 建议区分 PAdES/Basic/EPES 等签名类型。

---

### 9. RevisionCheckOperator

**文件**: [revision_operator.py](../../backend/app/engine/operators/revision_operator.py)
**算法**: 正则匹配 xref 段落数 → 交叉验证签名计数（Revision ≤ Sig_Count + 1）

#### 精准度: 算法设计合理

改进建议：
1. **xref 正则误匹配风险（中风险）** — 全文搜索 `xref` 可能匹配到注释中的文本。建议只搜索文件末尾最后几 KB（incremental update 总是在文件末尾追加）。
2. **异常时默认放行的安全风险（高风险）**

```python
# 检测异常时返回 pass_status=True！
return OperatorResult(operator_name=self.name, pass_status=True, ...)
```

恶意文档可利用检测异常绕过篡改检查。建议改为 `pass_status=False` 并记录异常。

---

### 10. PDFInfoOperator

**文件**: [pdf_info_operator.py](../../backend/app/engine/operators/pdf_info_operator.py)
**算法**: PyMuPDF 提取全文 → 按字符数判断 PDF 类型

#### 精准度问题

**文本型 PDF 判定阈值过宽（中风险）**

```python
if total_chars > max(5, len(doc) * 2):  # 每页平均仅需 2 字符
```

一个 100 页纯扫描件若有 OCR 产生的几个散乱字符（如页码数字），会被误判为文本型 PDF。

改进方案：将阈值提高到每页 20 个字符：

```python
if total_chars > max(20, len(doc) * 20):
```

---

### 11. OnlineVerificationOperator

**文件**: [online_verification_operator.py](../../backend/app/engine/operators/online_verification_operator.py)
**算法**: QR 内容 → 正则提取参数 → 组装 URL → DocumentDiff 比对

#### 精准度问题

**1. 简化语法转换的 re.escape 过度保护（中风险）**

`_convert_simple_pattern()` 把特殊字符（`.`、`-` 等）也转义了，如果用户的正则本身就包含特殊字符语义则会被破坏。

**2. 相似度阈值默认 95% 过于严格（中风险）**

在线拉取的参考文档可能含平台水印、页眉页脚差异。建议默认值改为 85%。

**3. 缺少请求去重缓存（低风险）**

同一个 URL 在多次校验中重复下载。建议添加 URL → pdf_bytes 缓存（TTL 5 分钟）。

---

### 12. URLFetchOperator

**文件**: [url_fetch_operator.py](../../backend/app/engine/operators/url_fetch_operator.py)
**算法**: HTTP GET → PDF 校验 → PDFInfoOperator 解析

#### 精准度: 简单可靠

改进建议：添加 User-Agent 伪装（部分服务器拦截无 UA 请求）。

---

### 13. TemplateFormatterOperator

**文件**: [template_formatter_operator.py](../../backend/app/engine/operators/template_formatter_operator.py)
**算法**: 模板字符串替换

#### 精准度: 纯字符串操作，无精度问题

---

## 三、内联逻辑类型（core.py 中）

### 14. regex_match / keyword_match

**文件**: [core.py](../../backend/app/engine/core.py)
**算法**: 全文正则搜索 / 子串匹配

#### 精准度问题

1. **关键词搜索区分大小写** — `in` 操作符不支持大小写不敏感。建议加 `lower()` 归一化。
2. **正则无超时保护** — 恶意用户可构造 ReDoS（如 `(a+)+b`）使 CPU 100%。建议添加 `re._compile` 超时或使用 `regex` 库。

### 15. comparison (data-compare)

**算法**: 字符串完全匹配

#### 精准度问题

`str(val_a).lower() == str(val_b).lower()` 只做精确匹配。建议支持相似度阈值（如 difflib 比值 > 0.9）和 whitespace 归一化。

### 16. variable_extractor

**算法**: 正则命名捕获组

#### 精准度: 标准正则提取，无问题

---

## 四、AI 使用总览

| 算子 | 使用 AI | AI 类型 | 默认模型 |
|------|---------|---------|----------|
| InstitutionSnifferOperator | **是** | LLM + VLM | Qwen + gpt-4o |
| TextLLMOperator | **是** | LLM | gpt-4o-mini |
| VisionLLMOperator | **是** | VLM | gpt-4o |
| StampDetectionOperator | 否 | — | — |
| TableVerificationOperator | 否 | — | — |
| DocumentDiffOperator | 否 | — | — |
| QRScannerOperator | 否 | — | — |
| SignatureOperator | 否 | — | — |
| RevisionCheckOperator | 否 | — | — |
| PDFInfoOperator | 否 | — | — |
| OnlineVerificationOperator | 否 | — | — |
| URLFetchOperator | 否 | — | — |
| TemplateFormatterOperator | 否 | — | — |

---

## 五、精准度改进优先级

### 高风险（影响正确性）

| # | 算子 | 问题 | 改进方案 |
|---|------|------|----------|
| 1 | StampDetection | HSV 阈值偏宽，误检率高 | 饱和度 50→80，明度 50→80 |
| 2 | RevisionCheck | 异常时默认放行 | `pass_status=True` → `pass_status=False` |
| 3 | VisionLLM | 无 60s 超时熔断 | 添加 `asyncio.wait_for(..., 60.0)` |
| 4 | PDFInfo | 文本型误判阈值过宽 | 2→20 字符/页 |

### 中风险（影响可靠性）

| # | 算子 | 问题 | 改进方案 |
|---|------|------|----------|
| 5 | Sniffer | Vision fallback 未复用全局配置 | 接入 ai_config_service |
| 6 | TextLLM | Mock confidence 不真实 | 0.95→0.5 或标记 skipped |
| 7 | TextLLM | 缺少防幻觉指令 | prompt 增加引用原文要求 |
| 8 | TextLLM/VisionLLM | 缺少重试机制 | 增加指数退避重试 |
| 9 | Sniffer | JSON 解析脆弱 | 改用 json.loads 直接解析 |
| 10 | Diff | 段落结构因 whitespace 归一化丢失 | 保留换行符 |
| 11 | Diff | 大文本分句逻辑有 bug | 不保留分隔符，过滤空串 |
| 12 | OnlineVerification | re.escape 过度保护 | 分段处理字面量和通配符 |
| 13 | OnlineVerification | 相似度阈值 95% 过严 | 默认改为 85% |
| 14 | Table | 表头判断硬编码 | 自动识别表头行 |
| 15 | core.py | 关键词搜索区分大小写 | 添加 lower() 归一化 |
| 16 | core.py | 正则无 ReDoS 保护 | 添加超时机制 |

### 低风险（影响体验）

| # | 算子 | 改进方案 |
|---|------|----------|
| 17 | Sniffer | 证书机构别名库扩展 |
| 18 | QR | 小二维码 300 DPI 重试 |
| 19 | Signature | 添加 CRL/OCSP 吊销检查 |
| 20 | Signature | 添加时间戳验证 |
| 21 | Revision | xref 搜索范围限于文件末尾 |
| 22 | Diff | 上下文长度可配置 |
| 23 | Table | 中文金额单位覆盖补全 |
| 24 | Table | 列类型自动推断 |
