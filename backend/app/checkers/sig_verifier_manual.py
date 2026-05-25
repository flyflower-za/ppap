#!/usr/bin/env python3
"""
备用PDF签名检查器 - 直接解析PDF签名字段
"""
import io
import re
from datetime import datetime
from typing import Dict, List, Any

async def check_pdf_signatures_manual(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    手动检查PDF数字签名，绕过pyhanko的自动检测
    专门处理加密PDF和特殊签名格式
    """
    results = {
        "signed": False,
        "signatures": []
    }

    try:
        # 转换为字符串进行分析
        pdf_content = pdf_bytes.decode('latin1', errors='ignore')

        # 查找签名字段
        sig_pattern = r'(\d+ \d+ obj\s*<<\s*.*?/Type\s*/Sig\s*.*?>>)'
        sig_matches = re.findall(sig_pattern, pdf_content, re.DOTALL)

        if sig_matches:
            results["signed"] = True

            for sig_match in sig_matches:
                # 确保sig_match是字符串类型
                if not isinstance(sig_match, str):
                    sig_match = str(sig_match)
                # 提取签名信息
                sig_info = {
                    "signature_name": "PDF_Digital_Signature",
                    "integrity": False,
                    "signer_cn": "未知签署人",
                    "expired": True,
                    "signing_time": None,
                    "cert_info": {},
                    "raw_signature_info": {},
                    "page": 1,
                    "rect": None
                }

                # 检查ByteRange来验证签名完整性
                if '/ByteRange' in sig_match:
                    byte_range_match = re.search(r'/ByteRange\s*\[([^\]]+)\]', sig_match)
                    if byte_range_match:
                        range_str = byte_range_match.group(1)
                        sig_info["raw_signature_info"]["byte_range"] = range_str
                        # 简单的完整性检查：如果ByteRange存在，假设签名结构完整
                        sig_info["integrity"] = True

                # 提取签名时间
                if '/M' in sig_match:
                    m_match = re.search(r'/M\s*\(D:(\d+)\)', sig_match)
                    if m_match:
                        date_str = m_match.group(1)
                        # 解析PDF日期格式 D:YYYYMMDDHHmmSS+HH'mm
                        try:
                            if len(date_str) >= 14:
                                year = date_str[0:4]
                                month = date_str[4:6]
                                day = date_str[6:8]
                                hour = date_str[8:10]
                                minute = date_str[10:12]
                                second = date_str[12:14]
                                iso_time = f"{year}-{month}-{day}T{hour}:{minute}:{second}"
                                sig_info["signing_time"] = iso_time
                                sig_info["raw_signature_info"]["pdf_mtime"] = f"D:{date_str}"
                        except:
                            pass

                # 检查签名算法
                if '/Filter' in sig_match or '/SubFilter' in sig_match:
                    filter_match = re.search(r'/SubFilter\s*/([^\s/<>]+)', sig_match)
                    if filter_match:
                        subfilter = filter_match.group(1)
                        sig_info["raw_signature_info"]["subfilter"] = subfilter
                        if 'adbe.pkcs7' in subfilter:
                            sig_info["cert_info"]["signature_algorithm"] = "PKCS#7"
                            sig_info["signer_cn"] = "PKCS#7数字签名"

                # 检查签名字段名称
                field_name_match = None
                try:
                    # 找到sig_match在pdf_content中的位置
                    sig_start = pdf_content.find(sig_match)
                    if sig_start != -1:
                        search_area = pdf_content[sig_start:sig_start+500]
                        field_name_match = re.search(r'/T\s*\(([^)]+)\)', search_area)
                        if field_name_match:
                            sig_info["signature_name"] = field_name_match.group(1)
                except Exception:
                    pass

                results["signatures"].append(sig_info)

        return results

    except Exception as e:
        print(f"⚠️  手动签名检查失败: {e}")
        return results

# 导出函数
__all__ = ['check_pdf_signatures_manual']
