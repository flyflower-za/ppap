"""
手动配置的 OIDC 端点（不使用发现端点）
用于无法使用发现端点的特殊情况
"""

# 如果发现端点无法使用，可以直接配置这些端点

MANUAL_OIDC_CONFIG = {
    "authorization_endpoint": "http://47.114.107.127:34321/realms/my-sso/protocol/openid-connect/auth",
    "token_endpoint": "http://47.114.107.127:34321/realms/my-sso/protocol/openid-connect/token",
    "userinfo_endpoint": "http://47.114.107.127:34321/realms/my-sso/protocol/openid-connect/userinfo",
    "issuer": "http://47.114.107.127:34321/realms/my-sso"
}

# 在 PPAP 配置界面中，不填写发现端点URL，
# 而是直接使用这些手动配置的端点