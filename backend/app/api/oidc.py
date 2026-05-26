"""
Generic OpenID Connect SSO Integration
Supports any OIDC provider: Keycloak, Auth0, Okta, Azure AD, Google, etc.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import uuid
import httpx
import json
import logging
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.schemas.user import Token, UserResponse
from app.api.deps import get_current_user
from app.core.audit_logger import log_audit_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/oidc", tags=["OpenID Connect SSO"])


class OIDCConfig(BaseModel):
    """Generic OpenID Connect Configuration"""
    enabled: bool = False
    provider_name: str = "generic"  # keycloak, auth0, okta, azure, google, etc.
    discovery_url: str = ""  # Must be provided: https://provider.com/.well-known/openid-configuration
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://47.114.107.127/auth/callback"

    # Scope configuration (default: openid email profile)
    scope: str = "openid email profile"

    # Role mapping (optional)
    admin_roles: list[str] = []
    manager_roles: list[str] = []
    user_roles: list[str] = []

    # Auto user creation
    auto_create_users: bool = True
    default_role: str = "USER"

    # Environment indicator
    environment: str = "test"  # test, production


class OIDCTokenResponse(BaseModel):
    """Response after successful OIDC authentication"""
    access_token: str
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = 3600


class OIDCUserInfo(BaseModel):
    """OIDC user information (standard claims)"""
    sub: str  # Subject (user ID)
    email: str
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    preferred_username: Optional[str] = None
    email_verified: bool = False
    roles: list[str] = []


async def get_oidc_config(db: AsyncSession) -> dict:
    """Get OIDC configuration from database"""
    from app.models.ldap_config import LDAPConfig

    # Try to get from LDAP config table (reuse SSO fields)
    result = await db.get(LDAPConfig, "main_config")
    if result and result.sso_enabled == "true":
        return {
            "enabled": True,
            "provider_name": result.sso_provider or "generic",
            "discovery_url": result.sso_idp_sso_url or "",
            "client_id": result.sso_entity_id or "",
            "client_secret": result.sso_sp_key or "",
            "redirect_uri": result.sso_acs_url or "http://47.114.107.127/auth/callback",
            "scope": "openid email profile",
            "admin_roles": [],
            "manager_roles": [],
            "user_roles": [],
            "auto_create_users": result.auto_create_users == "true",
            "default_role": result.default_role or "USER",
            "environment": result.ldap_server or "test"
        }

    # Return empty configuration by default
    return {
        "enabled": False,
        "provider_name": "generic",
        "discovery_url": "",
        "client_id": "",
        "client_secret": "",
        "redirect_uri": "http://47.114.107.127/auth/callback",
        "scope": "openid email profile",
        "admin_roles": [],
        "manager_roles": [],
        "user_roles": [],
        "auto_create_users": True,
        "default_role": "USER",
        "environment": "test"
    }


async def fetch_oidc_discovery(discovery_url: str) -> dict:
    """Fetch OpenID Connect discovery document from any provider"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(discovery_url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch OIDC discovery: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"无法连接到OIDC服务器: {str(e)}"
            )


async def exchange_code_for_token(
    code: str,
    redirect_uri: str,
    config: dict
) -> dict:
    """Exchange authorization code for access token (works with any OIDC provider)"""
    # Get discovery document to find token endpoint
    discovery = await fetch_oidc_discovery(config["discovery_url"])
    token_endpoint = discovery.get("token_endpoint")

    if not token_endpoint:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OIDC配置错误: 未找到token端点"
        )

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to exchange token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token交换失败: {str(e)}"
            )


async def get_oidc_userinfo(access_token: str, config: dict) -> dict:
    """Get user information from OIDC provider"""
    discovery = await fetch_oidc_discovery(config["discovery_url"])
    userinfo_endpoint = discovery.get("userinfo_endpoint")

    if not userinfo_endpoint:
        # If no userinfo endpoint, try to get user info from ID token
        logger.warning("No userinfo endpoint available, using ID token")
        return {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get userinfo: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"获取用户信息失败: {str(e)}"
            )


def determine_user_role(roles: list[str], config: dict) -> UserRole:
    """Determine user role based on OIDC provider roles"""
    admin_roles = config.get("admin_roles", [])
    manager_roles = config.get("manager_roles", [])

    for role in roles:
        if role in admin_roles:
            return UserRole.ADMIN
        if role in manager_roles:
            return UserRole.MANAGER

    return UserRole(config.get("default_role", "USER"))


