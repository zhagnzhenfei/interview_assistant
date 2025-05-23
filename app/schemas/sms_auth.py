from pydantic import BaseModel, Field, validator
import re
from typing import Optional

class PhoneNumberValidator:
    @staticmethod
    def validate_phone_number(v: str) -> str:
        """验证手机号格式是否正确"""
        if not v or not isinstance(v, str):
            raise ValueError("手机号不能为空")
        
        # 验证中国大陆手机号格式：1开头的11位数字
        pattern = r'^1[3-9]\d{9}$'
        if not re.match(pattern, v):
            raise ValueError("手机号格式不正确")
        
        return v

class SMSRequest(BaseModel):
    """发送验证码请求模型"""
    phone_number: str = Field(..., description="手机号码")
    
    # 验证手机号格式
    _validate_phone = validator('phone_number')(PhoneNumberValidator.validate_phone_number)

class VerifyCodeRequest(BaseModel):
    """验证码登录请求模型"""
    phone_number: str = Field(..., description="手机号码")
    code: str = Field(..., description="验证码", min_length=4, max_length=6)
    
    # 验证手机号格式
    _validate_phone = validator('phone_number')(PhoneNumberValidator.validate_phone_number)
    
    @validator('code')
    def validate_code(cls, v):
        """验证验证码格式"""
        if not v or not isinstance(v, str):
            raise ValueError("验证码不能为空")
        
        # 验证码必须是数字
        if not v.isdigit():
            raise ValueError("验证码必须是数字")
        
        return v

class SMSResponse(BaseModel):
    """短信发送响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")

class TokenResponse(BaseModel):
    """Token响应模型"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(172800, description="有效期(秒)")  # 2天有效期 