#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('/app')

async def test_latest_file():
    try:
        from app.checkers.sig_verifier import verify_pdf_signatures

        with open('/app/latest_test.pdf', 'rb') as f:
            pdf_bytes = f.read()

        print("🔍 测试最新上传文件的签名检查...")
        result = await verify_pdf_signatures(pdf_bytes)

        print(f"📊 签名检查结果:")
        print(f"   包含签名: {result.get('signed', False)}")
        print(f"   签名数量: {len(result.get('signatures', []))}")

        if result.get('signatures'):
            for sig in result['signatures']:
                print(f"\n   📝 签名详情:")
                print(f"     名称: {sig.get('signature_name')}")
                print(f"     完整性: {'✅' if sig.get('integrity') else '❌'}")
                print(f"     签署人: {sig.get('signer_cn')}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_latest_file())