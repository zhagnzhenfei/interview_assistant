#!/bin/bash

# 等待PostgreSQL启动
echo "Waiting for PostgreSQL to start..."
while ! nc -z code_pg 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

# 运行数据库迁移
echo "Running database migrations..."
alembic upgrade head

# 启动应用
echo "Starting application..."
uvicorn app_main:app --host 0.0.0.0 --port 8000 