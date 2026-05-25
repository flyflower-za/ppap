#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('/app')

async def main():
    try:
        print("🔍 开始测试签名检查...")
        with open('/app/test_signed.pdf', 'rb') as f:
            pdf_bytes = f.read()

        from app.checkers.sig_verifier import verify_pdf_signatures
        result = await verify_pdf_signatures(pdf_bytes)

        print(f"📊 签名检查结果:")
        print(f"   包含签名: {result.get('signed', False)}")
        print(f"   签名数量: {len(result.get('signatures', []))}")

        for i, sig in enumerate(result.get('signatures', []), 1):
            print(f"\n   📝 签名 #{i}:")
            print(f"     名称: {sig.get('signature_name')}")
            print(f"     完整性: {'✅' if sig.get('integrity') else '❌'}")
            print(f"     签署人: {sig.get('signer_cn')}")
            print(f"     算法: {sig.get('cert_info', {}).get('signature_algorithm', 'N/A')}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())