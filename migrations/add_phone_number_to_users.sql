-- 添加 phone_number 字段到 users 表
ALTER TABLE users ADD COLUMN phone_number VARCHAR(20) UNIQUE;

-- 为 phone_number 字段添加索引
CREATE INDEX idx_users_phone_number ON users (phone_number);

-- 更新已有用户记录，确保兼容性（可选，根据实际情况调整）
-- UPDATE users SET phone_number = CONCAT('temp_', id) WHERE phone_number IS NULL;

-- 更新 phone_number 为非空的注释（不是约束，只是文档说明）
COMMENT ON COLUMN users.phone_number IS '用户手机号，用于验证码登录';

-- 修改 password_hash 字段为可为空
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL; 