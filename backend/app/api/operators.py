"""
Operator Registry API - 算子注册表 API
提供算子的查询、管理和模板功能
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.operator_registry import OperatorRegistry, OperatorTemplate, INITIAL_OPERATORS
from app.models.rule_template import RuleTemplate, DEFAULT_RULE_TEMPLATES
from app.models.rule import DocumentCategory, VerificationRule
from app.schemas.operator import (
    OperatorRegistryResponse, OperatorRegistryCreate, OperatorRegistryUpdate,
    OperatorTemplateResponse, OperatorTemplateCreate,
    RuleTemplateResponse, RuleTemplateCreate, RuleTemplateUpdate
)
from app.core.audit_logger import log_audit_event

router = APIRouter(tags=["operators"])


@router.get("/registry", response_model=List[OperatorRegistryResponse])
async def list_operators(
    is_active: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取算子注册表列表（供 RuleGraphEditor 动态加载）"""
    result = await db.execute(
        select(OperatorRegistry)
        .where(OperatorRegistry.is_active == is_active)
        .where(OperatorRegistry.is_deprecated == False)
        .order_by(OperatorRegistry.priority, OperatorRegistry.operator_key)
    )
    return result.scalars().all()


@router.get("/registry/{operator_key}", response_model=OperatorRegistryResponse)
async def get_operator(
    operator_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取单个算子的详细信息"""
    result = await db.execute(
        select(OperatorRegistry).where(OperatorRegistry.operator_key == operator_key)
    )
    operator = result.scalars().first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    return operator


@router.post("/registry", response_model=OperatorRegistryResponse)
async def create_operator(
    operator_in: OperatorRegistryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建新算子（通常由系统初始化，管理员也可添加自定义算子）"""
    # 检查是否已存在
    existing = await db.execute(
        select(OperatorRegistry).where(OperatorRegistry.operator_key == operator_in.operator_key)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Operator with this key already exists")

    operator = OperatorRegistry(**operator_in.model_dump())
    db.add(operator)
    await db.commit()
    await db.refresh(operator)
    return operator


@router.put("/registry/{operator_key}", response_model=OperatorRegistryResponse)
async def update_operator(
    operator_key: str,
    operator_in: OperatorRegistryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新算子配置"""
    result = await db.execute(
        select(OperatorRegistry).where(OperatorRegistry.operator_key == operator_key)
    )
    operator = result.scalars().first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    update_data = operator_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(operator, field, value)

    await db.commit()
    await db.refresh(operator)
    return operator


@router.delete("/registry/{operator_key}")
async def delete_operator(
    operator_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除算子（软删除，标记为已弃用）"""
    result = await db.execute(
        select(OperatorRegistry).where(OperatorRegistry.operator_key == operator_key)
    )
    operator = result.scalars().first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    operator.is_deprecated = True
    operator.is_active = False
    await db.commit()
    return {"message": "Operator deprecated successfully"}


# --- Operator Templates ---

@router.get("/templates", response_model=List[OperatorTemplateResponse])
async def list_operator_templates(
    operator_key: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取算子配置模板列表"""
    stmt = select(OperatorTemplate)
    if operator_key:
        stmt = stmt.where(OperatorTemplate.operator_key == operator_key)
    stmt = stmt.order_by(OperatorTemplate.name)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/templates", response_model=OperatorTemplateResponse)
async def create_operator_template(
    template_in: OperatorTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建算子配置模板"""
    # 验证 operator_key 存在
    operator_exists = await db.execute(
        select(OperatorRegistry).where(OperatorRegistry.operator_key == template_in.operator_key)
    )
    if not operator_exists.scalars().first():
        raise HTTPException(status_code=400, detail=f"Operator {template_in.operator_key} does not exist")

    template = OperatorTemplate(
        **template_in.model_dump(),
        created_by=str(current_user.id)
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("/init-registry")
async def initialize_registry(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    初始化算子注册表（系统启动时调用）
    将现有硬编码算子同步到数据库
    """
    initialized_count = 0
    skipped_count = 0

    for operator_data in INITIAL_OPERATORS:
        existing = await db.execute(
            select(OperatorRegistry).where(
                OperatorRegistry.operator_key == operator_data["operator_key"]
            )
        )
        existing_op = existing.scalars().first()

        if existing_op:
            # 更新现有算子
            for key, value in operator_data.items():
                if key != "operator_key":  # 不更新主键
                    setattr(existing_op, key, value)
            skipped_count += 1
        else:
            # 创建新算子
            new_op = OperatorRegistry(**operator_data)
            db.add(new_op)
            initialized_count += 1

    await db.commit()
    return {
        "message": "Registry initialized successfully",
        "initialized": initialized_count,
        "updated": skipped_count,
        "total": len(INITIAL_OPERATORS)
    }


# --- Rule Templates ---

@router.get("/rule-templates", response_model=List[RuleTemplateResponse])
async def list_rule_templates(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    is_public: bool = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取规则模板列表（支持按分类和标签筛选）"""
    stmt = select(RuleTemplate).where(RuleTemplate.is_system == True)

    # 如果指定 is_public，则包含用户创建的公开模板
    if is_public is not None:
        stmt = select(RuleTemplate).where(
            (RuleTemplate.is_system == True) | (RuleTemplate.is_public == is_public)
        )

    # 按分类筛选
    if category:
        stmt = stmt.where(RuleTemplate.category_suggestions.contains([category]))

    # 按标签筛选
    if tag:
        stmt = stmt.where(RuleTemplate.tags.contains([tag]))

    stmt = stmt.order_by(RuleTemplate.usage_count.desc(), RuleTemplate.name)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/rule-templates/{template_id}", response_model=RuleTemplateResponse)
async def get_rule_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取单个规则模板的详细信息"""
    result = await db.execute(
        select(RuleTemplate).where(RuleTemplate.id == template_id)
    )
    template = result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Rule template not found")
    return template


@router.post("/rule-templates", response_model=RuleTemplateResponse)
async def create_rule_template(
    template_in: RuleTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建规则模板（用户可保存自定义规则组合为模板）"""
    template = RuleTemplate(
        **template_in.model_dump(),
        created_by=str(current_user.id)
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.put("/rule-templates/{template_id}", response_model=RuleTemplateResponse)
async def update_rule_template(
    template_id: str,
    template_in: RuleTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新规则模板"""
    result = await db.execute(
        select(RuleTemplate).where(RuleTemplate.id == template_id)
    )
    template = result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Rule template not found")

    # 只有创建者或管理员可以修改
    if template.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system templates")

    update_data = template_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/rule-templates/{template_id}")
async def delete_rule_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除规则模板"""
    result = await db.execute(
        select(RuleTemplate).where(RuleTemplate.id == template_id)
    )
    template = result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Rule template not found")

    if template.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system templates")

    await db.delete(template)
    await db.commit()
    return {"message": "Rule template deleted successfully"}


@router.post("/rule-templates/{template_id}/apply")
async def apply_rule_template(
    template_id: str,
    category_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """
    应用规则模板到指定分类
    将模板中的规则创建为该分类的专属规则
    """
    # 获取模板
    template_result = await db.execute(
        select(RuleTemplate).where(RuleTemplate.id == template_id)
    )
    template = template_result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Rule template not found")

    # 验证分类存在
    category_result = await db.execute(
        select(DocumentCategory).where(DocumentCategory.id == category_id)
    )
    category = category_result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # 创建规则
    created_rules = []
    for rule_data in template.template_rules:
        rule = VerificationRule(
            category_id=category_id,
            rule_name=rule_data.get("rule_name", "Untitled Rule"),
            rule_type=rule_data.get("rule_type", "plugin"),
            rule_content=rule_data.get("rule_content", ""),
            severity=rule_data.get("severity", "fail"),
            logic_config=rule_data.get("logic_config", {}),
            is_active=True,
            is_system=False
        )
        db.add(rule)
        created_rules.append(rule)

    # 更新模板使用计数
    template.usage_count = (template.usage_count or 0) + 1

    await db.commit()

    # 记录审计日志
    await log_audit_event(
        db=db,
        action="APPLY_RULE_TEMPLATE",
        user=current_user,
        resource_type="RULE_TEMPLATE",
        resource_id=template_id,
        details={
            "template_name": template.name,
            "category_id": category_id,
            "category_name": category.name,
            "rules_created": len(created_rules)
        },
        request=request
    )

    return {
        "message": "Template applied successfully",
        "category_id": category_id,
        "category_name": category.name,
        "rules_created": len(created_rules),
        "rules": [{"id": str(r.id), "name": r.rule_name} for r in created_rules]
    }


@router.get("/init-rule-templates")
async def initialize_rule_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    初始化系统预置规则模板
    """
    initialized_count = 0
    skipped_count = 0

    for template_data in DEFAULT_RULE_TEMPLATES:
        existing = await db.execute(
            select(RuleTemplate).where(
                RuleTemplate.name == template_data["name"],
                RuleTemplate.is_system == True
            )
        )
        existing_template = existing.scalars().first()

        if existing_template:
            # 更新现有模板
            for key, value in template_data.items():
                if key not in ["name", "created_by"]:
                    setattr(existing_template, key, value)
            skipped_count += 1
        else:
            # 创建新模板
            new_template = RuleTemplate(**template_data)
            db.add(new_template)
            initialized_count += 1

    await db.commit()
    return {
        "message": "Rule templates initialized successfully",
        "initialized": initialized_count,
        "updated": skipped_count,
        "total": len(DEFAULT_RULE_TEMPLATES)
    }
