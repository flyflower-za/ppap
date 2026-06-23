# 端口配置指南 (Port Configuration Guide)

在 PPAP 平台中，涉及到了前端、后端、数据库、对象存储等多个服务，它们分别占用不同的端口。本指南说明当前的端口配置以及如何修改。

## 当前端口配置

| 服务 | 端口 | 说明 |
|-----|------|------|
| **前端 Web 界面** | `80` | Nginx 提供的生产环境访问端口 |
| **后端 API** | `31234` | FastAPI 接口访问端口 (已从 8000 迁移) |
| **MinIO API** | `9000` | 对象存储内部通讯及文件下载代理 |
| **MinIO 控制台** | `9001` | MinIO Web 管理界面 |
| **PostgreSQL** | `5435` → `5432` | 宿主机 5435 映射到容器内 5432 |
| **Redis** | `6379` | 缓存与队列端口 |
| **Keycloak SSO (测试)** | `34321` | SSO 单点登录测试端点端口 |
| **前端开发** | `5173` | Vite 开发服务器端口 |

---

## 服务访问地址

- **前端 UI**: `http://localhost` (生产) / `http://localhost:5173` (开发)
- **后端 API 文档**: `http://localhost:31234/docs`
- **MinIO 控制台**: `http://localhost:9001` (minioadmin / minioadmin)
- **Keycloak 控制台**: `http://47.114.107.127:34321` (测试环境)

---

## 推荐做法：仅修改宿主机映射端口

最安全的方法是让 Docker 容器内部继续使用原端口，**只改变宿主机的对外暴露端口**。

打开 `deploy/docker-compose.yml` 文件，修改对应服务的 `ports` 属性中冒号**左侧**的数字：

### 修改后端 API 端口 (当前 31234)

```yaml
  backend:
    ports:
      - "31234:31234"  # 格式：宿主机端口:容器端口
```

如需改为其他端口（如 `40000`）：
```yaml
  backend:
    ports:
      - "40000:31234"  # 宿主机改为 40000，容器内保持 31234
```

### 修改前端 Web 端口 (当前 80)

```yaml
  frontend:
    ports:
      - "8080:80"  # 宿主机改为 8080
```

### 修改 MinIO 控制台端口 (当前 9001)

```yaml
  minio:
    ports:
      - "9000:9000"
      - "19001:9001"  # 宿主机改为 19001
```

---

## 进阶做法：全量修改

如需修改容器内部的默认端口，需要同步修改多个配置文件。

### 修改后端端口 (31234 → 其他端口)

1. **`backend/.env`**: 修改 `PORT=新端口号`
2. **`deploy/docker-compose.yml`**:
   ```yaml
   backend:
     environment:
       PORT: "新端口号"
     ports:
       - "新端口号:新端口号"
     command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "新端口号"]
   ```
3. **`frontend/vite.config.ts`**: 修改代理目标
   ```ts
   proxy: {
     '/api': {
       target: 'http://localhost:新端口号',
     },
   }
   ```
4. **`deploy/nginx.conf`**: 修改上游服务器
   ```nginx
   upstream backend {
       server backend:新端口号;
   }
   ```

### 修改前端开发端口 (5173 → 其他端口)

**`frontend/vite.config.ts`**:
```ts
export default defineConfig({
  server: {
    port: 新端口号,
  },
})
```

---

## 防火墙配置

如果使用 `ufw` 防火墙，确保放行所需端口：

```bash
# 前端
sudo ufw allow 80/tcp

# 后端 API
sudo ufw allow 31234/tcp

# MinIO 控制台 (可选)
sudo ufw allow 9001/tcp
```

---

## 端口变更历史

| 日期 | 变更 |
|------|------|
| 2026-06-24 | 增加在线防伪比对模块与文档差异比对，后端继续提供 31234 端口的结构化输出 API |
| 2026-05-26 | 增加 Keycloak SSO 登录测试端点支持，端口为 34321 |
| 2026-05-25 | 后端端口从 8000 迁移到 31234，避免与其它服务冲突 |
| 2026-05-24 | 项目初始版本，使用默认端口配置 |

---

## 注意事项

1. **数据库和 Redis** 默认未对外映射端口，仅容器内部访问，更安全
2. 修改端口后需要重启服务：`docker compose restart`
3. 确保新端口未被其他服务占用
4. 生产环境建议使用反向代理 (Nginx) 统一管理端口
