from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from router import chat_rt, user_rt, account_rt, order_rt, invite_rt, sms_auth_rt
import os
from dotenv import load_dotenv  # 需要安装 python-dotenv
from services.redis_service import redis_service
from contextlib import asynccontextmanager

# 加载环境变量
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时连接Redis
    await redis_service.connect()
    yield
    # 关闭时断开Redis连接
    await redis_service.disconnect()

app = FastAPI(lifespan=lifespan)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_rt.router)
app.include_router(user_rt.router)
app.include_router(account_rt.router)
app.include_router(order_rt.router)
app.include_router(invite_rt.router)

# 注册短信验证码认证路由
app.include_router(
    sms_auth_rt.router,
    tags=["SMS Authentication"]
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 配置静态文件目录
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploaded_images")  # 设置默认值
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    