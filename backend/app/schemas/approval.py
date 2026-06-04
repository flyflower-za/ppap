"""
Pydantic schemas for Rule Change Approval Workflow (P2)
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class RuleChangeRequestCreate(BaseModel):
    """Submit a new rule change request."""
    rule_id: Optional[UUID] = None  # Null for new rule creation
    change_type: str  # "create" | "update" | "delete" | "deactivate"
    proposed_rule_data: Dict[str, Any]  # Full rule definition snapshot
    reason: str
    impact_assessment: Optional[str] = None
    priority: str = "normal"  # "low" | "normal" | "high" | "urgent"
    category_id: Optional[UUID] = None
    test_results: Optional[Dict[str, Any]] = None


class ReviewAction(BaseModel):
    """Approve or reject a change request."""
    action: str  # "approve" | "reject"
    comment: Optional[str] = None


class RuleChangeRequestResponse(BaseModel):
    id: UUID
    rule_id: Optional[UUID] = None
    change_type: str
    proposed_rule_data: Dict[str, Any]
    reason: Optional[str] = None
    impact_assessment: Optional[str] = None
    status: str
    requested_by: Optional[UUID] = None
    requested_at: Optional[datetime] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    deployed_by: Optional[UUID] = None
    deployed_at: Optional[datetime] = None
    category_id: Optional[UUID] = None
    priority: str = "normal"
    test_results: Optional[Dict[str, Any]] = None

    # Resolved names (populated by API)
    requester_name: Optional[str] = None
    reviewer_name: Optional[str] = None
    deployer_name: Optional[str] = None

    class Config:
        from_attributes = True


class ApprovalPolicyResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    conditions: Dict[str, Any]
    requires_approval: bool
    required_approvers: Optional[Any] = None
    min_approvals_required: int = 1
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
