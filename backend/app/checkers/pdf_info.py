"""
PDF Info Checker - Localized Checker Module

Checks if the PDF is a text-based (searchable) PDF and gathers basic page metrics.
Uses PyMuPDF (fitz) for fast and robust document analysis.
"""
import fitz  # PyMuPDF


def check_pdf_text_layer(pdf_bytes: bytes) -> dict:
    """
    Analyzes the PDF to determine if it has a vector text layer (searchable/text-based)
    or if it is purely scanned (image-only).

    Args:
        pdf_bytes: Raw PDF file content as bytes.

    Returns:
        dict: {
            "is_text_pdf": bool,
            "page_count": int,
            "char_count": int,
            "sample_text": str,
            "has_images": bool
        }
    """
    result = {
        "is_text_pdf": False,
        "page_count": 0,
        "char_count": 0,
        "sample_text": "",
        "has_images": False
    }

    if not pdf_bytes or len(pdf_bytes) < 10:
        return result

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        result["page_count"] = len(doc)

        total_chars = 0
        sample_chars = []
        has_images = False

        for page in doc:
            # Check for images on this page
            image_list = page.get_images()
            if image_list:
                has_images = True

            # Extract text
            text = page.get_text()
            if text:
                total_chars += len(text)
                # Keep a small sample of the text for preview
                if len(sample_chars) < 200:
                    sample_chars.append(text.strip()[:200 - len(sample_chars)])

        result["char_count"] = total_chars
        result["has_images"] = has_images
        
        # If the character count is significant (e.g. more than 10 characters per page average),
        # then it is recognized as a text-based PDF.
        if total_chars > max(5, len(doc) * 2):
            result["is_text_pdf"] = True
            preview = " ".join(sample_chars).replace("\n", " ").strip()
            result["sample_text"] = preview[:150] + "..." if len(preview) > 150 else preview

        doc.close()
    except Exception as e:
        print(f"[PDF Info Checker] Error parsing PDF text layer: {e}")

    return result
