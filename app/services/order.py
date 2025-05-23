from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from models.order import Order, PaymentHistory, OrderStatus
from datetime import datetime
import stripe
from uuid import uuid4
import os
import logging
import redis
from collections import deque
import dotenv
from services.accounts import update_balance
from typing import Optional

dotenv.load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)

# Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "code_redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "redis123456")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# 初始化 Redis 连接
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=REDIS_DB,
    decode_responses=True
)

# 用于存储最近的事件（用于监控和调试）
recent_events = deque(maxlen=1000)

async def is_event_processed(event_id: str) -> bool:
    """检查事件是否已处理"""
    return bool(redis_client.exists(f"stripe:event:{event_id}"))

async def mark_event_processed(event_id: str, event_type: str):
    """标记事件为已处理"""
    redis_client.setex(
        f"stripe:event:{event_id}",
        24 * 60 * 60,  # 24小时过期
        event_type
    )
    recent_events.append({
        "id": event_id,
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat()
    })

async def log_payment_history(
    db: Session,
    order_id: int,
    amount: float,
    currency: str,
    status: str,
    payment_method: str,
    transaction_id: str
):
    """记录支付历史"""
    payment_history = PaymentHistory(
        order_id=order_id,
        amount=amount,
        currency=currency,
        status=status,
        payment_method=payment_method,
        transaction_id=transaction_id
    )
    db.add(payment_history)
    db.commit()

async def handle_checkout_completed(
    session: dict,
    db: Session,
    background_tasks: BackgroundTasks,
    event_id: str
):
    """处理支付成功事件"""
    try:
        order_number = session["metadata"]["order_number"]
        user_id = int(session["metadata"]["user_id"])
        amount = float(session["amount_total"]) / 100  # 转换为实际金额
        original_amount = float(session["metadata"]["original_amount"])
        
        # 更新订单状态
        order = db.query(Order).filter(Order.order_number == order_number).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        order.status = OrderStatus.PAID
        order.paid_at = datetime.utcnow()
        db.commit()
        
        # 增加用户余额（使用原始金额，而不是实际支付金额）
        background_tasks.add_task(
            update_balance,
            user_id,
            original_amount,  # 使用原始金额
            "充值",
            f"订单 {order_number} 支付成功"
        )
        
        # 记录支付历史
        background_tasks.add_task(
            log_payment_history,
            db,
            order.id,
            amount,
            session["currency"],
            "succeeded",
            "stripe",
            session["id"],
            event_id
        )
        
        logger.info(f"Payment completed for order {order_number}")
        
    except Exception as e:
        logger.error(f"Error handling checkout completed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_checkout_expired(
    session: dict,
    db: Session,
    background_tasks: BackgroundTasks,
    event_id: str
):
    """处理会话过期事件"""
    try:
        order_number = session.get("metadata", {}).get("order_number")
        amount_total = session.get("amount_total")
        currency = session.get("currency")
        
        logger.info(f"Processing payment expiration for order: {order_number}")
        
        # 更新订单状态
        order = db.query(Order).filter(Order.order_number == order_number).first()
        if not order:
            logger.error(f"Order not found: {order_number}")
            return
            
        if order.status == OrderStatus.EXPIRED:
            logger.warning(f"Order {order_number} already marked as expired")
            return
            
        order.status = OrderStatus.EXPIRED
        db.commit()
        
        # 记录支付历史
        background_tasks.add_task(
            log_payment_history,
            db,
            order.id,
            amount_total / 100,
            currency,
            "expired",
            "stripe",
            session["id"]
        )
        
        logger.info(f"Payment session expired for order: {order_number}")
        
    except Exception as e:
        logger.error(f"Error processing checkout expired: {str(e)}", exc_info=True)
        raise

