import asyncio
import json
import logging
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.engine.llm_utils import _get_ai_config, _safe_json_parse

logger = logging.getLogger(__name__)

# Model context-window estimation (conservative char limits for prompt text)
_MODEL_CONTEXT_LIMITS = {
    "gpt-4o": 15000,
    "gpt-4-turbo": 15000,
    "claude": 15000,
    "gpt-4o-mini": 8000,
    "gpt-3.5": 8000,
    "gemini": 15000,
    "deepseek": 15000,
    "qwen": 15000,
}


def _estimate_max_chars(model_name: str) -> int:
    """Estimate a safe prompt-text character limit based on model family."""
    model_lower = model_name.lower()
    for key, limit in _MODEL_CONTEXT_LIMITS.items():
        if key in model_lower:
            return limit
    return 3000  # safe fallback


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

        # ── Dynamic context window ──
        ai_config = await _get_ai_config(requested_model=kwargs.get("model"))
        model_name = kwargs.get("model") or ai_config.get("text_model", "gpt-4o-mini")
        max_chars = _estimate_max_chars(model_name)
        text_context = full_text[:max_chars]
        if len(full_text) > max_chars:
            logger.info("Text truncated from %d to %d chars for model %s", len(full_text), max_chars, model_name)

        # ── Anti-hallucination prompts ──
        if operation_mode == "extraction":
            system_prompt = """
你是一个严谨的文档信息提取专家。请根据以下文档文本提取指定信息。

原则：
- 只提取文档中**明确存在**的信息，不要推测、不要补全
- 如果信息不存在，对应字段返回 null
- 必须引用原文内容来支持提取结果
- 如果不确定，在 extracted_data 中标注 "uncertain": true

你必须且只能返回一个包含提取结果的 JSON 数据实例。
严格返回以下 JSON 格式，直接包含提取的字段：
{
    "field_name": "value",
    ...
}
"""
            user_prompt = f"文档内容:\n{text_context}\n\n提取要求:\n{target_prompt}"
        else:
            system_prompt = """
你是一个严谨的文档审核员。请根据以下文档文本回答用户问题。

原则：
- 严格基于提供的文档内容做出判断，**不要编造或推测**文档中没有的信息
- 必须引用原文中的具体内容来支持你的判断，引用格式：「原文：...」
- 如果文档内容不足以做出判断，confidence 必须 ≤ 0.5，并在 reason 中说明缺少哪些信息
- 如果不确定文档是否包含某些内容，请明确指出不确定的部分

你必须且只能返回一个包含检查结果的 JSON 数据实例。不要返回 JSON Schema 结构定义。

严格返回以下 JSON 格式：
{
    "passed": bool (是否通过审核),
    "confidence": float (0.0 到 1.0 的置信度),
    "reason": "string (判断的详细理由，需引用原文)",
    "extracted_data": {} (包含任何提取的关键信息)
}
"""
            user_prompt = f"文档内容:\n{text_context}\n\n审核要求:\n{target_prompt}"

        try:
            if not ai_config.get("enabled") or not ai_config.get("api_key"):
                # Fallback to mock when AI is not configured
                logger.warning("AI model not configured, using mock response.")
                response_data = {
                    "passed": True,
                    "confidence": 0.5,
                    "reason": "[Mock] LLM 未配置，使用降级响应 — 该判断未经实际 AI 分析。",
                    "extracted_data": {}
                }
            else:
                response_data = await self._call_llm_with_retry(
                    ai_config=ai_config,
                    model_name=model_name,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )

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

    async def _call_llm_with_retry(
        self,
        ai_config: dict,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        """Call LLM with exponential backoff retry for transient failures."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=ai_config["api_key"],
            base_url=ai_config.get("base_url", "https://api.openai.com/v1")
        )

        max_retries = 3
        base_delay = 2.0  # seconds

        for attempt in range(1, max_retries + 1):
            try:
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

                response = await asyncio.wait_for(api_coro, timeout=60.0)
                raw_content = response.choices[0].message.content
                return _safe_json_parse(raw_content)

            except asyncio.TimeoutError:
                if attempt < max_retries:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "LLM call timed out (attempt %d/%d), retrying in %.1fs...",
                        attempt, max_retries, delay
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error("LLM call timed out after %d attempts.", max_retries)
                return {
                    "passed": False,
                    "confidence": 0.0,
                    "reason": f"[熔断拦截] 大模型响应超时 (>60s)，重试 {max_retries} 次后仍失败",
                    "extracted_data": {}
                }

            except Exception as e:
                err_str = str(e).lower()
                # Only retry on transient errors: rate limits, 5xx, connection errors
                is_transient = any(k in err_str for k in [
                    "rate_limit", "429", "5xx", "500", "502", "503", "504",
                    "timeout", "connection", "temporary", "service unavailable",
                ])
                if is_transient and attempt < max_retries:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "LLM call transient error (attempt %d/%d): %s, retrying in %.1fs...",
                        attempt, max_retries, e, delay
                    )
                    await asyncio.sleep(delay)
                    continue

                # Non-transient or exhausted: propagate
                raise
