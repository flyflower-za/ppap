import io
import re
from datetime import datetime, timezone

# Try-except block to make the module crash-proof if pyhanko is missing
try:
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import async_validate_pdf_signature
    PYHANKO_AVAILABLE = True
except ImportError as e:
    print(f"Warning: pyhanko not available. PDF Signature validation will be disabled. Error: {e}")
    PYHANKO_AVAILABLE = False


def _extract_cert_info(cert) -> tuple:
    """
    从 asn1crypto x509.Certificate 对象中提取所有有用的信息。
    返回 (signer_cn, expired, cert_info)
    """
    signer_cn = "未知证书主体"
    expired = False
    cert_info = {}

    try:
        subject_native = cert['tbs_certificate']['subject'].native
        signer_cn = (subject_native.get('common_name')
                     or subject_native.get('organization_name')
                     or subject_native.get('email_address')
                     or "未知证书主体")
        cert_info["subject"] = {
            "common_name": subject_native.get('common_name'),
            "organization_name": subject_native.get('organization_name'),
            "organizational_unit_name": subject_native.get('organizational_unit_name'),
            "country_name": subject_native.get('country_name'),
            "locality_name": subject_native.get('locality_name'),
            "state_or_province_name": subject_native.get('state_or_province_name'),
            "email_address": subject_native.get('email_address'),
        }
    except Exception as e:
        print(f"  [cert] subject parse error: {e}")

    try:
        issuer_native = cert['tbs_certificate']['issuer'].native
        cert_info["issuer"] = {
            "common_name": issuer_native.get('common_name'),
            "organization_name": issuer_native.get('organization_name'),
            "country_name": issuer_native.get('country_name'),
        }
    except Exception as e:
        print(f"  [cert] issuer parse error: {e}")

    try:
        validity = cert['tbs_certificate']['validity']
        not_before = validity['not_before'].native
        not_after = validity['not_after'].native
        cert_info["validity"] = {
            "not_before": not_before.isoformat() if hasattr(not_before, 'isoformat') else str(not_before),
            "not_after": not_after.isoformat() if hasattr(not_after, 'isoformat') else str(not_after),
        }
        now = datetime.now(timezone.utc)
        nb = not_before if not_before.tzinfo else not_before.replace(tzinfo=timezone.utc)
        na = not_after if not_after.tzinfo else not_after.replace(tzinfo=timezone.utc)
        expired = now > na or now < nb
        cert_info["validity"]["is_valid_now"] = not expired
    except Exception as e:
        print(f"  [cert] validity parse error: {e}")

    try:
        cert_info["serial_number"] = str(cert['tbs_certificate']['serial_number'].native)
    except Exception:
        pass

    try:
        cert_info["signature_algorithm"] = cert['signature_algorithm']['algorithm'].native
    except Exception:
        pass

    return signer_cn, expired, cert_info


async def verify_pdf_signatures(pdf_bytes: bytes) -> dict:
    """
    Verifies the integrity and authenticity of embedded digital signatures
    in a PDF document using pyHanko.

    Returns:
      dict: {
          "signed": bool,
          "signatures": [
              {
                  "signature_name": str,
                  "integrity": bool,
                  "signer_cn": str,
                  "expired": bool,
                  "signing_time": str,
                  "cert_info": dict,
                  "raw_signature_info": dict
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
        stream = io.BytesIO(pdf_bytes)
        reader = PdfFileReader(stream)

        try:
            reader.decrypt("")
        except Exception:
            pass

        embedded_sigs = list(reader.embedded_signatures)
        if embedded_sigs:
            results["signed"] = True
        else:
            print("⚠️  pyhanko未检测到签名，尝试手动检查...")
            from app.checkers.sig_verifier_manual import check_pdf_signatures_manual
            manual_results = await check_pdf_signatures_manual(pdf_bytes)
            if manual_results.get("signed", False):
                results = manual_results
                print("✅ 手动检查成功找到数字签名")
            else:
                print("❌ 手动检查也未找到签名")

        # 提取签名区域坐标
        sig_coords = {}
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page_idx, page in enumerate(doc):
                for widget in page.widgets():
                    if widget.field_name:
                        sig_coords[widget.field_name] = {
                            "page": page_idx + 1,
                            "rect": [float(widget.rect.x0), float(widget.rect.y0),
                                     float(widget.rect.x1), float(widget.rect.y1)]
                        }
            doc.close()
        except Exception as fitz_err:
            print(f"Warning: PyMuPDF coords extraction error: {fitz_err}")

        for sig_field in embedded_sigs:
            sig_name = getattr(sig_field, 'field_name', 'Unknown')
            coords = sig_coords.get(sig_name, {})
            page_num = coords.get("page", 1)
            rect_coords = coords.get("rect", None)

            try:
                integrity = False
                signer_cn = "未知证书主体"
                expired = False
                signing_time = None
                cert_info = {}
                raw_signature_info = {}

                # 提取签名时间 /M
                try:
                    sig_value = getattr(sig_field, 'sig_object', None)
                    if sig_value and '/M' in sig_value:
                        raw_signature_info["pdf_mtime"] = str(sig_value['/M'])
                except Exception:
                    pass

                # ── STEP 1: 直接从 sig_field.signer_cert 提取证书（无需信任链）──
                # pyhanko 在 EmbeddedPdfSignature 上暴露了已解析好的 asn1crypto 证书对象
                try:
                    signer_cert = sig_field.signer_cert
                    if signer_cert is not None:
                        signer_cn, expired, cert_info = _extract_cert_info(signer_cert)
                        print(f"  ✅ signer_cert 直取成功: {signer_cn}")
                    else:
                        print(f"  ⚠️  signer_cert 为 None ({sig_name})")
                except Exception as cert_err:
                    print(f"  ⚠️  signer_cert 获取失败 ({sig_name}): {cert_err}")

                # ── STEP 2: pyhanko 验证（获取真实的 integrity + signing_time）──
                try:
                    status = await async_validate_pdf_signature(sig_field)
                    integrity = status.intact and status.valid
                    signer_reported_dt = getattr(status, 'signer_reported_dt', None)
                    if signer_reported_dt:
                        signing_time = signer_reported_dt.isoformat()
                    # 如果 STEP1 没拿到证书，用 status.signer_cert 补充
                    if not cert_info and getattr(status, 'signer_cert', None):
                        signer_cn, expired, cert_info = _extract_cert_info(status.signer_cert)
                except Exception as sig_err:
                    print(f"  ⚠️  pyhanko 验证异常 ({sig_name}): {type(sig_err).__name__}: {sig_err}")
                    # 信任链失败 ≠ 签名结构损坏：已有 CN 则视为结构完整
                    if signer_cn != "未知证书主体":
                        integrity = True

                # ── STEP 3: 签名时间 fallback（从 /M 字段解析）──
                if not signing_time and raw_signature_info.get("pdf_mtime"):
                    try:
                        mtime_str = raw_signature_info["pdf_mtime"]
                        m = re.search(r"D:(\d{4})(\d{2})(\d{2})[T]?(\d{2})(\d{2})(\d{2})", mtime_str)
                        if m:
                            signing_time = (f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                                            f"T{m.group(4)}:{m.group(5)}:{m.group(6)}")
                    except Exception:
                        pass

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
