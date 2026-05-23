"""
PDF QR Code Decoder - Localized Checker Module

Uses PyMuPDF (fitz) for PDF page rendering and OpenCV's built-in
QRCodeDetector for decoding. Zero system-level library dependencies.
"""
import fitz  # PyMuPDF
import numpy as np
import cv2


def decode_pdf_qrcodes(pdf_bytes: bytes, pages: list[int] | None = None) -> list[dict]:
    """
    Renders PDF pages to high-resolution images via PyMuPDF (fitz)
    and decodes all QR codes using OpenCV's built-in QRCodeDetector.

    No system-level zbar or external model dependencies required.

    Args:
        pdf_bytes: Raw PDF file content as bytes.
        pages: Optional list of 1-indexed page numbers to scan.
               If None, all pages are scanned.

    Returns:
        list of dict: [{"page": 1, "data": "https://example.com/verify/123"}]
    """
    results = []

    if not pdf_bytes or len(pdf_bytes) < 10:
        return results

    try:
        # Open PDF from memory bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # Initialize OpenCV's built-in QR detector (pure C++, no external libs)
        detector = cv2.QRCodeDetector()

        page_range = range(len(doc))
        if pages:
            # Convert 1-indexed user input to 0-indexed
            page_range = [p - 1 for p in pages if 0 < p <= len(doc)]

        for page_idx in page_range:
            page = doc[page_idx]

            # Render page to 200 DPI pixmap (good balance of speed vs accuracy)
            pix = page.get_pixmap(dpi=200)

            # Convert PyMuPDF Pixmap to NumPy array
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )

            # Convert to BGR for OpenCV
            if pix.n == 4:
                img = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            else:
                img = img_data

            def extract_rect(box_points):
                if box_points is None or len(box_points) == 0:
                    return None
                try:
                    pts = np.array(box_points).reshape(-1, 2)
                    xs = pts[:, 0]
                    ys = pts[:, 1]
                    scale_x = page.rect.width / pix.width
                    scale_y = page.rect.height / pix.height
                    x1 = float(np.min(xs)) * scale_x
                    y1 = float(np.min(ys)) * scale_y
                    x2 = float(np.max(xs)) * scale_x
                    y2 = float(np.max(ys)) * scale_y
                    return [x1, y1, x2, y2]
                except Exception:
                    return None

            # --- Strategy 1: Try detectAndDecodeMulti (OpenCV 4.7+) ---
            try:
                retval, decoded_texts, points, _ = detector.detectAndDecodeMulti(img)
                if retval and decoded_texts:
                    for i, text in enumerate(decoded_texts):
                        if text and text.strip():
                            rect = None
                            if points is not None and len(points) > i:
                                rect = extract_rect(points[i])
                            results.append({
                                "page": page_idx + 1,
                                "data": text.strip(),
                                "rect": rect
                            })
                    continue  # Successfully decoded, move to next page
            except (cv2.error, AttributeError):
                pass  # Fallback to single-QR detection

            # --- Strategy 2: Fallback to single detectAndDecode ---
            try:
                data, bbox, _ = detector.detectAndDecode(img)
                if data and data.strip():
                    results.append({
                        "page": page_idx + 1,
                        "data": data.strip(),
                        "rect": extract_rect(bbox)
                    })
            except cv2.error:
                pass

            # --- Strategy 3: Try with grayscale + threshold enhancement ---
            if not any(r["page"] == page_idx + 1 for r in results):
                try:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    # Adaptive threshold to improve contrast for low-quality scans
                    enhanced = cv2.adaptiveThreshold(
                        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY, 51, 10
                    )
                    data, bbox, _ = detector.detectAndDecode(enhanced)
                    if data and data.strip():
                        results.append({
                            "page": page_idx + 1,
                            "data": data.strip(),
                            "rect": extract_rect(bbox)
                        })
                except cv2.error:
                    pass

        doc.close()
    except Exception as e:
        print(f"[QR Decoder] Error processing PDF: {e}")

    return results
