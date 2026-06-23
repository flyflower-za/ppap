from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
import time

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.rule import DocumentCategory
from app.models.verification_module import VerificationModule, RuleModule, ModuleType, ModuleSeverity
from app.schemas.verification_module import (
    VerificationModuleCreate, VerificationModuleUpdate, VerificationModuleResponse,
    ModuleWithMetadata, RuleModuleAssign, RuleModulesResponse, MODULE_TYPE_METADATA
)
from app.core.audit_logger import log_audit_event

router = APIRouter()


# --- Module Metadata ---

@router.get("/metadata", response_model=dict)
async def get_module_metadata(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get metadata for all available module types.
    Used by frontend to render module configuration forms.
    """
    return {"module_types": MODULE_TYPE_METADATA}


# --- Verification Modules CRUD ---

@router.get("", response_model=List[ModuleWithMetadata])
async def list_modules(
    category_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all verification modules with optional filters.
    """
    query = select(VerificationModule).order_by(VerificationModule.sort_order, VerificationModule.name)

    if category_id:
        query = query.where(VerificationModule.category_id == category_id)
    if is_active is not None:
        query = query.where(VerificationModule.is_active == is_active)

    result = await db.execute(query)
    modules = result.scalars().all()

    # Add metadata to each module
    response = []
    for module in modules:
        module_dict = {
            **VerificationModuleResponse.model_validate(module).model_dump(),
            "metadata": MODULE_TYPE_METADATA.get(module.module_type, {})
        }
        response.append(ModuleWithMetadata(**module_dict))

    return response


@router.get("/{module_id}", response_model=ModuleWithMetadata)
async def get_module(
    module_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific module by ID."""
    result = await db.execute(
        select(VerificationModule).where(VerificationModule.id == module_id)
    )
    module = result.scalars().first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    return {
        **VerificationModuleResponse.model_validate(module).model_dump(),
        "metadata": MODULE_TYPE_METADATA.get(module.module_type, {})
    }


@router.post("", response_model=VerificationModuleResponse)
async def create_module(
    request: Request,
    module_in: VerificationModuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new verification module.
    """
    # Verify category exists if provided
    if module_in.category_id:
        category_result = await db.execute(
            select(DocumentCategory).where(DocumentCategory.id == module_in.category_id)
        )
        if not category_result.scalars().first():
            raise HTTPException(status_code=400, detail="Category not found")

    # Create module
    now = int(time.time())
    module_data = module_in.model_dump()
    module_data["created_at"] = now
    module_data["updated_at"] = now

    module = VerificationModule(**module_data)
    db.add(module)

    await log_audit_event(
        db=db,
        action="CREATE_MODULE",
        user=current_user,
        resource_type="MODULE",
        resource_id=module.id,
        details={"name": module.name, "module_type": module.module_type},
        request=request
    )

    await db.commit()
    await db.refresh(module)
    return module


@router.put("/{module_id}", response_model=VerificationModuleResponse)
async def update_module(
    request: Request,
    module_id: str,
    module_in: VerificationModuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing module."""
    result = await db.execute(
        select(VerificationModule).where(VerificationModule.id == module_id)
    )
    module = result.scalars().first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Prevent modification of system modules
    if module.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system modules")

    # Verify category exists if provided
    if module_in.category_id:
        category_result = await db.execute(
            select(DocumentCategory).where(DocumentCategory.id == module_in.category_id)
        )
        if not category_result.scalars().first():
            raise HTTPException(status_code=400, detail="Category not found")

    # Update fields
    update_data = module_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(module, field, value)
    module.updated_at = int(time.time())

    await log_audit_event(
        db=db,
        action="UPDATE_MODULE",
        user=current_user,
        resource_type="MODULE",
        resource_id=module.id,
        details={"updated_fields": list(update_data.keys())},
        request=request
    )

    await db.commit()
    await db.refresh(module)
    return module


@router.delete("/{module_id}")
async def delete_module(
    request: Request,
    module_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a module."""
    result = await db.execute(
        select(VerificationModule).where(VerificationModule.id == module_id)
    )
    module = result.scalars().first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Prevent deletion of system modules
    if module.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system modules")

    await db.delete(module)

    await log_audit_event(
        db=db,
        action="DELETE_MODULE",
        user=current_user,
        resource_type="MODULE",
        resource_id=module.id,
        details={"name": module.name},
        request=request
    )

    await db.commit()
    return {"message": "Module deleted successfully"}


@router.post("/restore-defaults")
async def restore_default_modules(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Restore default system verification modules.
    """
    now = int(time.time())

    default_modules = [
        {
            "name": "二维码识别检查",
            "description": "检查文档中是否包含有效的追溯二维码",
            "module_type": ModuleType.qr_scanner,
            "severity": ModuleSeverity.warning,
            "config": {},
            "is_system": True,
            "is_active": True,
            "sort_order": 1
        },
        {
            "name": "数字签名验证",
            "description": "验证PDF文档的电子数字签名",
            "module_type": ModuleType.signature_verifier,
            "severity": ModuleSeverity.critical,
            "config": {},
            "is_system": True,
            "is_active": True,
            "sort_order": 2
        },
        {
            "name": "文档篡改检查",
            "description": "检查文档签名后是否被修改",
            "module_type": ModuleType.revision_check,
            "severity": ModuleSeverity.critical,
            "config": {"max_revisions": 0, "allow_incremental": False},
            "is_system": True,
            "is_active": True,
            "sort_order": 3
        },
        {
            "name": "发证机构识别",
            "description": "自动识别文档的发证机构",
            "module_type": ModuleType.institution_sniffer,
            "severity": ModuleSeverity.info,
            "config": {},
            "is_system": True,
            "is_active": True,
            "sort_order": 4
        }
    ]

    for default_mod in default_modules:
        # Check if module already exists
        existing = await db.execute(
            select(VerificationModule).where(
                VerificationModule.name == default_mod["name"],
                VerificationModule.is_system == True
            )
        )
        existing_module = existing.scalars().first()

        if not existing_module:
            new_module = VerificationModule(**default_mod, created_at=now, updated_at=now)
            db.add(new_module)

    await log_audit_event(
        db=db,
        action="RESTORE_DEFAULT_MODULES",
        user=current_user,
        resource_type="SYSTEM",
        resource_id=None,
        details={"action": "Restored default verification modules"},
        request=request
    )

    await db.commit()
    return {"message": "Default modules restored successfully"}


# --- Rule-Module Assignment ---

@router.get("/rule/{rule_id}/modules", response_model=RuleModulesResponse)
async def get_rule_modules(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all modules assigned to a specific rule.
    """
    # Get rule-module junction records
    junction_result = await db.execute(
        select(RuleModule).where(RuleModule.rule_id == rule_id)
    )
    junction_records = junction_result.scalars().all()

    # Get module details
    module_ids = [r.module_id for r in junction_records]
    if not module_ids:
        return {"rule_id": rule_id, "modules": []}

    modules_result = await db.execute(
        select(VerificationModule)
        .where(VerificationModule.id.in_(module_ids))
        .order_by(VerificationModule.sort_order)
    )
    modules = modules_result.scalars().all()

    return {
        "rule_id": rule_id,
        "modules": [VerificationModuleResponse.model_validate(m) for m in modules]
    }


@router.put("/rule/{rule_id}/modules")
async def assign_rule_modules(
    request: Request,
    rule_id: str,
    assignment: RuleModuleAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Assign modules to a rule.
    Replaces all existing module assignments for this rule.
    """
    # Verify rule exists
    from app.models.rule import VerificationRule
    rule_result = await db.execute(
        select(VerificationRule).where(VerificationRule.id == rule_id)
    )
    if not rule_result.scalars().first():
        raise HTTPException(status_code=404, detail="Rule not found")

    # Verify all modules exist
    modules_result = await db.execute(
        select(VerificationModule).where(VerificationModule.id.in_(assignment.module_ids))
    )
    modules = modules_result.scalars().all()
    found_ids = {m.id for m in modules}
    missing_ids = set(assignment.module_ids) - found_ids
    if missing_ids:
        raise HTTPException(status_code=400, detail=f"Modules not found: {missing_ids}")

    # Delete existing assignments
    await db.execute(
        select(RuleModule).where(RuleModule.rule_id == rule_id)
    )
    # Actually delete
    from sqlalchemy import delete
    await db.execute(delete(RuleModule).where(RuleModule.rule_id == rule_id))

    # Create new assignments
    now = int(time.time())
    for module_id in assignment.module_ids:
        junction = RuleModule(rule_id=rule_id, module_id=module_id, created_at=now)
        db.add(junction)

    await log_audit_event(
        db=db,
        action="ASSIGN_MODULES",
        user=current_user,
        resource_type="RULE",
        resource_id=rule_id,
        details={"module_count": len(assignment.module_ids)},
        request=request
    )

    await db.commit()
    return {"message": f"Assigned {len(assignment.module_ids)} modules to rule"}
