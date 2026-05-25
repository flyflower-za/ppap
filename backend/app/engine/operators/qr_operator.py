import json
from typing import List, Any
from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.checkers.qr_decoder import decode_pdf_qrcodes

class QRScannerOperator(BaseOperator):
    """
    Operator to scan QR codes from the PDF document.
    """
    def __init__(self):
        super().__init__(name="QRScanner")

    @property
    def provides(self) -> List[str]:
        return ["qr_codes"]

    @property
    def requires(self) -> List[str]:
        return ["pdf_bytes"]

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        # Check if pdf_bytes is available
        pdf_bytes = context.shared_state.get("pdf_bytes")
        if not pdf_bytes:
            # We fall back to reading the file from disk if not pre-loaded in state
            try:
                with open(context.file_path, "rb") as f:
                    pdf_bytes = f.read()
            except Exception as e:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message=f"Failed to load PDF for QR scanning: {e}"
                )
        
        try:
            results = decode_pdf_qrcodes(pdf_bytes)
            # Store in shared context
            context.shared_state["qr_codes"] = results
            
            # Evaluate against kwargs rules if provided (e.g. required_qr_count, require_content_match)
            # By default, just executing the operator extracts the data.
            if results and len(results) > 0:
                pass_status = True
                msg = f"成功提取到 {len(results)} 个二维码数据。"
            else:
                pass_status = False
                msg = "未检测到任何二维码。"
            
            return OperatorResult(
                operator_name=self.name,
                pass_status=pass_status,
                message=msg,
                extracted_data={"qr_codes": results}
            )
        except Exception as e:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"QR Scanning failed: {e}"
            )
