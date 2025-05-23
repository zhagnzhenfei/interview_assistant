from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base
import enum

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    REFUNDED = "refunded"

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(36), unique=True, index=True)
    product_name = Column(String(255))
    amount = Column(Float)
    currency = Column(String(10))
    status = Column(Enum(OrderStatus, name="order_status", values_callable=lambda x: [e.value for e in x]), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    stripe_session_id = Column(String(255))
    paid_at = Column(DateTime, nullable=True)
    payment_url = Column(Text)
    invite_code = Column(String(50), nullable=True)
    original_amount = Column(Float, nullable=True)
    
    # 关联
    user = relationship("User", back_populates="orders")
    payment_history = relationship("PaymentHistory", back_populates="order")

class PaymentHistory(Base):
    __tablename__ = "payment_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    amount = Column(Float)
    currency = Column(String(10))
    status = Column(String(50))
    payment_method = Column(String(50))
    transaction_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    order = relationship("Order", back_populates="payment_history")