#!/usr/bin/env python3
"""
OIDC配置诊断工具
用于排查SSO登录问题
"""

import asyncio
import sys
import os

# 添加后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.ldap_config import LDAPConfig
import httpx

async def diagnose_oidc():
    """诊断OIDC配置"""

    print("🔍 PPAP OIDC 配置诊断工具")
    print("=" * 60)

    # 1. 检查数据库配置
    print("\n1️⃣ 检查数据库配置...")

    try:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await session.get(LDAPConfig, "main_config")

            if not result:
                print("❌ 未找到配置记录")
                return

            print("✅ 找到配置记录")
            print(f"   SSO启用: {result.sso_enabled}")
            print(f"   提供商: {result.sso_provider}")
            print(f"   发现URL: {result.sso_idp_sso_url}")
            print(f"   客户端ID: {result.sso_entity_id}")
            print(f"   客户端密钥: {'***' if result.sso_sp_key else '❌ 未设置'}")
            print(f"   回调地址: {result.sso_acs_url}")
            print(f"   自动创建用户: {result.auto_create_users}")

            # 检查关键字段是否缺失
            missing_fields = []
            if not result.sso_idp_sso_url:
                missing_fields.append("发现URL (sso_idp_sso_url)")
            if not result.sso_entity_id:
                missing_fields.append("客户端ID (sso_entity_id)")
            if not result.sso_sp_key:
                missing_fields.append("客户端密钥 (sso_sp_key)")

            if missing_fields:
                print(f"\n❌ 缺少关键配置字段: {', '.join(missing_fields)}")
                print("请在前端管理界面中完善这些配置")
                return

        await engine.dispose()

    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        return

    # 2. 测试Keycloak连接
    print("\n2️⃣ 测试Keycloak连接...")

    discovery_url = result.sso_idp_sso_url

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(discovery_url)
            response.raise_for_status()
            discovery = response.json()

            print("✅ 成功连接到Keycloak")
            print(f"   Issuer: {discovery.get('issuer', 'Unknown')}")
            print(f"   授权端点: {discovery.get('authorization_endpoint', 'Missing')}")
            print(f"   令牌端点: {discovery.get('token_endpoint', 'Missing')}")
            print(f"   用户信息端点: {discovery.get('userinfo_endpoint', 'Missing')}")

            # 检查必需的端点
            required_endpoints = ['authorization_endpoint', 'token_endpoint']
            missing_endpoints = [ep for ep in required_endpoints if not discovery.get(ep)]

            if missing_endpoints:
                print(f"❌ Keycloak发现文档缺少必需端点: {missing_endpoints}")
                return

    except httpx.HTTPError as e:
        print(f"❌ 连接Keycloak失败: {e}")
        print("请检查:")
        print("  1. Keycloak服务是否正在运行")
        print("  2. 发现URL是否正确")
        print("  3. 网络连接是否正常")
        return
    except Exception as e:
        print(f"❌ 解析发现文档失败: {e}")
        return

    # 3. 生成授权URL测试
    print("\n3️⃣ 生成授权URL测试...")

    try:
        auth_endpoint = discovery.get('authorization_endpoint')
        client_id = result.sso_entity_id
        redirect_uri = result.sso_acs_url or "http://localhost:5173/auth/callback"

        # 构建授权URL
        from urllib.parse import urlencode
        import uuid

        state = str(uuid.uuid4())
        params = urlencode({
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': state
        })
        auth_url = f"{auth_endpoint}?{params}"

        print("✅ 成功生成授权URL:")
        print(f"   {auth_url}")

    except Exception as e:
        print(f"❌ 生成授权URL失败: {e}")
        return

    # 4. 总结
    print("\n✅ 诊断完成 - OIDC配置正常")
    print("\n💡 下一步:")
    print("1. 确认Keycloak重定向URI包含: " + redirect_uri)
    print("2. 使用测试账户登录: sso-user / sso-password-123")
    print("3. 检查浏览器网络请求的详细信息")

if __name__ == "__main__":
    asyncio.run(diagnose_oidc())