#!/usr/bin/env python3
"""
检查Keycloak SSL配置状态
"""

import requests
import json

def check_keycloak_ssl():
    print("🔍 检查 Keycloak SSL 配置状态")
    print("=" * 50)

    # 测试不同的URL
    test_urls = [
        ("HTTP访问", "http://47.114.107.127:34321/realms/my-sso/.well-known/openid-configuration"),
        ("HTTPS访问", "https://47.114.107.127:34321/realms/my-sso/.well-known/openid-configuration"),
    ]

    for name, url in test_urls:
        print(f"\n📡 测试 {name}: {url}")
        try:
            response = requests.get(url, timeout=5, verify=False)
            print(f"   HTTP状态: {response.status_code}")

            if response.status_code == 200:
                print("   ✅ 成功连接!")
                return True
            elif response.status_code == 403:
                try:
                    error = response.json()
                    error_desc = error.get('error_description', 'Unknown error')
                    print(f"   ❌ 访问被拒绝: {error_desc}")

                    if "HTTPS required" in error_desc:
                        print("   🔧 需要修改 Keycloak SSL 设置")
                except:
                    print(f"   ❌ 访问被拒绝")
            else:
                print(f"   ⚠️ 其他错误: {response.status_code}")

        except requests.exceptions.SSLError:
            print("   ❌ SSL证书错误")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ 连接失败: {e}")

    print("\n" + "=" * 50)
    print("📋 结论:")
    print("如果HTTP访问显示'HTTPS required'，需要修改Keycloak配置:")
    print("1. Realm settings → Login 标签页")
    print("2. SSL required → 改为 'None'")
    print("3. 保存设置")

if __name__ == "__main__":
    check_keycloak_ssl()