#!/usr/bin/env python3
"""
直接测试手动签名检查器
"""
import asyncio
import sys
sys.path.append('/app')

async def test_manual_checker_direct():
    try:
        with open('/app/test_signed.pdf', 'rb') as f:
            pdf_bytes = f.read()

        print("🔍 直接测试手动签名检查器...")
        from app.checkers.sig_verifier_manual import check_pdf_signatures_manual

        result = await check_pdf_signatures_manual(pdf_bytes)

        print(f"📊 手动检查器结果:")
        print(f"   包含签名: {result.get('signed', False)}")
        print(f"   签名数量: {len(result.get('signatures', []))}")

        for i, sig in enumerate(result.get('signatures', []), 1):
            print(f"\n   📝 签名 #{i}:")
            print(f"     名称: {sig.get('signature_name')}")
            print(f"     完整性: {'✅' if sig.get('integrity') else '❌'}")
            print(f"     签署人: {sig.get('signer_cn')}")

        return result

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_manual_checker_direct())