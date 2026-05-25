import os
import tempfile
import httpx
from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult

class URLFetchOperator(BaseOperator):
    """
    Operator to automatically download a PDF from a given URL, save it temporarily,
    and extract its contents using the PDFInfoExtractor.
    """
    def __init__(self):
        super().__init__(name="URLFetchOperator")

    @property
    def provides(self) -> List[str]:
        return ["pdf_bytes", "pdf_info", "full_text"]

    @property
    def requires(self) -> List[str]:
        return []

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        url = kwargs.get("url")
        if not url:
            # Try to get from context if not in kwargs (though usually passed in kwargs in sandbox)
            url = context.shared_state.get("pdf_url")
            
        if not url:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message="缺失 URL 参数，无法下载 PDF。"
            )

        try:
            # Fetch the PDF
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                pdf_bytes = response.content

            if not pdf_bytes or len(pdf_bytes) < 100:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message="下载失败或文件为空。"
                )

            # Check if it's a valid PDF (basic check)
            if not pdf_bytes.startswith(b"%PDF-"):
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message="下载的文件不是有效的 PDF 格式。"
                )

            # Write to a temporary file in context if it doesn't have one
            if not context.file_path or not os.path.exists(context.file_path):
                fd, temp_file_path = tempfile.mkstemp(suffix=".pdf")
                os.close(fd)
                context.file_path = temp_file_path
                
            with open(context.file_path, "wb") as f:
                f.write(pdf_bytes)
                
            context.shared_state["pdf_bytes"] = pdf_bytes

            # Now recognize the content using PDFInfoExtractor logic
            # We dynamically load and run PDFInfoOperator
            from app.engine.operators.pdf_info_operator import PDFInfoOperator
            pdf_op = PDFInfoOperator()
            pdf_res = await pdf_op.execute(context)

            if not pdf_res.pass_status:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message=f"文件已下载，但解析内容失败: {pdf_res.message}",
                    extracted_data={"downloaded": True, "error": pdf_res.message}
                )

            # Return success
            return OperatorResult(
                operator_name=self.name,
                pass_status=True,
                message=f"成功从 URL 下载并解析 PDF。文件大小: {len(pdf_bytes)} 字节。",
                extracted_data={
                    "download_status": "success",
                    "file_size": len(pdf_bytes),
                    "pdf_info": context.shared_state.get("pdf_info", {})
                }
            )

        except Exception as e:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"从 URL 下载文件发生异常: {str(e)}"
            )
