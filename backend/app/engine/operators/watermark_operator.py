import logging
from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult

logger = logging.getLogger(__name__)

class WatermarkOperator(BaseOperator):
    """
    Operator to detect watermarks (text-based) in a PDF document.
    Checks for large, often diagonal text or specific keywords.
    """
    def __init__(self):
        super().__init__(name="WatermarkOperator")

    @property
    def provides(self) -> List[str]:
        return ["watermarks"]

    @property
    def requires(self) -> List[str]:
        return ["pdf_bytes"]

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        pdf_bytes = context.shared_state.get("pdf_bytes")
        if not pdf_bytes:
            try:
                with open(context.file_path, "rb") as f:
                    pdf_bytes = f.read()
            except Exception as e:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message=f"无法加载 PDF 文件: {e}"
                )

        keywords_input = kwargs.get("watermark_keywords", ["受控文件", "绝密", "机密", "DRAFT", "CONFIDENTIAL", "VOID", "作废"])
        if isinstance(keywords_input, str):
            keywords = [k.strip().lower() for k in keywords_input.split(",") if k.strip()]
        else:
            keywords = [k.lower() for k in keywords_input]
        
        detected_watermarks = []

        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_idx, page in enumerate(doc):
                blocks = page.get_text("dict")["blocks"]
                for b in blocks:
                    if b["type"] == 0:  # text block
                        for l in b["lines"]:
                            for s in l["spans"]:
                                text = s["text"].strip()
                                font_size = s["size"]
                                
                                if not text:
                                    continue
                                
                                # Condition 1: Extremely large font size (often used for diagonal watermarks)
                                is_large_font = font_size > 40
                                
                                # Condition 2: Keyword match
                                text_lower = text.lower()
                                is_keyword = any(kw in text_lower for kw in keywords)
                                
                                # A watermark is likely if it's very large, OR it matches a keyword and is reasonably large (e.g., > 15)
                                # We don't want to flag normal body text that happens to say "机密" unless specified by the rule strictly.
                                # But for this operator, we will flag it if it's large OR it matches exactly a watermark keyword.
                                if is_large_font or (is_keyword and font_size >= 15):
                                    detected_watermarks.append({
                                        "page": page_idx + 1,
                                        "text": text,
                                        "size": round(font_size, 2)
                                    })
                                    
            doc.close()
            
            # Deduplicate by text and page
            unique_watermarks = []
            seen = set()
            for wm in detected_watermarks:
                sig = (wm["page"], wm["text"])
                if sig not in seen:
                    seen.add(sig)
                    unique_watermarks.append(wm)

            context.shared_state["watermarks"] = unique_watermarks

            if unique_watermarks:
                texts = list(set([wm["text"] for wm in unique_watermarks]))
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,  # Presence of watermark usually means failure (e.g. DRAFT or VOID) or requires special handling
                    message=f"检测到可能的水印文本: {', '.join(texts[:3])}{' 等' if len(texts)>3 else ''}",
                    extracted_data={"watermarks": unique_watermarks}
                )
            else:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=True,
                    message="未检测到明显的水印标记。",
                    extracted_data={"watermarks": []}
                )

        except Exception as e:
            logger.error(f"Watermark detection failed: {e}")
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"水印检测发生错误: {e}"
            )
