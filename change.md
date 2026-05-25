# PPAP 引擎变更记录 (Changelog)

## 新增核心校验算子 (Operators)

本次升级在原有架构的基础上，向编排引擎中扩展了 4 个高级校验算子模块，以覆盖更复杂的非结构化与半结构化文档审核场景：

1. **物理公章/印章检测算子 (`StampDetectionOperator`)**
   - **路径**: `backend/app/engine/operators/stamp_operator.py`
   - **功能**: 使用 OpenCV 提取红色 HSV 颜色空间，结合形态学与轮廓面积特征，精准识别扫描件中的物理盖章及其具体坐标位置。

2. **水印分析算子 (`WatermarkOperator`)**
   - **路径**: `backend/app/engine/operators/watermark_operator.py`
   - **功能**: 使用 `pdfplumber`/`PyMuPDF` 解析文档底层 Text Dict。能够拦截超大字体的底纹以及命中了特定风险词汇（如"作废", "DRAFT", "CONFIDENTIAL"）的水印。

3. **智能对比差异算子 (`DocumentDiffOperator`)**
   - **路径**: `backend/app/engine/operators/diff_operator.py`
   - **功能**: 根据传入的 `base_document_url` 拉取基准底稿，并使用 `difflib.SequenceMatcher` 实现与当前待审文档的序列级文本防篡改比对，输出详细的增删改列表与相似度评分。

4. **结构化表格提取与对账算子 (`TableVerificationOperator`)**
   - **路径**: `backend/app/engine/operators/table_operator.py`
   - **功能**: 深度集成 `pdfplumber` 表格解析引擎，精确还原复杂财报或清单的行列坐标；并提供 `target_column_index` 参数支持对指定列（清洗货币单位后）的自动化累加对账。

## 核心引擎调整

- **模块挂载 (`backend/app/engine/core.py`)**:
  - 在 `VerificationEngine._available_operators` 中实例化并注册了上述 4 个算子。
  - 扩展了 `_determine_required_operators` 的 AST 逻辑树节点解析支持（`stamp_detection`, `watermark_detection`, `document_diff`, `table_verification`）。
- **沙盒接口暴露 (`backend/app/api/modules.py`)**:
  - 更新 `list_modules` 方法的返回值，补充了新算子的名称、描述以及专有的动态调试参数（如水印关键词列表、对比阈值百分比等）。

## 前端与容器运维修正

- **沙盒接口防缓存穿透 (`frontend/src/api/modules.ts`)**:
  - 修复了浏览器由于强缓存策略导致无法刷新最新算子列表的 Bug，通过在 `client.get('/modules/list')` 请求尾部追加时间戳参数 `?_t=xxx`（Cache-Buster）解决。
- **容器重启生效**:
  - 触发了 `docker restart ppap-backend` 热重启后端服务。
  - 触发了 `docker compose up -d --build frontend` 重构前端 Nginx 静态分发镜像。
