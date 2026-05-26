#!/bin/bash

echo "🔧 Keycloak HTTPS 限制关闭指南"
echo "=================================="
echo ""

# 检测可能的安装方式
echo "🔍 检测 Keycloak 安装方式..."

# 常见的 Keycloak 配置文件位置
CONFIG_LOCATIONS=(
    "/opt/keycloak/conf/keycloak.conf"
    "/opt/keycloak/conf/quarkus.properties"
    "/etc/keycloak/keycloak.conf"
    "/opt/wildfly/standalone/configuration/standalone.xml"
    "/opt/jboss/keycloak/standalone/configuration/standalone.xml"
)

echo ""
echo "📋 方法一：修改配置文件（推荐）"
echo "================================"

for config_path in "${CONFIG_LOCATIONS[@]}"; do
    if [ -f "$config_path" ]; then
        echo "✅ 找到配置文件: $config_path"
        echo ""
        echo "请编辑此文件，查找并修改以下配置："

        if [[ "$config_path" == *"quarkus"* ]] || [[ "$config_path" == *"keycloak.conf"* ]]; then
            echo ""
            echo "对于 Quarkus 版本的 Keycloak："
            echo "--------------------------------"
            echo "1. 查找行：https-required=all"
            echo "2. 修改为：https-required=none"
            echo "3. 或添加新行：https-required=none"
            echo ""
            echo "示例："
            echo "# 禁用HTTPS要求"
            echo "https-required=none"
        elif [[ "$config_path" == *"standalone.xml"* ]]; then
            echo ""
            echo "对于 Wildfly 版本的 Keycloak："
            echo "--------------------------------"
            echo "1. 查找 <spi name=\"strict-transport-security\"> 部分"
            echo "2. 修改或添加："
            echo "   <provider name=\"hsts-disabled\">"
            echo "       <enabled>true</enabled>"
            echo "   </provider>"
        fi
        break
    fi
done

echo ""
echo "📋 方法二：使用 Keycloak Admin CLI"
echo "================================"
echo "如果配置文件不易找到，可以使用CLI："
echo ""
echo "1. SSH登录到服务器："
echo "   ssh your-user@47.114.107.127"
echo ""
echo "2. 使用 admin CLI："
echo "   cd /opt/keycloak/bin  # 或其他安装路径"
echo "   ./kcadm.sh config credentials --server http://localhost:8080 --realm master"
echo "   # 输入 admin/admin"
echo ""
echo "3. 修改 master realm 设置："
echo "   ./kcadm.sh update realms/master -s sslRequired=NONE"
echo ""
echo "4. 修改 my-sso realm 设置："
echo "   ./kcadm.sh update realms/my-sso -s sslRequired=NONE"

echo ""
echo "📋 方法三：重启 Keycloak 服务"
echo "================================"
echo "修改配置后需要重启服务："
echo ""
echo " systemctl restart keycloak"
echo " # 或"
echo " systemctl restart wildfly"
echo " # 或"
echo " docker restart keycloak  # 如果是Docker部署"

echo ""
echo "📋 方法四：临时方案 - 清除浏览器HSTS"
echo "================================"
echo "如果无法修改服务器配置，清除浏览器HSTS缓存："
echo ""
echo "Chrome: 访问 chrome://net-internals/#hsts"
echo "         输入域名 47.114.107.127 并删除"
echo ""
echo "Firefox: 使用隐私模式或清除站点数据"
echo ""
echo "Edge: 访问 edge://net-internals/#hsts"
echo "       输入域名 47.114.107.127 并删除"

echo ""
echo "================================"
echo "💡 推荐操作顺序："
echo "1. 先尝试使用浏览器隐私模式访问"
echo "2. 如有服务器权限，使用 Admin CLI 方法"
echo "3. 查找并修改配置文件"
echo "4. 重启 Keycloak 服务"