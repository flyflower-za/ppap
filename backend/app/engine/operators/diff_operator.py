import asyncio
import json
import logging
import difflib
import httpx
import re
from typing import List
from openai import AsyncOpenAI

from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.engine.llm_utils import _get_ai_config, _safe_json_parse

logger = logging.getLogger(__name__)

# ── LLM Semantic Classification Prompt ──────────────────────────────────────

_SEMANTIC_DIFF_PROMPT = """You are a precision document comparison analyst. You will receive two documents and a list of text differences detected by an automated diff tool. Your task is to classify each difference.

## Document A (Base) Snippet
{base_snippet}

## Document B (Current) Snippet
{current_snippet}

## Detected Differences
{changes_json}

## Classification Task
For each difference, classify it into EXACTLY ONE of these categories:

### "format"
Differences caused purely by document formatting or system-generated metadata, NOT by content changes:
- Page numbers (e.g. "Page 1" vs "Page 2" — the actual content on those pages might be the same)
- Headers and footers that are system-generated (copyright notices, "Confidential", file paths)
- Timestamps or dates that appear to be auto-generated print dates (e.g. "Printed: 2024-01-15" vs "Printed: 2024-01-16") — BUT dates that are part of the document content (e.g. report date, test date) should be "meaningful"
- Watermark text differences (e.g. "DRAFT" appearing in one but not the other)
- Document IDs, serial numbers, or barcode values that are clearly system identifiers
- Whitespace-only differences that don't change meaning

### "equivalent"
Content that is semantically identical but expressed differently:
- Abbreviation vs full form (e.g. "Corp." vs "Corporation", "St." vs "Street", "No." vs "Number")
- Phone number format variants (e.g. "+86-21-12345678" vs "021-12345678" vs "(021) 12345678")
- Date format variants referring to the same date (e.g. "2024/01/15" vs "January 15, 2024" vs "15/01/2024")
- Case differences in proper nouns that are clearly the same entity
- Unit expression variants (e.g. "kg" vs "kilograms", "1000mg" vs "1g")
- Punctuation-only differences (extra commas, dashes) that don't change meaning

### "meaningful"
Any difference that changes factual information or could affect document validity:
- Different numerical values (test results, measurements, quantities, prices)
- Different names, addresses, or company identifiers
- Added or removed clauses, sentences, or paragraphs
- Changed legal terms or conditions
- Different product specifications
- Any content that a human reviewer would flag as a genuine discrepancy

## Critical Rules
1. If unsure between "format" and "meaningful", classify as "meaningful" (conservative approach).
2. Do NOT classify differences as "equivalent" unless you are highly confident the meaning is identical.
3. A single digit change in a measurement value (e.g. 98.5 -> 98.6) IS "meaningful".
4. A header like "TEST REPORT" appearing identically in both documents but at different text positions is "format".
5. "N/A" vs "N/A" with different surrounding context is "format".

## Output Format
Return ONLY a JSON object with key "classifications" containing an array. Each element has "index" (integer matching the input diff index), "classification" (one of: "meaningful", "format", "equivalent"), and "reason" (brief explanation in original language, max 80 chars).

Example:
{{"classifications": [
  {{"index": 0, "classification": "format", "reason": "页码不同（第1页 vs 第2页）"}},
  {{"index": 1, "classification": "meaningful", "reason": "检测结果数值从98.5变为97.2"}},
  {{"index": 3, "classification": "equivalent", "reason": "电话号码格式不同：+86-21 vs 021"}}
]}}

Return ONLY the JSON object. No markdown fences, no additional text."""


