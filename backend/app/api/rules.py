from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.rule import DocumentCategory, VerificationRule
from app.schemas.rule import (
    DocumentCategoryCreate, DocumentCategoryUpdate, DocumentCategoryResponse, DocumentCategoryWithRules,
    VerificationRuleCreate, VerificationRuleUpdate, VerificationRuleResponse
)
from app.core.audit_logger import log_audit_event

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
    
    await log_audit_event(
        db=db,
        action="CREATE_RULE",
        user=current_user,
        resource_type="RULE",
        resource_id=rule.id,
        details={"rule_name": rule.rule_name, "rule_type": rule.rule_type},
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
        
    await log_audit_event(
        db=db,
        action="UPDATE_RULE",
        user=current_user,
        resource_type="RULE",
        resource_id=rule.id,
        details={"updated_fields": list(update_data.keys())},
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
