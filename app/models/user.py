from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(100), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=True)
    openid = Column(String(64), unique=True, nullable=True)  # 新增 openid 字段
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    
    # 添加与 Order 的关系
    orders = relationship("Order", back_populates="user")