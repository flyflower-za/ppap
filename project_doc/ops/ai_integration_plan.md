# AI 介入规划分析

> 基于精准度审计报告（accuracy_analysis.md）对各功能模块的 AI 介入可行性分析

---

## 一、已使用 AI 的算子（需要加强）

### 1. InstitutionSnifferOperator
**当前 AI**: LLM + VLM
**加强方向**:
- LLM JSON 解析脆弱性修复（改用 `json.loads` 替代正则贪婪匹配）
- Vision fallback 接入 `ai_config_service` 统一配置，而非硬编码
- 增加防幻觉 prompt 指令

### 2. TextLLMOperator
**当前 AI**: LLM（gpt-4o-mini）
**加强方向**:
- 上下文窗口根据 `ModelProfile.max_tokens` 动态调整而非固定 3000 字符
- Mock fallback 置信度从 0.95 降至 0.5 或标记 `skipped`
- 添加防幻觉 prompt（要求引用原文证据）
- 增加指数退避重试机制

### 3. VisionLLMOperator
**当前 AI**: VLM（gpt-4o）
**加强方向**:
- 添加 60s 超时熔断（目前完全没有超时）
- zoom 参数根据场景动态调整（全页 2x，crop 小区域 3-4x）
- 增加重试机制

---

## 二、建议新接入 AI 的模块

### P0 — 强烈推荐

#### 4. StampDetectionOperator — VLM 替代 HSV 红膜检测
| 维度 | 当前（OpenCV HSV） | 改进（VLM） |
|------|-------------------|-------------|
| 误检率 | ~30-40%（红色页眉/表格线/文字触发） | <5% |
| 检测能力 | 仅红色圆形 | 任意印章 + 文字识别 |
| 跨页关联 | 不支持 | 可通过语义判断同一印章 |

**方案**: 两步级联
1. HSV 粗筛候选区域（低阈值高召回）
2. VLM 验证候选区域 + 提取印章文字

#### 5. PDFInfoOperator — VLM 文档自动分类
**当前**: 仅判断文本型/扫描型（阈值 2 字符/页）

**改进**: VLM 从首页图像识别文档类型（采购订单/质检报告/生产计划单/供应商资质/其他），替代当前用户手动选择文件类型的方式。

---

### P1 — 值得考虑

#### 6. TableVerificationOperator — VLM 复杂表格兜底
**当前**: pdfplumber 提取，在合并单元格/无边框/旋转文本场景准确率下降

**方案**: 两级策略
1. pdfplumber 正常提取 → 校验逻辑一致性
2. 检测到异常特征（合并单元格标记、低置信度）→ VLM 重提 + 汇总数字验证

**风险**: 调用成本可能较高，大表格图片 token 消耗大

#### 7. DocumentDiffOperator — LLM 语义比对
**当前**: SequenceMatcher 逐行比对，水印/页眉页脚等格式差异误报为内容变化

**方案**:
1. 传统算法识别差异行
2. LLM 判断差异是否属于「有意义的内容修改」vs「无关格式差异」
3. 语义等价识别（如 `tel: 021-12345678` = `电话: 021-12345678`）

#### 8. OnlineVerificationOperator — LLM 语义比对
同 DocumentDiffOperer，改善 95% 刚性阈值的误判问题

---

## 三、不推荐接入 AI

| 算子 | 原因 |
|------|------|
| QRScannerOperator | 3 层传统算法 fallback 已成熟，AI 无增值 |
| SignatureOperator | 密码学验证，AI 无帮助 |
| RevisionCheckOperator | PDF 结构分析，算法逻辑已确定 |
| URLFetchOperator | 纯 HTTP 下载，无需改造 |
| TemplateFormatterOperator | 纯字符串替换 |
| regex_match / keyword_match | 标准正则操作 |
| comparison (data-compare) | 值比对，可改进相似度计算但无需 AI |
| variable_extractor | 标准正则提取 |

---

## 四、优先级总览

| 优先级 | 模块 | AI 类型 | 预估效果 | 实现成本 |
|--------|------|---------|----------|----------|
| **P0** | StampDetection | VLM | 误检率 30% → <5%，印章文字提取 | 中（两级级联，需处理性能） |
| **P0** | PDFInfo | VLM | 自动文档分类，省去用户手动选择 | 低（调用一次 VLM） |
| **P1** | TableVerification | VLM 兜底 | 复杂表格场景兜底 | 中高（需判断何时 fallback） |
| **P1** | DocumentDiff | LLM | 减少误报，语义等价识别 | 中（需设计 prompt 判断规则） |
| **P1** | OnlineVerification | LLM | 减少刚性阈值误判 | 低（复用 DocumentDiff） |
| **P2** | Sniffer | — | JSON 解析修复，配置统一 | 低（代码加固） |
| **P2** | TextLLM | — | 防幻觉、重试、动态窗口 | 中（多处改进） |
| **P2** | VisionLLM | — | 超时、zoom 自适应、重试 | 低 |
