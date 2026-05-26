#!/usr/bin/env python3
"""
调试重定向URI问题的脚本
"""

import requests
import json

def test_oidc_redirect():
    print("🔍 OIDC 重定向URI 调试工具")
    print("=" * 60)

    # 1. 测试授权URL生成
    print("\n1️⃣ 测试授权URL生成...")
    auth_response = requests.get("http://localhost:31234/api/v1/oidc/auth-url")

    if auth_response.status_code == 200:
        data = auth_response.json()
        auth_url = data.get('auth_url', '')
        print(f"✅ 授权URL生成成功")
        print(f"📝 完整URL: {auth_url}")

        # 解析URL中的参数
        if 'redirect_uri=' in auth_url:
            start = auth_url.index('redirect_uri=') + len('redirect_uri=')
            end = auth_url.find('&', start)
            if end == -1:
                end = len(auth_url)
            redirect_uri = auth_url[start:end]
            print(f"🔀 当前使用的重定向URI: {redirect_uri}")

            # 检查常见问题
            issues = []
            if redirect_uri.endswith('/'):
                issues.append("尾部有斜杠")
            if 'localhost' in redirect_uri:
                issues.append("使用localhost而不是具体IP")

            if issues:
                print(f"⚠️  可能的问题: {', '.join(issues)}")
    else:
        print(f"❌ 授权URL生成失败: {auth_response.status_code}")
        print(auth_response.text)

    # 2. 测试Keycloak发现端点
    print("\n2️⃣ 检查Keycloak配置...")
    discovery_url = "http://47.114.107.127:34321/realms/my-sso/.well-known/openid-configuration"
    discovery_response = requests.get(discovery_url)

    if discovery_response.status_code == 200:
        discovery = discovery_response.json()
        print("✅ Keycloak发现端点正常")
        print(f"🔑 授权端点: {discovery.get('authorization_endpoint', 'N/A')}")

    # 3. 模拟授权请求测试
    print("\n3️⃣ 测试不同的重定向URI...")

    test_uris = [
        "http://localhost:5173/auth/callback",
        "http://localhost:5173/auth/callback/",
        "http://127.0.0.1:5173/auth/callback",
        "http://localhost:3000/auth/callback",
        "http://47.114.107.127:5173/auth/callback",
    ]

    auth_endpoint = "http://47.114.107.127:34321/realms/my-sso/protocol/openid-connect/auth"

    for test_uri in test_uris:
        print(f"\n测试URI: {test_uri}")
        params = {
            'client_id': 'my-app',
            'redirect_uri': test_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': 'test-state'
        }

        test_response = requests.get(auth_endpoint, params=params, allow_redirects=False)

        if test_response.status_code == 302:
            print("✅ 有效 - 重定向到登录页面")
        elif test_response.status_code == 400:
            print(f"❌ 无效 - HTTP 400")
            try:
                error_data = test_response.json()
                print(f"   错误: {error_data.get('error', 'Unknown')}")
                print(f"   描述: {error_data.get('error_description', 'No description')}")
            except:
                print(f"   响应: {test_response.text[:200]}")
        else:
            print(f"⚠️  其他状态: {test_response.status_code}")

    print("\n" + "=" * 60)
    print("📋 建议修复步骤:")
    print("1. 确认Keycloak客户端配置中包含正确的重定向URI")
    print("2. 确保PPAP配置中的回调地址与Keycloak完全一致")
    print("3. 检查URL协议(http/https)、端口、路径是否匹配")

if __name__ == "__main__":
    test_oidc_redirect()