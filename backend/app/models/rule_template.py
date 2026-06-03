"""
Rule Templates - 规则模板模型
提供预置的规则模板，用户可以一键应用到特定分类
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Text, DateTime, JSONB, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class RuleTemplate(Base):
    """规则模板 - 预定义的规则组合，可一键应用"""
    __tablename__ = "rule_templates"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # 建议适用的文档分类列表（存分类 ID 或名称）
    category_suggestions = Column(JSONB, default=list)

    # 是否为系统内置模板
    is_system = Column(Boolean, default=False)

    # 模板包含的规则定义（JSON 格式，与 VerificationRule 结构一致）
    template_rules = Column(JSONB, nullable=False)

    # 创建者
    created_by = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # 是否公开（其他用户可见）
    is_public = Column(Boolean, default=False)

    # 使用次数统计
    usage_count = Column(Integer, default=0)

    # 标签（用于分类和搜索）
    tags = Column(JSONB, default=list)

    # 模板缩略图（预览图 URL）
    thumbnail_url = Column(String(500))


# 预置规则模板示例
DEFAULT_RULE_TEMPLATES = [
    {
        "name": "标准采购订单检测模板",
        "description": "适用于企业采购订单文档的标准检测规则组合，包含签名验证、供应商一致性检查等",
        "category_suggestions": ["采购订单", "Purchase Order", "PO"],
        "is_system": True,
        "is_public": True,
        "tags": ["采购", "订单", "供应商", "签名"],
        "template_rules": [
            {
                "rule_name": "数字签名验证",
                "rule_type": "plugin",
                "rule_content": "REQUIRE_SIGNATURE",
                "severity": "fail",
                "logic_config": {}
            },
            {
                "rule_name": "供应商名称一致性",
                "rule_type": "logic_graph",
                "rule_content": "",
                "severity": "warning",
                "logic_config": {
                    "nodes": [
                        {
                            "id": "input",
                            "type": "input",
                            "label": "📥 文档输入",
                            "position": { "x": 100, "y": 50 },
                            "data": {}
                        },
                        {
                            "id": "sniffer",
                            "type": "institution-sniffer",
                            "label": "🏢 机构嗅探",
                            "position": { "x": 100, "y": 150 },
                            "data": {}
                        },
                        {
                            "id": "compare",
                            "type": "data-compare",
                            "label": "⚖️ 供应商名称比对",
                            "position": { "x": 100, "y": 250 },
                            "data": {
                                "source_a": "institution",
                                "source_b": "extracted_supplier_name",
                                "severity": "warning",
                                "hasSeverity": True
                            }
                        },
                        {
                            "id": "output",
                            "type": "output",
                            "label": "📊 最终判定",
                            "position": { "x": 100, "y": 350 },
                            "data": {}
                        }
                    ],
                    "edges": [
                        { "id": "e-input-sniffer", "source": "input", "target": "sniffer" },
                        { "id": "e-sniffer-compare", "source": "sniffer", "target": "compare" },
                        { "id": "e-compare-output", "source": "compare", "target": "output" }
                    ]
                }
            }
        ]
    },
    {
        "name": "质量检测报告模板",
        "description": "适用于产品质量检测报告的规则组合，重点关注报告编号、检测机构签名等",
        "category_suggestions": ["质量检测报告", "COA", "质检报告"],
        "is_system": True,
        "is_public": True,
        "tags": ["质检", "COA", "报告", "编号"],
        "template_rules": [
            {
                "rule_name": "报告编号格式验证",
                "rule_type": "regex",
                "rule_content": "^报告编号[：:]\\s*[A-Z0-9]{10,}",
                "severity": "warning",
                "logic_config": {}
            },
            {
                "rule_name": "检测机构签名验证",
                "rule_type": "plugin",
                "rule_content": "REQUIRE_SIGNATURE",
                "severity": "fail",
                "logic_config": {
                    "conditions": {
                        "institution": "CTI"
                    }
                }
            },
            {
                "rule_name": "二维码追溯检查",
                "rule_type": "plugin",
                "rule_content": "REQUIRE_QR_CODE",
                "severity": "warning",
                "logic_config": {}
            }
        ]
    },
    {
        "name": "生产计划单基础模板",
        "description": "生产计划文档的最基础检测规则，包含签名和完整性检查",
        "category_suggestions": ["生产计划单", "生产计划"],
        "is_system": True,
        "is_public": True,
        "tags": ["生产", "计划", "基础"],
        "template_rules": [
            {
                "rule_name": "PDF 电子数字签名验证",
                "rule_type": "plugin",
                "rule_content": "REQUIRE_SIGNATURE",
                "severity": "fail",
                "logic_config": {}
            },
            {
                "rule_name": "电子文档篡改检测",
                "rule_type": "plugin",
                "rule_content": "REQUIRE_REVISION_CHECK",
                "severity": "fail",
                "logic_config": {}
            }
        ]
    }
]
