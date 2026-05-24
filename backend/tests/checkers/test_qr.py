import pytest
import os
import cv2

from app.checkers.qr_decoder import decode_pdf_qrcodes


def test_qr_decoder_empty_pdf():
    """Test QR decoder handles empty/invalid input gracefully."""
    results = decode_pdf_qrcodes(b"")
    assert results == []

    results2 = decode_pdf_qrcodes(b"not a pdf")
    assert results2 == []


@pytest.mark.skipif(not hasattr(cv2, 'QRCodeEncoder'), reason="OpenCV QRCodeEncoder not available")
def test_qr_decoder_real_pdf(tmp_path):
    """Test QR decoder against a generated PDF with a QR code."""
    import fitz
    import numpy as np

    encoder = cv2.QRCodeEncoder.create()
    test_url = "https://ppap.example.com/verify/test-123"
    qr_img = encoder.encode(test_url)

    qr_path = str(tmp_path / "_test_qr.png")
    cv2.imwrite(qr_path, qr_img)

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    rect = fitz.Rect(100, 100, 300, 300)
    page.insert_image(rect, filename=qr_path)

    pdf_bytes = doc.tobytes()
    doc.close()

    results = decode_pdf_qrcodes(pdf_bytes)
    assert len(results) > 0
    
    # Verify the decoded content is correct
    found = False
    for r in results:
        if test_url in r['data']:
            found = True
            break
    assert found, "QR code data not found in decoded results"
