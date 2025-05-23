from pydantic import BaseModel
from datetime import datetime

class AccountCreate(BaseModel):
    user_id: str

class RechargeRequest(BaseModel):
    amount: float
    description: str = "账户充值"

class DeductRequest(BaseModel):
    amount: float
    description: str = "账户扣费"

class TransactionResponse(BaseModel):
    id: int
    account_id: int
    amount: float
    transaction_type: str
    balance_after: float
    created_at: datetime
    description: str