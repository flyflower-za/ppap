#!/usr/bin/env python3
"""
测试 Keycloak 连接并提供配置建议
"""

import requests

def test_keycloak_connection():
    print("🔍 Keycloak 连接测试工具")
    print("=" * 50)

    # 测试的URL列表
    test_urls = [
        "http://47.114.107.127:34321/realms/my-sso/.well-known/openid-configuration",
        "http://47.114.107.127:34321/auth/realms/my-sso/.well-known/openid-configuration",
    ]

    for url in test_urls:
        print(f"\n📡 测试: {url}")
        try:
            response = requests.get(url, timeout=5)
            print(f"   HTTP状态: {response.status_code}")

            if response.status_code == 200:
                print("   ✅ 成功连接！")

                data = response.json()
                print(f"   📋 Issuer: {data.get('issuer', 'N/A')}")
                print(f"   🔑 授权端点: {data.get('authorization_endpoint', 'N/A')}")

                print("\n   💡 使用此URL配置PPAP:")
                print(f"   发现URL: {url}")
                return url, data

            elif response.status_code == 403:
                print("   ❌ 访问被拒绝 (403)")
                try:
                    error_data = response.json()
                    print(f"   错误: {error_data.get('error_description', 'Unknown')}")
                except:
                    print(f"   响应: {response.text[:200]}")

            else:
                print(f"   ⚠️ 其他错误: {response.status_code}")
                print(f"   响应: {response.text[:200]}")

        except requests.exceptions.RequestException as e:
            print(f"   ❌ 连接失败: {e}")

    print("\n" + "=" * 50)
    print("❌ 所有URL都无法正常访问")
    print("\n建议:")
    print("1. 确认Keycloak服务正在运行")
    print("2. 检查网络连接")
    print("3. 修改Keycloak SSL要求设置为None")
    print("4. 确认Realm名称正确 (my-sso)")

if __name__ == "__main__":
    test_keycloak_connection()