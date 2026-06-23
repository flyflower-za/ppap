# MinIO 对象存储与文件生命周期管理指南

PPAP 平台使用 MinIO 作为私有对象存储服务，用于存放用户上传的待校验 PDF 报告、比对基准原件以及分析过程中产生的临时文件。为了防止存储空间爆满，合理规划文件生命周期至关重要。

---

## 1. 存储桶 (Bucket) 规划与访问控制

部署时，系统会自动执行初始化脚本，在 MinIO 中创建默认存储桶并配置访问权限：

| 存储桶名称 | 访问权限策略 | 存放内容说明 |
|------------|--------------|--------------|
| `ppap-files` | `Public` (公共只读) | 上传的待检测 PDF、解析提取的图表以及比对基准件 |

*注：虽然权限设为公共只读，但文件的 Object Key 采用 UUID 或哈希命名，具有极高的不可猜测性，保证了业务数据的安全性。*

---

## 2. 临时比对文件的生命周期管理 (Lifecycle)

平台运行一段时间后，会累积大量的待检测件与历史比对结果，这些数据在校验完成后往往不再需要长期保留。

我们可以配置 MinIO 自动清理策略，以定期释放磁盘空间。

### 推荐做法：通过 mc 客户端配置生命周期规则 (Lifecycle Rule)

通过 Docker Compose 部署的 MinIO 可以直接利用 `minio/mc` 客户端镜像，向存储桶添加生命周期策略。

#### 示例：自动删除 30 天前上传的所有临时文件

在宿主机上运行以下命令，为 `ppap-files` 桶中的 `temp/` 路径（临时缓存目录）配置 30 天自动过期的生命周期规则：

```bash
# 启动临时容器运行 mc 客户端配置生命周期规则
docker run --rm --network container:ppap-minio --entrypoint /bin/sh minio/mc -c "
  mc alias set ppapminio http://localhost:9000 minioadmin minioadmin && \
  mc ilm add --expiry-days 30 --prefix 'temp/' ppapminio/ppap-files
"
```

*说明：*
*   `--expiry-days 30`：设定文件保留时间为 30 天，超出后自动被 MinIO 物理删除。
*   `--prefix 'temp/'`：只对 `temp/` 前缀下的临时比对文件生效，避免误删重要的“比对基准原件”(`base/`)。

---

## 3. 手动磁盘空间清理与维护

若需立即释放磁盘空间，可通过以下方式进行清理：

### 方法一：通过 MinIO 控制台界面 (Web UI)
1.  浏览器访问 `http://localhost:9001` 并使用管理员账号（默认 `minioadmin / minioadmin`）登录。
2.  点击左侧导航栏的 **Object Browser**，进入 `ppap-files` 存储桶。
3.  勾选不需要的文件夹，点击右上角 **Delete** 进行安全删除。

### 方法二：命令行一键清空临时目录
```bash
docker run --rm --network container:ppap-minio --entrypoint /bin/sh minio/mc -c "
  mc alias set ppapminio http://localhost:9000 minioadmin minioadmin && \
  mc rm --recursive --force ppapminio/ppap-files/temp/
"
```
