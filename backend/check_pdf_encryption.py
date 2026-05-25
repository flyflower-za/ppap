#!/usr/bin/env python3
"""
检查PDF文件是否加密
"""
import sys
sys.path.append('/app')

try:
    import pypdf
except ImportError:
    try:
        import PyPDF2 as pypdf
    except ImportError:
        print("❌ 无法导入PDF库")
        sys.exit(1)

def check_pdf_encryption():
    """检查PDF加密状态"""
    print("🔍 检查PDF文件加密状态")
    print("=" * 50)

    try:
        with open('/app/test_signed.pdf', 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)

            # 检查是否加密
            is_encrypted = pdf_reader.is_encrypted
            print(f"📄 PDF加密状态: {'✅ 已加密' if is_encrypted else '❌ 未加密'}")

            if is_encrypted:
                print("⚠️  PDF文件已加密，需要密码才能访问内容")
                print("🔐 这可能就是为什么无法识别数字签名的原因")

                # 尝试获取加密信息
                try:
                    pdf_reader.decrypt("")  # 尝试空密码
                    print("✅ 空密码解密成功")
                except:
                    print("❌ 空密码解密失败，需要正确的密码")

            # 检查页面数量
            num_pages = len(pdf_reader.pages)
            print(f"📄 PDF页数: {num_pages}")

            # 检查元数据
            try:
                metadata = pdf_reader.metadata
                if metadata:
                    print(f"📋 PDF元数据:")
                    if '/Title' in metadata:
                        print(f"   标题: {metadata['/Title']}")
                    if '/Author' in metadata:
                        print(f"   作者: {metadata['/Author']}")
                    if '/Subject' in metadata:
                        print(f"   主题: {metadata['/Subject']}")
            except:
                print("📋 无法读取元数据")

            # 使用PyMuPDF检查签名字段
            try:
                import fitz
                doc = fitz.open("/app/test_signed.pdf")
                print(f"\n📝 PyMuPDF检查:")
                print(f"   页数: {len(doc)}")

                # 检查表单字段和签名
                for page_num, page in enumerate(doc):
                    widgets = page.widgets()
                    if widgets:
                        print(f"   第{page_num + 1}页字段数量: {len(widgets)}")
                        for widget in widgets:
                            if widget.field_name:
                                print(f"     字段名: {widget.field_name}, 类型: {widget.field_type}")
                    else:
                        print(f"   第{page_num + 1}页: 无表单字段")

                doc.close()
            except Exception as e:
                print(f"❌ PyMuPDF检查失败: {e}")

    except Exception as e:
        print(f"❌ 检查PDF时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_pdf_encryption()