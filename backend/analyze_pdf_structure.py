#!/usr/bin/env python3
"""
全面分析PDF文件结构，寻找数字签名
"""
import sys
sys.path.append('/app')

def analyze_pdf_structure():
    """全面分析PDF文件结构"""
    print("🔍 全面分析PDF文件结构")
    print("=" * 50)

    # 使用多种方法检查PDF签名
    pdf_path = '/app/test_signed.pdf'

    # 方法1: PyMuPDF深度检查
    print("📝 方法1: PyMuPDF深度检查")
    try:
        import fitz
        doc = fitz.open(pdf_path)
        print(f"   PDF信息: {doc.metadata}")
        print(f"   页数: {doc.page_count}")

        # 检查每一页的详细内容
        for page_num in range(doc.page_count):
            page = doc[page_num]
            print(f"\n   第{page_num + 1}页:")

            # 检查widgets（表单字段）
            try:
                widgets = list(page.widgets())
                print(f"     表单字段: {len(widgets)}")
                for widget in widgets:
                    print(f"       字段: {widget.field_name}, 类型: {widget.field_type}")
            except Exception as e:
                print(f"     表单字段检查失败: {e}")

            # 检查页面中的特殊对象
            try:
                # 获取页面内容
                text = page.get_text()
                if text.strip():
                    print(f"     文本内容长度: {len(text.strip())} 字符")

                # 检查是否有图像
                image_list = page.get_images()
                print(f"     图像数量: {len(image_list)}")

            except Exception as e:
                print(f"     页面内容检查失败: {e}")

        # 检查PDF的AcroForm字段
        try:
            xref = doc.pdf_object()
            if '/AcroForm' in xref:
                acroform = xref['/AcroForm']
                print(f"\n   📋 AcroForm字段: {acroform}")
                if '/Fields' in acroform:
                    fields = acroform['/Fields']
                    print(f"     字段数量: {len(fields)}")
                    for field in fields:
                        if '/T' in field:
                            print(f"       字段名: {field['/T']}")
                        if '/FT' in field:
                            print(f"       字段类型: {field['/FT']}")
                        if '/V' in field:
                            print(f"       字段值: {field['/V']}")

        except Exception as e:
            print(f"   AcroForm检查失败: {e}")

        doc.close()

    except Exception as e:
        print(f"❌ PyMuPDF检查失败: {e}")

    # 方法2: 检查PDF原始结构
    print(f"\n📝 方法2: PDF原始结构检查")
    try:
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()

        # 搜索签名相关的关键词
        keywords = [b'/Sig', b'/Signature', b'/ByteRange', b'/Contents', b'/Filter/Adobe.PPKLite', b'/SubFilter/adbe.pkcs7.detached']

        for keyword in keywords:
            count = pdf_content.count(keyword)
            if count > 0:
                print(f"   找到关键词 {keyword.decode('latin1')}: {count} 次")

        # 检查是否有签名字段
        if b'/Sig' in pdf_content:
            print(f"   ✅ PDF包含签名相关字段")

            # 提取签名相关部分
            sig_start = pdf_content.find(b'/Sig')
            if sig_start != -1:
                sig_snippet = pdf_content[max(0, sig_start-200):sig_start+400]
                print(f"   签名字段片段: {sig_snippet[:200]}")

    except Exception as e:
        print(f"❌ 原始结构检查失败: {e}")

    # 方法3: 使用PyPDF详细检查
    print(f"\n📝 方法3: PyPDF详细检查")
    try:
        import pypdf
    except ImportError:
        import PyPDF2 as pypdf

    with open(pdf_path, 'rb') as f:
        pdf_reader = pypdf.PdfReader(f)

        # 检查所有页面
        for page_num, page in enumerate(pdf_reader.pages):
            if '/Annots' in page:
                annotations = page['/Annots']
                print(f"   第{page_num + 1}页注释: {len(annotations)}")
                for annot in annotations:
                    if '/Subtype' in annot:
                        subtype = annot['/Subtype']
                        print(f"     注释类型: {subtype}")
                    if '/T' in annot:
                        print(f"     注释名称: {annot['/T']}")

        # 检查根对象中的AcroForm
        try:
            trailer = pdf_reader.trailer
            if '/Root' in trailer:
                root = trailer['/Root']
                root_obj = pdf_reader.get_object(root)
                if '/AcroForm' in root_obj:
                    acroform = root_obj['/AcroForm']
                    print(f"   📋 AcroForm对象: {acroform}")

                    if '/Fields' in acroform:
                        fields = acroform['/Fields']
                        print(f"     字段数量: {len(fields)}")
                        for field in fields:
                            field_obj = pdf_reader.get_object(field)
                            if '/T' in field_obj:
                                field_name = field_obj['/T']
                                print(f"       字段名: {field_name}")
                            if '/FT' in field_obj:
                                field_type = field_obj['/FT']
                                print(f"       字段类型: {field_type}")

        except Exception as e:
            print(f"   AcroForm检查失败: {e}")

if __name__ == "__main__":
    analyze_pdf_structure()