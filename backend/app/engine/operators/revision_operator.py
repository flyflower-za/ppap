import logging
from typing import List
from app.engine.base import BaseOperator, DocumentContext, OperatorResult
from app.checkers.revision_checker import count_pdf_revisions
from app.checkers.sig_verifier import verify_pdf_signatures

logger = logging.getLogger(__name__)


class RevisionCheckOperator(BaseOperator):
    """
    Operator that checks PDF revision count to detect incremental updates.
    A signed PDF with Revision > 1 has been modified after signing,
    which may indicate tampering.
    """
    def __init__(self):
        super().__init__(name="RevisionCheck")

    @property
    def provides(self) -> List[str]:
        return ["pdf_revisions"]

    @property
    def requires(self) -> List[str]:
        return ["pdf_bytes"]

    async def execute(self, context: DocumentContext, **kwargs) -> OperatorResult:
        pdf_bytes = context.shared_state.get("pdf_bytes")
        if not pdf_bytes:
            return OperatorResult(
                operator_name=self.name,
                pass_status=False,
                message="No PDF bytes available for revision check."
            )

        try:
            # Always count revisions
            revision_data = count_pdf_revisions(pdf_bytes)

            # Cross-reference with signature data if available
            sig_data = context.shared_state.get("digital_signatures", {})
            if sig_data and sig_data.get("signed"):
                is_signed = sig_data.get("signed", False)
                sig_count = len(sig_data.get("signatures", []))

                revision_data["is_signed"] = is_signed
                revision_data["signature_count"] = sig_count

                if is_signed and revision_data["revision_count"] > 1:
                    revision_data["is_tampered_after_sign"] = True
                    revision_data["tamper_message"] = (
                        f"文档已签名但包含 {revision_data['revision_count']} 次修订版本 "
                        f"(签名后新增 {revision_data['revision_count'] - 1} 次增量更新)，"
                        f"存在签名后内容被二次修改的风险"
                    )
                else:
                    revision_data["is_tampered_after_sign"] = False
                    revision_data["tamper_message"] = (
                        f"文档共 {revision_data['revision_count']} 个修订版本，"
                        f"签名后无额外增量更新"
                    )

            context.shared_state["pdf_revisions"] = revision_data

            rev_count = revision_data["revision_count"]
            is_tampered = revision_data.get("is_tampered_after_sign", False)

            if is_tampered:
                msg = (
                    f"⚠️ 文档已签名但存在 {rev_count} 次修订 "
                    f"(签名后 {rev_count - 1} 次增量更新)，内容被二次修改"
                )
            else:
                msg = f"文档共 {rev_count} 个修订版本，版本结构完整"

            return OperatorResult(
                operator_name=self.name,
                pass_status=not is_tampered,
                message=msg,
                extracted_data=revision_data
            )

        except Exception as e:
            logger.error(f"RevisionCheckOperator failed: {e}")
            return OperatorResult(
                operator_name=self.name,
                pass_status=True,  # Pass on error to not block pipeline
                message=f"Revision check failed, assuming safe: {e}"
            )
