#!/usr/bin/env python3
"""
测试解密后的PDF数字签名检查
"""
import asyncio
import sys
sys.path.append('/app')

async def test_decrypted_pdf_signature():
    """测试解密后的PDF签名"""
    print("🔍 测试解密后的PDF数字签名检查")
    print("=" * 50)

    try:
        # 首先用PyPDF解密
        try:
            import pypdf
        except ImportError:
            import PyPDF2 as pypdf

        with open('/app/test_signed.pdf', 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)

            if pdf_reader.is_encrypted:
                print("🔐 PDF已加密，尝试解密...")
                # 尝试解密
                decrypted = pdf_reader.decrypt("")
                if decrypted:
                    print("✅ 空密码解密成功")
                else:
                    print("❌ 空密码解密失败")
                    return

                # 将解密后的PDF写入临时文件
                writer = pypdf.PdfWriter()
                for page in pdf_reader.pages:
                    writer.add_page(page)

                decrypted_path = '/app/test_signed_decrypted.pdf'
                with open(decrypted_path, 'wb') as f_out:
                    writer.write(f_out)

                print(f"✅ 解密后的PDF已保存: {decrypted_path}")

        # 现在检查解密后PDF的签名
        from app.checkers.sig_verifier import verify_pdf_signatures

        with open(decrypted_path, 'rb') as f:
            pdf_bytes = f.read()

        print(f"\n🔐 开始数字签名检查...")
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

                cert_info = sig.get('cert_info', {})
                if cert_info:
                    print(f"     证书信息:")
                    if 'subject' in cert_info:
                        subject = cert_info['subject']
                        print(f"       主体: {subject.get('common_name', 'N/A')}")
                        print(f"       组织: {subject.get('organization_name', 'N/A')}")
                    if 'issuer' in cert_info:
                        issuer = cert_info['issuer']
                        print(f"       颁发者: {issuer.get('common_name', 'N/A')}")
                    if 'validity' in cert_info:
                        validity = cert_info['validity']
                        print(f"       有效期: {validity.get('not_before', 'N/A')} 到 {validity.get('not_after', 'N/A')}")
        else:
            print("❌ 解密后仍未找到数字签名")
            print("💡 可能的原因:")
            print("   1. PDF文件确实没有数字签名")
            print("   2. 签名格式不被pyhanko支持")
            print("   3. 签名在加密过程中被损坏")

        return result

    except Exception as e:
        print(f"❌ 检查时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_decrypted_pdf_signature())