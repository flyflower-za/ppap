#!/usr/bin/env python3
"""
深度分析PDF签名字段结构
"""
import sys
import re
sys.path.append('/app')

def deep_signature_analysis():
    """深度分析PDF签名字段"""
    print("🔍 深度分析PDF签名字段结构")
    print("=" * 50)

    pdf_path = '/app/test_signed.pdf'

    try:
        # 读取原始PDF内容
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read().decode('latin1')

        # 查找签名字段
        sig_pattern = r'(\d+ \d+ obj\s*<<\s*.*?/Type\s*/Sig\s*.*?>>)'
        sig_matches = re.findall(sig_pattern, pdf_content, re.DOTALL)

        print(f"📝 找到 {len(sig_matches)} 个可能的签名字段")

        for i, sig_match in enumerate(sig_matches[:3], 1):  # 只显示前3个
            print(f"\n   签名字段 #{i}:")
            # 清理显示
            clean_sig = sig_match.replace('\n', ' ').replace('\r', ' ')
            print(f"     {clean_sig[:200]}...")

            # 检查关键字段
            if '/ByteRange' in sig_match:
                byte_range_match = re.search(r'/ByteRange\s*\[([^\]]+)\]', sig_match)
                if byte_range_match:
                    print(f"     ✅ ByteRange: {byte_range_match.group(1)}")

            if '/Contents' in sig_match:
                contents_match = re.search(r'/Contents\s*([^\s<>]+)', sig_match)
                if contents_match:
                    print(f"     ✅ Contents: {contents_match.group(1)}")

            if '/Filter' in sig_match:
                filter_match = re.search(r'/Filter\s*/([^\s/<>]+)', sig_match)
                if filter_match:
                    print(f"     ✅ Filter: {filter_match.group(1)}")

            if '/SubFilter' in sig_match:
                subfilter_match = re.search(r'/SubFilter\s*/([^\s/<>]+)', sig_match)
                if subfilter_match:
                    print(f"     ✅ SubFilter: {subfilter_match.group(1)}")

        # 查找特定的签名字段名称
        field_pattern = r'/T\s*\(([^)]+)\)'
        field_matches = re.findall(field_pattern, pdf_content)
        print(f"\n📋 找到 {len(field_matches)} 个字段名称:")
        for field in field_matches[:10]:  # 只显示前10个
            print(f"     {field}")

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deep_signature_analysis()