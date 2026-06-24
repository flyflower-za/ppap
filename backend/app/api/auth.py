from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
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

    For SSO integration, this will verify the SSO token
    and create/update the user record.
    """
    # TODO: Implement SSO verification
    # For now, simple email + password lookup

    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user:
        # Auto-create user for demo (in production, this would come from SSO)
        # New users default to USER role (no email-based role inference)
        user = User(
            id=str(uuid.uuid4()),
            email=credentials.email,
            full_name=credentials.email.split("@")[0],
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
    user.last_login_at = datetime.utcnow()
    
    await log_audit_event(
        db=db,
        action="LOGIN",
        user=user,
        resource_type="SYSTEM",
        details={"email": credentials.email},
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
