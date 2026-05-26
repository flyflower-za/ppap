#!/bin/bash

echo "🧪 Keycloak 配置验证工具"
echo "=========================="
echo ""

# 测试发现端点
DISCOVERY_URL="http://47.114.107.127:34321/realms/my-sso/.well-known/openid-configuration"
echo "📡 测试发现端点..."
echo "URL: $DISCOVERY_URL"

RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$DISCOVERY_URL")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')

echo "HTTP状态: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Keycloak配置正确！"

    # 测试PPAP连接
    echo ""
    echo "📡 测试PPAP SSO集成..."
    PPAP_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:31234/api/v1/oidc/auth-url)
    PPAP_CODE=$(echo "$PPAP_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

    if [ "$PPAP_CODE" = "200" ]; then
        echo "✅ PPAP SSO集成正常！"
        echo ""
        echo "🎉 配置完成！现在可以使用SSO登录了"
    else
        echo "❌ PPAP SSO还有问题: $PPAP_CODE"
    fi
else
    echo "❌ Keycloak配置仍有问题"
    echo "响应: $BODY"
    echo ""
    echo "请确认："
    echo "1. Keycloak Realm设置中 SSL required = None"
    echo "2. Keycloak服务正在运行"
    echo "3. 网络连接正常"
fi