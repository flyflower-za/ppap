#!/usr/bin/env python3
"""
测试和配置 SSO 的脚本
用于验证 OIDC 配置是否正确
"""

import requests
import json
import sys

BASE_URL = "http://localhost:31234/api/v1"

def test_sso_config():
    """测试 SSO 配置"""
    print("🔍 测试 SSO 配置...")

    try:
        # 测试公开配置端点（不需要认证）
        response = requests.get(f"{BASE_URL}/oidc/config/public")
        print(f"📡 公开配置端点: {response.status_code}")

        if response.ok:
            config = response.json()
            print(f"✅ SSO 状态: {'已启用' if config.get('enabled') else '未启用'}")
            print(f"📋 提供商: {config.get('provider_name', 'generic')}")
            print(f"🌍 环境: {config.get('environment', 'test')}")
            return config.get('enabled', False)
        else:
            print(f"❌ 获取配置失败: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def configure_sso():
    """配置 SSO（需要管理员权限）"""
    print("\n⚙️  配置 SSO...")

    # 示例配置 - 根据实际情况修改
    sso_config = {
        "sso_enabled": True,
        "sso_provider": "keycloak",
        "sso_idp_sso_url": "http://47.114.107.127:34321/realms/my-sso/.well-known/openid-configuration",
        "sso_entity_id": "my-app",
        "sso_sp_key": "my-secret-password",
        "sso_acs_url": "http://localhost:5173/auth/callback",
        "auto_create_users": True,
        "default_role": "USER",
        "ldap_server": "test"
    }

    print("请提供管理员 API Token:")
    print("1. 先使用普通登录获取 token")
    print("2. 或者直接在请求头中提供 Authorization: Bearer YOUR_TOKEN")
    print("\n配置信息:")
    print(json.dumps(sso_config, indent=2, ensure_ascii=False))

    # 这里需要用户手动配置，或者提供 token
    print("\n💡 使用以下命令配置:")
    print(f"curl -X POST {BASE_URL}/ldap-config \\")
    print('  -H "Content-Type: application/json" \\')
    print('  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \\')
    print(f"  -d '{json.dumps(sso_config, ensure_ascii=False)}'")

def main():
    print("🚀 PPAP SSO 配置测试工具\n")

    # 首先检查 SSO 状态
    sso_enabled = test_sso_config()

    if not sso_enabled:
        print("\n⚠️  SSO 未启用")
        print("您需要:")
        print("1. 通过管理界面配置 SSO")
        print("2. 或使用 API 配置 SSO")
        configure_sso()
    else:
        print("\n✅ SSO 已启用!")
        print("现在登录页面应该显示 SSO 登录按钮")
        print("\n💡 如果仍然看不到按钮:")
        print("1. 检查前端控制台是否有错误")
        print("2. 确认前端正在调用 /api/v1/oidc/config/public")
        print("3. 刷新登录页面")

if __name__ == "__main__":
    main()