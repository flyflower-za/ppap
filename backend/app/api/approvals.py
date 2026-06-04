"""
Rule Change Approval Workflow API (P2)
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User, UserRole
from app.models.rule_approval import RuleChangeRequest, ApprovalPolicy, ApprovalStatus, DEFAULT_APPROVAL_POLICIES
from app.models.rule import VerificationRule, RuleType, Severity
from app.schemas.approval import (
    RuleChangeRequestCreate, RuleChangeRequestResponse,
    ReviewAction, ApprovalPolicyResponse
)
from app.core.audit_logger import log_audit_event

router = APIRouter()


# --- Helper: resolve user names ---
async def _enrich_request(db: AsyncSession, req: RuleChangeRequest) -> dict:
    """Convert ORM object to dict with resolved user names."""
    data = {
        "id": req.id,
        "rule_id": req.rule_id,
        "change_type": req.change_type,
        "proposed_rule_data": req.proposed_rule_data,
        "reason": req.reason,
        "impact_assessment": req.impact_assessment,
        "status": req.status.value if isinstance(req.status, ApprovalStatus) else req.status,
        "requested_by": req.requested_by,
        "requested_at": req.requested_at,
        "reviewed_by": req.reviewed_by,
        "reviewed_at": req.reviewed_at,
        "review_comment": req.review_comment,
        "deployed_by": req.deployed_by,
        "deployed_at": req.deployed_at,
        "category_id": req.category_id,
        "priority": req.priority,
        "test_results": req.test_results,
        "requester_name": None,
        "reviewer_name": None,
        "deployer_name": None,
    }
    # Resolve names
    for field, name_field in [("requested_by", "requester_name"), ("reviewed_by", "reviewer_name"), ("deployed_by", "deployer_name")]:
        uid = getattr(req, field)
        if uid:
            user = await db.get(User, uid)
            if user:
                data[name_field] = user.full_name or user.email
    return data


# --- Helper: check approval policy ---
async def _should_require_approval(db: AsyncSession, change_request: RuleChangeRequestCreate) -> bool:
    """Check if any active approval policy requires approval for this change."""
    result = await db.execute(select(ApprovalPolicy).where(ApprovalPolicy.is_active == True))
    policies = result.scalars().all()

    proposed = change_request.proposed_rule_data
    for policy in policies:
        conditions = policy.conditions or {}
        matched = True

        # Check severity condition
        if "severity" in conditions:
            if proposed.get("severity") not in conditions["severity"]:
                matched = False

        # Check is_global condition
        if "is_global" in conditions:
            is_global = not change_request.category_id
            if conditions["is_global"] != is_global:
                matched = False

        # Check rule_types condition
        if "rule_types" in conditions:
            if proposed.get("rule_type") not in conditions["rule_types"]:
                matched = False

        if matched:
            return policy.requires_approval

    # Default: no approval required
    return False


# --- Change Requests ---

@router.get("/change-requests", response_model=List[RuleChangeRequestResponse])
async def list_change_requests(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all change requests, optionally filtered by status."""
    stmt = select(RuleChangeRequest).order_by(RuleChangeRequest.requested_at.desc())
    if status:
        try:
            status_enum = ApprovalStatus(status)
            stmt = stmt.where(RuleChangeRequest.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    result = await db.execute(stmt)
    requests = result.scalars().all()

    enriched = []
    for req in requests:
        enriched.append(await _enrich_request(db, req))
    return enriched


@router.post("/change-requests", response_model=RuleChangeRequestResponse)
async def create_change_request(
    request: Request,
    change_in: RuleChangeRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit a new rule change request."""
    # Determine if approval is needed
    needs_approval = await _should_require_approval(db, change_in)

    cr = RuleChangeRequest(
        rule_id=str(change_in.rule_id) if change_in.rule_id else None,
        change_type=change_in.change_type,
        proposed_rule_data=change_in.proposed_rule_data,
        reason=change_in.reason,
        impact_assessment=change_in.impact_assessment,
        status=ApprovalStatus.PENDING if needs_approval else ApprovalStatus.APPROVED,
        requested_by=current_user.id,
        requested_at=datetime.utcnow(),
        category_id=str(change_in.category_id) if change_in.category_id else None,
        priority=change_in.priority,
        test_results=change_in.test_results
    )
    db.add(cr)

    await log_audit_event(
        db=db, action="CREATE_CHANGE_REQUEST", user=current_user,
        resource_type="CHANGE_REQUEST", resource_id=cr.id,
        details={"change_type": change_in.change_type, "needs_approval": needs_approval, "priority": change_in.priority},
        request=request
    )

    await db.commit()
    await db.refresh(cr)

    # If auto-approved, immediately deploy
    if not needs_approval:
        await _deploy_change(db, cr, current_user, request)
        await db.refresh(cr)

    return await _enrich_request(db, cr)


@router.get("/change-requests/{request_id}", response_model=RuleChangeRequestResponse)
async def get_change_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single change request by ID."""
    cr = await db.get(RuleChangeRequest, str(request_id))
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")
    return await _enrich_request(db, cr)


@router.post("/change-requests/{request_id}/review", response_model=RuleChangeRequestResponse)
async def review_change_request(
    request: Request,
    request_id: UUID,
    review: ReviewAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Approve or reject a change request. Requires ADMIN or MANAGER role."""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only admins and managers can review change requests")

    cr = await db.get(RuleChangeRequest, str(request_id))
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")

    if cr.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Cannot review a request with status '{cr.status.value}'")

    if review.action == "approve":
        cr.status = ApprovalStatus.APPROVED
    elif review.action == "reject":
        cr.status = ApprovalStatus.REJECTED
    else:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    cr.reviewed_by = current_user.id
    cr.reviewed_at = datetime.utcnow()
    cr.review_comment = review.comment

    await log_audit_event(
        db=db, action=f"REVIEW_CHANGE_REQUEST_{review.action.upper()}", user=current_user,
        resource_type="CHANGE_REQUEST", resource_id=cr.id,
        details={"action": review.action, "comment": review.comment},
        request=request
    )

    await db.commit()
    await db.refresh(cr)
    return await _enrich_request(db, cr)


@router.post("/change-requests/{request_id}/deploy", response_model=RuleChangeRequestResponse)
async def deploy_change_request(
    request: Request,
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Deploy an approved change request — apply the proposed changes to the actual rule."""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only admins and managers can deploy changes")

    cr = await db.get(RuleChangeRequest, str(request_id))
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")

    if cr.status != ApprovalStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only approved requests can be deployed")

    await _deploy_change(db, cr, current_user, request)
    await db.refresh(cr)
    return await _enrich_request(db, cr)


async def _deploy_change(db: AsyncSession, cr: RuleChangeRequest, current_user: User, request: Request):
    """Apply the proposed change to the actual rule table."""
    from app.api.rules import create_rule_version_snapshot

    proposed = cr.proposed_rule_data
    user_name = current_user.full_name or current_user.email

    if cr.change_type == "create":
        new_rule = VerificationRule(
            rule_name=proposed.get("rule_name", "Untitled"),
            rule_type=RuleType(proposed.get("rule_type", "keyword")),
            rule_content=proposed.get("rule_content", ""),
            severity=Severity(proposed.get("severity", "warning")),
            is_active=proposed.get("is_active", True),
            logic_config=proposed.get("logic_config", {}),
            category_id=str(cr.category_id) if cr.category_id else None,
        )
        db.add(new_rule)
        await db.flush()
        await create_rule_version_snapshot(
            db, new_rule, user_name,
            change_log=f"通过审批创建: {cr.reason or ''}",
            change_request_id=cr.id
        )
        cr.rule_id = new_rule.id

    elif cr.change_type == "update":
        rule = await db.get(VerificationRule, str(cr.rule_id))
        if rule:
            for field in ["rule_name", "rule_type", "rule_content", "severity", "is_active", "logic_config"]:
                if field in proposed:
                    val = proposed[field]
                    if field == "rule_type":
                        val = RuleType(val)
                    elif field == "severity":
                        val = Severity(val)
                    setattr(rule, field, val)
            await create_rule_version_snapshot(
                db, rule, user_name,
                change_log=f"通过审批更新: {cr.reason or ''}",
                change_request_id=cr.id
            )

    elif cr.change_type == "delete":
        rule = await db.get(VerificationRule, str(cr.rule_id))
        if rule and not rule.is_system:
            await db.delete(rule)

    elif cr.change_type == "deactivate":
        rule = await db.get(VerificationRule, str(cr.rule_id))
        if rule:
            rule.is_active = False
            await create_rule_version_snapshot(
                db, rule, user_name,
                change_log=f"通过审批停用: {cr.reason or ''}",
                change_request_id=cr.id
            )

    cr.status = ApprovalStatus.DEPLOYED
    cr.deployed_by = current_user.id
    cr.deployed_at = datetime.utcnow()

    await log_audit_event(
        db=db, action="DEPLOY_CHANGE_REQUEST", user=current_user,
        resource_type="CHANGE_REQUEST", resource_id=cr.id,
        details={"change_type": cr.change_type, "rule_id": cr.rule_id},
        request=request
    )

    await db.commit()


# --- Approval Policies ---

@router.get("/policies", response_model=List[ApprovalPolicyResponse])
async def list_policies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(ApprovalPolicy).order_by(ApprovalPolicy.created_at))
    return result.scalars().all()


@router.post("/policies/init")
async def init_policies(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Initialize default approval policies if none exist."""
    result = await db.execute(select(ApprovalPolicy))
    existing = result.scalars().all()
    if existing:
        return {"message": f"{len(existing)} policies already exist, skipping initialization"}

    for policy_data in DEFAULT_APPROVAL_POLICIES:
        policy = ApprovalPolicy(**policy_data)
        db.add(policy)

    await log_audit_event(
        db=db, action="INIT_APPROVAL_POLICIES", user=current_user,
        resource_type="SYSTEM", resource_id=None,
        details={"count": len(DEFAULT_APPROVAL_POLICIES)},
        request=request
    )

    await db.commit()
    return {"message": f"Initialized {len(DEFAULT_APPROVAL_POLICIES)} default approval policies"}
