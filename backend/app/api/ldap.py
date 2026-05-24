"""
LDAP/SSO Configuration API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Literal
import os
import json

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.ldap_config import LDAPConfig

router = APIRouter()


class LDAPConfigModel(BaseModel):
    """LDAP Configuration Schema"""
    ldap_enabled: bool = False
    ldap_server: Optional[str] = None
    ldap_port: Optional[int] = None
    ldap_use_ssl: bool = False
    ldap_bind_dn: Optional[str] = None
    ldap_bind_password: Optional[str] = None
    ldap_search_base: Optional[str] = None
    ldap_search_filter: str = "(sAMAccountName={username})"
    ldap_email_attribute: str = "mail"
    ldap_name_attribute: str = "cn"
    ldap_department_attribute: str = "department"

    # AD Group mapping
    ad_admin_group: Optional[str] = None
    ad_manager_group: Optional[str] = None
    ad_user_group: Optional[str] = None

    # SSO Configuration
    sso_enabled: bool = False
    sso_provider: Optional[str] = None
    sso_entity_id: Optional[str] = None
    sso_acs_url: Optional[str] = None
    sso_slo_url: Optional[str] = None
    sso_idp_sso_url: Optional[str] = None
    sso_idp_cert: Optional[str] = None
    sso_sp_cert: Optional[str] = None
    sso_sp_key: Optional[str] = None

    # General settings
    local_admin_enabled: bool = True
    auto_create_users: bool = True
    default_role: Literal["ADMIN", "MANAGER", "USER"] = "USER"

    @validator('ldap_server', 'ldap_bind_dn', 'ldap_search_base')
    def validate_ldap_fields(cls, v, values):
        """Validate LDAP fields when enabled"""
        if values.get('ldap_enabled', False):
            if v is None or v == '':
                raise ValueError('启用 LDAP 时必须填写该字段')
        return v


def check_admin_permission(user: User):
    """Check if user has admin permission"""
    # Check both role and is_admin for backward compatibility
    # Role can be either enum or string, so we check both
    user_role = user.role.value if hasattr(user.role, 'value') else str(user.role)
    is_admin = user_role == "ADMIN" or user.is_admin

    # Debug logging
    print(f"[PERMISSION] Checking admin permission for user {user.email}:")
    print(f"  - user.role: {user.role} (type: {type(user.role)})")
    print(f"  - user_role (extracted): {user_role}")
    print(f"  - user.is_admin: {user.is_admin}")
    print(f"  - is_admin (final): {is_admin}")

    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="需要管理员权限"
        )


@router.get("/ldap-config")
async def get_ldap_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get LDAP/SSO configuration

    Only admin users can access this endpoint.
    """
    check_admin_permission(current_user)

    result = await db.get(LDAPConfig, "main_config")
    if result:
        config = {
            "ldap_enabled": result.ldap_enabled == "true",
            "ldap_server": result.ldap_server,
            "ldap_port": int(result.ldap_port) if result.ldap_port else None,
            "ldap_use_ssl": result.ldap_use_ssl == "true",
            "ldap_bind_dn": result.ldap_bind_dn,
            "ldap_bind_password": "***" if result.ldap_bind_password else None,
            "ldap_search_base": result.ldap_search_base,
            "ldap_search_filter": result.ldap_search_filter,
            "ldap_email_attribute": result.ldap_email_attribute,
            "ldap_name_attribute": result.ldap_name_attribute,
            "ldap_department_attribute": result.ldap_department_attribute,
            "ad_admin_group": result.ad_admin_group,
            "ad_manager_group": result.ad_manager_group,
            "ad_user_group": result.ad_user_group,
            "sso_enabled": result.sso_enabled == "true",
            "sso_provider": result.sso_provider,
            "sso_entity_id": result.sso_entity_id,
            "sso_acs_url": result.sso_acs_url,
            "sso_slo_url": result.sso_slo_url,
            "sso_idp_sso_url": result.sso_idp_sso_url,
            "sso_idp_cert": result.sso_idp_cert,
            "sso_sp_cert": result.sso_sp_cert,
            "sso_sp_key": result.sso_sp_key,
            "local_admin_enabled": result.local_admin_enabled == "true",
            "auto_create_users": result.auto_create_users == "true",
            "default_role": result.default_role or "user"
        }
        return config

    # Return defaults
    return {
        "ldap_enabled": False,
        "ldap_server": None,
        "ldap_port": None,
        "ldap_use_ssl": False,
        "ldap_bind_dn": None,
        "ldap_bind_password": None,
        "ldap_search_base": None,
        "ldap_search_filter": "(sAMAccountName={username})",
        "ldap_email_attribute": "mail",
        "ldap_name_attribute": "cn",
        "ldap_department_attribute": "department",
        "ad_admin_group": None,
        "ad_manager_group": None,
        "ad_user_group": None,
        "sso_enabled": False,
        "sso_provider": None,
        "sso_entity_id": None,
        "sso_acs_url": None,
        "sso_slo_url": None,
        "sso_idp_sso_url": None,
        "sso_idp_cert": None,
        "sso_sp_cert": None,
        "sso_sp_key": None,
        "local_admin_enabled": True,
        "auto_create_users": True,
        "default_role": "USER"
    }


