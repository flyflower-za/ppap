#!/usr/bin/env python3
"""
Keycloak 管理控制台 HTTPS 要求修复指南
"""

print("🔧 Keycloak 管理控制台 HTTPS 要求修复")
print("=" * 60)

print("\n📋 问题分析:")
print("管理控制台登录要求HTTPS，但我们需要使用HTTP访问")

print("\n✅ 解决方案:")
print("=" * 60)

print("\n🎯 方案一：修改 Keycloak 主配置文件（推荐）")
print("-" * 40)
print("1. 编辑 Keycloak 配置文件:")
print("   位置: /opt/keycloak/conf/keycloak.conf 或类似路径")
print("")
print("2. 查找并修改以下配置:")
print("   # 注释掉或修改HTTPS要求")
print("   # https-required=all")
print("   https-required=none")
print("")
print("3. 重启 Keycloak 服务")

print("\n🎯 方案二：使用 Keycloak Admin CLI")
print("-" * 40)
print("1. 连接到Keycloak服务器:")
print("   ssh your-user@47.114.107.127")
print("")
print("2. 使用admin CLI修改设置:")
print("   cd /opt/keycloak/bin")
print("   ./kcadm.sh config credentials --server http://localhost:8080 --realm master")
print("   # 输入admin用户名密码")
print("")
print("3. 修改master realm的SSL要求:")
print("   ./kcadm.sh update realms/master -s sslRequired=NONE")

print("\n🎯 方案三：修改浏览器访问方式")
print("-" * 40)
print("1. 确保使用HTTP访问管理控制台:")
print("   http://47.114.107.127:34321/")
print("")
print("2. 如果浏览器自动重定向到HTTPS:")
print("   - 清除浏览器缓存")
print("   - 使用隐私/无痕模式")
print("   - 使用其他浏览器")

print("\n🎯 方案四：通过SSH直接修改数据库")
print("-" * 40)
print("1. 连接到服务器:")
print("   ssh your-user@47.114.107.127")
print("")
print("2. 访问Keycloak数据库，修改realm配置")
print("   这需要数据库访问权限")

print("\n" + "=" * 60)
print("💡 推荐顺序:")
print("1. 先尝试方案三（浏览器方式）")
print("2. 如果不行，尝试方案二（Admin CLI）")
print("3. 最后考虑方案一（修改配置文件）")
print("")
print("🔍 需要确定Keycloak的安装路径和配置方式")