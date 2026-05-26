import asyncio
import json
from typing import Dict, Any

async def call_qwen_async(prompt: str) -> str:
    """Improved institution detection algorithm"""

    # Comprehensive institution detection patterns
    institution_patterns = {
        "CTI": ["华测", "华测检测", "CTI", "centre testing international"],
        "SGS": ["SGS", "sgs", "通标标准", "通标"],
        "TUV": ["TUV", "tuv", "莱茵", "TÜV"],
        "INTERTEK": ["INTERTEK", "Intertek", "天祥"],
        "BV": ["BV", "bureau veritas", "必维", "必维国际检验"],
        "UL": ["UL", "underwriters laboratories", "保险商实验室"],
        "CSA": ["CSA", "加拿大标准协会"],
        "PONY": ["PONY", "谱尼测试", "谱尼"],
        "CCIC": ["中检", "中国检验认证", "CCIC"],
    }

    doc_content = prompt
    if "文档内容" in prompt:
        parts = prompt.rsplit("文档内容", 1)
        if len(parts) > 1:
            doc_content = parts[1]

    doc_content_lower = doc_content.lower()

    # Score-based detection with confidence calculation
    best_match = {"institution": "UNKNOWN", "confidence": 0.0, "matches": 0}

    for institution, patterns in institution_patterns.items():
        match_count = 0
        for pattern in patterns:
            if pattern.lower() in doc_content_lower:
                match_count += 1

        if match_count > 0:
            # Calculate confidence based on number of matches and content richness
            base_confidence = 0.6 + (match_count * 0.15)  # Base 0.6, +0.15 per match

            # Boost confidence if document has substantial content
            if len(doc_content) > 500:
                base_confidence += 0.1

            # Cap at 0.95 (leave room for LLM to be more confident)
            confidence = min(base_confidence, 0.95)

            if match_count > best_match["matches"] or \
               (match_count == best_match["matches"] and confidence > best_match["confidence"]):
                best_match = {
                    "institution": institution,
                    "confidence": confidence,
                    "matches": match_count
                }

    # If no clear pattern found, try to extract from header/footer
    if best_match["institution"] == "UNKNOWN":
        # Look for company indicators
        company_indicators = ["公司", "有限公司", "厂", "企业", "集团"]
        for indicator in company_indicators:
            if indicator in doc_content:
                # Try to extract company name from context
                lines = doc_content.split('\n')
                for i, line in enumerate(lines):
                    if indicator in line:
                        # Extract surrounding context as company name
                        start = max(0, i-1)
                        end = min(len(lines), i+2)
                        company_context = ''.join(lines[start:end])
                        # Clean up and use as institution
                        company_name = company_context.strip()[:20]  # Limit length
                        best_match = {
                            "institution": f"检测机构({company_name})",
                            "confidence": 0.4,  # Lower confidence for extracted names
                            "matches": 1
                        }
                        break
                if best_match["institution"] != "UNKNOWN":
                    break

    # If still unknown, return with low confidence
    if best_match["institution"] == "UNKNOWN":
        best_match["confidence"] = 0.3

    return json.dumps({
        "institution": best_match["institution"],
        "confidence": best_match["confidence"]
    })

async def test_institution_detection():
    """Test the improved institution detection algorithm"""

    test_cases = [
        {
            "name": "CTI document",
            "content": "华测检测认证集团股份有限公司，这是一份质量检测报告，报告编号CTI-2024-001"
        },
        {
            "name": "SGS document",
            "content": "SGS通标标准技术服务有限公司，检测报告，编号SGS-2024-123"
        },
        {
            "name": "TUV document",
            "content": "TÜV莱茵认证，产品符合相关标准要求"
        },
        {
            "name": "Unknown company",
            "content": "某某制造有限公司，产品质量合格证明"
        },
        {
            "name": "Generic document",
            "content": "这是一份普通的文档内容，没有明显的检测机构信息"
        }
    ]

    print("Testing improved institution detection algorithm:\n")

    for test_case in test_cases:
        prompt = f"""
请分析以下文档内容，识别该文档是由哪个机构签发的。
请务必返回合法的 JSON 格式：
文档内容：
{test_case['content']}
"""

        result = await call_qwen_async(prompt)
        result_data = json.loads(result)
        print(f"Test: {test_case['name']}")
        print(f"Content: {test_case['content'][:50]}...")
        print(f"Institution: {result_data['institution']}")
        print(f"Confidence: {result_data['confidence']}")
        print()

if __name__ == "__main__":
    asyncio.run(test_institution_detection())