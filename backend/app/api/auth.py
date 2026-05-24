from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
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
    Login endpoint.

    For SSO integration, this will verify the SSO token
    and create/update the user record.
    """
    # TODO: Implement SSO verification
    # For now, simple email lookup

    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user:
        # Auto-create user for demo (in production, this would come from SSO)
        # Determine role based on email
        if "admin" in credentials.email.lower():
            user_role = UserRole.ADMIN
            is_admin = True
        elif "manager" in credentials.email.lower():
            user_role = UserRole.MANAGER
            is_admin = False
        else:
            user_role = UserRole.USER
            is_admin = False

        user = User(
            id=str(uuid.uuid4()),
            email=credentials.email,
            full_name=credentials.email.split("@")[0],
            is_active=True,
            is_admin=is_admin,
            role=user_role,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
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
