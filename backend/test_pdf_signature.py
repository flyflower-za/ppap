#!/usr/bin/env python3
"""
测试特定PDF文件的数字签名
"""
import asyncio
import sys
sys.path.append('/app')

from app.checkers.sig_verifier import verify_pdf_signatures

async def test_pdf_signature():
    """测试PDF签名"""
    print("🔍 检查PDF文件的数字签名")
    print("=" * 50)

    try:
        # 读取PDF文件
        with open('/app/test_signed.pdf', 'rb') as f:
            pdf_bytes = f.read()

        print(f"📄 PDF文件大小: {len(pdf_bytes)} 字节")
        print(f"📄 PDF文件大小: {len(pdf_bytes) / 1024:.2f} KB")

        # 检查签名
        print("\n🔐 开始数字签名检查...")
        result = await verify_pdf_signatures(pdf_bytes)

        print(f"\n📊 签名检查结果:")
        print(f"   包含签名: {'是' if result.get('signed', False) else '否'}")
        print(f"   签名数量: {len(result.get('signatures', []))}")

        signatures = result.get('signatures', [])
        if signatures:
            print(f"\n📝 数字签名详情:")
            for i, sig in enumerate(signatures, 1):
                print(f"   签名 #{i}:")
                print(f"     名称: {sig.get('signature_name', 'Unknown')}")
                print(f"     完整性: {'✅ 完整' if sig.get('integrity', False) else '❌ 已篡改'}")
                print(f"     过期: {'❌ 已过期' if sig.get('expired', False) else '✅ 有效'}")
                print(f"     签署人: {sig.get('signer_cn', 'Unknown')}")
                print(f"     签署时间: {sig.get('signing_time', 'Unknown')}")
                print(f"     页码: {sig.get('page', 'Unknown')}")
                print(f"     位置: {sig.get('rect', 'Unknown')}")

                cert_info = sig.get('cert_info', {})
                if cert_info:
                    print(f"     证书信息:")
                    if 'subject' in cert_info:
                        subject = cert_info['subject']
                        print(f"       主体: {subject.get('common_name', 'N/A')}")
                        print(f"       组织: {subject.get('organization_name', 'N/A')}")
                        print(f"       部门: {subject.get('organizational_unit_name', 'N/A')}")
                    if 'issuer' in cert_info:
                        issuer = cert_info['issuer']
                        print(f"       颁发者: {issuer.get('common_name', 'N/A')}")
                    if 'validity' in cert_info:
                        validity = cert_info['validity']
                        print(f"       有效期: {validity.get('not_before', 'N/A')} 到 {validity.get('not_after', 'N/A')}")
        else:
            print("❌ 未找到任何数字签名")

        return result

    except Exception as e:
        print(f"❌ 检查签名时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_pdf_signature())