async def handle_payment_intent_succeeded(
    session: dict,
    db: Session,
    background_tasks: BackgroundTasks,
    event_id: str
):
    """处理支付意向成功事件"""
    try:
        payment_intent = session.get("id")
        amount = session.get("amount")
        currency = session.get("currency")
        
        logger.info(f"Processing payment intent success: {payment_intent}")
        
        # 查找相关订单
        order = db.query(Order).filter(Order.stripe_session_id == payment_intent).first()
        if not order:
            logger.error(f"Order not found for payment intent: {payment_intent}")
            return
            
        # 记录支付历史
        background_tasks.add_task(
            log_payment_history,
            db,
            order.id,
            amount / 100,
            currency,
            "succeeded",
            "stripe",
            payment_intent
        )
        
        logger.info(f"Payment intent succeeded: {payment_intent}")
        
    except Exception as e:
        logger.error(f"Error processing payment intent succeeded: {str(e)}", exc_info=True)
        raise

async def create_order(
    db: Session,
    user_id: int,
    product_name: str,
    amount: float,
    currency: str,
    background_tasks: BackgroundTasks,
    invite_code: Optional[str] = None,
    success_url: str = None,
    cancel_url: str = None
) -> Order:
    """创建订单"""
    try:
        # 生成订单号
        order_number = str(uuid4())
        domain = os.getenv("DOMAIN")

        # 验证邀请码
        final_amount = amount
        if invite_code:
            valid_codes = [code.strip() for code in os.getenv("VALID_INVITE_CODES", "").split(",") if code.strip()]
            if invite_code in valid_codes:
                final_amount = amount / 2  # 半价优惠
            else:
                raise HTTPException(status_code=400, detail="Invalid invite code")

        # 创建 Stripe 会话
        session = stripe.checkout.Session.create(
            payment_method_types=["card", "alipay"],
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "unit_amount": int(final_amount * 100),
                        "product_data": {
                            "name": product_name
                        }
                    },
                    "quantity": 1
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "order_number": order_number,
                "user_id": user_id,
                "invite_code": invite_code,
                "original_amount": amount,
                "final_amount": final_amount
            }
        )

        # 创建订单记录
        logger.info(f"Creating order with status: {OrderStatus.PENDING}")
        logger.info(f"Status type: {type(OrderStatus.PENDING)}")
        logger.info(f"Status value: {OrderStatus.PENDING.value}")
        logger.info(f"Payment URL: {session.url}")
        
        order = Order(
            order_number=order_number,
            product_name=product_name,
            amount=final_amount,           # 实际支付金额（如果有邀请码则是半价）
            original_amount=amount,        # 原始金额
            currency=currency,
            status=OrderStatus.PENDING,
            user_id=user_id,
            stripe_session_id=session.id,
            payment_url=session.url,
            invite_code=invite_code
        )
        
        logger.info(f"Order object status: {order.status}")
        logger.info(f"Order object status type: {type(order.status)}")
        logger.info(f"Order object status value: {order.status.value if hasattr(order.status, 'value') else order.status}")
        logger.info(f"Order payment URL: {order.payment_url}")
        
        db.add(order)
        db.commit()

        # 记录支付历史
        background_tasks.add_task(
            log_payment_history,
            db,
            order.id,
            final_amount,  # 使用实际支付金额记录支付历史
            currency,
            "pending",
            "stripe",
            session.id
        )

        logger.info(f"Created order {order_number} for user {user_id}")
        return order
        
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

async def get_order_by_number(
    db: Session,
    order_number: str,
    user_id: int
) -> Order:
    """获取订单信息"""
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    
    return order

async def get_order_payment_history(
    db: Session,
    order_number: str,
    user_id: int
) -> list[PaymentHistory]:
    """获取订单支付历史"""
    order = await get_order_by_number(db, order_number, user_id)
    return order.payment_history

async def get_recent_webhook_events():
    """获取最近的webhook事件（用于监控和调试）"""
    return {
        "events": list(recent_events),
        "total_processed": len(recent_events)
    } 