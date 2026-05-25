import io
import json
import asyncio
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import async_validate_pdf_signature

async def main():
    with open("../A225097188910101C.pdf", "rb") as f:
        pdf_bytes = f.read()

    stream = io.BytesIO(pdf_bytes)
    reader = PdfFileReader(stream)
    try:
        reader.decrypt("")
    except Exception as e:
        print("Decrypt error:", e)
    
    embedded_sigs = list(reader.embedded_signatures)
    print("Found embedded sigs:", len(embedded_sigs))
    
    for sig_field in embedded_sigs:
        sig_name = getattr(sig_field, 'field_name', 'Unknown')
        print(f"Signature name: {sig_name}")
        try:
            status = await async_validate_pdf_signature(sig_field)
            print(f"Intact: {status.intact}")
            print(f"Valid: {status.valid}")
            if getattr(status, 'signing_cert', None):
                subject_native = status.signing_cert.subject.native
                signer_cn = subject_native.get('common_name', subject_native.get('organization_name', 'Unknown'))
                print(f"Signer: {signer_cn}")
        except Exception as e:
            print(f"Error validating {sig_name}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
