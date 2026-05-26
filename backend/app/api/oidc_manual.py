"""
手动配置的 OIDC 端点（不使用发现端点）
用于无法使用发现端点的特殊情况
"""
from app.core.config import settings

# 如果发现端点无法使用，可以直接配置这些端点
# 请在 .env 中设置 OIDC_ISSUER_BASE_URL，例如：
#   OIDC_ISSUER_BASE_URL=http://your-keycloak:34321/realms/my-sso

def get_manual_oidc_config() -> dict:
    base = settings.OIDC_ISSUER_BASE_URL.rstrip("/")
    return {
        "authorization_endpoint": f"{base}/protocol/openid-connect/auth",
        "token_endpoint":         f"{base}/protocol/openid-connect/token",
        "userinfo_endpoint":      f"{base}/protocol/openid-connect/userinfo",
        "issuer":                 base,
    }

# 在 PPAP 配置界面中，不填写发现端点URL，
# 而是直接使用这些手动配置的端点