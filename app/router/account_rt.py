from fastapi import APIRouter, HTTPException, Security
from schemas.accounts_schemas import RechargeRequest, DeductRequest, TransactionResponse
from services.accounts import update_balance, get_balance_by_user_id, list_transactions
from fastapi_jwt import JwtAuthorizationCredentials
from services.auth import access_security
from sqlalchemy.orm import Session
from utils.database import get_db
from models.order import Order, OrderStatus
from sqlalchemy import func
import logging
logger = logging.getLogger(__name__)
router = APIRouter()

################
# 查询订单状态
################
@router.get("/accounts/order_status/{order_number}")
def get_order_status(
    order_number: str,
    credentials: JwtAuthorizationCredentials = Security(access_security)
):
    """查询单个订单状态"""
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        # 获取数据库会话
        db = next(get_db())
        
        # 查询订单
        order = (
            db.query(Order)
            .filter(
                Order.order_number == order_number,
                Order.user_id == int(user_id)
            )
            .first()
        )

        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")

        # 构建返回数据
        response = {
            "order_number": order.order_number,
            "product_name": order.product_name,
            "amount": float(order.amount),  # 实际支付金额
            "original_amount": float(order.original_amount) if order.original_amount else float(order.amount),  # 原始金额
            "currency": order.currency,
            "status": order.status.value,
            "created_at": order.created_at,
            "paid_at": order.paid_at,
            "payment_url": order.payment_url,
            "invite_code": order.invite_code
        }

        logger.info(f"成功查询订单状态 | 用户：{user_id} | 订单号：{order_number}")
        return response

    except HTTPException as e:
        logger.warning(f"业务异常 | 状态码：{e.status_code} | 详情：{e.detail}")
        raise
    except Exception as e:
        logger.error(
            f"查询订单状态失败 | 错误类型：{type(e).__name__} | 详情：{str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="服务器错误")

################
# 查询账号余额
################
@router.get("/accounts/balance")
def get_balance(credentials: JwtAuthorizationCredentials = Security(access_security),):
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        return get_balance_by_user_id(user_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器错误")


################
# 查询交易记录
################

@router.get("/accounts/transactions")
def get_transactions(
    page: int = 1,
    page_size: int = 10,
    credentials: JwtAuthorizationCredentials = Security(access_security),
):
    logger.info(
        f"开始查询交易记录 | 用户：{credentials.subject.get('user_id')} | 页码：{page} | 每页大小：{page_size}"
    )
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            logger.warning("未获取到用户ID | 认证信息无效")
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        # 参数校验
        if page < 1 or page_size < 1 or page_size > 100:
            logger.warning(f"无效的分页参数 | 页码：{page} | 每页大小：{page_size}")
            raise HTTPException(status_code=400, detail="无效的分页参数")

        logger.debug(f"查询交易记录 | 用户：{user_id} | 页码：{page} | 每页大小：{page_size}")
        transactions = list_transactions(user_id, page, page_size)

        logger.info(f"成功查询到交易记录 | 用户：{user_id} | 记录数：{len(transactions)}")
        return [TransactionResponse(**t.__dict__) for t in transactions]

    except HTTPException as e:
        logger.warning(f"业务异常 | 状态码：{e.status_code} | 详情：{e.detail}")
        raise
    except Exception as e:
        logger.error(
            f"查询交易记录失败 | 错误类型：{type(e).__name__} | 详情：{str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="服务器错误")