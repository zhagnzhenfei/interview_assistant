from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Numeric, DateTime
from datetime import datetime

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), unique=True, index=True)
    balance = Column(Numeric(15, 2), default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, index=True)
    amount = Column(Numeric(15, 2))
    transaction_type = Column(String(10))
    balance_after = Column(Numeric(15, 2))
    created_at = Column(DateTime, default=datetime.now)
    description = Column(String(255))