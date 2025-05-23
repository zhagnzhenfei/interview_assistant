from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from models.order import OrderStatus


# 请求体模型
class CreateOrderRequest(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    invite_code: Optional[str] = None
    success_url: str = Field(..., description="支付成功后的跳转URL")
    cancel_url: str = Field(..., description="支付取消后的跳转URL")
    # success_url: Optional[str] = "http://localhost:8000/static/success.html"  # 默认值
    # cancel_url: Optional[str] = "http://localhost:8000/static/cancel.html"    # 默认值

class OrderResponse(BaseModel):
    id: int
    order_number: str
    product_name: str
    amount: float
    currency: str
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    user_id: int 
    stripe_session_id: Optional[str] = None
    payment_url: str
    paid_at: Optional[datetime] = None  # 设为可选字段

    class Config:
        from_attributes = True

class PaymentHistoryResponse(BaseModel):
    id: int
    order_id: int
    amount: float
    currency: str
    status: str
    payment_method: str
    transaction_id: str
    created_at: datetime

    class Config:
        from_attributes = True