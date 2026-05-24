import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.engine.base import BaseOperator, DocumentContext, OperatorResult

logger = logging.getLogger(__name__)

# Mock AI response generator for prototype
def mock_llm_call(prompt: str, schema: dict) -> dict:
    """
    Mock LLM call that returns a valid JSON matching the schema.
    In production, this would use OpenAI/Aliyun API with JSON schema forcing.
    """
    logger.info(f"Mocking LLM Call with prompt length: {len(prompt)}")
    # We will return a fake result based on typical queries
    return {
        "passed": True,
        "confidence": 0.95,
        "reason": "通过大模型语义分析，提取到了符合要求的信息。",
        "extracted_data": {"matched_keywords": ["合格", "批准"]}
    }

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
        
        # In a real dynamic engine, the prompt and rules would be passed via kwargs
        # injected by the Engine based on the AST.
        target_prompt = kwargs.get("prompt", "请检查文档是否包含完整的盖章审批流程。")
        
        # Truncate text if too long for the context window
        max_chars = 10000
        text_context = full_text[:max_chars]
        
        system_prompt = f"""
        你是一个严谨的文档审核审核员。请根据以下提取的文档文本回答用户问题。
        你必须严格遵循以下 JSON 格式输出，不要输出任何其他多余内容：
        {LLMOutputSchema.schema_json()}
        """
        
        user_prompt = f"文档内容:\n{text_context}\n\n审核要求:\n{target_prompt}"
        
        try:
            # Here we would normally make an async HTTP call to the LLM
            # response_data = await call_openai_api(...)
            response_data = mock_llm_call(user_prompt, LLMOutputSchema.schema())
            
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
