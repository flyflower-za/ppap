#!/usr/bin/env python3
"""
完整的SSO授权流程测试
"""

import requests
import urllib.parse

def test_full_sso_flow():
    print("🔍 完整SSO授权流程测试")
    print("=" * 60)

    # 1. 测试发现端点
    print("\n1️⃣ 测试发现端点...")
    discovery_url = "http://47.114.107.127:34321/realms/my-sso/.well-known/openid-configuration"
    response = requests.get(discovery_url)

    if response.status_code == 200:
        print("✅ 发现端点正常")
        discovery = response.json()
        auth_endpoint = discovery.get('authorization_endpoint')
        print(f"📋 授权端点: {auth_endpoint}")
    else:
        print(f"❌ 发现端点失败: {response.status_code}")
        return

    # 2. 测试授权请求（模拟前端）
    print("\n2️⃣ 测试授权请求...")
    params = {
        'client_id': 'my-app',
        'redirect_uri': 'http://localhost:5173/auth/callback',
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': 'test-state-123'
    }

    auth_url = f"{auth_endpoint}?{urllib.parse.urlencode(params)}"
    print(f"📝 授权URL: {auth_url}")

    try:
        auth_response = requests.get(auth_endpoint, params=params, allow_redirects=False)
        print(f"📋 HTTP状态: {auth_response.status_code}")

        if auth_response.status_code == 302:
            # 重定向到登录页面
            location = auth_response.headers.get('Location', '')
            print(f"✅ 重定向到登录页面")
            print(f"📋 Location: {location[:100]}...")
        elif auth_response.status_code == 400:
            print("❌ 授权请求失败 (HTTP 400)")
            try:
                error_data = auth_response.json()
                error = error_data.get('error', 'Unknown')
                error_desc = error_data.get('error_description', 'No description')
                print(f"📋 错误: {error}")
                print(f"📋 描述: {error_desc}")

                if "HTTPS required" in error_desc:
                    print("\n🔧 仍然需要HTTPS，需要修改更多Keycloak设置")
            except:
                print(f"📋 响应: {auth_response.text[:300]}")
        elif auth_response.status_code == 403:
            print("❌ 访问被拒绝 (HTTP 403)")
            try:
                error_data = auth_response.json()
                error_desc = error_data.get('error_description', 'No description')
                print(f"📋 描述: {error_desc}")

                if "HTTPS required" in error_desc:
                    print("\n🔧 Keycloak仍然要求HTTPS")
                    print("需要检查以下设置:")
                    print("1. Realm settings → Login → SSL required = None")
                    print("2. Client设置 → 可能需要检查其他SSL相关选项")
            except:
                print(f"📋 响应: {auth_response.text[:300]}")
        else:
            print(f"⚠️ 其他状态: {auth_response.status_code}")
            print(f"📋 响应: {auth_response.text[:200]}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # 3. 测试不同的redirect_uri
    print("\n3️⃣ 测试不同的重定向URI...")
    test_uris = [
        'http://localhost:5173/auth/callback',
        'http://localhost:3000/auth/callback'
    ]

    for uri in test_uris:
        print(f"\n测试: {uri}")
        params['redirect_uri'] = uri
        test_response = requests.get(auth_endpoint, params=params, allow_redirects=False)
        print(f"状态: {test_response.status_code}")

        if test_response.status_code == 302:
            print("✅ 有效")
        else:
            try:
                error_data = test_response.json()
                error_desc = error_data.get('error_description', '')
                if error_desc:
                    print(f"❌ {error_desc}")
            except:
                pass

if __name__ == "__main__":
    test_full_sso_flow()