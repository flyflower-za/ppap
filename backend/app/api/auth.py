from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import uuid

from app.core.database import get_db
from app.core.security import create_access_token, verify_password, get_password_hash
from app.models.user import User, UserRole
from app.schemas.user import UserLogin, Token, UserResponse
from app.api.deps import get_current_user
from app.core.audit_logger import log_audit_event


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Login endpoint with password verification.

    Supports login via email OR username.
    For SSO integration, this will verify the SSO token
    and create/update the user record.
    """
    # TODO: Implement SSO verification

    login_id = credentials.login_id.strip().lower()

    # First try email exact match, then username exact match
    result = await db.execute(select(User).where(User.email == login_id))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.username == login_id))
        user = result.scalar_one_or_none()

    if not user:
        # Auto-create user for demo (in production, this would come from SSO)
        # username is auto-derived from email prefix (with conflict resolution)
        email = login_id if "@" in login_id else f"{login_id}@unknown.local"
        base_username = email.split("@")[0]
        username = base_username

        # Resolve username conflicts
        suffix = 2
        while True:
            existing = await db.execute(select(User).where(User.username == username))
            if not existing.scalar_one_or_none():
                break
            username = f"{base_username}{suffix}"
            suffix += 1

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            full_name=email.split("@")[0],
            is_active=True,
            is_admin=False,
            role=UserRole.USER,
            password_hash=get_password_hash(credentials.password),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Password verification
    if user.password_hash:
        if not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password",
            )
    else:
        # Legacy user (migrated, no password_hash set)
        # Allow login but require user to set a password
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password not set. Please contact administrator to set your password.",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await log_audit_event(
        db=db,
        action="LOGIN",
        user=user,
        resource_type="SYSTEM",
        details={"login_id": login_id, "email": user.email},
        request=request
    )
    
    await db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": user.id})

    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get current user info."""
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User changes their own password (requires old password)."""
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")

    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="请填写旧密码和新密码")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码长度至少 6 位")

    if not current_user.password_hash:
        raise HTTPException(status_code=400, detail="当前账号未设置密码，请联系管理员重置")

    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码不正确")

    current_user.password_hash = get_password_hash(new_password)
    await db.commit()

    return {"message": "密码修改成功"}
