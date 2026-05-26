#!/bin/bash

echo "🧪 验证 Keycloak 重定向URI配置"
echo "================================"
echo ""

# 测试5173端口
echo "📡 测试正确的重定向URI (5173端口)..."
curl -s "http://47.114.107.127:34321/realms/my-sso/protocol/openid-connect/auth" \
  -G \
  -d "client_id=my-app" \
  -d "redirect_uri=http://localhost:5173/auth/callback" \
  -d "response_type=code" \
  -d "scope=openid email profile" \
  -d "state=test" \
  -w "\nHTTP状态码: %{http_code}\n" \
  -o /dev/null

echo ""
echo "✅ 如果显示 HTTP状态码: 302，说明配置正确"
echo "❌ 如果显示 HTTP状态码: 400，说明还需要添加重定向URI"

echo ""
echo "================================"
echo "💡 配置完成后，刷新PPAP登录页面重试SSO登录"