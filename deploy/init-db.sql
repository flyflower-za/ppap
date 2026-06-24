-- PPAP File Verification Platform
-- Database Initialization Script

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types first
CREATE TYPE userrole AS ENUM ('ADMIN', 'MANAGER', 'USER');
CREATE TYPE filetype AS ENUM ('PRODUCTION_PLAN', 'QUALITY_REPORT', 'PURCHASE_ORDER', 'SUPPLIER_QUALIFICATION', 'PRODUCT_SPECIFICATION', 'OTHER');
CREATE TYPE filestatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'WARNING');
CREATE TYPE taskstatus AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED');
CREATE TYPE notificationtype AS ENUM ('SUCCESS', 'ERROR', 'WARNING', 'INFO');
CREATE TYPE severity AS ENUM ('warning', 'fail', 'reference');

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    department VARCHAR(255),
    avatar_url VARCHAR(500),
    sso_provider VARCHAR(50),
    sso_id VARCHAR(255),
    ldap_dn VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    email_notifications_enabled BOOLEAN DEFAULT true,
    notification_on_complete BOOLEAN DEFAULT true,
    notification_on_failure BOOLEAN DEFAULT true,
    daily_summary_enabled BOOLEAN DEFAULT false,
    role userrole NOT NULL DEFAULT 'USER',
    ad_groups VARCHAR(1000),
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_sso_id ON users(sso_id);

-- Files table
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    file_type filetype DEFAULT 'OTHER',
    page_count INTEGER,
    status filestatus DEFAULT 'PENDING',
    verification_progress INTEGER DEFAULT 0,
    verification_model VARCHAR(100),
    verification_result TEXT,
    pass_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    pass_rate INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    uploaded_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP,
    will_delete_at TIMESTAMP
);

CREATE INDEX idx_files_uploaded_by ON files(uploaded_by);
CREATE INDEX idx_files_status ON files(status);
CREATE INDEX idx_files_uploaded_at ON files(uploaded_at);
CREATE INDEX idx_files_file_type ON files(file_type);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    task_type VARCHAR(50) DEFAULT 'verify',
    status taskstatus DEFAULT 'PENDING',
    progress INTEGER DEFAULT 0,
    current_step VARCHAR(255),
    error_message TEXT,
    celery_task_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result TEXT
);

CREATE INDEX idx_tasks_file_id ON tasks(file_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_celery_task_id ON tasks(celery_task_id);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type notificationtype DEFAULT 'INFO',
    title VARCHAR(255) NOT NULL,
    message TEXT,
    link VARCHAR(500),
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

-- Notes table
CREATE TABLE IF NOT EXISTS notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notes_file_id ON notes(file_id);
CREATE INDEX idx_notes_author_id ON notes(author_id);

-- Insert default admin user (password: admin123)
-- Password hash is bcrypt hash of 'admin123'
INSERT INTO users (id, email, full_name, is_active, is_admin, role, password_hash)
VALUES (
    '01234567-0123-0123-0123-0123456789ab',
    'admin@example.com',
    'System Administrator',
    true,
    true,
    'ADMIN',
    '$2b$12$NdCnV7GiVsVixu18DzGsmeMlD1aP4Tz9B87nuc7gnVOkM0rGhyeqy'
) ON CONFLICT (email) DO NOTHING;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
