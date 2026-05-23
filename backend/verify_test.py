"""
Verification test script for localized checker modules.
Tests QR Code Decoder and PDF Digital Signature Verifier.
"""
import sys
import os

# Add parent path to import app correctly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def test_qr_decoder_import():
    """Test that the QR decoder module can be imported and its core dependencies load."""
    print("\n=== Test 1: QR Decoder Import ===")
    try:
        from app.checkers.qr_decoder import decode_pdf_qrcodes
        print("✅ QR Decoder module imported successfully")
        return True
    except Exception as e:
        print(f"❌ QR Decoder import failed: {e}")
        return False


def test_qr_decoder_empty_pdf():
    """Test QR decoder handles empty/invalid input gracefully."""
    print("\n=== Test 2: QR Decoder with empty input ===")
    from app.checkers.qr_decoder import decode_pdf_qrcodes
    results = decode_pdf_qrcodes(b"")
    assert results == [], f"Expected empty list, got {results}"
    print(f"✅ Empty bytes: returned {results} (correct)")
    
    results2 = decode_pdf_qrcodes(b"not a pdf")
    print(f"✅ Invalid PDF: returned {results2} (graceful failure)")


def test_qr_decoder_real_pdf():
    """Test QR decoder against a real PDF file if available."""
    print("\n=== Test 3: QR Decoder with real PDF ===")
    from app.checkers.qr_decoder import decode_pdf_qrcodes
    
    # Try to find any PDF in common locations
    test_paths = [
        "test.pdf",
        "app/test.pdf",
    ]
    
    for path in test_paths:
        if os.path.exists(path):
            print(f"📄 Found test PDF: {path}")
            with open(path, "rb") as f:
                pdf_bytes = f.read()
            results = decode_pdf_qrcodes(pdf_bytes)
            print(f"   QR codes found: {len(results)}")
            for r in results:
                print(f"   - Page {r['page']}: {r['data'][:80]}...")
            return
    
    print("⚠️  No test PDF found locally. Generating a simple PDF with PyMuPDF...")
    
    # Generate a test PDF with an embedded QR code image using PyMuPDF
    try:
        import fitz
        import cv2
        import numpy as np
        
        # Create a simple QR code image using OpenCV's QRCodeEncoder if available
        try:
            encoder = cv2.QRCodeEncoder.create()
            qr_img = encoder.encode("https://ppap.example.com/verify/test-123")
            
            # Save QR image temporarily
            qr_path = "/tmp/_test_qr.png"
            cv2.imwrite(qr_path, qr_img)
            
            # Create PDF and insert the QR image
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)  # A4
            rect = fitz.Rect(100, 100, 300, 300)
            page.insert_image(rect, filename=qr_path)
            
            pdf_bytes = doc.tobytes()
            doc.close()
            os.remove(qr_path)
            
            print("   Generated test PDF with embedded QR code.")
            results = decode_pdf_qrcodes(pdf_bytes)
            print(f"   QR codes found: {len(results)}")
            for r in results:
                print(f"   ✅ Page {r['page']}: {r['data']}")
            
            if len(results) == 0:
                print("   ⚠️  No QR detected (OpenCV encoder may not be available)")
        except (cv2.error, AttributeError) as enc_err:
            print(f"   ⚠️  OpenCV QRCodeEncoder not available: {enc_err}")
            print("   Skipping generated QR test. Manual test with real PDF recommended.")
    except Exception as e:
        print(f"   ❌ Test PDF generation failed: {e}")


def test_sig_verifier_import():
    """Test that the signature verifier module can be imported."""
    print("\n=== Test 4: Signature Verifier Import ===")
    try:
        from app.checkers.sig_verifier import verify_pdf_signatures, PYHANKO_AVAILABLE
        print(f"✅ Signature Verifier imported successfully (pyHanko available: {PYHANKO_AVAILABLE})")
        return True
    except Exception as e:
        print(f"❌ Signature Verifier import failed: {e}")
        return False


def test_sig_verifier_empty_pdf():
    """Test signature verifier handles empty/invalid input gracefully."""
    print("\n=== Test 5: Signature Verifier with empty input ===")
    from app.checkers.sig_verifier import verify_pdf_signatures
    
    results = verify_pdf_signatures(b"")
    assert results["signed"] == False
    print(f"✅ Empty bytes: signed={results['signed']}, signatures={results['signatures']}")
    
    results2 = verify_pdf_signatures(b"not a pdf at all")
    print(f"✅ Invalid PDF: signed={results2['signed']} (graceful failure)")


def test_sig_verifier_real_pdf():
    """Test signature verifier against a real PDF if available."""
    print("\n=== Test 6: Signature Verifier with real PDF ===")
    from app.checkers.sig_verifier import verify_pdf_signatures
    
    test_paths = ["test.pdf", "app/test.pdf"]
    for path in test_paths:
        if os.path.exists(path):
            print(f"📄 Found test PDF: {path}")
            with open(path, "rb") as f:
                pdf_bytes = f.read()
            results = verify_pdf_signatures(pdf_bytes)
            print(f"   Signed: {results['signed']}")
            for sig in results["signatures"]:
                print(f"   - {sig['signature_name']}: integrity={sig['integrity']}, "
                      f"signer={sig['signer_cn']}, expired={sig['expired']}")
            return
    
    print("⚠️  No test PDF found. Generate or provide a signed PDF for full testing.")


if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print("=" * 60)
    
    test_qr_decoder_import()
    test_qr_decoder_empty_pdf()
    test_qr_decoder_real_pdf()
    
    test_sig_verifier_import()
    test_sig_verifier_empty_pdf()
    test_sig_verifier_real_pdf()
    
    print("\n" + "=" * 60)
    print("All checker module tests completed.")
