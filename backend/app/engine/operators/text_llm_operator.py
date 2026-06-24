import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.services.ai_config_service import get_ai_config

logger = logging.getLogger(__name__)


async def _get_ai_config(model_type: str = "text", requested_model: str = None) -> dict:
    return await get_ai_config(model_type=model_type, requested_model=requested_model)


class LLMOutputSchema(BaseModel):
    passed: bool = Field(default=True, description="Whether the verification passed")
    confidence: float = Field(default=1.0, description="Confidence score from 0.0 to 1.0")
    reason: str = Field(default="", description="Explanation of the reasoning")
    extracted_data: dict = Field(default_factory=dict, description="Any extracted data relevant to the rule")


class TextLLMOperator(BaseOperator):
    """
    Operator that uses a Text-based Large Language Model to perform semantic analysis
    on the extracted text or specific spatial blocks.
    Enforces a strict JSON output using Pydantic.
    """
    def __init__(self):
        super().__init__(name="TextLLMOperator")

    @property
    def provides(self) -> List[str]:
        return ["llm_semantic_analysis"]

    @property
    def requires(self) -> List[str]:
        return ["full_text"]

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        full_text = context.shared_state.get("full_text", "")
        if not full_text:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message="No text available for LLM analysis."
            )

        target_prompt = kwargs.get("prompt", "请检查文档是否包含完整的盖章审批流程。")
        operation_mode = kwargs.get("operation_mode", "verification")

        # Truncate text if too long for the context window (Safety Truncation)
        max_chars = 3000
        text_context = full_text[:max_chars]

        # Adjust system prompt based on operation mode
        if operation_mode == "extraction":
            system_prompt = """
            你是一个文档信息提取专家。请从提供的文档文本中提取指定信息。
            你必须且只能返回一个包含提取结果的 JSON 数据实例。

            严格返回以下 JSON 格式，直接包含提取的字段：
            {
                "field_name": "value",
                ...
            }
            """
            user_prompt = f"文档内容:\n{text_context}\n\n提取要求:\n{target_prompt}"
        else:
            system_prompt = f"""
            你是一个严谨的文档审核审核员。请根据以下提取的文档文本回答用户问题。
            你必须且只能返回一个包含检查结果的 JSON 数据实例。不要返回 JSON Schema 结构定义。

            严格返回以下 JSON 格式：
            {{
                "passed": bool (是否通过审核),
                "confidence": float (0.0 到 1.0 的置信度),
                "reason": "string (判断的详细理由)",
                "extracted_data": {{}} (包含任何提取的关键信息)
            }}
            """
            user_prompt = f"文档内容:\n{text_context}\n\n审核要求:\n{target_prompt}"

        try:
            ai_config = await _get_ai_config(requested_model=kwargs.get("model"))

            if not ai_config.get("enabled") or not ai_config.get("api_key"):
                # Fallback to mock when AI is not configured
                logger.warning("AI model not configured, using mock response.")
                response_data = {
                    "passed": True,
                    "confidence": 0.95,
                    "reason": "[Mock] 通过大模型语义分析，提取到了符合要求的信息。",
                    "extracted_data": {"matched_keywords": ["合格", "批准"]}
                }
            else:
                from openai import AsyncOpenAI
                import asyncio
                client = AsyncOpenAI(
                    api_key=ai_config["api_key"],
                    base_url=ai_config.get("base_url", "https://api.openai.com/v1")
                )

                model_name = kwargs.get("model") or ai_config.get("text_model", "gpt-4o-mini")
                
                # Wrap the API call in a 60-second timeout circuit breaker
                api_coro = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=ai_config.get("max_tokens", 2048),
                    temperature=ai_config.get("temperature", 0.1),
                    response_format={"type": "json_object"}
                )
                
                try:
                    response = await asyncio.wait_for(api_coro, timeout=60.0)
                    raw_content = response.choices[0].message.content
                    response_data = json.loads(raw_content)
                except asyncio.TimeoutError:
                    logger.error("LLM API call timed out after 60 seconds.")
                    response_data = {
                        "passed": False,
                        "confidence": 0.0,
                        "reason": "[熔断拦截] 大模型响应超时 (>60s)，已降级",
                        "extracted_data": {}
                    }

            # Handle extraction mode (LLM only returned extracted data without verification fields)
            has_verification_fields = any(k in response_data for k in ("passed", "confidence", "reason"))
            if not has_verification_fields:
                # Pure extraction mode - pass validation and save extracted data
                extracted = response_data
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=True,
                    message=f"成功提取数据: {', '.join(extracted.keys())}",
                    extracted_data=extracted
                )

            # Validate with Pydantic for verification mode
            validated = LLMOutputSchema(**response_data)

            # Update shared state
            if "llm_semantic_analysis" not in context.shared_state:
                context.shared_state["llm_semantic_analysis"] = []
            context.shared_state["llm_semantic_analysis"].append(validated.dict())

            return OperatorResult(
                operator_name=self.name,
                pass_status=validated.passed,
                message=validated.reason,
                extracted_data=response_data.get("extracted_data", validated.dict())
            )
        except Exception as e:
            logger.error(f"TextLLMOperator failed: {e}")
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"LLM Plugin execution failed: {str(e)}"
            )
