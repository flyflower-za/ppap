"""
Rule Change Approval Workflow - 规则变更审批流程
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Text, DateTime, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base


class ApprovalStatus(str, enum.Enum):
    DRAFT = "draft"                # 草稿
    PENDING = "pending"            # 待审批
    APPROVED = "approved"          # 已批准
    REJECTED = "rejected"          # 已拒绝
    DEPLOYED = "deployed"          # 已部署
    ROLLED_BACK = "rolled_back"   # 已回滚


class RuleChangeRequest(Base):
    """规则变更请求 - 记录所有规则修改并支持审批流程"""
    __tablename__ = "rule_change_requests"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联的规则 (可为空，因为可能是新建规则)
    rule_id = Column(UUID(as_uuid=False), ForeignKey("verification_rules.id"))

    # 变更类型
    change_type = Column(String(20))  # "create" | "update" | "delete" | "deactivate"

    # 变更内容 (完整的规则定义)
    proposed_rule_data = Column(JSONB, nullable=False)

    # 变更原因和说明
    reason = Column(Text)
    impact_assessment = Column(Text)  # 影响评估

    # 状态
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.DRAFT)

    # 申请人
    requested_by = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    requested_at = Column(DateTime, default=datetime.utcnow)

    # 审批人
    reviewed_by = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    review_comment = Column(Text)

    # 部署信息
    deployed_by = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    deployed_at = Column(DateTime)

    # 关联的分类 (如果有)
    category_id = Column(UUID(as_uuid=False), ForeignKey("document_categories.id"))

    # 紧急程度
    priority = Column(String(20), default="normal")  # "low" | "normal" | "high" | "urgent"

    # 附加的测试结果 (沙盒测试的输出)
    test_results = Column(JSONB)

    # 关系
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    deployer = relationship("User", foreign_keys=[deployed_by])


class ApprovalPolicy(Base):
    """审批策略 - 定义哪些规则变更需要审批"""
    __tablename__ = "approval_policies"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 策略名称
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # 触发条件
    conditions = Column(JSONB, nullable=False)  # {"severity": ["fail"], "category_ids": [...], "is_global": true}

    # 审批要求
    requires_approval = Column(Boolean, default=True)
    required_approvers = Column(JSONB)  # [{"user_id": "...", "role": "admin"}, ...]
    min_approvals_required = Column(Integer, default=1)

    # 是否启用
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# 预置审批策略示例
DEFAULT_APPROVAL_POLICIES = [
    {
        "name": "全局拦截规则修改审批",
        "description": "修改全局生效且严重级别为 fail 的规则需要审批",
        "conditions": {
            "is_global": True,
            "severity": ["fail"]
        },
        "requires_approval": True,
        "required_approvers": [{"role": "admin"}],
        "min_approvals_required": 1
    },
    {
        "name": "LLM 规则配置审批",
        "description": "新建或修改 LLM 相关规则需要审批（成本控制）",
        "conditions": {
            "rule_types": ["llm_prompt", "logic_graph"],
            "contains_llm_node": True
        },
        "requires_approval": True,
        "required_approvers": [{"role": "supervisor"}],
        "min_approvals_required": 1
    },
    {
        "name": "分类专属规则免审批",
        "description": "特定分类的规则修改可以快速生效（沙盒测试通过后）",
        "conditions": {
            "is_global": False,
            "severity": ["warning", "reference"]
        },
        "requires_approval": False
    }
]
