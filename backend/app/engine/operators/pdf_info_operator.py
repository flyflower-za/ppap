from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.checkers.pdf_info import check_pdf_text_layer

class PDFInfoOperator(BaseOperator):
    """
    Operator to extract text layers, page counts and structural properties from the PDF.
    """
    def __init__(self):
        super().__init__(name="PDFInfoExtractor")

    @property
    def provides(self) -> List[str]:
        return ["pdf_info", "full_text"]

    @property
    def requires(self) -> List[str]:
        return ["pdf_bytes"]

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        pdf_bytes = context.shared_state.get("pdf_bytes")
        if not pdf_bytes:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message="PDF bytes missing."
            )
        
        try:
            results = check_pdf_text_layer(pdf_bytes)
            context.shared_state["pdf_info"] = results
            context.shared_state["full_text"] = results.get("full_text", "")
            
            is_text = results.get("is_text_pdf", False)
            char_count = results.get("char_count", 0)
            sample = results.get("sample_text", "")
            
            if is_text:
                msg = f"文本型PDF。包含可检索字元 {char_count} 个。预览: '{sample}'"
            else:
                msg = "图片/扫描型PDF，未检测到矢量文本图层。"
                
            return OperatorResult(
                operator_name=self.name,
                pass_status=True,
                message=msg,
                extracted_data={"pdf_info": results}
            )
        except Exception as e:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"PDF Info extraction failed: {e}"
            )
