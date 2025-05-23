from fastapi import HTTPException
from utils.database import get_db
from models.account import Account, Transaction
from typing import Optional, List, Dict
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError
import logging
from contextlib import contextmanager
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.orm import Session

# 加载环境变量
load_dotenv()

# 配置日志记录器
logger = logging.getLogger(__name__)

@contextmanager
def db_session():
    """带错误处理的数据库会话上下文管理器"""
    db = next(get_db())
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"数据库操作回滚，原因：{str(e)}", exc_info=True)
        raise
    finally:
        db.close()

# 核心业务逻辑
def update_balance(user_id: int, amount: float, trans_type: str, desc: str):
    logger.info(
        f"开始更新余额 | 用户：{user_id} | 类型：{trans_type} | 金额：{amount} | 描述：{desc}"
    )
    try:
        with db_session() as db:
            # 将 float 转换为 Decimal
            amount_decimal = Decimal(str(amount))
            
            # 检查并更新余额
            account = db.query(Account).filter(
                Account.user_id == user_id
            ).with_for_update().first()
            
            if not account or account.balance + amount_decimal < 0:
                raise Exception("Insufficient balance or account not found")
            
            # 更新余额
            account.balance += amount_decimal
            
            # 记录交易
            transaction = Transaction(
                account_id=account.id,
                amount=amount_decimal,
                transaction_type=trans_type,
                balance_after=account.balance,
                description=desc
            )
            db.add(transaction)
            
            return float(account.balance)
                
    except Exception as e:
        logger.error(f"Error updating balance: {str(e)}")
        raise

def get_balance_by_user_id(user_id: str) -> Dict:
    """获取用户余额"""
    try:
        with db_session() as db:
            account = db.query(Account).filter(Account.user_id == user_id).first()
            if not account:
                raise Exception("Account not found")
            return {"balance": float(account.balance)}
    except Exception as e:
        logging.error(f"Error getting balance: {str(e)}")
        raise

def get_account_by_user_id(user_id: str) -> Optional[Account]:
    """根据用户ID获取账户"""
    db = next(get_db())
    return db.query(Account).filter(Account.user_id == user_id).first()

def list_transactions(
    user_id: str,
    page: int = 1,
    page_size: int = 10
) -> List[Transaction]:
    """分页获取交易记录"""
    logger.debug(f"开始查询账户 | 用户：{user_id}")
    db = next(get_db())

    try:
        # 查询账户
        account = db.query(Account).filter(Account.user_id == user_id).first()
        if not account:
            logger.warning(f"账户不存在 | 用户：{user_id}")
            raise HTTPException(status_code=404, detail="账户不存在")

        logger.debug(f"查询交易记录 | 账户ID：{account.id} | 页码：{page} | 每页大小：{page_size}")
        transactions = (
            db.query(Transaction)
            .filter(Transaction.account_id == account.id)
            .order_by(Transaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        logger.debug(f"成功查询到交易记录 | 账户ID：{account.id} | 记录数：{len(transactions)}")
        return transactions

    except SQLAlchemyError as e:
        logger.error(
            f"数据库查询失败 | 错误类型：{type(e).__name__} | 详情：{str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        logger.error(
            f"未知错误 | 错误类型：{type(e).__name__} | 详情：{str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="服务器内部错误")

def pre_charge_balance(user_id: int, amount: float, task_id: str) -> None:
    """预扣用户余额"""
    try:
        with db_session() as db:
            # 检查余额是否足够
            account = db.query(Account).filter(
                Account.user_id == user_id,
                Account.balance >= amount
            ).with_for_update().first()
            
            if not account:
                raise Exception("Insufficient balance")
            
            # 创建预扣记录
            db.execute(
                text("""
                INSERT INTO pre_charges (user_id, amount, task_id, status)
                VALUES (:user_id, :amount, :task_id, 'pending')
                """),
                {
                    "user_id": user_id,
                    "amount": amount,
                    "task_id": task_id
                }
            )
            
    except Exception as e:
        logging.error(f"Error pre-charging balance: {str(e)}")
        raise

def refund_balance(user_id: int, amount: float, task_id: str) -> None:
    """退还预扣的余额"""
    try:
        with db_session() as db:
            # 检查预扣记录是否存在且状态为pending
            pre_charge = db.execute(
                text("""
                SELECT id FROM pre_charges 
                WHERE user_id = :user_id 
                AND task_id = :task_id 
                AND status = 'pending'
                FOR UPDATE
                """),
                {
                    "user_id": user_id,
                    "task_id": task_id
                }
            ).first()
            
            if not pre_charge:
                raise Exception("Pre-charge record not found or already processed")
            
            # 更新预扣记录状态
            db.execute(
                text("""
                UPDATE pre_charges 
                SET status = 'refunded', refunded_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """),
                {"id": pre_charge[0]}
            )
            
    except Exception as e:
        logging.error(f"Error refunding balance: {str(e)}")
        raise