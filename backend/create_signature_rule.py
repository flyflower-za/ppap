#!/usr/bin/env python3
"""
创建数字签名校验规则的脚本
"""
import asyncio
import sys
import uuid
sys.path.append('/app')

from sqlalchemy import text
from app.core.database import async_session_maker

async def create_signature_verification_rule():
    """创建数字签名校验规则"""
    print("🔧 创建数字签名校验规则")
    print("=" * 50)

    async with async_session_maker() as db:
        try:
            # 首先检查是否存在document_categories表
            cat_result = await db.execute(
                text("SELECT id FROM document_categories LIMIT 1")
            )
            category = cat_result.fetchone()

            if not category:
                # 如果没有类别，创建一个默认类别
                print("📁 创建默认文档类别...")
                cat_id = str(uuid.uuid4())
                await db.execute(
                    text("""
                        INSERT INTO document_categories (id, name, is_active)
                        VALUES (:id, :name, :is_active)
                    """),
                    {"id": cat_id, "name": "通用文档", "is_active": True}
                )
                await db.commit()
                print(f"✅ 创建默认类别: {cat_id}")
            else:
                cat_id = category[0]
                print(f"📁 使用现有类别: {cat_id}")

            # 创建数字签名校验规则
            rule_id = str(uuid.uuid4())
            print(f"\n📝 创建数字签名校验规则: {rule_id}")

            import json
            logic_config_json = json.dumps({
                "nodes": [
                    {
                        "id": "signature_check",
                        "type": "digital_signature",
                        "data": {
                            "expectedIssuer": ""
                        }
                    }
                ],
                "edges": []
            })

            await db.execute(
                text("""
                    INSERT INTO verification_rules (id, category_id, rule_name, rule_type, rule_content, severity, is_active, logic_config)
                    VALUES (:id, :category_id, :rule_name, :rule_type, :rule_content, :severity, :is_active, :logic_config)
                """),
                {
                    "id": rule_id,
                    "category_id": cat_id,
                    "rule_name": "数字签名校验",
                    "rule_type": "logic_graph",
                    "rule_content": "数字签名完整性检查",
                    "severity": "fail",
                    "is_active": True,
                    "logic_config": logic_config_json
                }
            )

            await db.commit()
            print("✅ 数字签名校验规则创建成功！")

            # 验证规则是否创建成功
            verify_result = await db.execute(
                text("SELECT rule_name, rule_type, is_active FROM verification_rules WHERE id = :id"),
                {"id": rule_id}
            )
            created_rule = verify_result.fetchone()

            if created_rule:
                print("\n📊 创建的规则详情:")
                print(f"   规则名称: {created_rule[0]}")
                print(f"   规则类型: {created_rule[1]}")
                print(f"   是否激活: {created_rule[2]}")
                print("\n🎉 现在上传的PDF应该能够识别数字签名了！")
            else:
                print("❌ 规则创建失败")

        except Exception as e:
            print(f"❌ 创建规则时出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await db.close()

if __name__ == "__main__":
    asyncio.run(create_signature_verification_rule())