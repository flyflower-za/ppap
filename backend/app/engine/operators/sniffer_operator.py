import json
from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.services.aliyun_service import aliyun_service

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
        if not full_text:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message="No text available for sniffing."
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
