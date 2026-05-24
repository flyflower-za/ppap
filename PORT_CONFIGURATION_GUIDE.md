# 端口修改与配置指南 (Port Configuration Guide)

在 PPAP 平台中，涉及到了前端、后端、数据库、对象存储等多个服务，它们分别占用不同的默认端口。如果您发现某些端口被占用，可以按照本指南进行修改。

## 系统默认占用端口一览

- **`80`**：前端 Web 界面访问端口 (由 Nginx 提供)
- **`8000`**：后端 FastAPI 接口访问端口
- **`9000`**：MinIO 对象存储 API 端口 (内部通讯及文件下载代理)
- **`9001`**：MinIO 对象存储 Web 管理控制台
- **`5432`**：PostgreSQL 数据库端口
- **`6379`**：Redis 缓存与队列端口
- **`5173`**：前端本地开发 (npm run dev) 端口

---

## 推荐做法：仅修改宿主机（对外暴露）端口

最安全、最快捷的方法是让 Docker 容器内部继续使用它们原本的端口，**只改变映射到您物理机（宿主机）上的对外暴露端口**。

打开 `deploy/docker-compose.yml` 文件，找到对应服务的 `ports` 属性，修改冒号**左侧**的数字即可：

### 1. 修改前端 Web 端口 (默认 80)
如果 80 端口被占用，比如您想换成 `8080` 端口：
```yaml
  frontend:
    ports:
      - "8080:80"  # 将原本的 "80:80" 左侧改成 8080
```
访问地址变成：`http://您的IP:8080`

### 2. 修改后端 API 端口 (默认 8000)
如果您想把 8000 换成 `8888`：
```yaml
  backend:
    ports:
      - "8888:8000"  # 将原本的 "8000:8000" 左侧改成 8888
```

### 3. 修改 MinIO 控制台端口 (默认 9001)
如果您想把 9001 换成 `19001`：
```yaml
  minio:
    ports:
      - "9000:9000"
      - "19001:9001" # 将原本的 9001:9001 左侧改成 19001
```
访问地址变成：`http://您的IP:19001`

*(注意：数据库 Postgres 和 Redis 默认没有在 docker-compose 中对外映射端口，因为只有内部微服务需要访问它们。这大大增强了安全性。)*

> **防火墙同步**：如果您开启了 `ufw` 等防火墙并使用了 `setup_firewall.sh`，记得在里面放行您新改的外部端口（比如 `ufw allow 8080/tcp` 等）。

---

## 进阶做法：全量修改（连同代码和内部网络一起改）

如果您因为特殊需要，或者有代码洁癖，想把内部环境的默认端口也全改掉，这就涉及到了复杂的依赖关系。以下是核心修改链路：

### 1. 彻底修改前端端口 (Nginx)
如果您想让容器内部的 Nginx 也不再监听 80 端口：
* **`deploy/nginx.conf`**: 将 `listen 80;` 改为 `listen 8080;`
* **`deploy/docker-compose.yml`**: 前端映射改为 `"8080:8080"`
* **前端开发端口 (5173)**: 修改 `frontend/vite.config.ts` 中的 `server: { port: 5173 }` 属性。

### 2. 彻底修改后端端口 (FastAPI)
如果您想把后端的内部端口 8000 换成 `8888`：
* **`backend/.env`**: 修改 `PORT=8888`
* **`deploy/docker-compose.yml`**: 映射改为 `"8888:8888"`
* **`deploy/nginx.conf`**: 将反向代理上游改成 `server backend:8888;`
* **前端开发代理**: 修改 `frontend/vite.config.ts` 中的代理 `target: 'http://localhost:8888'`

### 3. 彻底修改数据库端口 (PostgreSQL / Redis)
**PostgreSQL (5432 改 5433)**:
* `deploy/docker-compose.yml`: 为 postgres 增加环境变量 `PGPORT=5433`，并在 command 里指定端口。
* `deploy/.env` 和 `backend/.env`: 把里面所有的数据库连接串里的 `5432` 改为 `5433`。
* `backend/app/core/config.py`: 修改默认 `DATABASE_URL` 的端口。

**Redis (6379 改 6380)**:
* `deploy/docker-compose.yml`: 为 redis 修改 command 如 `command: redis-server --port 6380`。
* `deploy/.env` 和 `backend/.env`: 将 Redis 连接串中的 `6379` 改为 `6380`。

### 4. 彻底修改 MinIO 端口 (9000/9001)
* `deploy/docker-compose.yml`: 修改 MinIO 的 `command: server /data --console-address ":19001" --address ":19000"`。
* `backend/.env`: 修改 `MINIO_ENDPOINT=minio:19000`。
* `deploy/nginx.conf`: 修改 MinIO 的反代路径为 `proxy_pass http://minio:19000/ppap-files/;` 以及 `proxy_set_header Host minio:19000;`。
* `frontend/src/api/files.ts`: 把拦截替换 URL 里的 `http://minio:9000` 字符串改为 `http://minio:19000`。

---

## 结论

修改端口优先选择**推荐做法**：仅修改 `docker-compose.yml` 左侧的宿主机映射端口。这就像是换个门牌号，不用把里面的房子全拆了重建，安全且省心！
