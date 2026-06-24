-- 数据库迁移脚本：为现有的 PostgreSQL 数据库追加在线防伪校验枚举值
-- 在已有部署的系统中，由于 module_type 被定义为严格的 ENUM，新增代码枚举后需手动执行此语句。
-- (注：如果是全新部署且由 SQLAlchemy 自动构建表结构，则不需要执行此脚本)

ALTER TYPE moduletype ADD VALUE IF NOT EXISTS 'online_verification';

-- 为 users 表添加 password_hash 列（用于密码登录验证）
-- 已有用户的 password_hash 为 NULL，需通过管理员设置密码后才能登录
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- 为 verification_rules 表添加 module_id 列（规则直接关联校验模块）
ALTER TABLE verification_rules ADD COLUMN IF NOT EXISTS module_id UUID REFERENCES verification_modules(id);

-- 为 severity 枚举添加 reference 值（咨询性检查：运行并报告，但不计入评分）
ALTER TYPE severity ADD VALUE IF NOT EXISTS 'reference';
