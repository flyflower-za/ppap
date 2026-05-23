import io
from datetime import datetime

# Try-except block to make the module crash-proof if pyhanko or cryptography is missing
try:
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from cryptography.x509.oid import NameOID
    PYHANKO_AVAILABLE = True
except ImportError as e:
    print(f"Warning: pyhanko or cryptography not available. PDF Signature validation will be disabled. Error: {e}")
    PYHANKO_AVAILABLE = False

def verify_pdf_signatures(pdf_bytes: bytes) -> dict:
    """
    Verifies the integrity and authenticity of embedded digital signatures 
    in a PDF document using pyHanko and cryptography.
    
    Returns:
        dict: {
            "signed": bool,
            "signatures": [
                {
                    "signature_name": str,
                    "integrity": bool,    # True if the signed revision remains unaltered
                    "signer_cn": str,      # Common Name (CN) of the signer's certificate
                    "expired": bool        # True if the certificate validity period has passed
                }
            ]
        }
    """
    results = {
        "signed": False,
        "signatures": []
    }
    
    if not PYHANKO_AVAILABLE:
        return results

    try:
        # Wrap bytes in an in-memory BytesIO stream
        stream = io.BytesIO(pdf_bytes)
        reader = PdfFileReader(stream)
        
        # Extract all embedded signatures
        embedded_sigs = list(reader.embedded_signatures)
        if embedded_sigs:
            results["signed"] = True
            
            for sig_field in embedded_sigs:
                sig_name = sig_field.sig_field_spec.field_name
                
                try:
                    # Validate the signature
                    status = validate_pdf_signature(sig_field)
                    
                    # Extract signer Common Name (CN) from subject certificate
                    signer_cert = status.signer_cert
                    signer_cn = "未知证书主体"
                    expired = False
                    
                    if signer_cert:
                        try:
                            # Parse cryptography X.509 Certificate
                            subject = signer_cert.subject
                            cn_attrs = subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                            if cn_attrs:
                                signer_cn = cn_attrs[0].value
                            else:
                                signer_cn = str(signer_cert.subject)
                        except Exception:
                            signer_cn = "无法解析签署人CN"
                            
                        # Verify expiration date
                        try:
                            not_valid_after = getattr(signer_cert, "not_valid_after_utc", None)
                            if not_valid_after is None:
                                not_valid_after = signer_cert.not_valid_after
                            
                            # Clean timezone for comparison
                            if hasattr(not_valid_after, "replace"):
                                expiry_date = not_valid_after.replace(tzinfo=None)
                            else:
                                expiry_date = not_valid_after
                                
                            expired = datetime.utcnow() > expiry_date
                        except Exception:
                            pass
                    
                    # Determine integrity
                    # Signature is valid if the signed revision is intact
                    integrity = status.intact and status.valid
                    
                    results["signatures"].append({
                        "signature_name": sig_name,
                        "integrity": bool(integrity),
                        "signer_cn": signer_cn,
                        "expired": bool(expired)
                    })
                except Exception as sig_err:
                    print(f"Error checking signature field {sig_name}: {sig_err}")
                    results["signatures"].append({
                        "signature_name": sig_name,
                        "integrity": False,
                        "signer_cn": "签名解析异常",
                        "expired": True
                    })
        
        stream.close()
    except Exception as e:
        print(f"Error executing local PDF signature validation: {e}")
        
    return results
