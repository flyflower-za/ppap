#!/bin/bash

echo "🔍 PPAP OIDC 配置快速测试"
echo "============================"

# 1. 测试配置状态
echo ""
echo "1️⃣ 检查SSO配置状态..."
CONFIG=$(curl -s http://localhost:31234/api/v1/oidc/config/public)
echo "📋 公开配置: $CONFIG"

# 2. 测试授权URL端点
echo ""
echo "2️⃣ 测试授权URL生成..."
AUTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:31234/api/v1/oidc/auth-url)
HTTP_CODE=$(echo "$AUTH_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
RESPONSE_BODY=$(echo "$AUTH_RESPONSE" | sed '/HTTP_CODE/d')

echo "HTTP状态码: $HTTP_CODE"
echo "响应内容: $RESPONSE_BODY"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 授权URL生成成功"

    # 提取授权URL
    AUTH_URL=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('auth_url', 'N/A'))" 2>/dev/null)
    STATE=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('state', 'N/A'))" 2>/dev/null)

    echo "📝 授权URL: $AUTH_URL"
    echo "🔑 State参数: $STATE"
else
    echo "❌ 授权URL生成失败"
    echo "错误详情: $RESPONSE_BODY"
fi

# 3. 测试Keycloak连接
echo ""
echo "3️⃣ 测试Keycloak发现端点..."
DISCOVERY_URL="http://47.114.107.127:34321/realms/my-sso/.well-known/openid-configuration"
echo "📡 发现URL: $DISCOVERY_URL"

DISCOVERY_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$DISCOVERY_URL")
DISCOVERY_HTTP_CODE=$(echo "$DISCOVERY_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
DISCOVERY_BODY=$(echo "$DISCOVERY_RESPONSE" | sed '/HTTP_CODE/d')

echo "HTTP状态码: $DISCOVERY_HTTP_CODE"

if [ "$DISCOVERY_HTTP_CODE" = "200" ]; then
    echo "✅ Keycloak发现端点正常"

    # 提取关键端点
    AUTH_ENDPOINT=$(echo "$DISCOVERY_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('authorization_endpoint', 'N/A'))" 2>/dev/null)
    TOKEN_ENDPOINT=$(echo "$DISCOVERY_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token_endpoint', 'N/A'))" 2>/dev/null)

    echo "🔑 授权端点: $AUTH_ENDPOINT"
    echo "🎫 令牌端点: $TOKEN_ENDPOINT"
else
    echo "❌ Keycloak发现端点失败"
    echo "错误详情: $DISCOVERY_BODY"
fi

echo ""
echo "============================"
echo "🧪 诊断完成"