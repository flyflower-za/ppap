import logging
import difflib
import httpx
import tempfile
import os
from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult

logger = logging.getLogger(__name__)

class DocumentDiffOperator(BaseOperator):
    """
    Operator to compare the current document's text against a baseline document.
    """
    def __init__(self):
        super().__init__(name="DocumentDiffOperator")

    @property
    def provides(self) -> List[str]:
        return ["diff_results"]

    @property
    def requires(self) -> List[str]:
        return ["pdf_bytes"]
        
    def _extract_text_from_bytes(self, pdf_bytes: bytes) -> str:
        import fitz
        text = ""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text("text") + "\n"
            doc.close()
        except Exception as e:
            logger.error(f"Error extracting text for diff: {e}")
        return text

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
            # If no base document is provided, we can't do a diff. We just skip/pass.
            return OperatorResult(
                operator_name=self.name,
                pass_status=True,
                message="未提供基准文档URL，跳过差异比对。"
            )

        try:
            # Download base document
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(base_url)
                resp.raise_for_status()
                base_pdf_bytes = resp.content
                
            current_text = self._extract_text_from_bytes(current_pdf_bytes)
            base_text = self._extract_text_from_bytes(base_pdf_bytes)
            
            # Clean up texts for better comparison (normalize whitespace)
            import re
            current_text_clean = re.sub(r'\s+', ' ', current_text).strip()
            base_text_clean = re.sub(r'\s+', ' ', base_text).strip()
            
            if not current_text_clean and not base_text_clean:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=True,
                    message="两个文档似乎都是纯图像或无法提取文本。"
                )
                
            matcher = difflib.SequenceMatcher(None, base_text_clean, current_text_clean)
            similarity = matcher.ratio()
            
            # Extract basic diff stats
            opcodes = matcher.get_opcodes()
            changes = []
            for tag, i1, i2, j1, j2 in opcodes:
                if tag != 'equal':
                    changes.append({
                        "type": tag,
                        "base_text": base_text_clean[i1:i2],
                        "current_text": current_text_clean[j1:j2]
                    })
                    
            similarity_pct = round(similarity * 100, 2)
            context.shared_state["diff_results"] = {
                "similarity": similarity,
                "changes_count": len(changes)
            }
            
            # If similarity is exactly 100%, pass. Otherwise, you might want it to fail or just warn.
            # Usually diff operator is informational, but we can set a threshold.
            threshold_val = kwargs.get("similarity_threshold", 100.0)
            try:
                threshold = float(threshold_val)
            except (ValueError, TypeError):
                threshold = 100.0
            
            if similarity_pct >= threshold:
                pass_status = True
                msg = f"文本相似度为 {similarity_pct}%，符合阈值要求（>= {threshold}%）。"
            else:
                pass_status = False
                msg = f"文本相似度为 {similarity_pct}%，低于阈值要求（{threshold}%）。发现 {len(changes)} 处差异。"

            return OperatorResult(
                operator_name=self.name,
                pass_status=pass_status,
                message=msg,
                extracted_data={
                    "similarity": similarity_pct,
                    "changes_count": len(changes),
                    # "changes": changes[:10]  # Avoid returning massive diff arrays in UI, limit to first 10
                }
            )

        except Exception as e:
            logger.error(f"Document diff failed: {e}")
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"差异比对发生错误: {e}"
            )
