import json
import base64
import logging
from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.services.aliyun_service import aliyun_service
from app.engine.operators.vision_llm_operator import _get_ai_config

logger = logging.getLogger(__name__)

class InstitutionSnifferOperator(BaseOperator):
    """
    Operator to sniff the institution of the document using LLM on the extracted text.
    """
    def __init__(self):
        super().__init__(name="InstitutionSniffer")

    @property
    def provides(self) -> List[str]:
        return ["institution"]

    @property
    def requires(self) -> List[str]:
        return ["full_text"]

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        full_text = context.shared_state.get("full_text", "")
        pdf_bytes = context.shared_state.get("pdf_bytes")
        
        if not pdf_bytes:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message="No PDF bytes available for sniffing."
            )

        # Truncate text if too long (take the first 2000 chars and last 500 chars)
        if len(full_text) > 2500:
            text_to_analyze = full_text[:2000] + "\n...[truncated]...\n" + full_text[-500:]
        else:
            text_to_analyze = full_text

        prompt = f"""
请分析以下文档内容，识别该文档是由哪个机构签发的（如华测检测 CTI、SGS检测、某某公司等）。
请务必返回合法的 JSON 格式，包含以下字段：
- "institution": 提取到的机构名称简写或全称（例如："CTI", "SGS", "XXX公司"）。如果无法确定，请返回 "UNKNOWN"。
- "confidence": 0.0 到 1.0 的置信度。

文档内容：
{text_to_analyze}
"""
        
        try:
            # Use the async aliyun_service
            llm_res = await aliyun_service.call_qwen_async(prompt)
            # Find json block
            import re
            json_match = re.search(r'\{.*\}', llm_res.replace('\n', ''))
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(llm_res)

            institution = data.get("institution", "UNKNOWN")
            confidence = data.get("confidence", 0.0)

            # --- MULTIMODAL FALLBACK ---
            # If it's a scanned PDF (very short text) or text LLM returned UNKNOWN, fallback to Vision LLM
            if institution == "UNKNOWN" or len(full_text) < 50:
                logger.info("Text LLM failed to identify institution or text is too short. Falling back to Vision LLM.")
                vision_res = await self._run_vision_fallback(pdf_bytes)
                if vision_res:
                    institution = vision_res.get("institution", "UNKNOWN")
                    confidence = vision_res.get("confidence", 0.0)
            
            context.shared_state["institution"] = institution

            msg = f"嗅探完成：归属机构 [{institution}] (置信度: {confidence})"
            
            return OperatorResult(
                operator_name=self.name,
                pass_status=True,
                message=msg,
                extracted_data={"institution": institution, "confidence": confidence}
            )

        except Exception as e:
            # Fallback heuristic
            if "华测" in text_to_analyze or "CTI" in text_to_analyze:
                context.shared_state["institution"] = "CTI"
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=True,
                    message="嗅探异常，但命中关键词规则：归属机构 [CTI] (Fallback)",
                    extracted_data={"institution": "CTI", "confidence": 0.8}
                )

            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"Institution Sniffer failed: {e}"
            )

    async def _run_vision_fallback(self, pdf_bytes: bytes) -> dict:
        try:
            ai_config = await _get_ai_config("vision")
            if not ai_config.get("enabled") or not ai_config.get("api_key"):
                logger.warning("Vision AI config not available for fallback.")
                return None

            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # We'll render the first page for header/logo
            page = doc[0]
            zoom = 1.5
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            image_bytes_1 = pix.tobytes("jpeg")
            base64_image_1 = base64.b64encode(image_bytes_1).decode("utf-8")
            
            # If there's more than one page, also render the last page for sign-offs/stamps
            base64_image_2 = None
            if len(doc) > 1:
                page_last = doc[-1]
                pix_last = page_last.get_pixmap(matrix=mat, alpha=False)
                image_bytes_2 = pix_last.tobytes("jpeg")
                base64_image_2 = base64.b64encode(image_bytes_2).decode("utf-8")
                
            doc.close()

            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=ai_config["api_key"],
                base_url=ai_config.get("base_url", "https://api.openai.com/v1")
            )

            system_prompt = """
            请分析这张（或两张）文档的图片。第一张通常包含页眉或LOGO，如果有第二张，则通常是文档的尾页（可能包含落款或公章）。
            请根据图片中的视觉信息（如红头文件、公司 LOGO、落款文字、公章等）提取该文档的实际签发机构名称简写或全称。
            请务必严格返回合法的 JSON 格式，不输出任何其他多余内容：
            {"institution": "机构名称", "confidence": 0.95}
            如果无法确定，请返回 "UNKNOWN"。
            """

            content = [{"type": "text", "text": "提取图片中的签发机构："}]
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image_1}", "detail": "high"}})
            if base64_image_2:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image_2}", "detail": "high"}})

            response = await client.chat.completions.create(
                model=ai_config.get("vision_model", "gpt-4o"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=256,
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            raw = response.choices[0].message.content
            import re
            json_match = re.search(r'\{.*\}', raw.replace('\n', ''))
            try:
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = json.loads(raw)
                return data
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from Vision LLM. Raw output: {raw}")
                # Fallback: if the raw output is short, assume the model just returned the name
                if len(raw) < 50:
                    return {"institution": raw.strip(), "confidence": 0.8}
                return None
        except Exception as e:
            logger.error(f"Vision fallback failed: {e}")
            return None
