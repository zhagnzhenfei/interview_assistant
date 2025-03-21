from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgre:pg123456@localhost:5432/gsk")
engine = create_engine(DATABASE_URL)
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