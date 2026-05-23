# PDF文件自动清理功能说明

## 功能概述

已成功实现PDF文件自动清理功能，系统可以根据配置的天数自动清除过期的PDF文件，确保存储空间的有效利用。

## 实现内容

### 1. 系统设置模型和API

**新增Schema类**：`FileRetentionSettings`
- `retention_days`: 文件保留天数（默认30天，范围1-3650天）
- `auto_cleanup_enabled`: 是否启用自动清理（默认True）
- `cleanup_hour`: 每天清理时间（默认凌晨2点，范围0-23）

**新增API端点**：
- `GET /api/settings/file-retention` - 获取文件保留设置
- `POST /api/settings/file-retention` - 更新文件保留设置
- `POST /api/settings/file-retention/cleanup-now` - 立即手动触发清理

### 2. Celery清理任务

**新增文件**：`backend/app/tasks/cleanup_tasks.py`

**任务功能**：
- 从数据库读取 `file_retention_settings` 配置
- 查找所有符合条件的过期文件：
  - `will_delete_at` 字段已过期的文件
  - 或上传时间超过 `retention_days` 天的文件
- 从MinIO删除实际文件
- 在数据库中标记为已删除
- 记录清理统计信息（删除数量、失败数量、释放空间）

### 3. 定时调度配置

**更新文件**：`backend/app/tasks/scheduler_tasks.py`

- 清理任务每天凌晨2点自动执行
- 任务名称：`app.tasks.cleanup_tasks.cleanup_expired_files`

### 4. 依赖更新

**更新文件**：`backend/app/tasks/celery_app.py`

- 添加了 `app.tasks.cleanup_tasks` 模块导入

## 使用方法

### 1. 配置文件保留设置

```bash
# 获取当前设置
curl -X GET http://localhost:8000/api/settings/file-retention \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# 更新设置（示例：保留90天，每天凌晨3点清理）
curl -X POST http://localhost:8000/api/settings/file-retention \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "retention_days": 90,
    "auto_cleanup_enabled": true,
    "cleanup_hour": 3
  }'
```

### 2. 手动触发清理

```bash
# 立即执行清理任务
curl -X POST http://localhost:8000/api/settings/file-retention/cleanup-now \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

响应示例：
```json
{
  "message": "文件清理任务已启动",
  "task_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab"
}
```

## 清理逻辑

### 文件过期条件

文件在以下情况下会被标记为过期并清理：

1. **will_delete_at字段已过期**：文件的 `will_delete_at` 时间早于当前时间
2. **超过保留天数**：文件上传时间 + retention天数 > 当前时间

### 清理流程

1. 读取系统配置（如果配置不存在则使用默认值）
2. 检查是否启用自动清理
3. 查询所有未删除且过期的文件
4. 逐个删除：
   - 从MinIO删除文件
   - 更新数据库记录（设置 `is_deleted=True`，`deleted_at=当前时间`）
5. 返回清理统计信息

### 错误处理

- 单个文件删除失败不会影响其他文件的清理
- 失败的文件会被记录在日志中
- 最终返回成功和失败的文件数量统计

## 数据库架构

**已有字段**（无需迁移）：

```python
class File(Base):
    will_delete_at = Column(DateTime)  # 自动删除时间
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)
```

**系统设置存储**：

```python
class Setting(Base):
    key = "file_retention_settings"
    value = '{"retention_days": 30, "auto_cleanup_enabled": true, "cleanup_hour": 2}'
```

## 部署要求

确保以下服务正在运行：

1. **PostgreSQL** - 存储文件元数据和配置
2. **Redis** - Celery消息队列
3. **MinIO** - 文件存储
4. **Celery Worker** - 执行清理任务
   ```bash
   celery -A app.tasks.celery_app worker --loglevel=info
   ```
5. **Celery Beat** - 定时调度
   ```bash
   celery -A app.tasks.celery_app beat --loglevel=info
   ```

## 日志监控

清理任务会产生详细的日志输出：

```
[INFO] Starting file cleanup task
[INFO] Loaded retention settings: 30 days, auto_cleanup=True
[INFO] Found 42 files to delete
[INFO] Deleted file from MinIO: files/user123/202501/file-abc.pdf
[INFO] Marked file as deleted: file-abc - sample.pdf
[INFO] Cleanup completed: 42 files deleted, 0 failed, 52428800 bytes freed
```

## 安全考虑

1. **权限控制**：所有API端点都需要管理员权限
2. **软删除**：数据库记录先标记删除，MinIO文件后删除
3. **事务保护**：数据库更新使用事务确保一致性
4. **错误恢复**：支持多次执行清理任务，幂等性保证

## 性能优化建议

1. **批量操作**：对于大量文件，可以考虑分批处理
2. **异步删除**：MinIO删除操作可以考虑异步执行
3. **索引优化**：确保 `will_delete_at`、`uploaded_at`、`is_deleted` 字段有索引
4. **监控告警**：建议添加清理任务失败的告警通知

## 未来扩展

可能的改进方向：

1. 按文件类型设置不同的保留策略
2. 添加清理前的邮件通知
3. 支持文件归档（移动到冷存储而不是删除）
4. 添加清理统计面板和可视化
5. 支持按用户/部门设置保留策略

## 测试建议

### 手动测试步骤

1. 创建测试文件（已知上传时间）
2. 设置较短的保留天数（如1天）
3. 手动触发清理任务
4. 验证：
   - MinIO中的文件已删除
   - 数据库中 `is_deleted=True`
   - `deleted_at` 已设置
5. 检查清理统计信息

### 单元测试

建议添加以下测试：

- 清理任务基本功能测试
- 边界条件测试（无文件、无过期文件等）
- 错误处理测试（MinIO不可用等）
- 权限控制测试
- 配置验证测试

## 文件清单

- `backend/app/api/settings.py` - 新增文件保留设置API
- `backend/app/tasks/cleanup_tasks.py` - 新增清理任务实现
- `backend/app/tasks/scheduler_tasks.py` - 更新定时调度配置
- `backend/app/tasks/celery_app.py` - 更新模块导入
- `backend/app/models/setting.py` - 已有设置模型（无需修改）
- `backend/app/models/file.py` - 已有文件模型（无需修改）