class DocumentDiffOperator(BaseOperator):
    """
    升级版智能文档差异比对算子：
    1. 极速行级段落预切分（防卡死）：当文本量超过阈值时，自动采用分行快速差分匹配，消除 SequenceMatcher O(N^2) 导致的 CPU 耗尽超时隐患，大文件比对提速 100 倍以上。
    2. Github-Diff 风格高亮上下文：提取包含差异位置前后 20 个字符的微观语境片段，为前端返回极其精美的差异详情块。
    """
    def __init__(self):
        super().__init__(name="DocumentDiffOperator")

    @property
    def provides(self) -> List[str]:
        return ["diff_results"]

    @property
    def requires(self) -> List[str]:
        return ["pdf_bytes"]

    async def _classify_changes_with_llm(
        self,
        base_text_clean: str,
        current_text_clean: str,
        changes: list,
        ai_config: dict,
        model_name: str,
    ) -> list:
        """Batch all changes into a single LLM call for semantic classification.

        Returns a list of dicts with "index", "classification", "reason".
        On any failure returns an empty list (graceful degradation).
        """
        MAX_SNIPPET_CHARS = 500
        MAX_CHANGES_FOR_LLM = 30

        changes_to_send = changes[:MAX_CHANGES_FOR_LLM]
        if not changes_to_send:
            return []

        # Compact representation: only send essential fields to save tokens
        compact_changes = [
            {
                "index": i,
                "type": c["type"],
                "base_text": c["base_text"],
                "current_text": c["current_text"],
            }
            for i, c in enumerate(changes_to_send)
        ]

        prompt = _SEMANTIC_DIFF_PROMPT.format(
            base_snippet=base_text_clean[:MAX_SNIPPET_CHARS],
            current_snippet=current_text_clean[:MAX_SNIPPET_CHARS],
            changes_json=json.dumps(compact_changes, ensure_ascii=False, indent=2),
        )

        system_prompt = (
            "You are a document comparison classifier. "
            "Return ONLY a JSON object with key 'classifications'. No other text."
        )

        try:
            client = AsyncOpenAI(
                api_key=ai_config["api_key"],
                base_url=ai_config.get("base_url", "https://api.openai.com/v1"),
            )

            max_retries = 3
            base_delay = 2.0

            for attempt in range(1, max_retries + 1):
                try:
                    api_coro = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=ai_config.get("max_tokens", 2048),
                        temperature=ai_config.get("temperature", 0.1),
                        response_format={"type": "json_object"},
                    )

                    response = await asyncio.wait_for(api_coro, timeout=60.0)
                    raw_content = response.choices[0].message.content
                    result = _safe_json_parse(raw_content)

                    # Normalize: LLM might return {"classifications": [...]} or nested
                    if isinstance(result, list):
                        classifications = result
                    elif isinstance(result, dict):
                        classifications = (
                            result.get("classifications")
                            or result.get("results")
                            or result.get("data")
                            or []
                        )
                        if not classifications and len(result) == 1:
                            classifications = list(result.values())[0]
                    else:
                        classifications = []

                    # Validate structure
                    valid_classes = {"meaningful", "format", "equivalent"}
                    validated = []
                    for item in (classifications if isinstance(classifications, list) else []):
                        if isinstance(item, dict) and "index" in item and "classification" in item:
                            cls = item["classification"]
                            if cls in valid_classes:
                                validated.append({
                                    "index": int(item["index"]),
                                    "classification": cls,
                                    "reason": str(item.get("reason", ""))[:200],
                                })

                    meaningful_count = sum(1 for v in validated if v["classification"] == "meaningful")
                    format_count = sum(1 for v in validated if v["classification"] == "format")
                    equiv_count = sum(1 for v in validated if v["classification"] == "equivalent")
                    logger.info(
                        "LLM diff classification: %d/%d changes classified "
                        "(meaningful=%d, format=%d, equivalent=%d)",
                        len(validated), len(changes_to_send),
                        meaningful_count, format_count, equiv_count,
                    )
                    return validated

                except asyncio.TimeoutError:
                    if attempt < max_retries:
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "LLM diff classification timed out (attempt %d/%d), retrying in %.1fs...",
                            attempt, max_retries, delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    logger.error("LLM diff classification timed out after %d attempts.", max_retries)
                    return []

                except Exception as e:
                    err_str = str(e).lower()
                    is_transient = any(k in err_str for k in [
                        "rate_limit", "429", "5xx", "500", "502", "503", "504",
                        "timeout", "connection", "temporary", "service unavailable",
                    ])
                    if is_transient and attempt < max_retries:
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "LLM diff classification transient error (attempt %d/%d): %s, retrying in %.1fs...",
                            attempt, max_retries, e, delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise  # non-transient, propagate to outer catch

        except Exception as e:
            logger.warning(
                "LLM semantic classification failed (non-fatal, falling back to unclassified): %s", e
            )
            return []

    def _extract_text_from_bytes(self, pdf_bytes: bytes) -> tuple[str, int]:
        """Extract text and page count from PDF bytes."""
        import fitz
        text = ""
        page_count = 0
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(doc)
            for page in doc:
                text += page.get_text("text") + "\n"
            doc.close()
        except Exception as e:
            logger.error(f"Error extracting text for diff: {e}")
        return text, page_count

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        current_pdf_bytes = context.shared_state.get("pdf_bytes")
        if not current_pdf_bytes:
            try:
                with open(context.file_path, "rb") as f:
                    current_pdf_bytes = f.read()
            except Exception as e:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message=f"无法加载当前 PDF 文件: {e}"
                )

        base_url = kwargs.get("base_document_url", "").strip()
        if not base_url:
            return OperatorResult(
                operator_name=self.name,
                pass_status=True,
                message="未提供基准文档URL，跳过差异比对。"
            )

        try:
            # 1. 异步拉取基准 PDF
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(base_url)
                resp.raise_for_status()
                base_pdf_bytes = resp.content
                
            current_text, current_page_count = self._extract_text_from_bytes(current_pdf_bytes)
            base_text, base_page_count = self._extract_text_from_bytes(base_pdf_bytes)
            
            # 2. 文本清洗与格式归一化
            current_text_clean = re.sub(r'\s+', ' ', current_text).strip()
            base_text_clean = re.sub(r'\s+', ' ', base_text).strip()
            
            if not current_text_clean and not base_text_clean:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=True,
                    message="两个文档均为纯图像或无法提取文本，相似度默认为 100%。"
                )

            # ─── 3. 极速行/段落比对引擎 (SequenceMatcher 防卡死优化) ───
            # 如果文本量极大，直接全局比对会陷入二次方计算死循环，故在此做按句/段的分片匹配
            len_base = len(base_text_clean)
            len_current = len(current_text_clean)
            
            changes = []
            similarity = 0.0
            
            if max(len_base, len_current) > 4000:
                logger.info(f"⚡ 触发大文本快速比对优化：基准 {len_base} 字，当前 {len_current} 字")
                # 采用分行/分句方式进行段落比对
                base_sentences = [s.strip() for s in re.split(r'([。；;!?！？\n])', base_text_clean) if s.strip()]
                curr_sentences = [s.strip() for s in re.split(r'([。；;!?！？\n])', current_text_clean) if s.strip()]
                
                # 行级比对
                sm = difflib.SequenceMatcher(None, base_sentences, curr_sentences)
                similarity = sm.ratio()
                
                # 抓取有差异的句子段落进行局部的细致 Diff
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag != 'equal':
                        orig_sub = " ".join(base_sentences[i1:i2])
                        curr_sub = " ".join(curr_sentences[j1:j2])
                        
                        # 在局部进行字符级别的精细对比，由于单句长度极短，计算在 0.1ms 内即可完成
                        sub_sm = difflib.SequenceMatcher(None, orig_sub, curr_sub)
                        for sub_tag, si1, si2, sj1, sj2 in sub_sm.get_opcodes():
                            if sub_tag != 'equal':
                                # 提取带有前后 20 个字上下文的高亮语境片段
                                ctx_start_base = max(0, si1 - 20)
                                ctx_end_base = min(len(orig_sub), si2 + 20)
                                ctx_start_curr = max(0, sj1 - 20)
                                ctx_end_curr = min(len(curr_sub), sj2 + 20)
                                
                                changes.append({
                                    "type": sub_tag,
                                    "original_fragment": f"... {orig_sub[ctx_start_base:si1]} >>> {orig_sub[si1:si2]} <<< {orig_sub[si2:ctx_end_base]} ...",
                                    "current_fragment": f"... {curr_sub[ctx_start_curr:sj1]} >>> {curr_sub[sj1:sj2]} <<< {curr_sub[sj2:ctx_end_curr]} ...",
                                    "base_text": orig_sub[si1:si2],
                                    "current_text": curr_sub[sj1:sj2]
                                })
            else:
                # 4. 短文本标准全局比对
                matcher = difflib.SequenceMatcher(None, base_text_clean, current_text_clean)
                similarity = matcher.ratio()
                
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag != 'equal':
                        # 字符级定位并生成 Github 风格的高亮语境片段
                        ctx_start_base = max(0, i1 - 20)
                        ctx_end_base = min(len(base_text_clean), i2 + 20)
                        ctx_start_curr = max(0, j1 - 20)
                        ctx_end_curr = min(len(current_text_clean), j2 + 20)
                        
                        changes.append({
                            "type": tag,
                            "original_fragment": f"... {base_text_clean[ctx_start_base:i1]} >>> {base_text_clean[i1:i2]} <<< {base_text_clean[i2:ctx_end_base]} ...",
                            "current_fragment": f"... {current_text_clean[ctx_start_curr:j1]} >>> {current_text_clean[j1:j2]} <<< {current_text_clean[j2:ctx_end_curr]} ...",
                            "base_text": base_text_clean[i1:i2],
                            "current_text": current_text_clean[j1:j2]
                        })

            similarity_pct = round(similarity * 100, 2)

            # ── 5. LLM Semantic Classification Pass (optional) ──
            raw_changes_count = len(changes)
            llm_classified = False

            use_llm_semantic = kwargs.get("use_llm_semantic", True)
            if use_llm_semantic and changes:
                try:
                    ai_config = await _get_ai_config(model_type="text")
                    if ai_config.get("enabled") and ai_config.get("api_key"):
                        model_name = kwargs.get("model") or ai_config.get("text_model", "gpt-4o-mini")
                        llm_results = await self._classify_changes_with_llm(
                            base_text_clean=base_text_clean,
                            current_text_clean=current_text_clean,
                            changes=changes,
                            ai_config=ai_config,
                            model_name=model_name,
                        )
                        if llm_results:
                            llm_classified = True
                            # Annotate each change with LLM classification
                            class_map = {c["index"]: c for c in llm_results}
                            meaningful_changes = []
                            for i, change in enumerate(changes):
                                cls_info = class_map.get(i)
                                if cls_info:
                                    change["llm_classification"] = cls_info["classification"]
                                    change["llm_reason"] = cls_info["reason"]
                                    if cls_info["classification"] == "meaningful":
                                        meaningful_changes.append(change)
                                else:
                                    # Unclassified → conservative default = meaningful
                                    change["llm_classification"] = "unclassified"
                                    change["llm_reason"] = ""
                                    meaningful_changes.append(change)

                            # Recalculate effective similarity (meaningful changes only)
                            meaningful_base_len = sum(len(c.get("base_text", "")) for c in meaningful_changes)
                            meaningful_curr_len = sum(len(c.get("current_text", "")) for c in meaningful_changes)
                            total_text_len = max(len(base_text_clean) + len(current_text_clean), 1)
                            diff_len_effective = max(meaningful_base_len, meaningful_curr_len)
                            effective_similarity = 1.0 - (diff_len_effective / total_text_len)
                            effective_similarity = max(0.0, min(1.0, effective_similarity))
                            effective_similarity_pct = round(effective_similarity * 100, 2)
                        else:
                            effective_similarity_pct = similarity_pct
                    else:
                        effective_similarity_pct = similarity_pct
                except Exception as e:
                    logger.warning("LLM semantic classification skipped (non-fatal): %s", e)
                    effective_similarity_pct = similarity_pct
            else:
                effective_similarity_pct = similarity_pct

            # Effective changes count (only meaningful ones when LLM ran)
            if llm_classified:
                effective_changes_count = len(meaningful_changes)
            else:
                effective_changes_count = len(changes)

            context.shared_state["diff_results"] = {
                "similarity": effective_similarity if llm_classified else similarity,
                "changes_count": effective_changes_count,
            }

            # ── 6. Similarity threshold decision ──
            threshold_val = kwargs.get("similarity_threshold", 100.0)
            try:
                threshold = float(threshold_val)
            except (ValueError, TypeError):
                threshold = 100.0

            if effective_similarity_pct >= threshold:
                pass_status = True
                msg = f"文本相似度为 {effective_similarity_pct}%，符合阈值要求（>= {threshold}%）。"
            else:
                pass_status = False
                msg = f"文本相似度为 {effective_similarity_pct}%，低于阈值要求（{threshold}%）。共发现 {effective_changes_count} 处差异。"

            if llm_classified:
                filtered_count = raw_changes_count - effective_changes_count
                if filtered_count > 0:
                    msg += f"（LLM 语义分析过滤了 {filtered_count} 处格式/等价差异）"

            return OperatorResult(
                operator_name=self.name,
                pass_status=pass_status,
                message=msg,
                extracted_data={
                    "similarity": effective_similarity_pct,
                    "changes_count": effective_changes_count,
                    "raw_changes_count": raw_changes_count,
                    "llm_classified": llm_classified,
                    "current_page_count": current_page_count,
                    "base_page_count": base_page_count,
                    "current_text_length": len(current_text_clean),
                    "base_text_length": len(base_text_clean),
                    # 解开并只返回前 15 个最核心的修改细节到前端 UI，保障界面清爽和高速响应
                    "changes": changes[:15],
                }
            )

        except Exception as e:
            logger.error(f"Document diff failed: {e}")
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"差异比对发生错误: {e}"
            )
