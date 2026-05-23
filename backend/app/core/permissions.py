"""
Permission checking utilities for role-based access control
"""
from functools import wraps
from typing import Callable, List
from fastapi import HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.api.deps import get_current_user


def require_role(*allowed_roles: UserRole):
    """
    Decorator to require specific roles for endpoint access

    Usage:
        @require_role(UserRole.ADMIN, UserRole.MANAGER)
        async def some_endpoint():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            # Get user role value (handle both enum and string)
            user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

            # Check if user's role is in allowed roles
            user_role_enum = UserRole(user_role) if user_role in [r.value for r in UserRole] else UserRole.USER
            if user_role_enum not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"需要以下权限之一: {', '.join([r.value for r in allowed_roles])}"
                )

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def require_admin(func: Callable):
    """Decorator to require admin role"""
    return require_role(UserRole.ADMIN)(func)


def require_manager_or_admin(func: Callable):
    """Decorator to require manager or admin role"""
    return require_role(UserRole.MANAGER, UserRole.ADMIN)(func)


def check_user_permission(
    current_user: User,
    required_permission: str
) -> bool:
    """
    Check if user has specific permission

    Args:
        current_user: Current user object
        required_permission: Permission to check

    Returns:
        True if user has permission, False otherwise
    """
    # Get user role value
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    user_role_enum = UserRole(user_role) if user_role in [r.value for r in UserRole] else UserRole.USER

    # Define permission matrix
    permissions = {
        # File/Report access
        "view_own_files": [UserRole.USER, UserRole.MANAGER, UserRole.ADMIN],
        "view_department_files": [UserRole.MANAGER, UserRole.ADMIN],
        "view_all_files": [UserRole.ADMIN],

        # Settings access
        "view_profile": [UserRole.USER, UserRole.MANAGER, UserRole.ADMIN],
        "view_notifications": [UserRole.USER, UserRole.MANAGER, UserRole.ADMIN],
        "view_smtp": [UserRole.ADMIN],
        "view_ldap": [UserRole.ADMIN],
        "view_email_templates": [UserRole.ADMIN],
        "view_users": [UserRole.ADMIN],

        # Actions
        "upload_files": [UserRole.USER, UserRole.MANAGER, UserRole.ADMIN],
        "delete_files": [UserRole.MANAGER, UserRole.ADMIN],
        "manage_users": [UserRole.ADMIN],
        "manage_settings": [UserRole.ADMIN],
    }

    allowed_roles = permissions.get(required_permission, [])
    return user_role_enum in allowed_roles


def get_accessible_departments(current_user: User) -> List[str]:
    """
    Get list of departments the user can access

    Args:
        current_user: Current user object

    Returns:
        List of department names the user can access
    """
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    user_role_enum = UserRole(user_role) if user_role in [r.value for r in UserRole] else UserRole.USER

    # Admin can access all departments
    if user_role_enum == UserRole.ADMIN:
        return None  # None means no filter (all departments)

    # Manager can access their own department
    if user_role_enum == UserRole.MANAGER:
        return [current_user.department] if current_user.department else []

    # Regular user can only access their own files (handled separately)
    return []
