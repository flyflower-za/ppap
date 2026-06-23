# 测试环境与集成测试运行指南 (Testing and Integration Guide)

为了保障 PPAP 平台的各引擎算子和 API 接口在代码迭代后的稳定性，项目内置了完整的单元测试与集成测试集。本指南介绍如何在本地或开发环境中正确搭建依赖并运行这些测试。

---

## 1. 测试依赖环境准备

后端测试包含数据库交互测试和引擎离线计算测试。部分 API 测试依赖于可用的 PostgreSQL 和 Redis 实例。

### 推荐方法：利用 Docker Compose 启动最小化测试依赖
您无需完整启动包含 Web 前端和后台 Worker 的全套容器，只需启动数据库和缓存层即可：

```bash
# 切换到 deploy 目录
cd deploy

# 仅启动数据库与 Redis 容器
docker compose up -d postgres redis
```

*注：PostgreSQL 测试连接默认会映射到宿主机的 `5435` 端口（容器内 5432），这与宿主机本地已安装的 5432 端口 PostgreSQL 避开了冲突。*

---

## 2. 后端单元与集成测试运行

PPAP 使用 `pytest` 框架对后端进行测试。

### 步骤一：激活虚拟环境并安装依赖
在后端目录下准备 Python 环境：

```bash
cd backend
# 建议使用虚拟环境 (venv / conda)
source .venv/bin/activate  # 或 conda activate ppap

# 安装开发与测试依赖
pip install -r requirements-dev.txt
```

### 步骤二：执行测试命令
可以通过不同的命令组合来执行全量或局部的测试：

```bash
# 1. 运行全量测试 (包括 API、数据库及引擎算子)
pytest tests/ -v

# 2. 仅运行引擎算子执行逻辑相关的测试 (不依赖数据库连通，推荐频繁运行)
pytest tests/engine/ -v

# 3. 运行特定测试文件
pytest tests/engine/test_rule_execution.py -v

# 4. 运行特定测试用例
pytest tests/engine/test_rule_execution.py::test_logic_graph_variable_extraction_and_diff -v
```

---

## 3. 前端测试与语法检查

前端基于 Vite + Vue3 + TypeScript 构建，提供了 Lint 检查和集成校验。

```bash
cd frontend

# 安装依赖
npm install

# 1. 运行 TypeScript 类型检查
npm run type-check

# 2. 进行 ESLint 代码规范及语法检查
npm run lint
```

---

## 4. 常见测试问题与解决办法 (Troubleshooting)

#### Q1: 运行 API 测试时遇到 `OSError: Multiple exceptions: Connect call failed` 错误？
*   **原因**：API 路由集成测试在执行时会尝试连接数据库。如果 `ppap-postgres` 容器没有运行，或宿主机端口映射不正确，就会导致连接失败。
*   **解决**：确保运行了 `docker compose up -d postgres`，且 `backend/.env` 中的 `DATABASE_URL` 配置的端口指向宿主机的 `5435` 端口。

#### Q2: 算子比对 PDF 测试时抛出 `Document diff failed: too many values to unpack`？
*   **原因**：这通常是因为 Mock 代码的返回值与重构后的算子方法签名不匹配。
*   **解决**：在编写测试的 Mock 时（如 mock 提取 PDF 文本），要确保返回的元组格式正确（例如返回 `(text, page_count)` 而不是单纯的 `text` 字符串）。
