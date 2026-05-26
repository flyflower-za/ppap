#!/usr/bin/env python3
"""
临时 HTTPS 代理用于 Keycloak 开发测试
将 HTTP Keycloak 请求包装为 HTTPS
"""

from flask import Flask, request, Response, redirect
import requests

app = Flask(__name__)

KEYCLOAK_BASE = "http://47.114.107.127:34321"

@app.route('/realms/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def proxy_realm(path):
    """代理 Keycloak Realm 请求"""

    # 构建目标 URL
    target_url = f"{KEYCLOAK_BASE}/realms/{path}"
    if request.query_string:
        target_url += f"?{request.query_string.decode()}"

    # 转发请求
    resp = requests.request(
        method=request.method,
        url=target_url,
        headers={k: v for k, v in request.headers if k != 'Host'},
        data=request.get_data(),
        allow_redirects=False,
        timeout=10
    )

    # 构建响应
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.raw.headers.items()
               if name.lower() not in excluded_headers]

    return Response(
        resp.content,
        status=resp.status_code,
        headers=headers
    )

@app.route('/.well-known/<path:path>', methods=['GET'])
def proxy_well_known(path):
    """代理 .well-known 发现文档"""
    return proxy_realm(f".well-known/{path}")

if __name__ == '__main__':
    # 注意：这里使用自签名证书仅用于开发测试
    print("🚀 启动 Keycloak HTTPS 代理...")
    print("📡 代理地址: https://localhost:34322")
    print("🎯 目标地址: http://47.114.107.127:34321")
    print("\n⚠️  这是开发用的临时代理，请勿用于生产环境")

    # 如果需要生成自签名证书：
    # openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

    app.run(
        host='0.0.0.0',
        port=34322,
        ssl_context=('cert.pem', 'key.pem'),  # 需要自签名证书
        debug=True
    )