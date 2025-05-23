from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # 允许从ORM模型创建

class UserLogin(BaseModel):
    username: str
    password: str

class WxLoginRequest(BaseModel):
    code: str 