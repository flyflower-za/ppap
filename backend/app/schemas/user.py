from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Literal
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: str
    department: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""
    username: Optional[str] = None  # Auto-derived from email if not provided
    sso_provider: Optional[str] = None
    sso_id: Optional[str] = None


class UserUpdate(BaseModel):
    """User update schema."""
    full_name: Optional[str] = None
    department: Optional[str] = None
    email_notifications_enabled: Optional[bool] = None
    notification_on_complete: Optional[bool] = None
    notification_on_failure: Optional[bool] = None
    daily_summary_enabled: Optional[bool] = None


class UserResponse(UserBase):
    """User response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    avatar_url: Optional[str] = None
    role: Literal["ADMIN", "MANAGER", "USER"] = "USER"
    is_active: bool
    is_admin: bool
    email_notifications_enabled: bool
    notification_on_complete: bool
    notification_on_failure: bool
    daily_summary_enabled: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserLogin(BaseModel):
    """User login schema."""
    login_id: str
    password: str
    sso_token: Optional[str] = None


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
