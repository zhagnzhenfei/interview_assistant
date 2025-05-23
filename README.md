# interview_assistant

## 数据库部署

```bash
docker run -d \
  --name gsk_pg \
  -e POSTGRES_PASSWORD=pg123456 \
  -e POSTGRES_USER=postgre \
  -e POSTGRES_DB=gsk \
  -v pg_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:15-alpine
```

## Redis 部署

```bash
docker run -d \
  --name gsk_redis \
  -p 6379:6379 \
  redis:7-alpine \
  --requirepass "redis123456"
```

## 功能特性

- 用户注册与登录
- 手机验证码登录 (新功能 - 见 [SMS验证码登录文档](SMS_Verification_README.md))
- 账户管理
- 订单处理

## 手机验证码登录

该项目新增了基于手机号和短信验证码的登录注册功能。详细信息请参考：

- [开发计划说明书](SMS_Verification_Development_Plan.md)
- [功能详细文档](SMS_Verification_README.md)

### 主要特点

- 手机号验证与登录
- 短信验证码发送
- 自动注册新用户
- 频率限制与安全保护
- Redis存储验证码

## 项目构建与运行

```bash
# 克隆项目
git clone <repo-url>

# 安装依赖
cd app
pip install -r requirements.txt

# 运行数据库迁移
psql -U postgre -d gsk -f migrations/add_phone_number_to_users.sql

# 启动服务
cd app
uvicorn app_main:app --reload
```

## API文档

启动服务后，可以访问 Swagger UI 文档：

```
http://localhost:8000/docs
```

## 环境变量配置

项目依赖的环境变量在 `.env` 文件中配置：

```
DATABASE_URL=postgresql://postgre:pg123456@localhost:5432/gsk
JWT_SECRET_KEY=your-jwt-secret-key
REDIS_URL=redis://:redis123456@localhost:6379/0
SMS_API_KEY=your-sms-api-key
SMS_API_SECRET=your-sms-api-secret
```