async def create_or_update_user(db: AsyncSession, userinfo: dict, config: dict) -> User:
    """Create or update user based on OIDC user info"""
    email = userinfo.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC未提供邮箱信息"
        )

    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Extract roles from userinfo (if available)
    roles = userinfo.get("roles", [])
    if isinstance(roles, str):
        roles = [roles]

    # Determine user role
    user_role = determine_user_role(roles, config)
    is_admin = (user_role == UserRole.ADMIN)

    if user:
        # Update existing user
        user.full_name = userinfo.get("name") or user.full_name
        user.is_active = True
        user.role = user_role
        user.is_admin = is_admin
        user.last_login_at = datetime.utcnow()
    else:
        # Create new user
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            full_name=userinfo.get("name") or email.split("@")[0],
            is_active=True,
            is_admin=is_admin,
            role=user_role,
            last_login_at=datetime.utcnow()
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/config")
async def get_oidc_sso_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get OIDC SSO configuration (admin only) - includes sensitive data"""
    from app.api.ldap import check_admin_permission
    check_admin_permission(current_user)

    config = await get_oidc_config(db)
    return config


@router.get("/config/public")
async def get_public_oidc_config(
    db: AsyncSession = Depends(get_db)
):
    """Get public OIDC SSO configuration (no auth required) - for login page"""
    config = await get_oidc_config(db)

    # Only return non-sensitive information needed for login page
    return {
        "enabled": config.get("enabled", False),
        "provider_name": config.get("provider_name", "generic"),
        "environment": config.get("environment", "test"),
        # Don't expose sensitive data like client_secret, discovery_url details
    }


@router.get("/auth-url")
async def get_authorization_url(
    db: AsyncSession = Depends(get_db)
):
    """Get OIDC authorization URL for frontend redirect"""
    config = await get_oidc_config(db)

    if not config.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC SSO未启用"
        )

    try:
        discovery = await fetch_oidc_discovery(config["discovery_url"])
        auth_endpoint = discovery.get("authorization_endpoint")

        if not auth_endpoint:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OIDC配置错误: 未找到authorization端点"
            )

        # Generate state for CSRF protection
        state = str(uuid.uuid4())

        # Build authorization URL
        from urllib.parse import urlencode
        scope = config.get("scope", "openid email profile")
        params = urlencode({
            'client_id': config['client_id'],
            'redirect_uri': config['redirect_uri'],
            'response_type': 'code',
            'scope': scope,
            'state': state
        })
        auth_url = f"{auth_endpoint}?{params}"

        return {
            "auth_url": auth_url,
            "state": state,
            "provider": config.get("provider_name", "generic")
        }

    except Exception as e:
        logger.error(f"Failed to generate auth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成授权URL失败: {str(e)}"
        )


@router.post("/callback", response_model=Token)
async def oidc_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle OIDC OAuth2 callback

    This endpoint receives the authorization code from any OIDC provider,
    exchanges it for tokens, and creates/updates the user.
    """
    config = await get_oidc_config(db)

    if not config.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC SSO未启用"
        )

    try:
        # Exchange code for token
        token_response = await exchange_code_for_token(code, config["redirect_uri"], config)
        access_token = token_response.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未获取到访问令牌"
            )

        # Get user info from OIDC provider
        userinfo = await get_oidc_userinfo(access_token, config)

        # Create or update user
        user = await create_or_update_user(db, userinfo, config)

        # Log audit event
        await log_audit_event(
            db=db,
            action="SSO_LOGIN",
            user=user,
            resource_type="SYSTEM",
            details={
                "provider": config.get("provider_name", "oidc"),
                "email": user.email
            },
            request=request
        )
        await db.commit()

        # Create JWT token for our app
        app_token = create_access_token(data={"sub": user.id})

        return Token(
            access_token=app_token,
            user=UserResponse.model_validate(user),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OIDC authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SSO认证失败: {str(e)}"
        )


@router.post("/test-config")
async def test_oidc_config(
    config: OIDCConfig,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Test OIDC configuration for any provider"""
    from app.api.ldap import check_admin_permission
    check_admin_permission(current_user)

    try:
        # Test connection to OIDC provider
        discovery = await fetch_oidc_discovery(config.discovery_url)

        return {
            "success": True,
            "message": f"成功连接到OIDC服务器: {discovery.get('issuer', 'Unknown')}",
            "provider": config.provider_name,
            "details": {
                "issuer": discovery.get("issuer"),
                "authorization_endpoint": discovery.get("authorization_endpoint"),
                "token_endpoint": discovery.get("token_endpoint"),
                "userinfo_endpoint": discovery.get("userinfo_endpoint"),
                "supported_scopes": discovery.get("scopes_supported", []),
                "supported_response_types": discovery.get("response_types_supported", [])
            }
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"连接OIDC服务器失败: {str(e)}"
        }