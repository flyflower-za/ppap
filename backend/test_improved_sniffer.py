import asyncio
from app.services.aliyun_service import aliyun_service

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

        result = await aliyun_service.call_qwen_async(prompt)
        print(f"Test: {test_case['name']}")
        print(f"Content: {test_case['content'][:50]}...")
        print(f"Result: {result}")
        print()

if __name__ == "__main__":
    asyncio.run(test_institution_detection())