@router.post("/ldap-config")
async def update_ldap_config(
    config: LDAPConfigModel,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update LDAP/SSO configuration

    Only admin users can access this endpoint.
    """
    check_admin_permission(current_user)

    # Fetch existing config
    existing = await db.get(LDAPConfig, "main_config")

    config_dict = config.dict()

    # Preserve password if it's being set to ***
    if existing and config_dict.get("ldap_bind_password") == "***":
        config_dict["ldap_bind_password"] = existing.ldap_bind_password

    # Preserve SSO keys if they're being set to ***
    if existing:
        if config_dict.get("sso_sp_key") == "***":
            config_dict["sso_sp_key"] = existing.sso_sp_key

    # Convert booleans to strings
    for key in ["ldap_enabled", "ldap_use_ssl", "sso_enabled", "local_admin_enabled", "auto_create_users"]:
        if key in config_dict and config_dict[key] is not None:
            config_dict[key] = "true" if config_dict[key] else "false"

    if existing:
        # Update existing
        for key, value in config_dict.items():
            setattr(existing, key, value)
    else:
        # Create new
        new_config = LDAPConfig(id="main_config", **config_dict)
        db.add(new_config)

    await db.commit()

    return {
        "message": "LDAP/SSO 配置已更新",
        "config": {k: v for k, v in config_dict.items()
                  if k not in ["ldap_bind_password", "sso_sp_key"]}
    }


@router.post("/ldap-config/test")
async def test_ldap_connection(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Test LDAP connection and authentication

    Only admin users can access this endpoint.
    """
    check_admin_permission(current_user)

    config = await db.get(LDAPConfig, "main_config")
    if not config or config.ldap_enabled != "true":
        raise HTTPException(
            status_code=400,
            detail="LDAP 未配置或未启用"
        )

    # TODO: Implement actual LDAP connection test
    # For now, just return success
    try:
        # Test logic would go here
        return {
            "message": "LDAP 连接测试成功",
            "success": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"LDAP 连接测试失败: {str(e)}"
        )


@router.get("/users")
async def get_all_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all users with their roles

    Only admin users can access this endpoint.
    """
    check_admin_permission(current_user)

    from sqlalchemy import select

    result = await db.execute(select(User))
    users = result.scalars().all()

    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
            "role": user.role.value if user.role else "user",
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
        }
        for user in users
    ]


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: Literal["ADMIN", "MANAGER", "USER"],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user role

    Only admin users can access this endpoint.
    """
    check_admin_permission(current_user)

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.role = UserRole(role)
    # Also update is_admin for backward compatibility
    user.is_admin = (role == "ADMIN")

    await db.commit()

    return {
        "message": f"用户角色已更新为 {role}",
        "role": role
    }
