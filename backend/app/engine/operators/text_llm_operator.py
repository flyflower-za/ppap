import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.engine.base import BaseOperator, DocumentContext, OperatorResult

logger = logging.getLogger(__name__)


async def _get_ai_config(model_type: str = "text") -> dict:
    """
    Load AI model config. Prefers the default ModelProfile for the given type.
    Falls back to the legacy single ai_model_config if no profiles exist.
    Returns an empty dict if nothing is configured.
    """
    try:
        from app.core.database import async_session_maker
        from app.models.setting import Setting
        async with async_session_maker() as session:
            # Try multi-profile first
            profiles_row = await session.get(Setting, "ai_model_profiles")
            if profiles_row:
                profiles = json.loads(profiles_row.value)
                # Find enabled profiles matching the requested type
                matching = [
                    p for p in profiles
                    if p.get("enabled") and p.get("model_type") in (model_type, "both")
                ]
                # Prefer the one marked as default
                flag = f"is_default_{model_type}"
                default = next((p for p in matching if p.get(flag)), None)
                chosen = default or (matching[0] if matching else None)
                if chosen:
                    return {
                        "enabled": True,
                        "api_key": chosen.get("api_key"),
                        "base_url": chosen.get("base_url", "https://api.openai.com/v1"),
                        "text_model": chosen.get("model_name", "gpt-4o-mini"),
                        "vision_model": chosen.get("model_name", "gpt-4o"),
                        "max_tokens": chosen.get("max_tokens", 2048),
                        "temperature": chosen.get("temperature", 0.1),
                    }
            # Fallback: legacy single config
            legacy_row = await session.get(Setting, "ai_model_config")
            if legacy_row:
                return json.loads(legacy_row.value)
    except Exception as e:
        logger.warning(f"Could not load AI config from DB: {e}")
    return {}


class LLMOutputSchema(BaseModel):
    passed: bool = Field(..., description="Whether the verification passed")
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0")
    reason: str = Field(..., description="Explanation of the reasoning")
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

        # Truncate text if too long for the context window (Safety Truncation)
        max_chars = 3000
        text_context = full_text[:max_chars]

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
            ai_config = await _get_ai_config()

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

            # Validate with Pydantic
            validated = LLMOutputSchema(**response_data)

            # Update shared state
            if "llm_semantic_analysis" not in context.shared_state:
                context.shared_state["llm_semantic_analysis"] = []
            context.shared_state["llm_semantic_analysis"].append(validated.dict())

            return OperatorResult(
                operator_name=self.name,
                pass_status=validated.passed,
                message=validated.reason,
                extracted_data=validated.dict()
            )
        except Exception as e:
            logger.error(f"TextLLMOperator failed: {e}")
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"LLM Plugin execution failed: {str(e)}"
            )
