import asyncio
import json
import sys
from app.checkers.sig_verifier import verify_pdf_signatures

async def main():
    with open("../A225097188910101C.pdf", "rb") as f:
        pdf_bytes = f.read()
    results = await verify_pdf_signatures(pdf_bytes)
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
