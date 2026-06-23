import logging
from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult

logger = logging.getLogger(__name__)

class TemplateFormatterOperator(BaseOperator):
    """
    Operator to dynamically format a template string with variables resolved from upstream nodes.
    Useful for splicing URLs or strings dynamically in a logic graph.
    """
    def __init__(self):
        super().__init__(name="TemplateFormatter")

    @property
    def provides(self) -> List[str]:
        return ["formatted_result"]

    @property
    def requires(self) -> List[str]:
        return []

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        # At this stage, the parameters in kwargs are already interpolated by the orchestrator
        # e.g., kwargs["template"] = "https://example/api/123456;1qa2ws"
        template_str = kwargs.get("template", "")
        
        if not template_str:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message="模板为空或格式错误",
                extracted_data={"formatted_result": ""}
            )

        return OperatorResult(
            operator_name=self.name,
            pass_status=True,
            message="模板格式化拼接成功",
            extracted_data={"formatted_result": template_str}
        )
