from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.rule import DocumentCategory, VerificationRule
from app.models.rule_version import RuleVersion
from app.schemas.rule import (
    DocumentCategoryCreate, DocumentCategoryUpdate, DocumentCategoryResponse, DocumentCategoryWithRules,
    VerificationRuleCreate, VerificationRuleUpdate, VerificationRuleResponse,
    RuleVersionResponse, RuleDryRunRequest
)
from app.core.audit_logger import log_audit_event
from sqlalchemy import func
from datetime import datetime

router = APIRouter()

# --- Document Categories ---

@router.get("/categories", response_model=List[DocumentCategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(DocumentCategory).order_by(DocumentCategory.name))
    return result.scalars().all()

@router.get("/categories/{category_id}", response_model=DocumentCategoryWithRules)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(DocumentCategory)
        .options(selectinload(DocumentCategory.rules))
        .where(DocumentCategory.id == str(category_id))
    )
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.post("/categories", response_model=DocumentCategoryResponse)
async def create_category(
    category_in: DocumentCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    category = DocumentCategory(**category_in.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category

@router.put("/categories/{category_id}", response_model=DocumentCategoryResponse)
async def update_category(
    category_id: UUID,
    category_in: DocumentCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(DocumentCategory).where(DocumentCategory.id == str(category_id)))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
        
    await db.commit()
    await db.refresh(category)
    return category

@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(DocumentCategory).where(DocumentCategory.id == str(category_id)))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    await db.delete(category)
    await db.commit()
    return {"message": "Category deleted successfully"}

# --- Verification Rules ---

@router.get("/rules", response_model=List[VerificationRuleResponse])
async def list_rules(
    category_id: UUID = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stmt = select(VerificationRule)
    if category_id:
        stmt = stmt.where(VerificationRule.category_id == str(category_id))
    result = await db.execute(stmt.order_by(VerificationRule.rule_name))
    return result.scalars().all()

@router.post("/rules", response_model=VerificationRuleResponse)
async def create_rule(
    request: Request,
    rule_in: VerificationRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    data = rule_in.model_dump()
    if data.get("category_id"):
        data["category_id"] = str(data["category_id"])
    rule = VerificationRule(**data)
    db.add(rule)
    await db.flush() # Generate ID for snapshotting
    
    # Create initial version snapshot
    await create_rule_version_snapshot(db, rule, current_user.full_name or current_user.email)
    
    await log_audit_event(
        db=db,
        action="CREATE_RULE",
        user=current_user,
        resource_type="RULE",
        resource_id=rule.id,
        details={"rule_name": rule.rule_name, "rule_type": rule.rule_type, "data": data},
        request=request
    )
    
    await db.commit()
    await db.refresh(rule)
    return rule

@router.put("/rules/{rule_id}", response_model=VerificationRuleResponse)
async def update_rule(
    request: Request,
    rule_id: UUID,
    rule_in: VerificationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(VerificationRule).where(VerificationRule.id == str(rule_id)))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    update_data = rule_in.model_dump(exclude_unset=True)
    if update_data.get("category_id"):
        update_data["category_id"] = str(update_data["category_id"])
    for field, value in update_data.items():
        setattr(rule, field, value)
        
    # Create new version snapshot
    await create_rule_version_snapshot(db, rule, current_user.full_name or current_user.email)
    
    await log_audit_event(
        db=db,
        action="UPDATE_RULE",
        user=current_user,
        resource_type="RULE",
        resource_id=rule.id,
        details={"updated_fields": list(update_data.keys()), "data": update_data},
        request=request
    )
        
    await db.commit()
    await db.refresh(rule)
    return rule

@router.delete("/rules/{rule_id}")
async def delete_rule(
    request: Request,
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(VerificationRule).where(VerificationRule.id == str(rule_id)))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
        
    if rule.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system-provided default rules.")
    
    await db.delete(rule)
    
    await log_audit_event(
        db=db,
        action="DELETE_RULE",
        user=current_user,
        resource_type="RULE",
        resource_id=rule.id,
        details={"rule_name": rule.rule_name},
        request=request
    )
    
    await db.commit()
    return {"message": "Rule deleted successfully"}

@router.post("/restore-defaults")
async def restore_defaults(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Restore default system verification rules."""
    from app.models.rule import RuleType, Severity
    
    default_rules = [
        {
            "rule_name": "文档二维码识别与解析",
            "rule_type": RuleType.plugin,
            "rule_content": "REQUIRE_QR_CODE",
            "severity": Severity.warning,
            "is_system": True
        },
        {
            "rule_name": "PDF 电子数字签名验证",
            "rule_type": RuleType.plugin,
            "rule_content": "REQUIRE_SIGNATURE",
            "severity": Severity.warning,
            "is_system": True
        }
    ]
    
    # Iterate through defaults, check if exists, if not create it, if yes reset it.
    for d_rule in default_rules:
        result = await db.execute(select(VerificationRule).where(
            VerificationRule.rule_name == d_rule["rule_name"],
            VerificationRule.is_system == True
        ))
        existing_rule = result.scalars().first()
        
        if existing_rule:
            # Check if values actually changed to avoid duplicate redundant versions
            if (existing_rule.rule_content != d_rule["rule_content"] or
                existing_rule.rule_type != d_rule["rule_type"] or
                existing_rule.severity != d_rule["severity"] or
                not existing_rule.is_active):
                existing_rule.rule_content = d_rule["rule_content"]
                existing_rule.rule_type = d_rule["rule_type"]
                existing_rule.severity = d_rule["severity"]
                existing_rule.is_active = True
                await create_rule_version_snapshot(db, existing_rule, "System")
        else:
            new_rule = VerificationRule(**d_rule)
            db.add(new_rule)
            await db.flush()
            await create_rule_version_snapshot(db, new_rule, "System")
            
    await log_audit_event(
        db=db,
        action="RESTORE_DEFAULT_RULES",
        user=current_user,
        resource_type="SYSTEM",
        resource_id=None,
        details={"action": "Restored default verification rules"},
        request=request
    )
    
    await db.commit()
    return {"message": "System default rules restored successfully."}


# --- Rule Versioning Helpers & Routes ---

async def create_rule_version_snapshot(db: AsyncSession, rule: VerificationRule, user_name: str):
    stmt = select(func.max(RuleVersion.version_number)).where(RuleVersion.rule_id == rule.id)
    res = await db.execute(stmt)
    max_ver = res.scalar() or 0
    next_ver = max_ver + 1
    
    snapshot = RuleVersion(
        rule_id=rule.id,
        version_number=next_ver,
        rule_name=rule.rule_name,
        rule_type=rule.rule_type,
        rule_content=rule.rule_content,
        severity=rule.severity,
        is_active=rule.is_active,
        logic_config=rule.logic_config,
        created_by=user_name
    )
    db.add(snapshot)
    return snapshot

@router.get("/rules/{rule_id}/versions", response_model=List[RuleVersionResponse])
async def list_rule_versions(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all historical versions of a specific rule."""
    result = await db.execute(
        select(RuleVersion)
        .where(RuleVersion.rule_id == str(rule_id))
        .order_by(RuleVersion.version_number.desc())
    )
    return result.scalars().all()

@router.post("/rules/{rule_id}/rollback", response_model=VerificationRuleResponse)
async def rollback_rule(
    request: Request,
    rule_id: UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Rollback a rule to a specific historical version."""
    version_result = await db.execute(
        select(RuleVersion)
        .where(RuleVersion.rule_id == str(rule_id), RuleVersion.version_number == version_number)
    )
    target_version = version_result.scalars().first()
    if not target_version:
        raise HTTPException(status_code=404, detail="Rule version not found")

    rule_result = await db.execute(select(VerificationRule).where(VerificationRule.id == str(rule_id)))
    rule = rule_result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Update rule attributes to target version configuration
    rule.rule_name = target_version.rule_name
    rule.rule_type = target_version.rule_type
    rule.rule_content = target_version.rule_content
    rule.severity = target_version.severity
    rule.is_active = target_version.is_active
    rule.logic_config = target_version.logic_config

    # Create a new version snapshot tracking this rollback action
    user_name = current_user.full_name or current_user.email
    await create_rule_version_snapshot(db, rule, f"{user_name} (回滚至版本 #{version_number})")

    await log_audit_event(
        db=db,
        action="ROLLBACK_RULE",
        user=current_user,
        resource_type="RULE",
        resource_id=rule.id,
        details={"rollback_to_version": version_number},
        request=request
    )

    await db.commit()
    await db.refresh(rule)
    return rule

@router.post("/rules/dry-run")
async def rule_dry_run(
    request: Request,
    dry_run_in: RuleDryRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Simulate rule validation in-memory on a target file without saving any data."""
    from app.models.file import File
    from app.core.minio_client import minio_client
    from app.engine.core import VerificationEngine
    from app.engine.base import DocumentContext
    from app.models.rule import RuleType as ModelRuleType, Severity as ModelSeverity
    
    file_record = await db.get(File, str(dry_run_in.file_id))
    if not file_record:
        raise HTTPException(status_code=404, detail="Sample file not found")

    try:
        pdf_bytes = minio_client.download_file(file_record.file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch sample file bytes: {e}")

    try:
        temp_rule = VerificationRule(
            rule_name=dry_run_in.rule_name,
            rule_type=ModelRuleType(dry_run_in.rule_type),
            rule_content=dry_run_in.rule_content,
            severity=ModelSeverity(dry_run_in.severity),
            logic_config=dry_run_in.logic_config,
            is_active=True
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=f"Invalid rule configuration: {val_err}")

    context = DocumentContext(
        file_path=file_record.file_path,
        file_type=file_record.file_type.value,
        shared_state={"pdf_bytes": pdf_bytes} if pdf_bytes else {}
    )

    engine_logs = []
    async def progress_cb(msg: str):
        engine_logs.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": msg
        })

    try:
        engine = VerificationEngine()
        result = await engine.run(context, [temp_rule], progress_callback=progress_cb)
    except Exception as exec_err:
        raise HTTPException(status_code=500, detail=f"Engine execution failed: {exec_err}")

    return {
        "logs": engine_logs,
        "result": result
    }
