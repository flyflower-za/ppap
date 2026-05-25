# Changelog

All notable changes to the PPAP project will be documented in this file.

## [2026-05-25] - 端口配置优化

### 问题描述
- 系统中存在端口冲突，8000端口已被其他服务占用
- 需要调整PPAP项目的端口配置以避免冲突

### 详细修改记录

#### 1. 前端开发服务器代理配置
**文件路径**: `/home/zhouao2/ppap/frontend/vite.config.ts`
**修改位置**: 第17行，proxy配置段
**修改时间**: 2026-05-25 10:30

**代码对比**:
```diff
server: {
  port: 5173,
  proxy: {
    '/api': {
-     target: 'http://localhost:8000',
+     target: 'http://localhost:31234',
      changeOrigin: true,
      ws: true,
    },
  },
}
```

**原因**: 将前端代理指向新的后端端口，避免与占用的8000端口冲突

---

#### 2. Docker端口映射配置
**文件路径**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
**修改位置**: 第74行，backend服务配置段
**修改时间**: 2026-05-25 10:39

**代码对比**:
```diff
backend:
  build:
    context: ../backend
    dockerfile: Dockerfile
  container_name: ppap-backend
  restart: unless-stopped
  environment:
    DATABASE_URL: postgresql+asyncpg://ppap:ppap123@postgres:5432/ppap
    REDIS_URL: redis://redis:6379/0
    MINIO_ENDPOINT: minio:9000
    MINIO_SECURE: "false"
    SECRET_KEY: ${SECRET_KEY:-change-this-in-production}
    CORS_ORIGINS: '["http://localhost:3000","http://localhost:5173"]'
  ports:
-   - "31234:8000"
+   - "31234:31234"
  depends_on:
```

**原因**: 保持Docker容器内外端口一致，与应用配置中的PORT=31234匹配

---

#### 3. 部署脚本端口配置
**文件路径**: `/home/zhouao2/ppap/deploy.sh`
**修改位置**: 第88行，部署完成提示信息段
**修改时间**: 2026-05-25 10:45

**代码对比**:
```diff
echo -e "=== Deployment Completed Successfully ===${NC}"
echo -e "Access the services at:"
echo -e "  - Frontend UI:   http://localhost"
- echo -e "  - Backend API:   http://localhost:8000/docs"
+ echo -e "  - Backend API:   http://localhost:31234/docs"
echo -e "  - MinIO Console: http://localhost:9001 (minioadmin / minioadmin)"
```

**原因**: 更新部署脚本中的API文档地址，确保显示正确的后端端口

---

#### 4. Docker容器环境变量配置 (修复)
**文件路径**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
**修改位置**: 第67行，backend服务environment配置段
**修改时间**: 2026-05-25 10:50
**问题**: Docker容器缺少PORT环境变量，导致后端服务仍监听8000端口

**代码对比**:
```diff
backend:
  build:
    context: ../backend
    dockerfile: Dockerfile
  container_name: ppap-backend
  restart: unless-stopped
  environment:
+   PORT: "31234"
    DATABASE_URL: postgresql+asyncpg://ppap:ppap123@postgres:5432/ppap
    REDIS_URL: redis://redis:6379/0
    MINIO_ENDPOINT: minio:9000
    MINIO_SECURE: "false"
    SECRET_KEY: ${SECRET_KEY:-change-this-in-production}
    CORS_ORIGINS: '["http://localhost:3000","http://localhost:5173"]'
```

**原因**: 确保Docker容器内的后端服务使用正确的PORT环境变量，解决外部访问31234端口失败的问题

---

#### 5. Docker容器启动命令配置 (修复)
**文件路径**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
**修改位置**: 第75行后，backend服务配置段
**修改时间**: 2026-05-25 10:55
**问题**: Dockerfile中硬编码了8000端口，导致环境变量无效

**代码对比**:
```diff
backend:
  build:
    context: ../backend
    dockerfile: Dockerfile
  container_name: ppap-backend
  restart: unless-stopped
  environment:
    PORT: "31234"
    DATABASE_URL: postgresql+asyncpg://ppap:ppap123@postgres:5432/ppap
    REDIS_URL: redis://redis:6379/0
    MINIO_ENDPOINT: minio:9000
    MINIO_SECURE: "false"
    SECRET_KEY: ${SECRET_KEY:-change-this-in-production}
    CORS_ORIGINS: '["http://localhost:3000","http://localhost:5173"]'
  ports:
    - "31234:31234"
+  command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "31234"]
```

**原因**: 覆盖Dockerfile中的硬编码端口，确保后端服务监听31234端口

