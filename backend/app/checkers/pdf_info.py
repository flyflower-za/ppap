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
        "has_images": False,
        "blocks": [], # Will store spatial text blocks
        "full_text": ""
    }

    if not pdf_bytes or len(pdf_bytes) < 10:
        return result

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        result["page_count"] = len(doc)

        total_chars = 0
        sample_chars = []
        has_images = False
        all_blocks = []
        full_text_list = []

        for page_num, page in enumerate(doc):
            # Check for images on this page
            image_list = page.get_images()
            if image_list:
                has_images = True

            # Extract text normally
            text = page.get_text()
            if text:
                total_chars += len(text)
                full_text_list.append(text)
                if len(sample_chars) < 200:
                    sample_chars.append(text.strip()[:200 - len(sample_chars)])
            
            # Extract spatial blocks
            blocks = page.get_text("blocks")
            for b in blocks:
                # b format: (x0, y0, x1, y1, text, block_no, block_type)
                # block_type 0 = text, 1 = image
                b_text = b[4].strip()
                b_type = b[6]
                if b_text and b_type == 0:
                    all_blocks.append({
                        "page": page_num + 1,
                        "bbox": [b[0], b[1], b[2], b[3]], # x0, y0, x1, y1
                        "text": b_text
                    })

        result["char_count"] = total_chars
        result["has_images"] = has_images
        result["blocks"] = all_blocks
        result["full_text"] = "\n".join(full_text_list)
        
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
