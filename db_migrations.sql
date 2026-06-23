-- 数据库迁移脚本：为现有的 PostgreSQL 数据库追加在线防伪校验枚举值
-- 在已有部署的系统中，由于 module_type 被定义为严格的 ENUM，新增代码枚举后需手动执行此语句。
-- (注：如果是全新部署且由 SQLAlchemy 自动构建表结构，则不需要执行此脚本)

ALTER TYPE moduletype ADD VALUE IF NOT EXISTS 'online_verification';
