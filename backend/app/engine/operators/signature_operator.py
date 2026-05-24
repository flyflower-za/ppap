from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.checkers.sig_verifier import verify_pdf_signatures

class SignatureOperator(BaseOperator):
    """
    Operator to verify digital signatures in the PDF document.
    """
    def __init__(self):
        super().__init__(name="SignatureVerifier")

    @property
    def provides(self) -> List[str]:
        return ["digital_signatures"]

    @property
    def requires(self) -> List[str]:
        return ["pdf_bytes"]

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        pdf_bytes = context.shared_state.get("pdf_bytes")
        if not pdf_bytes:
            try:
                with open(context.file_path, "rb") as f:
                    pdf_bytes = f.read()
            except Exception as e:
                return OperatorResult(
                    operator_name=self.name,
                    pass_status=False,
                    message=f"Failed to load PDF for signature verification: {e}"
                )
        
        try:
            results = await verify_pdf_signatures(pdf_bytes)
            context.shared_state["digital_signatures"] = results
            
            is_signed = results.get("signed", False)
            sigs = results.get("signatures", [])
            valid_sigs = [s for s in sigs if s.get("integrity", False)]
            
            msg = f"Found {len(sigs)} digital signature(s), {len(valid_sigs)} intact." if is_signed else "No digital signatures found."
            
            return OperatorResult(
                operator_name=self.name,
                pass_status=True,
                message=msg,
                extracted_data={"digital_signatures": results}
            )
        except Exception as e:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message=f"Signature Verification failed: {e}"
            )
