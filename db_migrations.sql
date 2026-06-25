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

-- 为 users 表添加 username 列（用于用户名/邮箱双登录）
-- 已有用户的 username 为空，将自动从 email 前缀填充
ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(255);
-- 先填充存量用户的 username（取 email @ 前缀）
UPDATE users SET username = LOWER(SPLIT_PART(email, '@', 1)) WHERE username IS NULL OR username = '';
-- 处理冲突：重复前缀添加数字后缀
DO $$
DECLARE
    dup RECORD;
    new_username VARCHAR(255);
    suffix INT;
BEGIN
    FOR dup IN SELECT id, email FROM users WHERE username IN (
        SELECT username FROM users GROUP BY username HAVING COUNT(*) > 1
    ) ORDER BY created_at
    LOOP
        suffix := 2;
        LOOP
            new_username := LOWER(SPLIT_PART(dup.email, '@', 1)) || suffix;
            EXIT WHEN NOT EXISTS (SELECT 1 FROM users WHERE username = new_username AND id != dup.id);
            suffix := suffix + 1;
        END LOOP;
        UPDATE users SET username = new_username WHERE id = dup.id AND username = LOWER(SPLIT_PART(dup.email, '@', 1));
    END LOOP;
END $$;
-- 最后设置 NOT NULL + UNIQUE
ALTER TABLE users ALTER COLUMN username SET NOT NULL;
ALTER TABLE users ADD CONSTRAINT users_username_unique UNIQUE (username);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- 为 notes 表添加 author_name 列（用于仲裁记录中显示用户名，避免关联查询）
ALTER TABLE notes ADD COLUMN IF NOT EXISTS author_name VARCHAR(255);
