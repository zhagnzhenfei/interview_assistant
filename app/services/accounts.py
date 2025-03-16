from fastapi import HTTPException
from utils.database import get_db
from models.account import Account, Transaction
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError
import logging
from contextlib import contextmanager

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
def update_balance(user_id: str, amount: float, trans_type: str, desc: str):
    logger.info(
        f"开始更新余额 | 用户：{user_id} | 类型：{trans_type} | 金额：{amount} | 描述：{desc}"
    )
    try:
        with db_session() as db:
            # 使用行锁查询账户
            account = db.query(Account)\
                      .filter(Account.user_id == user_id)\
                      .with_for_update()\
                      .first()
                      
            if not account:
                logger.warning(f"账户不存在 | 用户：{user_id}")
                raise HTTPException(status_code=404, detail="账户不存在")

            # 计算新余额
            amount_decimal = Decimal(str(amount))  # 注意：先转str避免浮点精度问题

            # 计算新余额
            new_balance = account.balance + amount_decimal
            logger.debug(
                f"余额计算 | 原余额：{account.balance} | 变动金额：{amount} | 新余额：{new_balance}"
            )

            # 余额校验（重要！恢复注释掉的校验）
            if new_balance < Decimal('0'):
                logger.error(
                    f"余额不足 | 用户：{user_id} | 当前余额：{account.balance} | 尝试扣费：{amount}"
                )
                raise HTTPException(status_code=400, detail="余额不足")

            # 更新账户余额
            account.balance = new_balance
            logger.debug(f"账户余额已更新 | 用户：{user_id} | 新余额：{new_balance}")

            # 记录交易
            transaction = Transaction(
                account_id=account.id,  
                amount=abs(amount_decimal),
                transaction_type=trans_type,
                balance_after=new_balance,
                description=desc
            )
            db.add(transaction)
            logger.debug(f"交易记录已创建 | 交易ID：{transaction.id}")

            return float(new_balance)
            
    except HTTPException as he:
        # 已知业务异常直接抛出
        logger.warning(f"业务异常 | {he.detail}")
        raise
    except SQLAlchemyError as se:
        logger.critical(
            f"数据库操作失败 | 错误类型：{type(se).__name__} | 详细信息：{str(se)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="数据库操作失败")
    except Exception as e:
        logger.error(
            f"未知错误 | 错误类型：{type(e).__name__} | 详细信息：{str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="服务器内部错误")


def get_balance_by_user_id(user_id: str) -> Optional[Account]:
    """根据用户ID获取账户"""
    db = next(get_db())
    account = db.query(Account).filter(Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")
    
 
    return {"balance": float(account.balance)}

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