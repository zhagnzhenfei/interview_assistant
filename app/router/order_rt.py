from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks, Security
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from utils.database import get_db
from models.order import Order
from schemas.order_schemas import CreateOrderRequest, OrderResponse, PaymentHistoryResponse
import stripe
import os
from dotenv import load_dotenv
from services.auth import access_security
from fastapi_jwt import JwtAuthorizationCredentials
import logging
from services.order import (
    create_order,
    get_order_by_number,
    get_order_payment_history,
    get_recent_webhook_events,
    is_event_processed,
    mark_event_processed,
    handle_checkout_completed,
    handle_checkout_expired,
    handle_payment_intent_succeeded
)

# 配置日志
logger = logging.getLogger(__name__)

load_dotenv()

router = APIRouter()

# 初始化 Stripe
stripe.api_key = os.getenv("TEST_STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/create-order/", response_model=OrderResponse)
async def create_order_endpoint(
    request: CreateOrderRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    credentials: JwtAuthorizationCredentials = Security(access_security)
):
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        return await create_order(
            db=db,
            user_id=int(user_id),
            product_name=request.product_name,
            amount=request.amount,
            currency=request.currency,
            background_tasks=background_tasks,
            invite_code=request.invite_code,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        )
        
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook/")
async def webhook_received(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    # 1. 验证签名
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=WEBHOOK_SECRET
        )
    except ValueError:
        logger.warning("Invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 2. 防重放攻击检查
    event_id = event["id"]
    if await is_event_processed(event_id):
        logger.info(f"Duplicate event {event_id} received")
        return JSONResponse(status_code=200, content={"status": "duplicate"})
    
    # 3. 环境验证（测试/生产隔离）
    if event["livemode"] != (os.getenv("ENV") == "production"):
        raise HTTPException(
            status_code=400,
            detail="Invalid environment"
        )

    # 4. 事件处理
    try:
        match event["type"]:
            case "checkout.session.completed":
                await handle_checkout_completed(event["data"]["object"], db, background_tasks, event_id)
            case "checkout.session.expired":
                await handle_checkout_expired(event["data"]["object"], db, background_tasks, event_id)
            case "payment_intent.succeeded":
                await handle_payment_intent_succeeded(event["data"]["object"], db, background_tasks, event_id)
            case _:
                logger.info(f"Unhandled event type: {event['type']}")
    except Exception as e:
        logger.error(f"Event processing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        # 标记事件为已处理
        await mark_event_processed(event_id, event["type"])

    return JSONResponse(status_code=200, content={"status": "success"})

# 获取最近的webhook事件（用于监控和调试）
@router.get("/webhook/events/")
async def get_recent_events():
    """获取最近的webhook事件（用于监控和调试）"""
    return await get_recent_webhook_events()

# 获取订单
@router.get("/orders/{order_number}", response_model=OrderResponse)
async def get_order(
    order_number: str,
    db: Session = Depends(get_db),
    credentials: JwtAuthorizationCredentials = Security(access_security)
):
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        return await get_order_by_number(db, order_number, int(user_id))
    except Exception as e:
        logger.error(f"Error getting order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 获取订单支付历史
@router.get("/orders/{order_number}/payment-history", response_model=list[PaymentHistoryResponse])
async def get_payment_history(
    order_number: str,
    db: Session = Depends(get_db),
    credentials: JwtAuthorizationCredentials = Security(access_security)
):
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        return await get_order_payment_history(db, order_number, int(user_id))
    except Exception as e:
        logger.error(f"Error getting payment history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))