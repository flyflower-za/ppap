import asyncio
from app.engine.operators.sniffer_operator import InstitutionSnifferOperator
from app.engine.base import DocumentContext
import sys

async def main():
    with open("../A225097188910101C_Signed-new.pdf", "rb") as f:
        pdf_bytes = f.read()

    ctx = DocumentContext(file_path="dummy.pdf")
    ctx.shared_state["pdf_bytes"] = pdf_bytes
    ctx.shared_state["full_text"] = "" # force vision fallback
    
    op = InstitutionSnifferOperator()
    res = await op.execute(ctx)
    print("Result:", res.dict())

if __name__ == "__main__":
    asyncio.run(main())
