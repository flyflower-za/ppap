import json
import logging
import base64
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.engine.base import BaseOperator, DocumentContext, OperatorResult

logger = logging.getLogger(__name__)


async def _get_ai_config(model_type: str = "vision", requested_model: str = None) -> dict:
    """
    Load AI model config. Prefers the default ModelProfile for the given type.
    Falls back to the legacy single ai_model_config if no profiles exist.
    """
    try:
        from app.core.database import async_session_maker
        from app.models.setting import Setting
        async with async_session_maker() as session:
            profiles_row = await session.get(Setting, "ai_model_profiles")
            if profiles_row:
                profiles = json.loads(profiles_row.value)
                matching = [
                    p for p in profiles
                    if p.get("enabled") and p.get("model_type") in (model_type, "both")
                ]
                chosen = None
                if requested_model:
                    chosen = next((p for p in matching if p.get("model_name") == requested_model), None)
                    
                if not chosen:
                    flag = f"is_default_{model_type}"
                    default = next((p for p in matching if p.get(flag)), None)
                    chosen = default or (matching[0] if matching else None)
                    
                if chosen:
                    return {
                        "enabled": True,
                        "api_key": chosen.get("api_key"),
                        "base_url": chosen.get("base_url", "https://api.openai.com/v1"),
                        "vision_model": chosen.get("model_name", "gpt-4o"),
                        "max_tokens": chosen.get("max_tokens", 1024),
                        "temperature": chosen.get("temperature", 0.1),
                    }
            legacy_row = await session.get(Setting, "ai_model_config")
            if legacy_row:
                return json.loads(legacy_row.value)
    except Exception as e:
        logger.warning(f"Could not load AI config from DB: {e}")
    return {}


class VisionOutputSchema(BaseModel):
    passed: bool = Field(..., description="Whether the verification passed based on visual evidence")
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0")
    reason: str = Field(..., description="Explanation of the visual reasoning")
    bounding_boxes: List[dict] = Field(default_factory=list, description="Any detected bounding boxes {x0, y0, x1, y1, label}")


class VisionLLMOperator(BaseOperator):
    """
    Operator that uses a Vision-Language Model (VLM) to analyze document layouts,
    seals, handwriting, or specific cropped regions based on bounding boxes.

    Vision strategy:
    - If `crop_bbox` kwarg is provided (x0, y0, x1, y1 in points), only that
      region of the target page is sent to the VLM (e.g. for QR codes, stamps
      in a known corner). This greatly reduces token cost.
    - If no `crop_bbox` is given, the full page is rendered and sent (e.g. for
      holistic layout or signature checks that span the whole page).
    """
    def __init__(self):
        super().__init__(name="VisionLLMOperator")

    @property
    def provides(self) -> List[str]:
        return ["vision_analysis"]

    @property
    def requires(self) -> List[str]:
        return ["pdf_bytes"]

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        pdf_bytes = context.shared_state.get("pdf_bytes")
        if not pdf_bytes:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message="No PDF bytes available for Vision analysis."
            )

        target_prompt = kwargs.get("prompt", "请检查页面右下角是否包含红色实体公章。")
        target_page = kwargs.get("page_num", 1)
        # Optional: crop_bbox = (x0, y0, x1, y1) in PDF user-space points
        crop_bbox: Optional[tuple] = kwargs.get("crop_bbox", None)

        try:
            ai_config = await _get_ai_config(requested_model=kwargs.get("model"))

            if not ai_config.get("enabled") or not ai_config.get("api_key"):
                # Fallback to mock when AI is not configured
                logger.warning("AI model not configured, using mock vision response.")
                response_data = {
                    "passed": True,
                    "confidence": 0.88,
                    "reason": "[Mock] 视觉大模型分析完毕，在指定坐标区域内检测到了清晰的公司公章印记。",
                    "bounding_boxes": [{"x0": 100, "y0": 200, "x1": 250, "y1": 350, "label": "公章"}]
                }
            else:
                # Render page (or crop) to JPEG using PyMuPDF
                try:
                    import fitz  # PyMuPDF
                except ImportError:
                    return OperatorResult(
                        operator_name=self.name,
                        pass_status=False,
                        message="PyMuPDF (fitz) is not installed. Cannot render PDF page for Vision LLM."
                    )

                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                if target_page < 1 or target_page > len(doc):
                    return OperatorResult(
                        operator_name=self.name,
                        pass_status=False,
                        message=f"Page {target_page} does not exist in the document."
                    )

                page = doc[target_page - 1]
                zoom = 2.0  # 2x = ~144 DPI, good balance of quality vs cost

                if crop_bbox:
                    # Only render the specified bounding box region
                    x0, y0, x1, y1 = crop_bbox
                    clip_rect = fitz.Rect(x0, y0, x1, y1)
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, clip=clip_rect, alpha=False)
                else:
                    # Render full page
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, alpha=False)

                image_bytes = pix.tobytes("jpeg")
                base64_image = base64.b64encode(image_bytes).decode("utf-8")
                doc.close()

                region_desc = f"裁剪区域 {crop_bbox}" if crop_bbox else f"第 {target_page} 页完整页面"

                from openai import AsyncOpenAI
                client = AsyncOpenAI(
                    api_key=ai_config["api_key"],
                    base_url=ai_config.get("base_url", "https://api.openai.com/v1")
                )

                system_prompt = f"""
                你是一个严谨的文档视觉审核员。请根据提供的文档图像回答审核问题。
                你必须且只能返回一个包含检查结果的 JSON 数据实例。不要返回 JSON Schema 结构定义。
                
                严格返回以下 JSON 格式：
                {{
                    "passed": bool (是否通过审核),
                    "confidence": float (0.0 到 1.0 的置信度),
                    "reason": "string (判断的详细理由)",
                    "extracted_data": {{}} (包含任何提取的关键信息)
                }}
                """

                model_name = kwargs.get("model") or ai_config.get("vision_model", "gpt-4o")
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"审核要求: {target_prompt}\n(图像来自: {region_desc})"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=ai_config.get("max_tokens", 1024),
                    temperature=ai_config.get("temperature", 0.1),
                    response_format={"type": "json_object"}
                )

                raw_content = response.choices[0].message.content
                response_data = json.loads(raw_content)

            # Validate with Pydantic
            validated = VisionOutputSchema(**response_data)

            # Update shared state
            if "vision_analysis" not in context.shared_state:
                context.shared_state["vision_analysis"] = []
            context.shared_state["vision_analysis"].append(validated.dict())

            return OperatorResult(
                operator_name=self.name,
                pass_status=validated.passed,
                message=validated.reason,
                extracted_data=validated.dict()
            )
        except Exception as e:
            logger.error(f"VisionLLMOperator failed: {e}")
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"Vision Plugin execution failed: {str(e)}"
            )