---

#### 6. 防火墙端口配置
**文件路径**: `/home/zhouao2/ppap/setup_firewall.sh`
**修改位置**: 第37-38行，防火墙规则配置段
**修改时间**: 2026-05-25 10:58

**代码对比**:
```diff
# Backend API
- echo -e "Allowing Backend API (Port 8000)..."
- ufw allow 8000/tcp
+ echo -e "Allowing Backend API (Port 31234)..."
+ ufw allow 31234/tcp
```

**原因**: 更新防火墙规则，允许外部访问31234端口

---

#### 7. Nginx MIME类型配置 (修复PDF渲染问题)
**文件路径**: `/home/zhouao2/ppap/deploy/nginx.conf`
**修改位置**: 第28行后，server配置段
**修改时间**: 2026-05-25 10:52
**问题**: .mjs文件的MIME类型设置为application/octet-stream，导致PDF.js worker加载失败

**代码对比**:
```diff
# Frontend static files
location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}

+ # Fix MIME type for .mjs files (PDF.js worker)
+ location ~* \.mjs$ {
+     root /usr/share/nginx/html;
+     add_header Content-Type application/javascript always;
+ }
```

**原因**: 使用专门的location块和add_header指令强制设置.mjs文件的MIME类型为application/javascript，解决PDF.js worker加载失败的问题

---

#### 8. PDF.js Worker加载方式修复 (彻底解决PDF渲染问题)
**文件路径**: `/home/zhouao2/ppap/frontend/src/views/FileDetailPage.vue`
**修改位置**: 第485-488行，PDF.js导入和配置段
**修改时间**: 2026-05-25 10:54
**问题**: 本地.mjs worker文件在nginx环境下的MIME类型和加载路径问题

**代码对比**:
```diff
- import * as pdfjsLib from 'pdfjs-dist'
- import pdfWorker from 'pdfjs-dist/build/pdf.worker.mjs?url'
- 
- pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker
+ import * as pdfjsLib from 'pdfjs-dist'
+ 
+ // Use CDN for PDF.js worker to avoid MIME type issues
+ pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`
```

**原因**: 使用CDN版本的PDF.js worker来避免本地文件的MIME类型和路径问题，确保PDF渲染功能稳定可靠

**附加修复**: 重新安装前端依赖并重新构建前端，解决了rollup构建依赖问题

---

### 相关配置文件

#### 无需修改的配置文件
以下文件已正确配置，无需修改：

1. **后端环境配置**: `/home/zhouao2/ppap/backend/.env`
   - 第9行: `PORT=31234` ✅

2. **后端默认配置**: `/home/zhouao2/ppap/backend/app/core/config.py`
   - 第15行: `PORT: int = 8000` (默认值，被.env覆盖) ✅

3. **数据库配置**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
   - 第16行: `"5435:5432"` (PostgreSQL端口映射) ✅

4. **Redis配置**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
   - 第32行: `"6379:6379"` (Redis端口映射) ✅

5. **MinIO配置**: `/home/zhouao2/ppap/deploy/docker-compose.yml`
   - 第51行: `"9000:9000"` (MinIO API端口) ✅
   - 第52行: `"9001:9001"` (MinIO控制台端口) ✅

### 端口分配总结

#### 主要服务端口
- **后端API服务器**: 31234 (原8000，已迁移)
- **前端开发服务器**: 5173
- **前端生产服务器**: 80

#### 数据存储端口
- **PostgreSQL**: 5435 (外部) → 5432 (容器内部)
- **Redis**: 6379
- **MinIO API**: 9000
- **MinIO 控制台**: 9001

#### 其他端口
- **SMTP**: 465 (默认未启用)

### 部署说明
由于配置变更，需要重新创建Docker容器：

```bash
# 停止并删除现有容器
cd /home/zhouao2/ppap/deploy
docker compose down

# 重新构建并启动
docker compose up -d --build
```

### 验证步骤
1. 确认后端服务在31234端口正常运行
2. 测试前端开发服务器代理功能
3. 验证API接口访问: `http://localhost:31234/api/v1/docs`
4. 检查各服务间通信正常

### 影响范围
- ✅ 本地开发环境配置
- ✅ Docker容器化部署
- ✅ 前后端连接配置
- ❌ 无数据库迁移需求
- ❌ 无代码逻辑变更

---

## 版本历史

| 日期 | 版本 | 描述 |
|------|------|------|
| 2026-05-25 | 1.0.1 | 端口配置优化，解决8000端口冲突 |
| 2026-05-24 | 1.0.0 | PPAP项目初始版本 |
