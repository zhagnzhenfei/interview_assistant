from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    transaction_type = Column(String(10), nullable=False)
    balance_after = Column(Numeric(15, 2), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 关系
    account = relationship("Account", back_populates="transactions") 