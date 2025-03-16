-- 创建 users 表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP  -- 更新时间
);

-- 账户表
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES users(id),
    balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00 CHECK (balance >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 交易记录表
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    account_id INT NOT NULL REFERENCES accounts(id),
    amount DECIMAL(15, 2) NOT NULL,
    transaction_type VARCHAR(10) NOT NULL CHECK (transaction_type IN ('充值', '扣费')),
    balance_after DECIMAL(15, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_time ON transactions(created_at);