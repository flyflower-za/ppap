#!/usr/bin/env python3
"""
测试修复后的签名检查器
"""
import asyncio
import sys
sys.path.append('/app')

from app.checkers.sig_verifier import verify_pdf_signatures

async def test_fixed_signature_check():
    try:
        with open('/app/test_signed.pdf', 'rb') as f:
            pdf_bytes = f.read()

        print("🔍 测试修复后的签名检查器...")
        result = await verify_pdf_signatures(pdf_bytes)

        print(f"📊 结果:")
        print(f"   包含签名: {result.get('signed', False)}")
        print(f"   签名数量: {len(result.get('signatures', []))}")

        if result.get('signatures'):
            for sig in result['signatures']:
                print(f"\n   📝 签名详情:")
                print(f"     名称: {sig.get('signature_name')}")
                print(f"     完整性: {'✅' if sig.get('integrity') else '❌'}")
                print(f"     签署人: {sig.get('signer_cn')}")
        else:
            print("❌ 仍未找到签名")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fixed_signature_check())