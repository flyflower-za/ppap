"""
PDF Revision Checker - Localized Checker Module

Detects incremental updates (revisions) to a PDF document.
Each incremental update adds a cross-reference (xref) section.
A signed PDF with Revision > 1 has been modified after signing,
which may indicate tampering or unauthorized changes.

Ref: PDF 32000-1:2008 Section 7.5.6 Incremental Updates
"""
import re
import io
import logging

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


def count_pdf_revisions(pdf_bytes: bytes) -> dict:
    """
    Count the number of revisions (incremental updates) in a PDF file
    by detecting xref sections in the raw PDF content.

    Each valid PDF has at least 1 xref section.
    Each incremental update appends a new xref section at the end.
    Therefore revision_count = number of xref sections found.

    Returns:
        dict: {
            "revision_count": int,       # Total revisions found
            "has_multiple_revisions": bool,  # True if revision_count > 1
            "is_tampered_after_signing": bool,  # True if revisions > 1 AND signed
            "total_file_size": int,
            "last_revision_offset": int,  # Byte offset of the last xref section
        }
    """
    result = {
        "revision_count": 1,
        "has_multiple_revisions": False,
        "is_tampered_after_sign": False,
        "total_file_size": 0,
        "last_revision_offset": 0,
    }

    if not pdf_bytes or len(pdf_bytes) < 20:
        return result

    result["total_file_size"] = len(pdf_bytes)

    try:
        # Decode as latin-1 (lossless for binary PDF content)
        pdf_text = pdf_bytes.decode("latin-1")

        # Count xref sections.
        # Pattern: 'xref' on its own line (preceded by newline or start of file)
        # followed by whitespace/newline.
        xref_matches = re.findall(r'(?:^|\n\r?|\r)xref[\s\r\n]', pdf_text, re.MULTILINE)

        revision_count = len(xref_matches)
        result["revision_count"] = max(revision_count, 1)  # At least 1

        # Find the byte offset of the LAST xref section
        if xref_matches:
            last_match = xref_matches[-1]
            last_offset = pdf_text.rfind(last_match)
            result["last_revision_offset"] = last_offset

        # Check if there are multiple revisions
        result["has_multiple_revisions"] = revision_count > 1

        # Additionally check using PyMuPDF for cross-validation
        if PYMUPDF_AVAILABLE and revision_count >= 1:
            _enrich_with_pymupdf(pdf_bytes, result)

    except Exception as e:
        logger.error(f"[Revision Checker] Error analyzing PDF revisions: {e}")

    return result


def _enrich_with_pymupdf(pdf_bytes: bytes, result: dict) -> None:
    """Use PyMuPDF to enrich revision data with page/xref info."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        result["page_count"] = len(doc)
        result["xref_length"] = doc.xref_length()

        # Check if xref contains objects that suggest incremental updates
        # (e.g., multiple /Catalog or /Root modifications)
        incremental_object_count = 0
        for i in range(1, doc.xref_length()):
            try:
                obj_str = doc.xref_object(i, compressed=True)
                if obj_str and ("/Catalog" in obj_str or "/Root" in obj_str):
                    incremental_object_count += 1
            except Exception:
                pass

        result["catalog_modifications"] = incremental_object_count

        doc.close()
    except Exception as e:
        logger.warning(f"[Revision Checker] PyMuPDF enrichment failed: {e}")


def check_revision_after_signing(pdf_bytes: bytes, sig_result: dict) -> dict:
    """
    Cross-reference revision count with signature presence.
    If the PDF is signed AND has multiple revisions, it indicates
    the file was modified after signing (incremental update).

    Args:
        pdf_bytes: Raw PDF bytes
        sig_result: Result from verify_pdf_signatures()

    Returns:
        dict with enriched tamper detection
    """
    revision_data = count_pdf_revisions(pdf_bytes)
    is_signed = sig_result.get("signed", False)
    sig_count = len(sig_result.get("signatures", []))

    revision_data["is_signed"] = is_signed
    revision_data["signature_count"] = sig_count

    # Core logic: signed + multiple revisions = tamper risk
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

    return revision_data
