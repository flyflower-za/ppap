import io
import asyncio
from pyhanko.pdf_utils.reader import PdfFileReader

async def main():
    with open("../A225097188910101C.pdf", "rb") as f:
        pdf_bytes = f.read()

    stream = io.BytesIO(pdf_bytes)
    reader = PdfFileReader(stream)
    try:
        reader.decrypt("")
    except Exception:
        pass
    
    embedded_sigs = list(reader.embedded_signatures)
    
    for sig_field in embedded_sigs:
        print("Dir:", dir(sig_field))
        sig_obj = sig_field.sig_object
        print("Sig obj:", sig_obj)
        # Try to extract the certificate from pkcs7
        signing_cert = sig_field.signer_cert
        print("Signer cert:", signing_cert)
        if signing_cert:
            subject_native = signing_cert.subject.native
            print("Subject:", subject_native)
            
        try:
            integrity_info = sig_field.compute_integrity_info()
            print("Integrity info:", integrity_info)
        except Exception as e:
            print("Integrity info error:", e)
        
if __name__ == "__main__":
    asyncio.run(main())
