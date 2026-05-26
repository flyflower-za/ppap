"""
OpenAI兼容LLM配置测试脚本
测试签发机构嗅探算法的LLM接口配置
"""
import asyncio
import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_llm_config():
    try:
        from app.services.aliyun_service import aliyun_service
        from app.core.config import settings

        print("🧪 测试OpenAI兼容LLM配置")
        print("=" * 60)

        # 显示配置信息
        print(f"📍 Endpoint: {settings.ALIYUN_AGENT_ENDPOINT}")
        print(f"🔑 API Key: {settings.ALIYUN_ACCESS_KEY_ID[:10] if settings.ALIYUN_ACCESS_KEY_ID else 'None'}...")
        model_name = getattr(settings, 'ALIYUN_MODEL_NAME', 'gpt-3.5-turbo')
        print(f"🤖 Model: {model_name}")

        # 检查是否配置了LLM
        if not settings.ALIYUN_ACCESS_KEY_ID or not settings.ALIYUN_AGENT_ENDPOINT:
            print("\n⚠️  未检测到LLM配置，将使用智能fallback算法")
            print("📖 请参考 LLM_CONFIG_GUIDE.md 配置LLM接口")
            return

        print("\n📄 测试用例：")

        # 测试用例
        test_cases = [
            {
                "name": "CTI机构文档",
                "content": "华测检测认证集团股份有限公司，这是一份质量检测报告，报告编号CTI-2024-001"
            },
            {
                "name": "SGS机构文档",
                "content": "SGS通标标准技术服务有限公司，检测报告，编号SGS-2024-123"
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. {test_case['name']}")
            print(f"   内容: {test_case['content'][:30]}...")

            test_prompt = f"""
请分析以下文档内容，识别该文档是由哪个机构签发的。
请务必返回合法的 JSON 格式，包含以下字段：
- "institution": 机构名称简写或全称
- "confidence": 0.0 到 1.0 的置信度

文档内容：
{test_case['content']}
"""

            try:
                result = await aliyun_service.call_qwen_async(test_prompt)
                print(f"   ✅ 调用成功")

                # 尝试解析JSON结果
                try:
                    result_data = json.loads(result)
                    institution = result_data.get('institution', 'N/A')
                    confidence = result_data.get('confidence', 'N/A')
                    print(f"   📊 结果: 机构={institution}, 置信度={confidence}")
                except json.JSONDecodeError:
                    print(f"   📄 原始结果: {result[:100]}...")

            except Exception as e:
                print(f"   ❌ 调用失败: {str(e)[:100]}")

        print("\n" + "=" * 60)
        print("🎉 测试完成！如果所有测试都通过，说明LLM配置正确。")

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保在backend目录下运行此脚本")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm_config())