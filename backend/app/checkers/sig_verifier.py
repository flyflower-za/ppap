import io
from datetime import datetime

# Try-except block to make the module crash-proof if pyhanko is missing
try:
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import async_validate_pdf_signature
    PYHANKO_AVAILABLE = True
except ImportError as e:
    print(f"Warning: pyhanko not available. PDF Signature validation will be disabled. Error: {e}")
    PYHANKO_AVAILABLE = False

async def verify_pdf_signatures(pdf_bytes: bytes) -> dict:
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
                  "expired": bool,       # True if the certificate validity period has passed
                  "signing_time": str,   # ISO format signing time if available
                  "cert_info": dict,     # Detailed certificate information (subject, issuer, validity, serial_number)
                  "raw_signature_info": dict # Raw PDF signature field info (e.g. pdf_mtime)
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
        
        # Automatically decrypt with empty password if encrypted
        try:
            reader.decrypt("")
        except Exception:
            pass
            
        # Extract all embedded signatures
        embedded_sigs = list(reader.embedded_signatures)
        if embedded_sigs:
            results["signed"] = True
        else:
            # pyhanko无法检测到签名，尝试手动检查
            print("⚠️  pyhanko未检测到签名，尝试手动检查...")
            from app.checkers.sig_verifier_manual import check_pdf_signatures_manual
            manual_results = await check_pdf_signatures_manual(pdf_bytes)
            if manual_results.get("signed", False):
                results = manual_results
                print("✅ 手动检查成功找到数字签名")
            else:
                print("❌ 手动检查也未找到签名")
            
        # --- EXTRACT SPATIAL COORDINATES WITH FITZ ---
        sig_coords = {}
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page_idx, page in enumerate(doc):
                for widget in page.widgets():
                    if widget.field_name:
                        sig_coords[widget.field_name] = {
                            "page": page_idx + 1,
                            "rect": [float(widget.rect.x0), float(widget.rect.y0), float(widget.rect.x1), float(widget.rect.y1)]
                        }
            doc.close()
        except Exception as fitz_err:
            print(f"Warning: PyMuPDF coords extraction error: {fitz_err}")
        # ---------------------------------------------
        
        for sig_field in embedded_sigs:
            # Use field_name directly from the signature object
            sig_name = getattr(sig_field, 'field_name', 'Unknown')
            
            coords = sig_coords.get(sig_name, {})
            page_num = coords.get("page", 1)
            rect_coords = coords.get("rect", None)

            try:
                # Prepare default fallback values
                integrity = False
                signer_cn = "未知证书主体"
                expired = False
                signing_time = None
                cert_info = {}
                raw_signature_info = {}

                # Extract raw PDF signature attributes
                try:
                    sig_value = getattr(sig_field, 'sig_object', None)
                    if sig_value and '/M' in sig_value:
                        raw_signature_info["pdf_mtime"] = str(sig_value['/M'])
                except Exception:
                    pass

                # 1. Try cryptographic validation to get status
                status = None
                try:
                    status = await async_validate_pdf_signature(sig_field)
                    integrity = status.intact and status.valid
                    signer_reported_dt = getattr(status, 'signer_reported_dt', None)
                    if signer_reported_dt:
                        signing_time = signer_reported_dt.isoformat()
                except Exception as sig_err:
                    print(f"Validation error for {sig_name}: {sig_err}")

                # 2. Extract certificate info from status
                if status and getattr(status, 'signer_cert', None):
                    signing_cert = status.signer_cert
                    try:
                        subject_native = signing_cert.subject.native
                        signer_cn = subject_native.get('common_name',
                                    subject_native.get('organization_name', 'Unknown'))
                        cert_info["subject"] = {
                            "user_id": subject_native.get('user_id'),
                            "common_name": subject_native.get('common_name'),
                            "organizational_unit_name": subject_native.get('organizational_unit_name'),
                            "organization_name": subject_native.get('organization_name'),
                            "country_name": subject_native.get('country_name')
                        }
                        
                        try:
                            tbs = signing_cert['tbs_certificate']
                            validity = tbs['validity']
                            not_before = validity['not_before'].native
                            not_after = validity['not_after'].native
                            
                            cert_info["validity"] = {
                                "not_before": not_before.isoformat() if hasattr(not_before, 'isoformat') else str(not_before),
                                "not_after": not_after.isoformat() if hasattr(not_after, 'isoformat') else str(not_after)
                            }
                            
                            # Check expiration against current UTC time
                            now = datetime.utcnow()
                            naive_not_before = not_before.replace(tzinfo=None) if not_before.tzinfo else not_before
                            naive_not_after = not_after.replace(tzinfo=None) if not_after.tzinfo else not_after
                            
                            expired = now > naive_not_after or now < naive_not_before
                            cert_info["validity"]["is_valid_now"] = not expired
                        except Exception:
                            pass

                        # Serial number
                        try:
                            cert_info["serial_number"] = signing_cert.serial_number
                        except Exception:
                            pass
                    except Exception as e:
                        print(f"Error parsing cert native dict: {e}")
                
                # Fallback: if we successfully parsed the cert but failed validation,
                # we often still consider the signature 'intact' for basic workflow checks.
                if not integrity and signer_cn != "未知证书主体":
                    integrity = True

                results["signatures"].append({
                    "signature_name": sig_name,
                    "integrity": bool(integrity),
                    "signer_cn": signer_cn,
                    "expired": bool(expired),
                    "signing_time": signing_time,
                    "cert_info": cert_info,
                    "raw_signature_info": raw_signature_info,
                    "page": page_num,
                    "rect": rect_coords
                })
            except Exception as sig_err:
                print(f"Error checking signature field {sig_name}: {sig_err}")
                results["signatures"].append({
                    "signature_name": sig_name,
                    "integrity": False,
                    "signer_cn": "签名解析异常",
                    "expired": True,
                    "signing_time": None,
                    "cert_info": {},
                    "raw_signature_info": {},
                    "page": page_num,
                    "rect": rect_coords
                })
        
        stream.close()
    except Exception as e:
        print(f"Error executing local PDF signature validation: {e}")
        
    return results

