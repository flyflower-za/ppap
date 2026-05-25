#!/usr/bin/env python3
"""
检查PPAP项目中的数字签名校验规则
"""
import asyncio
import sys
sys.path.append('/app')

from sqlalchemy import text
from app.core.database import async_session_maker

async def check_signature_rules():
    """检查数据库中的数字签名规则"""
    print("🔍 检查PPAP项目中的数字签名校验规则")
    print("=" * 50)

    async with async_session_maker() as db:
        try:
            # 查询所有规则
            result = await db.execute(
                text("SELECT rule_name, rule_type, rule_content, is_active, logic_config FROM verification_rules")
            )
            rules = result.fetchall()

            print(f"📋 总共找到 {len(rules)} 个校验规则\n")

            has_sig_plugin = False
            has_sig_logic = False

            for i, rule in enumerate(rules, 1):
                rule_name, rule_type, rule_content, is_active, logic_config = rule

                print(f"{i}. {rule_name}")
                print(f"   类型: {rule_type}")
                print(f"   内容: {rule_content}")
                print(f"   激活: {is_active}")

                # 检查是否涉及数字签名
                if rule_content and "signature" in str(rule_content).lower():
                    has_sig_plugin = True
                    print("   ✅ 包含数字签名插件要求")

                if logic_config:
                    import json
                    try:
                        logic = json.loads(logic_config)
                        if 'digital_signature' in str(logic):
                            has_sig_logic = True
                            print("   ✅ 包含数字签名逻辑节点")
                    except:
                        pass

                print()

            print("=" * 50)
            print("📊 数字签名规则检查结果:")
            print(f"   数字签名插件规则: {'✅ 存在' if has_sig_plugin else '❌ 不存在'}")
            print(f"   数字签名逻辑节点: {'✅ 存在' if has_sig_logic else '❌ 不存在'}")

            if not has_sig_plugin and not has_sig_logic:
                print("\n⚠️  没有找到数字签名校验规则！")
                print("   这就是为什么上传的PDF没有识别到数字签名的原因。")
                print("\n💡 解决方案:")
                print("   1. 在系统设置中添加数字签名校验规则")
                print("   2. 或者修改现有规则，添加数字签名检查要求")

        finally:
            await db.close()

if __name__ == "__main__":
    asyncio.run(check_signature_rules())