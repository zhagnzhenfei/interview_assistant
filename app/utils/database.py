from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
import os
from dotenv import load_dotenv
from sqlalchemy.pool import QueuePool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,  # 连接池大小
    max_overflow=10,  # 最大溢出连接数
    pool_timeout=30,  # 连接超时时间
    pool_recycle=1800,  # 连接回收时间（30分钟）
    pool_pre_ping=True  # 在使用连接前先测试连接是否有效
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)